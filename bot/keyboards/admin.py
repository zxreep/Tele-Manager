from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def admin_panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Broadcast", callback_data="admin:broadcast")],
            [InlineKeyboardButton(text="Analytics", callback_data="admin:analytics")],
            [InlineKeyboardButton(text="Premium", callback_data="admin:premium")],
        ]
    )
