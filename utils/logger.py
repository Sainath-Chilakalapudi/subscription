import logging
from logging.handlers import RotatingFileHandler
from .config import Config

def setup_logger():
    try:
        logger = logging.getLogger(Config.LOGGER_NAME)
        logger.setLevel(logging.INFO)

        handler = RotatingFileHandler("bot.log", maxBytes=10 * 1024 * 1024, backupCount=10)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        # Optional: Add a StreamHandler for logging to console
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

        return logger
    except (IOError, OSError) as e:
        print(f"Error setting up logger: {e}")
        return None

LOGGER = setup_logger()

if LOGGER is None:
    # Handle the case where logger setup failed
    pass

        # try:
        #     await post_message.edit_reply_markup(reply_markup)
        # except FloodWait as e:
        #     await asyncio.sleep(e.value)
        #     await post_message.edit_reply_markup(reply_markup)
        # except Exception:
        #     pass