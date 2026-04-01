import logging
import os
from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional, Protocol, Set

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.exc import SQLAlchemyError

from bot.services.analytics_service import AnalyticsService
from bot.services.premium_service import PremiumService

router = Router(name="admin_panel")
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class UserAnalytics:
    total_users: int
    active_today: int
    active_7d: int
    active_30d: int
    new_users_daily: Dict[date, int]


@dataclass(frozen=True)
class GroupAnalytics:
    active_groups: int
    active_channels: int
    broadcast_sent: int
    broadcast_delivered: int
    broadcast_failed: int


class AdminPanelStorage(Protocol):
    async def get_user_analytics(self) -> UserAnalytics: ...

    async def get_group_analytics(self) -> GroupAnalytics: ...

    async def premium_add(self, user_id: int, days: int) -> None: ...

    async def premium_remove(self, user_id: int) -> bool: ...

    async def premium_list(self) -> List[int]: ...


class ServiceBackedAdminPanelStorage:
    def __init__(self, premium_service: PremiumService, analytics_service: AnalyticsService) -> None:
        self._premium_service = premium_service
        self._analytics_service = analytics_service

    async def get_user_analytics(self) -> UserAnalytics:
        snapshot = await self._analytics_service.get_snapshot()
        return UserAnalytics(
            total_users=snapshot.get("total_users", 0),
            active_today=snapshot.get("daily_active_users", 0),
            active_7d=snapshot.get("weekly_active_users", 0),
            active_30d=snapshot.get("monthly_active_users", 0),
            new_users_daily=snapshot.get("new_users_daily", {}),
        )

    async def get_group_analytics(self) -> GroupAnalytics:
        snapshot = await self._analytics_service.get_snapshot()
        active_groups = snapshot.get("active_groups_24h", 0)
        return GroupAnalytics(
            active_groups=active_groups,
            active_channels=0,
            broadcast_sent=0,
            broadcast_delivered=0,
            broadcast_failed=0,
        )

    async def premium_add(self, user_id: int, days: int) -> None:
        await self._premium_service.grant_premium(user_id=user_id, days=days)

    async def premium_remove(self, user_id: int) -> bool:
        return await self._premium_service.revoke_premium(user_id=user_id)

    async def premium_list(self) -> List[int]:
        return await self._premium_service.list_active_premium()


storage: AdminPanelStorage | None = None


def set_admin_panel_storage(custom_storage: AdminPanelStorage) -> None:
    global storage
    storage = custom_storage


def _parse_superadmin_ids(raw_value: Optional[str]) -> Set[int]:
    if not raw_value:
        return set()

    result: Set[int] = set()
    for part in raw_value.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            result.add(int(part))
        except ValueError:
            continue
    return result


SUPERADMIN_IDS = _parse_superadmin_ids(os.getenv("SUPERADMIN_IDS"))


def _is_superadmin(user_id: Optional[int]) -> bool:
    return bool(user_id and user_id in SUPERADMIN_IDS)


async def _guard_admin(message: Message) -> bool:
    if _is_superadmin(message.from_user.id if message.from_user else None):
        return True

    await message.answer("❌ Access denied. Super-admin only.")
    return False


async def _guard_admin_callback(query: CallbackQuery) -> bool:
    if _is_superadmin(query.from_user.id if query.from_user else None):
        return True

    await query.answer("Access denied", show_alert=True)
    return False


def _admin_panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="User Analytics", callback_data="admin:user_analytics")],
            [InlineKeyboardButton(text="Group Analytics", callback_data="admin:group_analytics")],
            [InlineKeyboardButton(text="Broadcast", callback_data="admin:broadcast")],
            [InlineKeyboardButton(text="Premium Members", callback_data="admin:premium_members")],
        ]
    )


def _back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="admin:root")]]
    )


def _format_daily_trend(daily_values: Dict[date, int]) -> str:
    if not daily_values:
        return "No daily signup data yet."

    lines: List[str] = []
    for day, value in sorted(daily_values.items()):
        lines.append(f"• {day.isoformat()}: {value}")
    return "\n".join(lines)


def _get_storage() -> AdminPanelStorage | None:
    return storage


@router.message(Command("admin"))
async def admin_panel(message: Message) -> None:
    if not await _guard_admin(message):
        return

    await message.answer("🛠 <b>Admin Panel</b>", reply_markup=_admin_panel_keyboard())


@router.callback_query(F.data == "admin:root")
async def admin_panel_root(query: CallbackQuery) -> None:
    if not await _guard_admin_callback(query):
        return

    await query.message.edit_text("🛠 <b>Admin Panel</b>", reply_markup=_admin_panel_keyboard())
    await query.answer()


@router.callback_query(F.data == "admin:user_analytics")
async def user_analytics(query: CallbackQuery) -> None:
    if not await _guard_admin_callback(query):
        return

    current_storage = _get_storage()
    if current_storage is None:
        await query.answer("Storage is not configured.", show_alert=True)
        return

    try:
        data = await current_storage.get_user_analytics()
    except SQLAlchemyError:
        logger.exception("admin.user_analytics.db_error")
        await query.answer("User analytics unavailable (DB error).", show_alert=True)
        return

    text = (
        "👤 <b>User Analytics</b>\n\n"
        f"Total users: <b>{data.total_users}</b>\n"
        f"Active today: <b>{data.active_today}</b>\n"
        f"Active 7d: <b>{data.active_7d}</b>\n"
        f"Active 30d: <b>{data.active_30d}</b>\n\n"
        "📈 <b>New users trend (daily)</b>\n"
        f"{_format_daily_trend(data.new_users_daily)}"
    )

    await query.message.edit_text(text, reply_markup=_back_keyboard())
    await query.answer()


