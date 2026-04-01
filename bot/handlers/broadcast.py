from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.services.broadcast_service import BroadcastService

router = Router(name=__name__)
service = BroadcastService()


@router.message(Command("broadcast"))
async def broadcast(message: Message) -> None:
    payload = message.text.replace("/broadcast", "", 1).strip() if message.text else ""
    if not payload:
        await message.answer("Usage: /broadcast <message>")
        return

    sent = await service.broadcast_text(payload)
    await message.answer(f"Broadcast queued for {sent} recipients")
