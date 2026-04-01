from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Group, User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class PremiumRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_user(self, telegram_id: int) -> User | None:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_active_premium_users(self, at: datetime) -> list[int]:
        stmt = (
            select(User.telegram_id)
            .where(User.is_premium.is_(True), User.premium_until.is_not(None), User.premium_until >= at)
            .order_by(User.telegram_id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def upsert_premium(self, telegram_id: int, expires_at: datetime) -> None:
        user = await self.get_user(telegram_id)
        if user is None:
            user = User(
                telegram_id=telegram_id,
                is_premium=True,
                premium_until=expires_at,
                last_seen_at=datetime.now(tz=timezone.utc),
            )
            self.session.add(user)
        else:
            user.is_premium = True
            user.premium_until = expires_at

    async def clear_premium(self, telegram_id: int) -> bool:
        user = await self.get_user(telegram_id)
        if user is None or not user.is_premium:
            return False

        user.is_premium = False
        user.premium_until = None
        return True


class AnalyticsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def count_users_since(self, start_at: datetime) -> int:
        stmt = select(func.count(User.id)).where(User.last_seen_at >= start_at)
        result = await self.session.execute(stmt)
        return int(result.scalar_one() or 0)

    async def count_total_users(self) -> int:
        result = await self.session.execute(select(func.count(User.id)))
        return int(result.scalar_one() or 0)

    async def count_messages_since(self, start_at: datetime) -> int:
        # Fallback metric: user activity updates tracked by last_seen_at window.
        return await self.count_users_since(start_at)

    async def count_groups(self, *, active_only: bool, since: datetime | None = None) -> int:
        stmt = select(func.count(Group.id))
        if active_only:
            stmt = stmt.where(Group.is_active.is_(True))
        if since is not None:
            stmt = stmt.where(Group.last_seen_at >= since)
        result = await self.session.execute(stmt)
        return int(result.scalar_one() or 0)

    async def count_new_users_by_day(self, *, days: int, now: datetime) -> dict[datetime.date, int]:
        start_at = now - timedelta(days=days)
        day_bucket = func.date_trunc("day", User.created_at)
        stmt = (
            select(day_bucket.label("day"), func.count(User.id).label("count"))
            .where(User.created_at >= start_at)
            .group_by(day_bucket)
            .order_by(day_bucket)
        )
        result = await self.session.execute(stmt)

        trend: dict[datetime.date, int] = {}
        for day, count in result.all():
            trend[day.date()] = int(count)
        return trend


class GroupRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_group_summary(self, chat_id: int, *, now: datetime) -> dict:
        group_stmt = select(Group).where(Group.telegram_chat_id == chat_id)
        group_result = await self.session.execute(group_stmt)
        group = group_result.scalar_one_or_none()
        if group is None:
            return {
                "chat_id": chat_id,
                "members": 0,
                "active_today": 0,
                "is_active": False,
                "last_seen_at": None,
            }

        active_window_start = now - timedelta(days=1)
        active_today = 1 if group.last_seen_at and group.last_seen_at >= active_window_start else 0
        return {
            "chat_id": chat_id,
            "members": 0,
            "active_today": active_today,
            "is_active": bool(group.is_active),
            "last_seen_at": group.last_seen_at,
        }
