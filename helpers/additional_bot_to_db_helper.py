from bot.bot_instance import get_bot_instance
from utils.logger import LOGGER
import asyncio
from pyrogram.errors import FloodWait, ChatAdminRequired, UserNotParticipant, PeerIdInvalid, UserBannedInChannel


#--------------------------------- Kick and unban user 


async def kick_and_unban_user(user_id: int, chat_id: int):
    """
    Kicks a user from a channel and then unbans them.

    Args:
        chat_id: The ID of the channel.
        user_id: The ID of the user to kick and unban.
    """
    try:
        bot_instance = await get_bot_instance()
        # Kick the user from the channel
        await bot_instance.ban_chat_member(chat_id, user_id)
        LOGGER.info(f"User {user_id} kicked from channel {chat_id}")

        # Briefly pause to avoid potential rate limiting (optional)
        await asyncio.sleep(1)

        # Unban the user from the channel
        await bot_instance.unban_chat_member(chat_id, user_id)
        LOGGER.info(f"User {user_id} unbanned from channel {chat_id}")

    except FloodWait as e:
        LOGGER.error(f"Flood wait triggered. Sleeping for {e.value} seconds.")
        await asyncio.sleep(e.value)
        await kick_and_unban_user(chat_id, user_id)  # Retry after flood wait

    except ChatAdminRequired:
        LOGGER.error(f"Bot needs admin rights in channel {chat_id} to perform remove the user action.")
        raise ChatAdminRequired(f"Bot needs admin rights in channel {chat_id} to perform remove the user action.")

    except UserNotParticipant:
        LOGGER.error(f"User {user_id} is not a member of channel {chat_id}.")

    except PeerIdInvalid:
        LOGGER.error(f"Invalid chat ID ({chat_id}) or user ID ({user_id}). Please check.")
        raise
    
    except UserBannedInChannel:
        LOGGER.error(f"User {user_id} is not banned in channel {chat_id} trying to unban.")
        await bot_instance.unban_chat_member(chat_id, user_id)
        LOGGER.error(f"User {user_id} unbanned from channel {chat_id}")

    except Exception as e:
        LOGGER.error(f"An unexpected error occurred: {e}")

