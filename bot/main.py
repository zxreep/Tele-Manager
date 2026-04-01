import asyncio
import importlib
import logging
import pkgutil
from collections.abc import Iterable

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.commands import register_bot_commands
from bot.config import get_settings
from bot.db.session import SessionLocal
from bot.handlers.admin_panel import ServiceBackedAdminPanelStorage, set_admin_panel_storage
from bot.handlers.analytics import set_analytics_service
from bot.handlers.premium import set_premium_service
from bot.middlewares.auth import AuthMiddleware
from bot.middlewares.logging import LoggingMiddleware
from bot.middlewares.rate_limit import RateLimitMiddleware
from bot.services.analytics_service import AnalyticsService
from bot.services.group_service import GroupService
from bot.services.premium_service import PremiumService

logger = logging.getLogger(__name__)


def discover_routers(package_name: str = "bot.handlers") -> Iterable:
    package = importlib.import_module(package_name)

    for _, module_name, is_pkg in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
        if is_pkg:
            continue
        module = importlib.import_module(module_name)
        router = getattr(module, "router", None)
        if router is not None:
            yield router


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

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=MemoryStorage())

    premium_service = PremiumService(session_factory=SessionLocal)
    analytics_service = AnalyticsService(session_factory=SessionLocal)
    _group_service = GroupService(session_factory=SessionLocal)

    set_premium_service(premium_service)
    set_analytics_service(analytics_service)
    set_admin_panel_storage(ServiceBackedAdminPanelStorage(premium_service, analytics_service))

    dp.message.middleware(LoggingMiddleware())
    dp.callback_query.middleware(LoggingMiddleware())

    dp.message.middleware(AuthMiddleware(admin_ids=set(settings.admin_ids)))
    dp.callback_query.middleware(AuthMiddleware(admin_ids=set(settings.admin_ids)))

    dp.message.middleware(RateLimitMiddleware())

    for router in discover_routers():
        dp.include_router(router)

    await register_bot_commands(bot, settings.admin_ids)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
