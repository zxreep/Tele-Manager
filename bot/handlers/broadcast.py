"""Admin broadcast commands with batching, rate limiting, and delivery logging."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Protocol, Sequence

from telegram import Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from bot.handlers.group_management import AdminVerifier, GroupRepository, ManagedChat
from bot.utils import escape_html, html_code


@dataclass(slots=True)
class BroadcastResult:
    chat_id: int
    success: bool
    error: str | None
    sent_at: datetime


class BroadcastTargetRepository(Protocol):
    """Persistence contract for per-target broadcast logging."""

    async def log_broadcast_target(
        self,
        *,
        source_command: str,
        chat_id: int,
        message: str,
        success: bool,
        error: str | None,
        sent_at: datetime,
    ) -> None:
        """Write one delivery attempt row in `broadcast_targets`."""


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _split_command_payload(text: str) -> tuple[str, str] | None:
    parts = text.split(maxsplit=2)
    if len(parts) < 3:
        return None
    return parts[1], parts[2]


async def _run_batched_send(
    *,
    bot,
    target_ids: Iterable[int],
    message: str,
    target_repo: BroadcastTargetRepository,
    source_command: str,
    batch_size: int,
    workers: int,
    min_interval_seconds: float,
) -> list[BroadcastResult]:
    """Send messages in bounded async batches and collect target-level outcomes."""

    queue: asyncio.Queue[int] = asyncio.Queue()
    for chat_id in target_ids:
        queue.put_nowait(chat_id)

    results: list[BroadcastResult] = []
    lock = asyncio.Lock()

    async def worker() -> None:
        while not queue.empty():
            chunk: list[int] = []
            for _ in range(batch_size):
                if queue.empty():
                    break
                chunk.append(queue.get_nowait())

            for chat_id in chunk:
                sent_at = _now()
                success = True
                error: str | None = None

                try:
                    await bot.send_message(chat_id=chat_id, text=message)
                except TelegramError as exc:
                    success = False
                    error = str(exc)

                await target_repo.log_broadcast_target(
                    source_command=source_command,
                    chat_id=chat_id,
                    message=message,
                    success=success,
                    error=error,
                    sent_at=sent_at,
                )

                async with lock:
                    results.append(
                        BroadcastResult(
                            chat_id=chat_id,
                            success=success,
                            error=error,
                            sent_at=sent_at,
                        )
                    )

                # simple global send pacing to reduce risk of Telegram flood limits
                await asyncio.sleep(min_interval_seconds)

    await asyncio.gather(*(worker() for _ in range(max(1, workers))))
    return results


async def _ensure_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    message = update.effective_message
    user = update.effective_user
    if not message or not user:
        return False

    verifier: AdminVerifier = context.application.bot_data["admin_verifier"]
    if await verifier.is_platform_admin(user.id):
        return True

    await message.reply_text("❌ This command is restricted to platform admins.")
    return False


async def send_one_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """`/send_one <chat_id> <message>`"""

    message = update.effective_message
    if not message:
        return

    if not await _ensure_admin(update, context):
        return

    payload = _split_command_payload(message.text or "")
    if not payload:
        await message.reply_text("Usage: /send_one <chat_id> <message>")
        return

    chat_id_raw, body = payload
    try:
        chat_id = int(chat_id_raw)
    except ValueError:
        await message.reply_text("chat_id must be an integer.")
        return

    target_repo: BroadcastTargetRepository = context.application.bot_data[
        "broadcast_target_repository"
    ]

    result = await _run_batched_send(
        bot=context.bot,
        target_ids=[chat_id],
        message=body,
        target_repo=target_repo,
        source_command="send_one",
        batch_size=1,
        workers=1,
        min_interval_seconds=0.05,
    )

    if result and result[0].success:
        await message.reply_text(f"✅ Sent to {html_code(chat_id)}", parse_mode="HTML")
    else:
        err = result[0].error if result else "unknown error"
        await message.reply_text(
            f"❌ Failed for {html_code(chat_id)}: <code>{escape_html(err)}</code>",
            parse_mode="HTML",
        )


async def send_many_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """`/send_many <chat_id,chat_id,...> <message>`"""

    message = update.effective_message
    if not message:
        return

    if not await _ensure_admin(update, context):
        return

    payload = _split_command_payload(message.text or "")
    if not payload:
        await message.reply_text("Usage: /send_many <chat_id,chat_id,...> <message>")
        return

    chat_ids_raw, body = payload
    try:
        target_ids = [int(item.strip()) for item in chat_ids_raw.split(",") if item.strip()]
    except ValueError:
        await message.reply_text("All chat ids must be integers.")
        return

    if not target_ids:
        await message.reply_text("At least one chat id is required.")
        return

    target_repo: BroadcastTargetRepository = context.application.bot_data[
        "broadcast_target_repository"
    ]

    results = await _run_batched_send(
        bot=context.bot,
        target_ids=target_ids,
        message=body,
        target_repo=target_repo,
        source_command="send_many",
        batch_size=10,
        workers=2,
        min_interval_seconds=0.05,
    )

    success_count = sum(1 for row in results if row.success)
    failure_count = len(results) - success_count
    await message.reply_text(
        f"Completed send_many: success={success_count}, failed={failure_count}."
    )


async def broadcast_all_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """`/broadcast_all <message>` to all active managed groups/channels."""

    message = update.effective_message
    if not message:
        return

    if not await _ensure_admin(update, context):
        return

    raw = message.text or ""
    parts = raw.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply_text("Usage: /broadcast_all <message>")
        return
    body = parts[1]

    group_repo: GroupRepository = context.application.bot_data["group_repository"]
    active_targets: Sequence[ManagedChat] = await group_repo.list_active_chats()
    target_ids = [chat.chat_id for chat in active_targets]

    if not target_ids:
        await message.reply_text("No active targets available for broadcast.")
        return

    target_repo: BroadcastTargetRepository = context.application.bot_data[
        "broadcast_target_repository"
    ]

    results = await _run_batched_send(
        bot=context.bot,
        target_ids=target_ids,
        message=body,
        target_repo=target_repo,
        source_command="broadcast_all",
        batch_size=20,
        workers=3,
        min_interval_seconds=0.05,
    )

    success_count = sum(1 for row in results if row.success)
    failure_count = len(results) - success_count
    await message.reply_text(
        f"Broadcast completed for {len(results)} targets: "
        f"success={success_count}, failed={failure_count}."
    )
