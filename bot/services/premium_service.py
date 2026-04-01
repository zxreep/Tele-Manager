from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker

from bot.db.repositories import PremiumRepository


logger = logging.getLogger(__name__)


class PremiumService:
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def is_premium(self, user_id: int, *, at: datetime | None = None) -> bool:
        now = at or datetime.now(tz=timezone.utc)
        try:
            async with self._session_factory() as session:
                repo = PremiumRepository(session)
                user = await repo.get_user(user_id)

                if user is None:
                    logger.info("premium.missing_user", extra={"user_id": user_id})
                    return False

                if not user.is_premium or user.premium_until is None:
                    return False

                is_active = user.premium_until >= now
                if not is_active:
                    logger.info(
                        "premium.expired",
                        extra={"user_id": user_id, "premium_until": user.premium_until.isoformat()},
                    )
                return is_active
        except SQLAlchemyError:
            logger.exception("premium.db_error", extra={"user_id": user_id})
            return False

    async def grant_premium(self, user_id: int, days: int, *, starts_at: datetime | None = None) -> datetime:
        effective_start = starts_at or datetime.now(tz=timezone.utc)
        # Business rule: extend from current expiry if still active, otherwise from now.
        try:
            async with self._session_factory() as session:
                repo = PremiumRepository(session)
                existing = await repo.get_user(user_id)
                base = effective_start
                if existing and existing.premium_until and existing.premium_until > effective_start:
                    base = existing.premium_until

                expires_at = base + timedelta(days=days)
                await repo.upsert_premium(user_id, expires_at)
                await session.commit()
                logger.info(
                    "premium.granted",
                    extra={"user_id": user_id, "days": days, "premium_until": expires_at.isoformat()},
                )
                return expires_at
        except SQLAlchemyError:
            logger.exception("premium.grant_db_error", extra={"user_id": user_id, "days": days})
            raise

    async def revoke_premium(self, user_id: int) -> bool:
        try:
            async with self._session_factory() as session:
                repo = PremiumRepository(session)
                removed = await repo.clear_premium(user_id)
                if removed:
                    await session.commit()
                    logger.info("premium.revoked", extra={"user_id": user_id})
                else:
                    await session.rollback()
                    logger.info("premium.revoke_noop", extra={"user_id": user_id})
                return removed
        except SQLAlchemyError:
            logger.exception("premium.revoke_db_error", extra={"user_id": user_id})
            raise

    async def list_active_premium(self, *, at: datetime | None = None) -> list[int]:
        now = at or datetime.now(tz=timezone.utc)
        try:
            async with self._session_factory() as session:
                repo = PremiumRepository(session)
                users = await repo.list_active_premium_users(now)
                if not users:
                    logger.info("premium.empty_list")
                return users
        except SQLAlchemyError:
            logger.exception("premium.list_db_error")
            raise
