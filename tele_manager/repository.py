from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from tele_manager.models import Group, User


@dataclass
class AnalyticsCounters:
    dau: int
    wau: int
    group_count: int
    active_users: int


def upsert_user_on_activity(
    db: Session,
    telegram_id: int,
    username: str | None = None,
    is_admin: bool | None = None,
    is_premium: bool | None = None,
    seen_at: datetime | None = None,
) -> User:
    seen_at = seen_at or datetime.now(timezone.utc)
    user = db.scalar(select(User).where(User.telegram_id == telegram_id))

    if user is None:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_seen_at=seen_at,
            last_seen_at=seen_at,
            is_admin=is_admin if is_admin is not None else False,
            is_premium=is_premium if is_premium is not None else False,
        )
        db.add(user)
    else:
        user.last_seen_at = seen_at
        if username is not None:
            user.username = username
        if is_admin is not None:
            user.is_admin = is_admin
        if is_premium is not None:
            user.is_premium = is_premium

    db.flush()
    return user


def upsert_group_on_activity(
    db: Session,
    chat_id: int,
    title: str | None,
    group_type: str,
    active: bool = True,
    seen_at: datetime | None = None,
) -> Group:
    seen_at = seen_at or datetime.now(timezone.utc)
    group = db.scalar(select(Group).where(Group.chat_id == chat_id))

    if group is None:
        group = Group(chat_id=chat_id, title=title, type=group_type, added_at=seen_at, active=active)
        db.add(group)
    else:
        group.title = title
        group.type = group_type
        group.active = active

    db.flush()
    return group


def get_user_flags(db: Session, telegram_id: int) -> tuple[bool, bool]:
    row = db.execute(
        select(User.is_admin, User.is_premium).where(User.telegram_id == telegram_id)
    ).one_or_none()
    if row is None:
        return False, False
    return row[0], row[1]


def list_broadcast_target_groups(db: Session, target_type: str) -> list[Group]:
    query = select(Group).where(Group.active.is_(True))
    if target_type in {"group", "supergroup", "channel"}:
        query = query.where(Group.type == target_type)
    elif target_type == "all":
        query = query.where(Group.type.in_(["group", "supergroup", "channel"]))
    return list(db.scalars(query.order_by(Group.id)))


def get_analytics_counters(db: Session, now: datetime | None = None) -> AnalyticsCounters:
    now = now or datetime.now(timezone.utc)
    day_start = now - timedelta(days=1)
    week_start = now - timedelta(days=7)

    dau = db.scalar(select(func.count(User.id)).where(User.last_seen_at >= day_start)) or 0
    wau = db.scalar(select(func.count(User.id)).where(User.last_seen_at >= week_start)) or 0
    group_count = db.scalar(select(func.count(Group.id))) or 0
    active_users = db.scalar(select(func.count(User.id)).where(User.last_seen_at >= week_start)) or 0

    return AnalyticsCounters(dau=dau, wau=wau, group_count=group_count, active_users=active_users)
