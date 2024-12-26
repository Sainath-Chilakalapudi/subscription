from bot.bot_instance import get_bot_instance
from sqlalchemy.exc import NoResultFound
from pyrogram.errors import FloodWait, ChatAdminRequired, UserNotParticipant, PeerIdInvalid, UserBannedInChannel
from db.channel_helpers import get_all_channels
from db.subscription_helpers import update_subscription
from db.connection import get_db
from db.admin_helpers import list_admins
from helpers.text_helper import create_channel_mention
from typing import Dict, List, Tuple
from utils.logger import LOGGER
import asyncio


async def update_single_user_subscription(session, user_id, channel_id, admin_id, duration_text):
    try:
        is_success = True
        result = await update_subscription(session, user_id, channel_id, admin_id, duration_text)
    except ChatAdminRequired as e:
        is_success = False
        result = f"{e}"
    except PeerIdInvalid as e:
        is_success = False
        return f"PeerIdInvalid please make sure the bot is able to interact with the channel: {e}"
    except NoResultFound as e:
        is_success = False
        result = f"{e}"
    except Exception as e: # Invalid input
        raise

    return is_success, result

# async def check_status() -> Tuple[Dict[int, str], bool]:
    """
    Checks bot's access status for all channels/groups, grouped by admin.
    Returns a dictionary where keys are admin IDs and values are status messages,
    and a boolean indicating if all channels are operational.
    """
    try:
        bot_instance = await get_bot_instance()
        admin_status_reports = {}
        all_channels_operational = True

        with next(get_db()) as session:
            admins = list_admins(session)

            for admin in admins:
                admin_id = admin['admin_id']
                admin_channels = admin['channels']
                status_report = ""
                channels_operational = True

                for channel in admin_channels:
                    channel_id = channel['id']
                    channel_name = channel['name']
                    try:
                        chat = await bot_instance.get_chat(channel_id)
                        member = await bot_instance.get_chat_member(channel_id, bot_instance.me.id)

                        if member.privileges:
                            status_report += f"✅ {create_channel_mention(channel_name, channel_id)}: Working Properly\n"
                        else:
                            status_report += f"⚠️ {create_channel_mention(channel_name, channel_id)}: Admin Rights Needed\n"
                            channels_operational = False
                            all_channels_operational = False

                    except ChatAdminRequired:
                        status_report += f"⚠️ {create_channel_mention(channel_name, channel_id)}: Admin Rights Needed\n"
                        channels_operational = False
                        all_channels_operational = False

                    except (PeerIdInvalid, ValueError):
                        status_report += f"🗣 {create_channel_mention(channel_name, channel_id)}: Needs Interaction\n"
                        channels_operational = False
                        all_channels_operational = False

                    except FloodWait as e:
                        await asyncio.sleep(e.value)
                    except Exception as e:
                        LOGGER.error(f"Unexpected error checking channel {channel_name}: {type(e)} {str(e)}")
                        status_report += f"❌ {create_channel_mention(channel_name, channel_id)}: Error checking status: {e}\n"
                        channels_operational = False
                        all_channels_operational = False


                if not channels_operational:  # Append instructions if any channel has issues
                    status_report += get_instruction_message()  # See below

                admin_status_reports[admin_id] = status_report
        return admin_status_reports, all_channels_operational
    except Exception as e:
        LOGGER.error(f"Error in check_status: {e}")
        return f"❌ Error checking status: {str(e)}"

