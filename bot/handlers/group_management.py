"""Group and channel lifecycle management handlers (aiogram 3.x)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol, Sequence, cast

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Chat, ChatMemberUpdated, Message

router = Router(name="group_management")


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


def _resolve_group_repository(
    message_or_event: Message | ChatMemberUpdated,
    group_repository: GroupRepository | None,
) -> GroupRepository | None:
    if group_repository is not None:
        return group_repository

    bot = message_or_event.bot
    return cast(GroupRepository | None, bot.get("group_repository"))


@router.my_chat_member()
async def handle_bot_membership_change(
    event: ChatMemberUpdated,
    group_repository: GroupRepository | None = None,
) -> None:
    """Track when the bot is added/removed from groups or channels."""

    chat = event.chat
    if chat.type not in {"group", "supergroup", "channel"}:
        return

    repository = _resolve_group_repository(event, group_repository)
    if repository is None:
        return

    old_status = event.old_chat_member.status
    new_status = event.new_chat_member.status

    became_active = old_status in {"left", "kicked"} and new_status in {
        "member",
        "administrator",
    }
    became_inactive = new_status in {"left", "kicked"}

    if became_active:
        await repository.upsert_chat(_build_managed_chat(chat))
    elif became_inactive:
        await repository.mark_inactive(chat.id, _now())


@router.message(Command("groups"))
async def list_groups_command(
    message: Message,
    is_admin: bool = False,
    group_repository: GroupRepository | None = None,
) -> None:
    """Admin-only `/groups` command."""

    if not is_admin:
        await message.answer("❌ This command is restricted to platform admins.")
        return

    repository = _resolve_group_repository(message, group_repository)
    if repository is None:
        await message.answer("⚠️ Group repository is not configured.")
        return

    chats = await repository.list_active_chats()

    if not chats:
        await message.answer("No active groups/channels are currently registered.")
        return

    lines = ["Manageable groups/channels:"]
    for item in chats:
        handle = f"@{item.username}" if item.username else "(no public @username)"
        lines.append(f"• `{item.chat_id}` — {item.title} [{item.chat_type}] {handle}")

    await message.answer("\n".join(lines), parse_mode="Markdown")
