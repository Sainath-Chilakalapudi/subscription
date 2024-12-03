from bot import Bot
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton,KeyboardButton, InlineKeyboardMarkup, CallbackQuery,ReplyKeyboardMarkup, Message
from pyrogram.enums import ChatMemberStatus, ChatType
from pyrogram.errors import ChatAdminRequired
from db.connection import get_db
from db.user_helpers import add_user
from db.channel_helpers import get_channel_name_by_id, get_channel_link, update_channel_link, add_or_update_channel_connection, get_all_channels, delete_channel
from db.subscription_helpers import add_subscription
# # from db.connection import get_db
from helpers.text_helper import sanitize_fullname
from helpers.filters import admins_filter, calling_bot_filter, anonymous_message_filter
# from db.channel_helpers import add_channel, delete_channel, get_all_channels
from utils.logger import LOGGER


"""
+=======================================================================================================+
--------------------------------      LIST OF FEATURES      --------------------------------------------
+=======================================================================================================+
Channel : /start@botusername
Admin : /addchannel
Admin : /showchannels
Admin : /removechannel
Channel : /scan
+=======================================================================================================+
"""




# ---------------------- Setting up connection to channel / group (automatic for group) (/start@botname for channel) ---------------------------

#  filters.command("start") & calling_bot_filter & admin_or_bot_invite_filter
@Bot.on_message(calling_bot_filter & (filters.channel | (filters.group & (admins_filter | anonymous_message_filter)))) # Matches /start@botusername (no space)
async def handle_new_channel_connection(client: Client, message: Message):
    try:
        # Check if the bot has permission to invite users
        if not await has_invite_users_permission(client, message):
            await message.reply(
                "🚫 I need permission to invite users to this group.\n"
                "Please grant me the 'Invite Users' permission and try again."
            )
            LOGGER.warning(f"Permission denied in chat: {message.chat.id}")
            return
        chat_id = message.chat.id

        with next(get_db()) as db:
            channel_name = get_channel_name_by_id(db, chat_id)

            if channel_name is not None:
                channel_id = chat_id
                existing_link = get_channel_link(db, channel_id)
                if existing_link:
                    # Try to revoke the old link (handle possible errors)
                    try:
                        await client.revoke_chat_invite_link(channel_id, existing_link)
                        LOGGER.info(f"Successfully revoked old invite link for channel {channel_id}")
                    except Exception as e:
                        LOGGER.error(f"Error revoking invite link for channel {channel_id}: {e}")

                # Create a new invite link with join request turned on
                new_link = await client.create_chat_invite_link(channel_id, creates_join_request=True)
                invite_link = new_link.invite_link

                # Update the link in the database
                if update_channel_link(db, channel_id, invite_link):
                    LOGGER.info(f"Reinitialized link for channel {channel_id} generated: {new_link}")
                    await message.reply(
                        f"✅ Successfully reconnected to the channel!\n\n"
                        f"**Channel Name:** {channel_name}\n\n"
                        f"Invite link has now been updated."
                    )
                    return
                else:
                    LOGGER.error(f" Failed to reinitialize the link for channel {channel_id}.")
                    await message.reply(f"❌ Failed to update the link for channel in the database.")
                    return

        # Create a join-request invite link for the current chat (group)        
        link = await client.create_chat_invite_link(chat_id, creates_join_request=True)
        invite_link = link.invite_link
        is_channel = message.chat.type == ChatType.CHANNEL # boolean to say if it is channel or group

        # Add the channel connection details to the database
        channel_name = message.chat.title  # Assuming you want to use the chat title
        with next(get_db()) as db:
            success = add_or_update_channel_connection(db, chat_id, channel_name, invite_link, is_channel)

        if success:
            await message.reply(
                f"✅ Successfully connected to the channel!\n\n"
                f"**Channel Name:** {channel_name}\n\n"
                f"Members **subscriptions** can now be managed easily."
            )
            LOGGER.info(f"New Channel connection added: {channel_name} (ID: {chat_id})")
        else:
            await message.reply(
                "⚠️ Failed to add the channel connection to the database.\n"
                "Please try again later or contact support."
            )
            LOGGER.error(f"Failed to add New channel connection: {channel_name} (ID: {chat_id})")

    except Exception as e:
        await message.reply(
            "❌ An unexpected error occurred while handling your request.\n"
            "Please try again later."
        )
        LOGGER.error(f"Error handling /start command for chat {message.chat.id}: {e}")

