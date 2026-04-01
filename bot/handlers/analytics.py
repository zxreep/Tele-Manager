from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.services.analytics_service import AnalyticsService
from bot.utils import escape_html

router = Router(name=__name__)
service: AnalyticsService | None = None


def set_analytics_service(custom_service: AnalyticsService) -> None:
    global service
    service = custom_service


@router.message(Command("analytics"))
async def analytics_report(message: Message) -> None:
    if service is None:
        await message.answer("Analytics service is unavailable right now. Please try later.")
        return

    report = await service.get_snapshot()
    if report.get("error"):
        await message.answer("Analytics temporarily unavailable due to a database issue.")
        return

    await message.answer(f"Analytics snapshot: {report}")
