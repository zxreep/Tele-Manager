import time
from collections.abc import Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject


class RateLimitMiddleware(BaseMiddleware):
    def __init__(self, interval_seconds: float = 0.5) -> None:
        self.interval_seconds = interval_seconds
        self._last_seen: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict], Awaitable],
        event: TelegramObject,
        data: dict,
    ):
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
            now = time.monotonic()
            previous = self._last_seen.get(user_id, 0)
            if now - previous < self.interval_seconds:
                await event.answer("Too many requests. Please slow down.")
                return None
            self._last_seen[user_id] = now

        return await handler(event, data)
