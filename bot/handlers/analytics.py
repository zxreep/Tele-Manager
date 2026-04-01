from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.services.analytics_service import AnalyticsService
from bot.utils import escape_html

router = Router(name=__name__)
service = AnalyticsService()


@router.message(Command("analytics"))
async def analytics_report(message: Message) -> None:
    report = await service.get_snapshot()
    await message.answer(f"Analytics snapshot: <code>{escape_html(report)}</code>")
