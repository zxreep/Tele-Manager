from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.services.group_service import GroupService

router = Router(name=__name__)
service = GroupService()


@router.message(Command("group_stats"))
async def group_stats(message: Message) -> None:
    stats = await service.get_group_summary(message.chat.id)
    await message.answer(f"Group summary: {stats}")