# helper function to check if Bot is admin in channel and also has Invite users option set
async def has_invite_users_permission(client: Client, message: Message) -> bool:
    # Check if the message is from a group, supergroup, or channel
    LOGGER.info(message.chat.type)
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP, ChatType.CHANNEL]:
        chat_id = message.chat.id
        
        try:
            # Get the bot's status and privileges in the chat
            chat_member = await client.get_chat_member(chat_id, client.me.id)
            # Check if the bot is an administrator
            if chat_member.status == ChatMemberStatus.ADMINISTRATOR:
                # Check if the bot has "Invite Users" permission
                privileges = chat_member.privileges
                if privileges and privileges.can_invite_users:
                    return True
        except ChatAdminRequired:
            # If the bot is not an admin, it will raise this error
            return False
    return False

# ------------------------------ add channel - /addchannel --------------------------

@Bot.on_message(filters.command("addchannel") & filters.private & admins_filter)
async def add_channel_menu(client: Client, message: Message):
    try:
        buttons = [
            [InlineKeyboardButton("Add me to your Channel", callback_data="addto_channel"),
            InlineKeyboardButton("Add me to your Group", callback_data="addto_group")],
            [InlineKeyboardButton("Cancel", callback_data="canceladdchannel")]
        ]
        await message.reply_text(
            "For which type of Chat do you want to add me in?",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        LOGGER.error(f"Error in /addchannel: {str(e)}")
        await message.reply_text("There was an error processing your request. Please contact support.")

@Bot.on_callback_query(filters.regex("addto_(channel|group)"))
async def handle_add_to_chatn(client: Client, callback_query: CallbackQuery):
    try:
        # Acknowledge the callback query (to prevent "loading" circle on the client)
        await callback_query.answer()
        # Extract the channel or group type
        channel_or_group = callback_query.data.split("_")[1]
        username = client.me.username
        link = f"https://t.me/{username}?start{channel_or_group}&botby=@crazydarkhunter&admin=invite_users+manage_chat"
        
        if channel_or_group == "channel":
            link += "+post_messages"
        else:
            link += "+restrict_members"

        buttons = [
            [InlineKeyboardButton(f"Add me to {channel_or_group}", url=link),
            InlineKeyboardButton("Done", callback_data=f"done_{channel_or_group}")]
        ]
        
        await callback_query.edit_message_text(
            f"Choose an option for {channel_or_group}:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        await callback_query.answer()
    except Exception as e:
        LOGGER.error(f"Error in handle_add_to_chat: {str(e)}")
        await callback_query.message.reply_text("There was an error processing your request. Please try again.")

@Bot.on_callback_query(filters.regex("done_(channel|group)"))
async def handle_donen(client: Client, callback_query: CallbackQuery):
    try:
        # Acknowledge the callback query (to prevent "loading" circle on the client)
        await callback_query.answer()
        channel_or_group = callback_query.data.split("_")[1]
        username = client.me.username
        
        if channel_or_group == "channel":
            message = (
                "To initialize me in on channel where you have added me, please follow these steps:\n\n"
                "1. Go to the channel where you added me.\n"
                "2. Ensure I have 'Post Messages' & 'add members' permission enabled in the channel.\n"
                f"3. Send the command: `/start@{username}`\n"
                "4. Wait for my confirmation message.\n\n"
                "Once you see the confirmation, you're ready to go!"
            )
            await callback_query.edit_message_text(message)
        elif channel_or_group == "group":
            message = (
                "If you've added me to a group, initialization usually happens automatically.\n\n "
                "Please check the group for the following:\n"
                "1. A recent `/start` command.\n"
                "2. My confirmation message in reply to the `/start` command.\n\n"
                "If you don't see these, or if my confirmation indicates a failure, "
                f"please send: `/start@{username}` in the group to initialize the connection or contact support"
            )
            await callback_query.edit_message_text(message)
    except Exception as e:
        LOGGER.error(f"Error in handle_done: {str(e)}")
        await callback_query.message.reply_text("There was an error processing your request. Please try again.")

@Bot.on_callback_query(filters.regex("canceladdchannel"))
async def cancel_add_channeln(client: Client, callback_query: CallbackQuery):
    try:
    # Acknowledge the callback query (to prevent "loading" circle on the client)
        await callback_query.answer()
        await callback_query.edit_message_text("Add channel cancelled.")
        await callback_query.answer()
    except Exception as e:
        LOGGER.error(f"Error in cancel_add_channel: {str(e)}")
        await callback_query.message.reply_text("There was an error processing your request. Please try again.")

# ------------------------------ Show channels - /showchannels ----------------------------------------------

@Bot.on_message(filters.command("showchannels") & filters.private & admins_filter)
async def show_channels_handler(client: Client, message: Message):
    """
    Handles the /showchannels command to display all channels.
    """
    try:
        with next(get_db()) as db:
            # Fetch the list of channels
            channels = get_all_channels(db)
            if not channels:
                await message.reply_text("No managed channels available.")
                return
            
            # Display channels as inline buttons with links (users inside it can only access it)
            buttons = [
                [InlineKeyboardButton(channel["name"], url=f"https://t.me/c/{str(channel['id'])[4:]}/")]
                for channel in channels
            ]
            await message.reply_text(
                "All Managed Channels:",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
    except Exception as e:
        LOGGER.error(f"Error in /showchannels: {e}")
        await message.reply_text("❌ An error occurred while processing the command.")


# ----------------------------- remove channel - /removechannel ------------------------------------

@Bot.on_message(filters.command("removechannel") & filters.private & admins_filter)
async def remove_channel_handler(client: Client, message: Message):
    try:
        with next(get_db()) as db:
            # Fetch the list of channels
            channels = get_all_channels(db)
            if not channels:
                await message.reply_text("No managed channels available.")
                return

            # Display channels as inline buttons
            buttons = [
                [InlineKeyboardButton(channel["name"], callback_data=f"remove1_{channel['id']}_{channel['name']}")]
                for channel in channels
            ]
            await message.reply_text(
                "Select a channel to remove from database:",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
    except Exception as e:
        LOGGER.error(f"Error in /removechannel: {e}")
        await message.reply_text("❌ An error occurred while processing the command.")


@Bot.on_callback_query(filters.regex(r"remove1_-\d+"))
async def generate_verification(client: Client, callback_query: CallbackQuery):
    try:
        channel_id = int(callback_query.data.split("_")[1])
        channel_name = callback_query.data.split("_")[2]

        # Acknowledge the callback query (to prevent "loading" circle on the client)
        await callback_query.answer()
        await callback_query.message.delete()
        
        await callback_query.message.reply_text(
            f"Are you sure you want to remove **{channel_name}** from the database? This will delete all channel members' subscriptions from the database and **cannot be undone**.",
            reply_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("Ok, Delete", callback_data=f"confirm_remove2_{channel_id}"),
                InlineKeyboardButton("Cancel", callback_data="cancel")],
            ])
        )
        return
    except Exception as e:
        LOGGER.error(f"Error in generate_verification: {e}")
        await callback_query.message.reply_text("❌ An error occurred while deleting the channel. Please try again later.")


@Bot.on_callback_query(filters.regex(r"confirm_remove2_-\d+"))
async def confirm_remove(client: Client, callback_query: CallbackQuery):
    try:
        # Acknowledge the callback query (to prevent "loading" circle on the client)
        await callback_query.answer()
        await callback_query.message.delete()

        channel_id = int(callback_query.data.split("_")[2])
        await callback_query.message.reply_text(
            "You really want to delete this channel? This will delete all channel members' subscriptions from the database and cannot be undone.",
            reply_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("Yes, I don't care if channel members' subscriptions are deleted", callback_data=f"final_remove3_{channel_id}")],
                [InlineKeyboardButton("Cancel now, it's not late", callback_data="canceldelete")]
            ])
        )
    except Exception as e:
        LOGGER.error(f"Error in confirm_remove: {e}")
        await callback_query.message.reply_text("❌ An error occurred while deleting the channel. Please try again later.")


