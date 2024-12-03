from bot import Bot
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait
from pyrogram.enums import ParseMode
from utils.config import Config
from utils.logger import LOGGER
from pyrogram import Client, filters
from bot.bot_instance import get_bot_instance

import asyncio
from datetime import datetime

@Bot.on_message(filters.private)
async def greet_user(client: Client, message: Message):
    user = message.from_user
    mention_text = f"<a href=\"tg://user?id={user.id}\">{user.first_name} {user.last_name}</a>"

    # Send the greeting with the mention
    await message.reply_text(
        f"Hi {mention_text}! I'm @{client.username}",
        parse_mode=ParseMode.HTML
    )

