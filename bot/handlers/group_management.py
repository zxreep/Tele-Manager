"""Group and channel lifecycle management handlers.

This module focuses on:
- tracking when the bot is added to/removed from groups and channels;
- exposing an admin-only `/groups` command to list manageable targets.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol, Sequence

from telegram import Chat, Update
from telegram.ext import ContextTypes


@dataclass(slots=True)
class ManagedChat:
    """Stored metadata for a manageable group/channel."""

    chat_id: int
    title: str
    chat_type: str
    username: str | None
    invite_link: str | None
    active: bool
    updated_at: datetime


class GroupRepository(Protocol):
    """Persistence contract used by handlers in this module."""

    async def upsert_chat(self, chat: ManagedChat) -> None:
        """Create or update the managed chat metadata."""

    async def mark_inactive(self, chat_id: int, at: datetime) -> None:
        """Mark an existing managed chat as inactive."""

    async def list_active_chats(self) -> Sequence[ManagedChat]:
        """Return active managed chats/channels."""


class AdminVerifier(Protocol):
    """Contract for platform-admin validation."""

    async def is_platform_admin(self, user_id: int) -> bool:
        """Return True when the sender is allowed to run admin commands."""


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _build_managed_chat(chat: Chat) -> ManagedChat:
    return ManagedChat(
        chat_id=chat.id,
        title=chat.title or chat.full_name or str(chat.id),
        chat_type=chat.type,
        username=chat.username,
        invite_link=getattr(chat, "invite_link", None),
        active=True,
        updated_at=_now(),
    )


async def handle_bot_membership_change(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Track when the bot is added/removed from groups or channels.

    Expected context values:
    - `group_repository`: implementation of :class:`GroupRepository`.
    """

    membership_update = update.my_chat_member
    if not membership_update:
        return

    chat = membership_update.chat
    if chat.type not in {"group", "supergroup", "channel"}:
        return

    repository: GroupRepository = context.application.bot_data["group_repository"]

    old_status = membership_update.old_chat_member.status
    new_status = membership_update.new_chat_member.status

    became_active = old_status in {"left", "kicked"} and new_status in {
        "member",
        "administrator",
    }
    became_inactive = new_status in {"left", "kicked"}

    if became_active:
        await repository.upsert_chat(_build_managed_chat(chat))
    elif became_inactive:
        await repository.mark_inactive(chat.id, _now())


async def list_groups_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin-only `/groups` command.

    Expected context values:
    - `group_repository`: implementation of :class:`GroupRepository`.
    - `admin_verifier`: implementation of :class:`AdminVerifier`.
    """

    message = update.effective_message
    user = update.effective_user
    if not message or not user:
        return

    verifier: AdminVerifier = context.application.bot_data["admin_verifier"]
    is_admin = await verifier.is_platform_admin(user.id)
    if not is_admin:
        await message.reply_text("❌ This command is restricted to platform admins.")
        return

    repository: GroupRepository = context.application.bot_data["group_repository"]
    chats = await repository.list_active_chats()

    if not chats:
        await message.reply_text("No active groups/channels are currently registered.")
        return

    lines = ["Manageable groups/channels:"]
    for item in chats:
        handle = f"@{item.username}" if item.username else "(no public @username)"
        lines.append(f"• `{item.chat_id}` — {item.title} [{item.chat_type}] {handle}")

    await message.reply_text("\n".join(lines), parse_mode="Markdown")
