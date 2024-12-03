# from server import run_server
from bot.bot_instance import get_bot_instance
from db.connection import Base, engine
from helpers.scheduler import start_scheduler
import argparse
import asyncio
from pyrogram import idle

async def main():
    # run_server()  # Start the dummy server
    parser = argparse.ArgumentParser(description="Start the bot.")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    if args.debug:
        print("Debug mode enabled")

    Base.metadata.create_all(bind=engine)
    print("Database initialized.")

    print("Bot is being started...")
    bot_instance = await get_bot_instance()  # Await to get the actual bot instance

    async def start_bot_and_scheduler():
        bot_instance.loop.create_task(start_scheduler())  # Start scheduler as a background task
        await bot_instance.start()  # Start the bot (crucially AFTER creating scheduler task)
        print("Bot and scheduler started. Press Ctrl+C to stop.")
        await idle()
        await bot_instance.stop()

    try:
        await start_bot_and_scheduler()  # Await the coroutine directly
    except (KeyboardInterrupt, SystemExit):
        print("\nStopping bot and scheduler...")
    finally:  # Ensure bot is stopped in case of errors
        print("Bot and scheduler stopped.")

if __name__ == "__main__":
    asyncio.run(main())
