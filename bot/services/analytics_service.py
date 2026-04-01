from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker

from bot.db.repositories import AnalyticsRepository

logger = logging.getLogger(__name__)


class AnalyticsService:
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def get_snapshot(self, *, now: datetime | None = None) -> dict:
        current = now or datetime.now(tz=timezone.utc)
        daily_window = current - timedelta(days=1)
        weekly_window = current - timedelta(days=7)
        monthly_window = current - timedelta(days=30)

        try:
            async with self._session_factory() as session:
                repo = AnalyticsRepository(session)
                daily_active = await repo.count_users_since(daily_window)
                weekly_active = await repo.count_users_since(weekly_window)
                monthly_active = await repo.count_users_since(monthly_window)
                total_users = await repo.count_total_users()
                messages_processed = await repo.count_messages_since(daily_window)
                active_groups = await repo.count_groups(active_only=True, since=daily_window)
                trend = await repo.count_new_users_by_day(days=7, now=current)

            payload = {
                "daily_active_users": daily_active,
                "weekly_active_users": weekly_active,
                "monthly_active_users": monthly_active,
                "messages_processed": messages_processed,
                "total_users": total_users,
                "active_groups_24h": active_groups,
                "new_users_daily": trend,
                "aggregation_windows": {
                    "daily": daily_window.isoformat(),
                    "weekly": weekly_window.isoformat(),
                    "monthly": monthly_window.isoformat(),
                },
            }
            if total_users == 0:
                logger.info("analytics.empty_dataset", extra={"window": "30d"})
            return payload
        except SQLAlchemyError:
            logger.exception("analytics.db_error")
            return {
                "daily_active_users": 0,
                "weekly_active_users": 0,
                "monthly_active_users": 0,
                "messages_processed": 0,
                "total_users": 0,
                "active_groups_24h": 0,
                "new_users_daily": {},
                "error": "database_unavailable",
            }
