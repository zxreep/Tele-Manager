import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from bot.commands import register_bot_commands
from bot.config import get_settings
from bot.middlewares.auth import AuthMiddleware
from bot.middlewares.logging import LoggingMiddleware
from bot.middlewares.rate_limit import RateLimitMiddleware
from bot.handlers import load_registered_routers


logger = logging.getLogger(__name__)


async def on_startup(bot: Bot) -> None:
    logger.info("Bot started as @%s", (await bot.get_me()).username)


async def on_shutdown(bot: Bot) -> None:
    logger.info("Shutting down bot session")
    await bot.session.close()


async def main() -> None:
    settings = get_settings()

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.middleware(LoggingMiddleware())
    dp.callback_query.middleware(LoggingMiddleware())

    dp.message.middleware(AuthMiddleware(admin_ids=set(settings.admin_ids)))
    dp.callback_query.middleware(AuthMiddleware(admin_ids=set(settings.admin_ids)))

    dp.message.middleware(RateLimitMiddleware())

    for router in load_registered_routers():
        dp.include_router(router)

    await register_bot_commands(bot, settings.admin_ids)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
