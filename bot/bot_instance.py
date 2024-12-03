# Singleton Lazy Initialization

from bot import Bot
import asyncio

_bot_instance = None

async def _initialize_bot():
    bot = Bot()  # Instantiate the bot
    await asyncio.sleep(0)  # This allows the async event loop to handle the instantiation properly
    return bot

async def get_bot_instance():
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = await _initialize_bot()  # Call the async wrapper to initialize the bot
    return _bot_instance