@router.callback_query(F.data == "admin:group_analytics")
async def group_analytics(query: CallbackQuery) -> None:
    if not await _guard_admin_callback(query):
        return

    current_storage = _get_storage()
    if current_storage is None:
        await query.answer("Storage is not configured.", show_alert=True)
        return

    try:
        data = await current_storage.get_group_analytics()
    except SQLAlchemyError:
        logger.exception("admin.group_analytics.db_error")
        await query.answer("Group analytics unavailable (DB error).", show_alert=True)
        return

    text = (
        "👥 <b>Group Analytics</b>\n\n"
        f"Active groups: <b>{data.active_groups}</b>\n"
        f"Active channels: <b>{data.active_channels}</b>\n\n"
        "📣 <b>Broadcast delivery stats</b>\n"
        f"Sent: <b>{data.broadcast_sent}</b>\n"
        f"Delivered: <b>{data.broadcast_delivered}</b>\n"
        f"Failed: <b>{data.broadcast_failed}</b>"
    )

    await query.message.edit_text(text, reply_markup=_back_keyboard())
    await query.answer()


@router.callback_query(F.data == "admin:broadcast")
async def broadcast_page(query: CallbackQuery) -> None:
    if not await _guard_admin_callback(query):
        return

    await query.message.edit_text(
        "📣 <b>Broadcast</b>\n\nUse your existing broadcast command/workflow from here.",
        reply_markup=_back_keyboard(),
    )
    await query.answer()


@router.callback_query(F.data == "admin:premium_members")
async def premium_members_page(query: CallbackQuery) -> None:
    if not await _guard_admin_callback(query):
        return

    current_storage = _get_storage()
    if current_storage is None:
        await query.answer("Storage is not configured.", show_alert=True)
        return

    try:
        members = await current_storage.premium_list()
    except SQLAlchemyError:
        logger.exception("admin.premium_list.db_error")
        await query.answer("Premium list unavailable (DB error).", show_alert=True)
        return

    body = "\n".join(f"• <code>{user_id}</code>" for user_id in members) if members else "No premium users."

    await query.message.edit_text(
        "💎 <b>Premium Members</b>\n\n"
        "Commands:\n"
        "• <code>/premium_add &lt;user_id&gt; &lt;days&gt;</code>\n"
        "• <code>/premium_remove &lt;user_id&gt;</code>\n"
        "• <code>/premium_list</code>\n\n"
        f"Current list:\n{body}",
        reply_markup=_back_keyboard(),
    )
    await query.answer()


@router.message(Command("premium_add"))
async def premium_add(message: Message) -> None:
    if not await _guard_admin(message):
        return

    current_storage = _get_storage()
    if current_storage is None:
        await message.answer("Storage is not configured.")
        return

    parts = message.text.split(maxsplit=2) if message.text else []
    if len(parts) != 3:
        await message.answer("Usage: /premium_add <user_id> <days>")
        return

    try:
        user_id = int(parts[1])
        days = int(parts[2])
    except ValueError:
        await message.answer("user_id and days must be integers.")
        return

    if days <= 0:
        await message.answer("days must be greater than 0.")
        return

    try:
        await current_storage.premium_add(user_id=user_id, days=days)
    except SQLAlchemyError:
        logger.exception("admin.premium_add.db_error", extra={"user_id": user_id, "days": days})
        await message.answer("Could not add premium due to DB error.")
        return

    await message.answer(f"✅ Premium added for <code>{user_id}</code> for <b>{days}</b> days.")


@router.message(Command("premium_remove"))
async def premium_remove(message: Message) -> None:
    if not await _guard_admin(message):
        return

    current_storage = _get_storage()
    if current_storage is None:
        await message.answer("Storage is not configured.")
        return

    parts = message.text.split(maxsplit=1) if message.text else []
    if len(parts) != 2:
        await message.answer("Usage: /premium_remove <user_id>")
        return

    try:
        user_id = int(parts[1])
    except ValueError:
        await message.answer("user_id must be an integer.")
        return

    try:
        removed = await current_storage.premium_remove(user_id=user_id)
    except SQLAlchemyError:
        logger.exception("admin.premium_remove.db_error", extra={"user_id": user_id})
        await message.answer("Could not remove premium due to DB error.")
        return

    if not removed:
        await message.answer(f"ℹ️ User {html_code(user_id)} was not premium.")
        return

    await message.answer(f"✅ Premium removed for {html_code(user_id)}.")


@router.message(Command("premium_list"))
async def premium_list(message: Message) -> None:
    if not await _guard_admin(message):
        return

    current_storage = _get_storage()
    if current_storage is None:
        await message.answer("Storage is not configured.")
        return

    try:
        members = await current_storage.premium_list()
    except SQLAlchemyError:
        logger.exception("admin.premium_list_command.db_error")
        await message.answer("Could not fetch premium users due to DB error.")
        return

    if not members:
        await message.answer("No premium users.")
        return

    formatted = "\n".join(f"• {html_code(user_id)}" for user_id in members)
    await message.answer(f"💎 <b>Premium users</b>\n{formatted}")