@Bot.on_callback_query(filters.regex(r"final_remove3_-\d+"))
async def final_confirm_remove(client: Client, callback_query: CallbackQuery):
    try:
        # Acknowledge the callback query (to prevent "loading" circle on the client)
        await callback_query.answer()
        await callback_query.message.delete()

        channel_id = int(callback_query.data.split("_")[2])
        with next(get_db()) as db:
                # Delete the channel from the database
                result = delete_channel(db, channel_id)
                if result:
                    await callback_query.message.reply_text(f"✅ Channel with ID `{channel_id}` has been deleted successfully.")
                else:
                    await callback_query.message.reply_text(
                        f"❌ Failed to delete the channel with ID `{channel_id}`. It might not exist."
                    )
    except Exception as e:
        LOGGER.error(f"Error in final_confirm_remove: {e}")
        await callback_query.message.reply_text("❌ An error occurred while deleting the channel. Please try again later.")


@Bot.on_callback_query(filters.regex("canceldelete"))
async def cancel_delete(client: Client, callback_query: CallbackQuery):
    # Acknowledge the callback query (to prevent "loading" circle on the client)
    await callback_query.answer()
    await callback_query.message.delete()
    await callback_query.message.reply_text("❌ Channel removal cancelled.")



# ----------------------------- scan channel for existing users - /scan ------------------------------------

