"""Admin broadcast commands with batching, rate limiting, and delivery logging."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Protocol, cast

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message

from bot.handlers.group_management import GroupRepository, ManagedChat

router = Router(name="broadcast")


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


def _resolve_group_repository(bot: Bot, repo: GroupRepository | None) -> GroupRepository | None:
    if repo is not None:
        return repo
    return cast(GroupRepository | None, bot.get("group_repository"))


def _resolve_target_repository(
    bot: Bot,
    repo: BroadcastTargetRepository | None,
) -> BroadcastTargetRepository | None:
    if repo is not None:
        return repo
    return cast(BroadcastTargetRepository | None, bot.get("broadcast_target_repository"))


async def _run_batched_send(
    *,
    bot: Bot,
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
                except TelegramAPIError as exc:
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

                await asyncio.sleep(min_interval_seconds)

    await asyncio.gather(*(worker() for _ in range(max(1, workers))))
    return results


@router.message(Command("send_one"))
async def send_one_command(
    message: Message,
    is_admin: bool = False,
    broadcast_target_repository: BroadcastTargetRepository | None = None,
) -> None:
    """`/send_one <chat_id> <message>`"""

    if not is_admin:
        await message.answer("❌ This command is restricted to platform admins.")
        return

    payload = _split_command_payload(message.text or "")
    if not payload:
        await message.answer("Usage: /send_one <chat_id> <message>")
        return

    chat_id_raw, body = payload
    try:
        chat_id = int(chat_id_raw)
    except ValueError:
        await message.reply_text("chat_id must be an integer.")
        return

    target_repo = _resolve_target_repository(message.bot, broadcast_target_repository)
    if target_repo is None:
        await message.answer("⚠️ Broadcast target repository is not configured.")
        return

    result = await _run_batched_send(
        bot=message.bot,
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


@router.message(Command("send_many"))
async def send_many_command(
    message: Message,
    is_admin: bool = False,
    broadcast_target_repository: BroadcastTargetRepository | None = None,
) -> None:
    """`/send_many <chat_id,chat_id,...> <message>`"""

    if not is_admin:
        await message.answer("❌ This command is restricted to platform admins.")
        return

    payload = _split_command_payload(message.text or "")
    if not payload:
        await message.answer("Usage: /send_many <chat_id,chat_id,...> <message>")
        return

    chat_ids_raw, body = payload
    try:
        target_ids = [int(item.strip()) for item in chat_ids_raw.split(",") if item.strip()]
    except ValueError:
        await message.answer("All chat ids must be integers.")
        return

    if not target_ids:
        await message.answer("At least one chat id is required.")
        return

    target_repo = _resolve_target_repository(message.bot, broadcast_target_repository)
    if target_repo is None:
        await message.answer("⚠️ Broadcast target repository is not configured.")
        return

    results = await _run_batched_send(
        bot=message.bot,
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
    await message.answer(f"Completed send_many: success={success_count}, failed={failure_count}.")


@router.message(Command("broadcast_all"))
async def broadcast_all_command(
    message: Message,
    is_admin: bool = False,
    group_repository: GroupRepository | None = None,
    broadcast_target_repository: BroadcastTargetRepository | None = None,
) -> None:
    """`/broadcast_all <message>` to all active managed groups/channels."""

    if not is_admin:
        await message.answer("❌ This command is restricted to platform admins.")
        return

    raw = message.text or ""
    parts = raw.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: /broadcast_all <message>")
        return
    body = parts[1]

    group_repo = _resolve_group_repository(message.bot, group_repository)
    if group_repo is None:
        await message.answer("⚠️ Group repository is not configured.")
        return

    target_repo = _resolve_target_repository(message.bot, broadcast_target_repository)
    if target_repo is None:
        await message.answer("⚠️ Broadcast target repository is not configured.")
        return

    active_targets: list[ManagedChat] = list(await group_repo.list_active_chats())
    target_ids = [chat.chat_id for chat in active_targets]

    if not target_ids:
        await message.answer("No active targets available for broadcast.")
        return

    results = await _run_batched_send(
        bot=message.bot,
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
    await message.answer(
        f"Broadcast completed for {len(results)} targets: success={success_count}, failed={failure_count}."
    )