async def check_admin_status(admin_id: int, admin_channels: List[Dict]) -> Tuple[str, bool]:
    """
    Checks the bot's access status for channels/groups associated with a specific admin.
    
    Args:
        bot_instance (TelegramClient): The Telegram bot instance.
        admin_id (int): The ID of the admin to check.
        admin_channels (List[Dict]): List of channels associated with the admin.
    
    Returns:
        Tuple[str, bool]: A tuple containing the status report (str) and a boolean
                          indicating if all channels are operational.
    """
    bot_instance = await get_bot_instance()
    status_report = "All Channels Status Report 📝\n"
    channels_operational = True

    for channel in admin_channels:
        channel_id = channel['id']
        channel_name = channel['name']
        try:
            chat = await bot_instance.get_chat(channel_id)
            member = await bot_instance.get_chat_member(channel_id, bot_instance.me.id)

            if member.privileges:
                status_report += f"✅ {create_channel_mention(channel_name, channel_id)}: Working Properly\n"
            else:
                status_report += f"⚠️ {create_channel_mention(channel_name, channel_id)}: Admin Rights Needed\n"
                channels_operational = False

        except ChatAdminRequired:
            status_report += f"⚠️ {create_channel_mention(channel_name, channel_id)}: Admin Rights Needed\n"
            channels_operational = False

        except (PeerIdInvalid, ValueError):
            status_report += f"🗣 {create_channel_mention(channel_name, channel_id)}: Needs Interaction\n"
            channels_operational = False

        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception as e:
            LOGGER.error(f"Unexpected error checking channel {channel_name}: {type(e)} {str(e)}")
            status_report += f"❌ {create_channel_mention(channel_name, channel_id)}: Error checking status: {e}\n"
            channels_operational = False

    if not channels_operational:  # Append instructions if any channel has issues
        status_report += get_instruction_message()  # Assuming this function is defined elsewhere

    return status_report, channels_operational

async def check_status(admin_id: int = None) -> Tuple[Dict[int, str], bool]:
    """
    Checks the bot's access status for all channels/groups, optionally grouped by a specific admin.
    Returns a dictionary where keys are admin IDs and values are status messages,
    and a boolean indicating if all channels are operational.
    
    Args:
        admin_id (int, optional): The ID of the specific admin to check (default: None).
    
    Returns:
        Tuple[Dict[int, str], bool]: A tuple containing a dictionary of admin status reports
                                    and a boolean indicating if all channels are operational.
    """
    try:
        admin_status_reports = {}
        all_channels_operational = True

        with next(get_db()) as session:
            if admin_id:
                # Fetch a specific admin and their channels
                admin = list_admins(session, admin_id)
                print(f"Admin Id given and list size {len(admin)}")
                if not admin:
                    LOGGER.warning(f"No admin found with ID: {admin_id}")
                    return {}, False  # Return empty dict and False if admin not found
                admins = admin # Single entry is needed to be made as list
            else:
                # Fetch all admins
                print(f"Admin Id is not given")
                admins = list_admins(session)
                print(f"size of admins list - {list_admins}")

            for admin in admins:
                admin_id = admin['admin_id']
                admin_channels = admin['channels']
                status_report, channels_operational = await check_admin_status(admin_id, admin_channels)

                admin_status_reports[admin_id] = status_report
                all_channels_operational = channels_operational
                print(f"is it fine - {all_channels_operational}")
        return admin_status_reports, all_channels_operational
    except Exception as e:
        LOGGER.error(f"Error in check_status: {e}")
        return {}, False  # Return empty dict and False on error


def get_instruction_message():
    # Define all message lines in a tuple
    required_actions = (
        "\n\n⚠️⚠️⚠️ **Attention Required:**",
        "At least one of your channels is **not Working properly**. "
        "Please follow theses instructions to ensure all channels are functioning correctly.\n",
        "- - - **Instructions Based on Channel Status:** - - -\n",
        
        "⚠️ **For channels marked 'Admin Rights Needed':**",
        "  • Go to channel/group settings",
        "  • Click 'Administrators'",
        "  • Add bot as admin with these permissions:",
        "    - Add members",
        "    - Ban users",
        "    - Invite users via link\n",
        
        "🗣 **For channels marked 'Needs Interaction':**",
        "  • Visit the channel/group",
        "  • Quick React to any random message in the channel.",
        "  • If above doesn't work send a message/sticker/GIF.",
        "  • Or forward one message to the channel.\n",
        
        "✅ **For channels marked 'Working Properly':**",
        "  • No action is required."
    )
    
    # Join all lines into a single response string
    return "\n".join(required_actions)
