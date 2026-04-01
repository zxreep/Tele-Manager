from __future__ import annotations

from dataclasses import dataclass

from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault


@dataclass(frozen=True)
class CommandInfo:
    command: str
    description: str
    admin_only: bool = False


COMMANDS: tuple[CommandInfo, ...] = (
    CommandInfo("start", "Show welcome message and capabilities"),
    CommandInfo("help", "Show all available commands"),
    CommandInfo("analytics", "View usage metrics snapshot"),
    CommandInfo("premium", "Check your premium status"),
    CommandInfo("admin", "Open admin panel", admin_only=True),
)


def _to_bot_commands(commands: tuple[CommandInfo, ...]) -> list[BotCommand]:
    return [BotCommand(command=item.command, description=item.description) for item in commands]


def build_capabilities_message(*, is_admin: bool) -> str:
    user_commands = [item for item in COMMANDS if not item.admin_only]

    lines = [
        "👋 <b>Welcome to Tele-Manager</b>",
        "",
        "Here is what I can do:",
        *[f"• <code>/{item.command}</code> — {item.description}" for item in user_commands],
    ]

    if is_admin:
        admin_commands = [item for item in COMMANDS if item.admin_only]
        lines.extend(
            [
                "",
                "🛡 <b>Admin capabilities</b>",
                *[f"• <code>/{item.command}</code> — {item.description}" for item in admin_commands],
            ]
        )
    else:
        lines.extend(
            [
                "",
                "Need advanced controls? Ask an admin for access.",
            ]
        )

    lines.extend(["", "Use /help anytime to see this list again."])
    return "\n".join(lines)


async def register_bot_commands(bot: Bot, admin_ids: list[int]) -> None:
    user_commands = tuple(item for item in COMMANDS if not item.admin_only)
    admin_commands = tuple(COMMANDS)

    await bot.set_my_commands(_to_bot_commands(user_commands), scope=BotCommandScopeDefault())

    for admin_id in admin_ids:
        await bot.set_my_commands(
            _to_bot_commands(admin_commands),
            scope=BotCommandScopeChat(chat_id=admin_id),
        )
