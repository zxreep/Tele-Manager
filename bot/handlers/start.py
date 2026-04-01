from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot.commands import build_capabilities_message

router = Router(name=__name__)


@router.message(CommandStart())
async def start_command(message: Message, is_admin: bool = False) -> None:
    await message.answer(build_capabilities_message(is_admin=is_admin))
