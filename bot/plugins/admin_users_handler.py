import random
from bot import Bot
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message
from pyrogram.errors import FloodWait, ChatAdminRequired, UserNotParticipant, PeerIdInvalid, UserBannedInChannel
from helpers.filters import admins_filter,normal_filter, is_bulk_updating
from db.connection import get_db
from db.user_helpers import get_user_channels, get_user_subscription
from db.channel_helpers import get_all_channels, get_channel_mention, get_invite_link
from db.subscription_helpers import get_subscriptions, update_subscription
from db.verification_helpers import generate_verification_code, validate_and_add_user
from utils.logger import LOGGER
from bot.bot_instance import get_bot_instance
from helpers.text_helper import sanitize_fullname, send_long_message
from helpers.additional_bot_helpers import update_single_user_subscription



"""
+=======================================================================================================+
--------------------------------      LIST OF FEATURES      --------------------------------------------
+=======================================================================================================+
Admin : /adduser
Admin : /verify <code> or /code <code>
Admin : /showusers
Admin : /updatesubscriptions
Admin :  /updateuser <user_id> <duration>
+=======================================================================================================+
"""



# ------------------------------------  Adding User - /adduser --------------------------------------------------


@Bot.on_message(filters.command("adduser") & filters.private & admins_filter)
async def add_user_handler(client: Client, message: Message):
    """
    Handles the /adduser command to add a new user with a subscription to a channel.
    """
    try:
        LOGGER.info("Received /adduser command.")
        with next(get_db()) as db:
            # Fetch the list of channels
            channels = get_all_channels(db)
            if not channels:
                LOGGER.warning("No managed channels found in the database.")
                await message.reply_text("No managed channels available.")
                return

            # Display channels as inline buttons
            buttons = [
                [InlineKeyboardButton(channel["name"], callback_data=f"adduser_{channel['id']}_{channel['name']}")]
                for channel in channels
            ]
            LOGGER.info(f"Displaying channels for selection: {[channel['id'] for channel in channels]}")
            await message.reply_text(
                "Select a channel to add a user:",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
    except Exception as e:
        LOGGER.error(f"Error in /adduser handler: {e}")
        await message.reply_text("❌ An error occurred while processing the command.")


@Bot.on_callback_query(filters.regex(r"adduser_-\d+"))
async def generate_verification(client: Client, callback_query: CallbackQuery):
    """
    Handles the callback for selecting a channel and generates a verification code.
    """
    try:
        LOGGER.info("Received callback query for adding a user.")
        channel_id = int(callback_query.data.split("_")[1])
        channel_name = callback_query.data.split("_")[2]
        admin_id = callback_query.message.chat.id

        # Acknowledge the callback query (to prevent "loading" circle on the client)
        await callback_query.answer()

        # Delete the original message containing the buttons
        await callback_query.message.delete()

        LOGGER.debug(f"Channel ID: {channel_id}, Admin ID: {admin_id}")
        with next(get_db()) as db:
            # Generate verification code
            verification_code = generate_verification_code(db, admin_id, channel_id)
            LOGGER.info(f"Generated verification code: {verification_code.code} for channel ID: {channel_id}")

            await callback_query.answer("Verification code generated successfully.")
            await callback_query.message.reply_text(
                f"Generated verification code for {channel_name}: `{verification_code.code}`\n\n"
                "Please ask the user to send this code to the bot within **10 minutes**.\n\n"
                "They can use either of the following commands to send the code:\n"
                "`/code <verification_code>`\n"
                "`/verify <verification_code>`\n\n"
                "**Copyable command for easy use:**\n"
                f"`/code {verification_code.code}` or `/verify {verification_code.code}`",
                parse_mode=ParseMode.MARKDOWN
            )
    except Exception as e:
        LOGGER.error(f"Error in generate_verification callback: {e}")
        await callback_query.answer("❌ An error occurred while generating the verification code.", show_alert=True)
        await callback_query.message.reply_text("❌ An error occurred while generating the code.")

@Bot.on_message(filters.command(["code", "verify"]) & filters.private & normal_filter)
async def validate_user(client: Client, message: Message):
    """
    Validates the verification code sent by the user.
    """
    try:
        LOGGER.info("Received private message for verification.")
        user_id = message.from_user.id
        code = message.command[1]
        fullname = await sanitize_fullname(message.from_user.first_name, message.from_user.last_name)
        username = message.from_user.username or "Unknown"

        LOGGER.debug(f"User ID: {user_id}, Verification Code: {code}, Username: {username}")
        with next(get_db()) as db:
            is_valid, channel_id, is_new_to_channel, admin_id = validate_and_add_user(db, user_id, code, username, fullname)
            channel_mention = get_channel_mention(db, channel_id)

            bot_instance = await get_bot_instance()

            if is_valid:
                if is_new_to_channel:
                    LOGGER.info(f"User {username} (ID: {user_id}) is now authorised to {channel_mention} (ID: {channel_id}) successfully.")
                    info = await message.reply_text("✅ You have been successfully authorised!")
                    
                    invite_link = get_invite_link(db,channel_id)
                    if invite_link:
                        # Notify the user with the invite link
                        await info.edit_text(
                            f"You can now join the channel using this invite link. Once you request to join, you'll be accepted shortly:\n\n"
                            f"{invite_link}"
                        )
                        await bot_instance.send_message(
                            chat_id=admin_id, 
                            text=f"✅ {fullname} (`{user_id}`) has been granted access to {channel_mention} successfully!"
                        )
                        return
                    # else
                    # Inform the user there was an issue generating the invite link
                    await info.edit_text(
                        "There was an issue generating your invite link. Please contact the admin and try again later."
                    )
                    await bot_instance.send_message(
                        chat_id=admin_id,
                        text=f"❌ **{fullname}** - `{user_id}` could not get the invite link for {channel_mention}. "
                            f"Please try again later. If the problem continues, delete the bot's invite link from the channel and use `/genlink` "
                            f"to create a new one. Store the new link in the database and try the process again."
                    )
                    return
                LOGGER.info(f"User {username} (ID: {user_id}) is already present in the channel.")
                await message.reply_text("ℹ️ You are already present in the channel.")
                subscription_info = get_user_subscription(db, user_id, channel_id)

                response = (
                    f"- - - User is already present in {channel_mention} - - -\n"
                    f'👤 [{subscription_info["user_fullname"]}](tg://user?id={subscription_info["user_id"]})\n\n'
                    f"📅 Expires: `{subscription_info['expiry_date']}`\n\n\n"
                )
                await bot_instance.send_message(chat_id=admin_id, text=response)
                LOGGER.info(f"{fullname} - `{user_id}` is already present in `{channel_mention}`")
            else:
                LOGGER.warning(f"Invalid or expired verification code received from User ID: {user_id}.")
                await message.reply_text("❌ Invalid or expired verification code.")
    except Exception as e:
        LOGGER.error(f"Error in validate_user: {e}")
        await message.reply_text("❌ An error occurred during verification.")


# ---------------------------------- Show Users - /showusers ------------------------------------


@Bot.on_message(filters.command("showusers") & filters.private & admins_filter)
async def show_users_handler(client: Client, message: Message):
    """
    Handles the /showusers command to display all users in a channel.
    """
    try:
        with next(get_db()) as db:
            # Fetch the list of channels
            channels = get_all_channels(db)
            if not channels:
                await message.reply_text("No managed channels available.")
                return

            # Display channels as inline buttons
            buttons = [
                [InlineKeyboardButton(channel["name"], callback_data=f"show_{channel['id']}_{channel['name']}")]
                for channel in channels
            ]
            await message.reply_text(
                "Select a channel to show users:",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
    except Exception as e:
        LOGGER.error(f"Error in /showusers: {e}")
        await message.reply_text("❌ An error occurred while processing the command.")

@Bot.on_callback_query(filters.regex(r"show_-\d+"))
async def handle_show_users(client: Client, callback_query: CallbackQuery):
    """
    Displays the list of users in the selected channel.
    """
    try:  
        channel_id = int(callback_query.data.split("_")[1])
        channel_name = callback_query.data.split("_")[2]
        admin_id = callback_query.message.chat.id

        # Acknowledge the callback query (to prevent "loading" circle on the client)
        await callback_query.answer()

        # Delete the original message containing the buttons
        await callback_query.message.delete()

        found, subscriptions = await get_users_list(channel_id)
        if not found:
            await callback_query.message.reply_text(f"ℹ️ No users found in **{channel_name}**")
            return
        
        waiting_msg = await callback_query.message.reply_text("Please wait loading users info...")
        response = await format_users_list(channel_name, subscriptions)

        await send_long_message(client, admin_id, response)
        await waiting_msg.delete()
    except Exception as e:
        LOGGER.error(f"Error showing users handle_show_users: {e}")
        await callback_query.message.reply_text("❌ An error occurred while showing users.")


# -------------------------- Helper Functions to get user list 

# helper function to get users list
async def get_users_list(channel_id):
    with next(get_db()) as db:
        subscriptions = get_subscriptions(db, channel_id)
        if not subscriptions:
            return False, None
        return True, subscriptions
    
async def format_users_list(channel_name, subscriptions):
    """
    Formats the list of subscriptions into a readable string.

    :param channel_name: The name of the channel for display purposes.
    :param subscriptions: List of subscription dictionaries.
    :return: A formatted string containing user information.
    """
    response = f"__Users in the Channel__ - **{channel_name}**:\n\n"
    for idx, sub in enumerate(subscriptions, start=1):
        full_name = sub['fullname']
        user_id = sub['user_id']
        expiry_date = sub['expiry_date']

        response += (
            f"- - - User #{idx} - - -\n"
            f"👤 [{full_name}](tg://user?id={user_id})\n\n"
            f"📅 Expires: `{expiry_date}`\n\n\n"
        )
    return response

# ---------------------------------- Update Subscription bulk - /updatesubscriptions ------------------------------------


@Bot.on_message(filters.command("updatesubscriptions") & filters.private & admins_filter)
async def update_subscription_handler(client: Client, message: Message):
    """
    Handles the /updatesubscription command to update user subscriptions in a channel.
    """
    try:
        with next(get_db()) as db:
            # Fetch the list of channels
            channels = get_all_channels(db)
            if not channels:
                await message.reply_text("No managed channels available.")
                return

            # Display channels as inline buttons
            buttons = [
                [InlineKeyboardButton(channel["name"], callback_data=f"updates_{channel['id']}_{channel['name']}")]
                for channel in channels
            ]
            await message.reply_text(
                "Select a channel to update subscriptions:",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
    except Exception as e:
        LOGGER.error(f"Error in /updatesubscription: {e}")
        await message.reply_text("❌ An error occurred while processing the command.")

@Bot.on_callback_query(filters.regex(r"updates_-\d+"))
async def handle_subscription_update(client: Client, callback_query: CallbackQuery):
    """
    Handles subscription updates for a selected channel.
    """
    try:
        channel_id = int(callback_query.data.split("_")[1])
        channel_name = callback_query.data.split("_")[2]
        admin_id = callback_query.message.chat.id

        # Acknowledge the callback query (to prevent "loading" circle on the client)
        await callback_query.answer()

        # Delete the original message containing the buttons
        await callback_query.message.delete()

        found, subscriptions = await get_users_list(channel_id)
        if not found:
            await callback_query.message.reply_text(f"ℹ️ No users found in {channel_name}")
            return
        
        waiting_msg = await callback_query.message.reply_text("Please wait loading users info...")
        response = await format_users_list(channel_name, subscriptions)

        await send_long_message(client, admin_id, response)
        await waiting_msg.delete()
        
        help_message = (
            f"**Help for Bulk Subscription Update Command**\n\n"
            f"To update multiple user's subscriptions at once, follow these simple steps:\n\n"
            
            f"**Input Format**:\n"
            f"1. **User Index + Duration**: \n"
            f"- To update the subscription of a user, provide the user's index (e.g., #1, #2 without '#') followed by the duration or specific date.\n\n"
            
            f"**Example Inputs**:\n"
            f"- `9 3d`: Update user #9 to expire in 3 days.\n"
            f"- `2 3d`: Update user #2 to expire in 3 days.\n"
            f"- `1 2y`: Update user #1 to expire in 2 years.\n"
            f"- `3 2023-11-23`: Set user #3's expiry date to 23rd Nov 2023.\n"
            f"- `23 11-01-2023`: Set user #23's expiry date to 1st Nov 2023.\n"
            f"- `2 1y`: Update user #2 to expire in 1 year.\n\n"
            
            f"**Duration Formats**:\n"
            f"- `\"Xd\"` or `\"X d\"` for X days (e.g., `\"3d\"` for 3 days).\n"
            f"- `\"Xw\"` or `\"X w\"` for X weeks (e.g., `\"2w\"` for 2 weeks).\n"
            f"- `\"Xm\"` or `\"X m\"` for X months (e.g., `\"6m\"` for 6 months).\n"
            f"- `\"Xy\"` or `\"X y\"` for X years (e.g., `\"1y\"` for 1 year).\n"
            f"- Exact dates in either of these formats:\n"
            f"  - `\"DD-MM-YYYY\"` (e.g., `\"25-12-2024\"`)\n"
            f"  - `\"YYYY-MM-DD\"` (e.g., `\"2024-12-25\"`)\n\n"
            
            f"**How to Stop**:\n"
            f"When you're done providing the updates, send **`done`** or **`stop`** to finalize the process.\n\n"
            
            f"**Example Usage**:\n"
            f"\n`1 10d\n2 3w\n3 2023-12-25`\n This above one will Update user #1 for 10 days, user #2 for 3 weeks, and set user #3's expiry to 25th December 2023.\n"
            f"\n`5 2y\n6 2024-11-01`\n This above one will Update user #5 for 2 years and user #6 to expire on 1st November 2024.\n\n"
            
            f"Start by typing the updates below."
        )
        await callback_query.message.reply_text(help_message)

        # Store the necessary data in a context dictionary or database
        user_data = {
            'channel_id': channel_id,
            'channel_name': channel_name,
            'subscriptions': subscriptions
        }
        Bot.add_bulk_update_state(admin_id, user_data)

    except Exception as e:
        LOGGER.error(f"Error updating subscriptions handle_subscription_update: {e}")
        await callback_query.message.reply_text("❌ An error occurred while updating subscriptions.")

# ------------------------- listens for admin inputs for updating subscriptions

@Bot.on_message(is_bulk_updating)
async def process_admin_input(client: Client, message: Message):
    """
    Processes the admin's input for updating subscriptions.
    """
    try:
        admin_id = message.from_user.id

        # Retrieve stored data - Check if this is the same admin who used /updatesubscription
        user_data = Bot.get_bulk_update_state(admin_id)
        
        channel_id = user_data['channel_id']
        channel_name = user_data['channel_name']

        if message.text.strip().lower() in ['done', 'stop']:
            print(f"text - {message.text.strip().lower()} and bool - {message.text.strip().lower() in ['done', 'stop']}")
            Bot.delete_bulk_update_state(admin_id)
            await message.reply_text("Subscription updates process completed.")
            #sending the updated list
            found , subscriptions = await get_users_list(channel_id)
            if not found:
                await message.reply_text(f"ℹ️ No users found in {channel_name}")
                return
            
            response = await format_users_list(channel_name, subscriptions)
            
            waiting_msg = await message.reply_text("Please wait loading users info...")
            await send_long_message(client, admin_id, response)
            await waiting_msg.delete()
            return

        # Process the admin's input
        updates = message.text.strip().lower()
        update_lines = updates.split('\n')

        results = []
        for line in update_lines:
            if not line.strip():
                continue  # Skip empty lines

            parts = line.strip().split()
            idx = parts[0]
            if not idx.isdigit():
                results.append(f"Invalid index '{idx}'.")
                continue

            idx = int(idx) - 1  # Adjust for zero-based index
            if idx < 0 or idx >= len(user_data['subscriptions']):
                results.append(f"Index '{idx + 1}' is out of range.")
                continue

            subscription = user_data['subscriptions'][idx]
            user_id = subscription['user_id']

            # Determine the action
            if len(parts) == 1:
                # Default extension
                duration_text = '30d'
            elif len(parts) == 2:
                duration_text = parts[1]
            elif len(parts) == 3:
                duration_text = parts[1] + parts[2]
            else:
                results.append(f"Invalid format in line: '{line}'.")
                continue

            # Update the subscription
            with next(get_db()) as db:
                try:
                    _, result = await update_single_user_subscription(db, user_id, channel_id, duration_text)
                    results.append(result)
                except Exception as e:
                    results.append(f"Error updating user {user_id}: {str(e)}")

        # Send the update results to the admin
        await message.reply_text('\n'.join(results) + "\n\nYou can enter more updates or type 'done' to finish.")
    except Exception as e:
        LOGGER.error(f"Error processing admin input process_admin_input: {e}")
        await message.reply_text("❌ An error occurred while processing your input.")


# --------------------------------- Update Single user - /updateuser --------------------------------------

@Bot.on_message(filters.command("updateuser") & filters.private & admins_filter)
async def update_user_subscription(client: Client, message: Message):
    try:
        if len(message.command) < 2 or len(message.command) > 4:
            await message.reply_text("Usage: /updateuser <user_id> [<duration>]", parse_mode = ParseMode.MARKDOWN)
            return

        user_id = message.command[1]
        duration_text = message.command[2] if len(message.command) > 2 else "30d"
        duration_text += message.command[3] if len(message.command) > 3 else ""

        with next(get_db()) as db:
            channels = get_user_channels(db, int(user_id))
            
            if not channels:
                await message.reply_text(f"No channels found for user {user_id}.")
                return

            # Create inline keyboard with channel options
            keyboard = [
                [InlineKeyboardButton(f"{channel['channel_name']}", callback_data=f"updatesingle_{user_id}_{channel['channel_id']}_{duration_text}")]
                for channel in channels
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await message.reply_text("Choose the channel to update:", reply_markup=reply_markup)
    except Exception as e:
        LOGGER.error(f"Error updating subscription update_user_subscription: {e}")
        await message.message.reply_text("❌ An error occurred while tring to update user subscription : {e}")

@Bot.on_callback_query(filters.regex(r"updatesingle_[a-z0-9_-]+"))
async def callback_update_subscription(client: Client, callback_query: CallbackQuery):
    try:
        _, user_id, channel_id, duration_text = callback_query.data.split('_')
        user_id, channel_id = int(user_id), int(channel_id)
        
        with next(get_db()) as db:
            try:
                result = await update_subscription(db, user_id, channel_id, duration_text)
                await callback_query.answer(result)
                await callback_query.message.edit_text(result)
            except Exception as e:
                LOGGER.error(f"Error occured in input given by admin : {str(e)}")
                await callback_query.answer(f"An error occurred: \n{str(e)}")
                await callback_query.message.edit_text(f"Failed to update subscription : \n{str(e)}")
    except Exception as e:
        LOGGER.error(f"Error updating subscription callback_update_subscription : {e}")
        await callback_query.message.reply_text("❌ An error occurred while trying to update user subscription: {e}")

