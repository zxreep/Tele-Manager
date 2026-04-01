from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker

from bot.db.repositories import GroupRepository

logger = logging.getLogger(__name__)


class GroupService:
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def get_group_summary(self, chat_id: int) -> dict:
        now = datetime.now(tz=timezone.utc)
        try:
            async with self._session_factory() as session:
                repo = GroupRepository(session)
                summary = await repo.get_group_summary(chat_id, now=now)
                if summary["members"] == 0 and summary["active_today"] == 0:
                    logger.info("group.empty_summary", extra={"chat_id": chat_id})
                return summary
        except SQLAlchemyError:
            logger.exception("group.db_error", extra={"chat_id": chat_id})
            return {
                "chat_id": chat_id,
                "members": 0,
                "active_today": 0,
                "is_active": False,
                "last_seen_at": None,
                "error": "database_unavailable",
            }