@Bot.on_message(filters.command("scan") & (filters.channel | (filters.group & (anonymous_message_filter | admins_filter) )))
async def scan_members(client: Client, message: Message):
    """Handles the /scan command in the channel to fetch member details."""
    try:
        channel_id = message.chat.id
        
        # Check if the bot is an admin in the channel
        bot_user = await client.get_me()
        bot_member = await client.get_chat_member(channel_id, bot_user.id)
        
        if bot_member.status != ChatMemberStatus.ADMINISTRATOR:
            await message.reply("Please make the bot an admin with appropriate privileges.")
            return

        # Initialize a list to hold non-admin members
        non_admin_users = []

        # Use async for to collect members from the async generator
        async for member in client.get_chat_members(channel_id):
            if not member.user.is_bot and member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                non_admin_users.append(member)
        
        if not non_admin_users:
            await message.reply("No non-admin users found to scan.")
            return
        
        Total = len(non_admin_users)
        failed, success = 0,0
        
        # Add non-admin users to the database and set their subscription
        with next(get_db()) as db:
            for member in non_admin_users:
                user_id = member.user.id
                username = member.user.username
                fullname = sanitize_fullname(member.user.first_name, member.user.last_name)
                
                # Add user to database
                user = add_user(db, user_id, username, fullname)
                if not user:
                    failed += 1
                    continue
                
                # Add subscription with 3 days duration
                subscription = add_subscription(db, user_id, channel_id, 3)
                if not subscription:
                    failed += 1
                success +=1
            
        status_message = (
            f"- -**Scan Summary**- -:\n\n"
            f"Total Users: {Total}\n\n"
            f"✅ Success: {success}\n\n"
            f"❌ Failed: {failed}\n\n"
        )

        # Send message to the user who initiated the scan command
        await message.reply(status_message)
    except Exception as e:
        LOGGER.info(f"Error in scan_members: {e}")
        await message.reply("❌ An error occurred while scanning.")