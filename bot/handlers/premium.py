from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.services.premium_service import PremiumService

router = Router(name=__name__)
service = PremiumService()


@router.message(Command("premium"))
async def premium_status(message: Message) -> None:
    active = await service.is_premium(message.from_user.id)
    await message.answer("Premium active ✅" if active else "Premium inactive ❌")
