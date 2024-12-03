from bot import Bot
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message
from db.connection import get_db
from db.channel_helpers import add_channel, delete_channel, get_all_channels
from helpers.filters import devs_filter
from utils.logger import LOGGER


"""
+=======================================================================================================+
--------------------------------      LIST OF FEATURES      --------------------------------------------
+=======================================================================================================+
DEV : /addchannel <channel_id> <channel_name>
DEV : /listchannels
DEV : /deletechannel <channel_id>
+=======================================================================================================+
"""


# Command: /addchannel
@Bot.on_message(filters.command("addchannel") & filters.private & devs_filter)
async def add_channel_handler(client: Client, message: Message):
    """
    Handles the /addchannel command to add a new channel to the database.
    """
    try:
        # Check if a channel ID and name are provided in the message
        if len(message.command) < 3:
            await message.reply_text(
                "Usage: /addchannel <channel_id> <channel_name>\n"
                "Example: /addchannel -1001234567890 MyChannel", parse_mode=ParseMode.MARKDOWN
            )
            return

        # Extract channel ID and name from the message
        channel_id = int(message.command[1])
        channel_name = " ".join(message.command[2:])

        with next(get_db()) as db:
            # Add the channel to the database
            result = add_channel(db, channel_id, channel_name)

            if result:
                await message.reply_text(
                    f"✅ Channel `{channel_name}` (ID: `{channel_id}`) has been added successfully."
                )
            else:
                await message.reply_text(
                    f"❌ Failed to add channel `{channel_name}` (ID: `{channel_id}`). It might already exist."
                )

    except ValueError:
        await message.reply_text("❌ Invalid channel ID format. Please provide a numeric ID.")
    except Exception as e:
        LOGGER.error(f"Error in /addchannel: {e}")
        await message.reply_text("❌ An error occurred while adding the channel. Please try again later.")

# Command: /listchannels
@Bot.on_message(filters.command("listchannels") & filters.private & devs_filter)
async def dev_show_channels_handler(client: Client, message: Message):
    """
    Handles the /listchannels command to list all managed channels.
    """
    try:
        with next(get_db()) as db:
            # Retrieve all channels from the database
            channels = get_all_channels(db)

            if not channels:
                await message.reply_text("ℹ️ No channels found in the database.")
                return

            # Format the list of channels
            response = "**Managed Channels:**\n"
            for idx, channel in enumerate(channels, start=1):
                response += f"{idx}. {channel['name']} (ID: `{channel['id']}`)\n"

            await message.reply_text(response)

    except Exception as e:
        LOGGER.error(f"Error in /listchannels: {e}")
        await message.reply_text("❌ An error occurred while retrieving the channel list. Please try again later.")

# Command: /deletechannel
@Bot.on_message(filters.command("deletechannel") & filters.private & devs_filter)
async def delete_channel_handler(client: Client, message: Message):
    """
    Handles the /deletechannel command to delete a channel and its associated data.
    """
    try:
        # Check if a channel ID is provided
        if len(message.command) < 2:
            await message.reply_text(
                "Usage: /deletechannel <channel_id>\n"
                "Example: /deletechannel -1001234567890"
            )
            return

        # Extract channel ID from the message
        channel_id = int(message.command[1])

        with next(get_db()) as db:
            # Delete the channel from the database
            result = delete_channel(db, channel_id)

            if result:
                await message.reply_text(f"✅ Channel with ID `{channel_id}` has been deleted successfully.")
            else:
                await message.reply_text(
                    f"❌ Failed to delete the channel with ID `{channel_id}`. It might not exist."
                )

    except ValueError:
        await message.reply_text("❌ Invalid channel ID format. Please provide a numeric ID.")
    except Exception as e:
        LOGGER.error(f"Error in /deletechannel: {e}")
        await message.reply_text("❌ An error occurred while deleting the channel. Please try again later.")