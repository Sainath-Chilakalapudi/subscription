from bot import Bot
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from utils.logger import LOGGER
from helpers.filters import admins_filter
from helpers.text_helper import send_long_message
from helpers.scheduler import run_daily_routine_manually
from helpers.additional_bot_helpers import check_status
from utils.logger import LOGGER
from utils.config import Config
from bot.bot_instance import get_bot_instance
import asyncio

"""
+=======================================================================================================+
--------------------------------      LIST OF FEATURES      --------------------------------------------
+=======================================================================================================+
Admin : /cleanusers
Admin : /status
+=======================================================================================================+
"""


@Bot.on_message(filters.command("cleanusers") & filters.private & admins_filter)
async def clean_users(_, message):
    try:
        await message.reply("Trying to clean Users whose subscriptions are expired")
        await run_daily_routine_manually()
        await message.reply("Process succesfully Completed")
    except Exception as e:
        LOGGER.error(f"Error in clean_users : {e}")
        await message.reply(" Sorry an error occured.")

@Bot.on_message(filters.command("status") & filters.private & admins_filter)
async def check_status_handler(_, message):
    try:
        admin_id = message.chat.id
        bot_instance = await get_bot_instance()
        response, _ = await check_status()
        await send_long_message(bot_instance,admin_id,response)
    except Exception as e:
        LOGGER.error(f"Error in check_status_handler : {e}")
        await message.reply(" Sorry an error occured.")

# Define the /about command
@Bot.on_message(filters.command("about") & filters.private)
async def about_handler(_, message: Message):
    """
    Handler for the /about command. Displays information about the bot.
    """
    about_text = (
        "🤖 **About This Bot**\n\n"
        "Hello! I am a subscription management bot designed to help "
        "admins manage user access to Telegram channels and groups.\n\n"
        "✨ **Features:**\n"
        "- Automatically accept join requests based on active subscriptions.\n"
        "- Notify admins about pending requests.\n"
        "- Update or revoke user subscriptions.\n"
        "- Clean up expired users and manage invite links.\n\n"
        "🔧 **Built With:**\n"
        "- Python\n"
        "- SQLAlchemy\n"
        "- Pyrogram\n\n"
        f"👨‍💻 **Developed By:** {', '.join([f'tg://user?id={dev_id}>Developer {i+1}</a>' for i, dev_id in enumerate(Config.DEV_IDS) if dev_id != 0])}\n\n"
        "Feel free to reach out for support or suggestions!"
    )

    await message.reply_text(
        about_text,
        disable_web_page_preview=True,
        # reply_markup=InlineKeyboardMarkup(
        #     [[InlineKeyboardButton("Source Code", url="https://github.com/YourRepoHere")]]
        # ),
    )


# Define the /help command
@Bot.on_message(filters.command("help") & filters.private)
async def help_handler(_, message: Message):
    """
    Handler for the /help command. Displays a list of available commands for the user.
    """
    help_text = (
        "🛠️ **Help Menu**\n\n"
        "Here are the available commands:\n\n"
        "**Admin Commands:**\n"
        "1. `/cleanusers` - Remove users whose subscriptions have expired.\n"
        "2. `/status` - Check the bot's status.\n"
        "3. `/deletelinks` - Delete old invite links from a channel.\n"
        "4. `/regenlink` - Regenerate an invite link for a channel.\n\n"
        "**General Commands:**\n"
        "5. `/about` - Learn more about this bot.\n"
        "6. `/help` - Show this help message.\n\n"
        "**Note:** These commands are only available for authorized admins and devs.\n"    
        "ℹ️ For additional assistance or questions, contact the bot admin."
    )

    await message.reply_text(help_text)