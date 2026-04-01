from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router(name=__name__)


@router.message(Command("help"))
async def help_command(message: Message) -> None:
    await message.answer(
        "Available commands:\n"
        "/start - start the bot\n"
        "/help - show this message\n"
        "/analytics - basic usage metrics"
    )
