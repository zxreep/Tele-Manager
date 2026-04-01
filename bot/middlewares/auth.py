from collections.abc import Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject


class AuthMiddleware(BaseMiddleware):
    def __init__(self, admin_ids: set[int] | None = None) -> None:
        self.admin_ids = admin_ids or set()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict], Awaitable],
        event: TelegramObject,
        data: dict,
    ):
        user = data.get("event_from_user")
        data["is_admin"] = bool(user and user.id in self.admin_ids)
        return await handler(event, data)
