from bot.bot_instance import get_bot_instance
from sqlalchemy.exc import NoResultFound
from pyrogram.errors import FloodWait, ChatAdminRequired, UserNotParticipant, PeerIdInvalid, UserBannedInChannel
from db.channel_helpers import get_all_channels
from db.subscription_helpers import update_subscription
from db.connection import get_db
from helpers.text_helper import create_channel_mention
from typing import Dict, List
from utils.logger import LOGGER
import asyncio


async def update_single_user_subscription(session, user_id, channel_id, duration_text):
    try:
        is_success = True
        result = await update_subscription(session, user_id, channel_id, duration_text)
    except ChatAdminRequired as e:
        is_success = False
        result = f"{e}"
    except PeerIdInvalid as e:
        need_to_stop = False
        result = f"PeerIdInvalid please make sure the bot is able to interact with the channel: {e}"
    except NoResultFound as e:
        need_to_stop = False
        result = f"{e}"
    except Exception as e: # Invalid input
        raise

    return is_success, result

async def check_status():
    """
    Checks bot's access status for all channels/groups in database.
    Returns formatted status message with emojis and proper spacing.
    """
    bot_instance = await get_bot_instance()
    
    # Status counters and collectors
    status_counts = {
        "good": 0,
        "admin_required": 0,
        "peer_invalid": 0
    }
    
    status_details: Dict[str, List[str]] = {
        "good": [],
        "admin_required": [],
        "peer_invalid": []
    }

    try:
        with next(get_db()) as db:
            channels = get_all_channels(db)
            
            if not channels:
                return "❌ No channels found in database!"

            # Check each channel
            for channel in channels:
                try:
                    chat = await bot_instance.get_chat(channel["id"])
                    member = await bot_instance.get_chat_member(channel["id"], bot_instance.me.id)
                    
                    if member.privileges:  # Bot has admin rights
                        status_counts["good"] += 1
                        status_details["good"].append(create_channel_mention(channel['name'], channel["id"]))
                    else:
                        status_counts["admin_required"] += 1
                        status_details["admin_required"].append(create_channel_mention(channel['name'], channel["id"]))
                        
                except ChatAdminRequired:
                    status_counts["admin_required"] += 1
                    status_details["admin_required"].append(create_channel_mention(channel['name'], channel["id"]))
                except (PeerIdInvalid, ValueError):
                    status_counts["peer_invalid"] += 1
                    status_details["peer_invalid"].append(create_channel_mention(channel['name'], channel["id"]))
                except FloodWait as e:
                    await asyncio.sleep(e.value)
                except Exception as e:
                    LOGGER.error(f"Unexpected error checking channel {channel['name'][:-1]}: {type(e)} {str(e)}")

            # Format the response message
            response = "📊 **Channel/Group Status Report**\n\n"
            
            # Summary section
            response += "📑 **Summary:**\n"
            response += f"✅ Working Properly: {status_counts['good']}\n"
            response += f"⚠️ Admin Rights Needed: {status_counts['admin_required']}\n"
            response += f"🗣 Need Interaction: {status_counts['peer_invalid']}\n\n"
            
            # Detailed section
            response += "📋 **Detailed Status:**\n\n"
            
            if status_details["good"]:
                response += "✅ **Working Properly:**\n"
                for channel in status_details["good"]:
                    response += f"  • {channel}\n"
                response += "\n"
            
            if status_details["admin_required"]:
                response += "⚠️ **Admin Rights Needed:**\n"
                for channel in status_details["admin_required"]:
                    response += f"  • {channel}\n"
                response += "\n"
            
            if status_details["peer_invalid"]:
                response += "🗣 **Need Interaction:**\n"
                for channel in status_details["peer_invalid"]:
                    response += f"  • {channel}\n"
                response += "\n"

            response += "\n\n- - - **Required Actions:** - - -\n"
            response += "⚠️ **For 'Admin Rights Needed' channels:**\n"
            response += "  • Go to channel/group settings\n"
            response += "  • Click 'Administrators'\n"
            response += "  • Add bot as admin with these permissions:\n"
            response += "    - Add members\n"
            response += "    - Ban users\n"
            response += "    - Invite users via link\n\n"
            
            response += "🗣 **For 'Need Interaction' channels:**\n"
            response += "  • Add bot to the channel/group\n"
            response += "  • Make bot admin\n"
            response += "  • Send one message in the group\n"
            response += "  • Or forward one message to the group\n\n"
            
            response += "✅ **Working channels** have all required permissions and access.\n"
            
            return response, all(status_counts[key] == 0 for key in ['admin_required', 'peer_invalid'])

    except Exception as e:
        LOGGER.error(f"Error in check_status: {e}")
        return f"❌ Error checking status: {str(e)}"