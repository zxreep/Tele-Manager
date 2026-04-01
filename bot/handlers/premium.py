from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.services.premium_service import PremiumService

router = Router(name=__name__)
service: PremiumService | None = None


def set_premium_service(custom_service: PremiumService) -> None:
    global service
    service = custom_service


@router.message(Command("premium"))
async def premium_status(message: Message) -> None:
    if service is None:
        await message.answer("Premium service is unavailable right now. Please try later.")
        return

    if not message.from_user:
        await message.answer("Unable to identify user.")
        return

    active = await service.is_premium(message.from_user.id)
    await message.answer("Premium active ✅" if active else "Premium inactive ❌")
