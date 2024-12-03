from bot import Bot
from pyrogram import Client, filters, errors
from pyrogram.types import Message
from pyrogram.errors import BadRequest, FloodWait, ChatAdminRequired
from db.connection import get_db
from db.subscription_helpers import add_subscription
from db.channel_helpers import get_all_channels, get_channel_link, update_channel_link, get_channel_mention
from db.user_helpers import get_user_mention, get_user_subscription
from pyrogram.types import InlineKeyboardButton,KeyboardButton, InlineKeyboardMarkup, CallbackQuery,ReplyKeyboardMarkup, Message
from pyrogram.errors import ChatAdminRequired, UserNotParticipant, PeerIdInvalid
from db.pendingrequest_helpers import check_pending_request, delete_pending_request
from helpers.filters import is_new_user_updating, admins_filter, devs_filter, is_deleting_channel_links_filter
from helpers.additional_bot_helpers import update_single_user_subscription
from utils.logger import LOGGER
from bot.bot_instance import get_bot_instance
import asyncio


"""
+=======================================================================================================+
--------------------------------      LIST OF FEATURES      --------------------------------------------
+=======================================================================================================+
Channel : Handling User joins
Admin : Handling Edit subscription for new user join
Admin : /deletelinks
Admin : /regenlink
+=======================================================================================================+
"""



# @Bot.on_chat_join_request()
# async def check_join_request(client: Client, message: Message):
#     user_id = message.from_user.id
#     channel_id = message.chat.id  # The group/channel ID where the request is coming from

#     # Log the incoming join request
#     LOGGER.info(f"Received join request from user {user_id} for channel/group {channel_id}")

#     # Open session to check if the user has a pending request
#     with next(get_db()) as db:
#         # Check if there is a pending request for this user in the current channel
#         if check_pending_request(db, user_id, channel_id):
#             LOGGER.info(f"User {user_id} has a pending request for channel/group {channel_id}. Accepting the request.")
            
#             # Accept the user into the group/channel
#             try:
#                 # Accepting the join request
#                 await client.approve_chat_join_request(channel_id, user_id)
#                 LOGGER.info(f"User {user_id} accepted into the group/channel {channel_id}.")

#                 # Remove the pending request from database
#                 if delete_pending_request(db, user_id, channel_id):
#                     LOGGER.info(f"Pending request removed for user {user_id} in channel/group {channel_id}.")
#                 else:
#                     LOGGER.warning(f"Failed to delete pending request for user {user_id} in channel/group {channel_id}.")

#                 # Add the user to the subscription (30 days by default)
#                 add_subscription(db, user_id, channel_id, days=30)
#                 LOGGER.info(f"Subscription added for user {user_id} in channel/group {channel_id} for 30 days.")

#                 # Fetch the current channel invite link
#                 current_link = get_channel_link(db, channel_id)
#                 LOGGER.info(f"Current invite link for channel/group {channel_id} is {current_link}")

#                 # Revoke the current invite link using Pyrogram
#                 if current_link:
#                     try:
#                         await client.revoke_chat_invite_link(channel_id, current_link)
#                         LOGGER.info(f"Revoked old invite link for channel/group {channel_id}.")
#                     except Exception as e:
#                         LOGGER.error(f"Error revoking invite link: {e}")

#                 # Create a new invite link
#                 new_link = await client.create_chat_invite_link(channel_id, creates_join_request=True)
#                 LOGGER.info(f"New invite link for channel/group {channel_id}: {new_link.invite_link}")

#                 # Update the invite link in the database
#                 if update_channel_link(db, channel_id, new_link.invite_link):
#                     LOGGER.info(f"Channel link updated successfully for channel/group {channel_id}.")
#                 else:
#                     LOGGER.warning(f"Failed to update channel link for channel/group {channel_id}.")
#             except Exception as e:
#                 LOGGER.error(f"Error accepting user {user_id} into group/channel {channel_id}: {e}")
#         else:
#             LOGGER.info(f"No pending request found for user {user_id} in channel/group {channel_id}. Doing nothing.")

# --------------------- Accept user join request automatically and ask admin for new user subscription duration updates----------------------------------------------------

@Bot.on_chat_join_request()
async def check_join_request(client: Client, message: Message):
    try:
        user_id = message.from_user.id
        channel_id = message.chat.id  # The group/channel ID where the request is coming from

        # Log the incoming join request
        LOGGER.info(f"Received join request from user {user_id} for channel/group {channel_id}")

        # Open session to check if the user has a pending request
        with next(get_db()) as session:  # Assuming get_session is a function to fetch DB session
            response = ()

            # Check if the join request is from a user who mistakenly left the group and still has a subscription running
            subscription = get_user_subscription(session, user_id, channel_id)
            if subscription is not None:
                await client.approve_chat_join_request(channel_id, user_id)
                bot_instance = await get_bot_instance()

                user_warn_text = (
                    f"🎉 You have been successfully accepted to {get_channel_mention(session,channel_id)}.\n\n"
                    f"😊 Please don't leave us when you still have an active subscription.\n\n"
                )
                await bot_instance.send_message(
                    chat_id=user_id,
                    text=user_warn_text
                )
                response = (
                    f"- - - User Subscription info - - -\n"
                    f"👤 {get_user_mention(session,user_id)}\n\n"
                    f"✨ {get_channel_mention(session,channel_id)}\n\n"
                    f"📅 Expires: `{subscription['expiry_date']}`\n\n\n"
                )
                await bot_instance.send_message(
                    chat_id=user_id,
                    text=response
                )
                return

            # Check if there is a pending request for this user in the current channel
            pending_exists, admin_id = check_pending_request(session, user_id, channel_id)
            if pending_exists:
                LOGGER.info(f"User {user_id} has a pending request for channel/group {channel_id}. Accepting the request.")
                # Accepting the join request
                await client.approve_chat_join_request(channel_id, user_id)

                add_subscription(session, user_id, channel_id, days=30)

                # Delete pending request after adding the user
                delete_pending_request(session, user_id, channel_id)
                
                # # Get the channel's invite link and revoke it (Pyrogram)
                # old_link = get_channel_link(session, channel_id)
                # try:
                #     await client.revoke_chat_invite_link(channel_id, old_link)
                #     LOGGER.info(f"Revoked old invite link for channel/group {channel_id}")
                # except Exception as e:
                #     LOGGER.error(f"Error revoking old link: {e}")
                
                # # Generate a new invite link
                # new_link = await client.create_chat_invite_link(channel_id, creates_join_request=True)
                # LOGGER.info(f"New invite link created for channel/group {channel_id}")
                
                # # Update the link in the database
                # update_channel_link(session, channel_id, new_link.invite_link)

                subscription = get_user_subscription(session, user_id, channel_id)
                if subscription is None:
                    LOGGER.error("Even after adding new user subscription, was unable to fetch subswcription at check_join_request.")
                    return
                response = (
                    f"- - - User Subscription info - - -\n"
                    f"👤 {get_user_mention(session,user_id)}\n\n"
                    f"✨ {get_channel_mention(session,channel_id)}\n\n"
                    f"📅 Expires: `{subscription['expiry_date']}`\n\n\n"
                )

                # Send a confirmation message to the admin about the successful user addition
                bot_instance = await get_bot_instance()

                user_message_text = (
                    f"🎉 You have been successfully added to {get_channel_mention(session,channel_id)}.\n\n"
                    f"😊 Wishing you all the best for what lies ahead.\n\n"
                )
                await bot_instance.send_message(
                    chat_id=user_id,
                    text=user_message_text
                )
                # to user
                await bot_instance.send_message(
                    chat_id=user_id,
                    text=response
                )
                await bot_instance.send_message(
                    chat_id=admin_id,
                    text=response
                )

                admin_message_text = (
                    f"🎉 User {get_user_mention(session, user_id)} has been successfully added to the group/channel {get_channel_mention(session,channel_id)}.\n\n"
                    f"✅ The user has been subscribed for 30 days by default.\n\n"
                    "Would you like to edit this subscription? You can either:\n"
                    "1. Change the duration\n"
                    "2. Remove the subscription (kick the user).\n\n"
                    "Please choose an action by clicking one of the options below."
                )

                edit_new_user_keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("Edit Subscription", callback_data=f"editsub_{user_id}_{channel_id}")],
                    [InlineKeyboardButton("Close", callback_data=f"updateNotNeeded_{user_id}_{channel_id}")]
                ])
                
                # Send message to the admin with buttons
                await bot_instance.send_message(
                    chat_id=admin_id,
                    text=admin_message_text,
                    reply_markup=edit_new_user_keyboard
                )
                
                LOGGER.info(f"Admin {admin_id} has been notified about the user addition.")
                return
            else:
                LOGGER.info(f"No pending request for user {user_id} in channel/group {channel_id}. Doing nothing.")

            


    except Exception as e:
        LOGGER.error(f"Error in check_join_request: {e}")


# Callback handler for the "Edit Subscription" button
@Bot.on_callback_query(filters.regex(r"editsub_\d+"))
async def handle_callback_query(client: Client, callback_query):
    try:# Acknowledge the callback query (to prevent "loading" circle on the client)
        await callback_query.answer()
        await callback_query.message.delete()
        admin_id = callback_query.message.chat.id
        user_id = int(callback_query.data.split("_")[1])
        channel_id = int(callback_query.data.split("_")[2])

        # Ask the admin to provide the update in the format 'duration' or 'kick'
        await callback_query.answer()
        await client.send_message(
            admin_id,
            "Please enter the update in one of the following format:\n"
            "1. 'duration' (e.g., '30d' or '30 d' for 30 days, '3m' or '3 m' for 3 months, '1y' or '1 y' for 1 year) __or__\n"
            "2. 'kick' to remove the user from the group/channel."
        )
        
        # Store the state of the update
        Bot.add_single_update_state(admin_id, {
            "user_id": user_id,
            "channel_id": channel_id,
        })
    except Exception as e:
        LOGGER.error(f"Error in /adduser handler: {e}")
        await callback_query.message.reply_text("❌ An error occurred while processing the command.")


@Bot.on_callback_query(filters.regex(r"updateNotNeeded_\d+"))
async def cancel(client: Client, callback_query: CallbackQuery):
    try:
        # Acknowledge the callback query (to prevent "loading" circle on the client)
        await callback_query.answer()
        await callback_query.message.delete()
    except Exception as e:
        LOGGER.error(f"Error in /adduser handler: {e}")
        await callback_query.message.reply_text("❌ An error occurred while processing the command.")


# ------------------------- listens for admin inputs for updating new user subscription
@Bot.on_message(is_new_user_updating)
async def handle_new_user_update(client: Client, message: Message):
    try:
        admin_id = message.from_user.id
        user_data = Bot.get_single_update_state(admin_id)
    # A good idea -    # if admin_state and admin_state.get("action") == "edit_subscription":
        user_id = user_data['user_id']
        channel_id = user_data['channel_id']
    
        line = message.text.strip().lower()
        parts = line.strip().split()

        if line in ("cancel" or "done"):
            Bot.delete_single_update_state(message.from_user.id)
            await message.reply_text("Cancelled Editing operation. User subscription stays for the defailt: 30 days.")
            return
        if len(parts) == 1:
            duration_text = parts[0]
        elif len(parts) == 2:
            duration_text = parts[0] + parts[1]
        else:
            await message.reply_text(
                f"**Invalid format**\n\n"
                "Please enter the update in one of the following formats:\n\n"
                "1. **Quantity + Duration Symbol**\n"
                "   - For **days**: 'quantity d' (e.g., '25d', '35 d')\n"
                "   - For **months**: 'quantity m' (e.g., '3m', '5 m')\n"
                "   - For **years**: 'quantity y' (e.g., '1y', '2 y')\n\n"
                "2. **'kick'** to remove the user from the group/channel.\n\n"
                "If you want to abort the operation send **cancel** to cancel the update"
            )
            return
        
        with next(get_db()) as session:
            try:
                if duration_text.strip().lower() == "kick":
                    is_success, result = await update_single_user_subscription(session, user_id, channel_id, duration_text)
                    await message.reply_text(result)
                    return

                is_success, result = await update_single_user_subscription(session, user_id, channel_id, duration_text)
                if not is_success:
                    await message.reply_text(result)
                    return

                is_success, final_result = await update_single_user_subscription(session, user_id, channel_id, "-30d") # roll back to set newly
                if not is_success:
                    await message.reply_text(final_result)
                    return
                await message.reply_text(final_result)
            except Exception as e:
                LOGGER.error(f"Error occured in input given by admin : {str(e)}")
                await message.reply_text(
                    f"**Invalid format**\n\n"
                    "Please enter the update in one of the following formats:\n\n"
                    "1. **Quantity + Duration Symbol**\n"
                    "   - For **days**: 'quantity d' (e.g., '25d', '35 d')\n"
                    "   - For **months**: 'quantity m' (e.g., '3m', '5 m')\n"
                    "   - For **years**: 'quantity y' (e.g., '1y', '2 y')\n\n"
                    "2. **'kick'** to remove the user from the group/channel.\n\n"
                    "If you want to abort the operation send **cancel** to cancel the update"
                )
                return
        
        # After the update is done, clear the update state
        Bot.delete_single_update_state(message.from_user.id)
    except Exception as e:
        LOGGER.error(f"Error in handle_new_user_update: {e}")
        await message.reply_text("❌ An error occurred while processing the command.")

# -------------------------- delete excess links that bot have created ----------------------------------------

@Bot.on_message(filters.command("deletelinks") & filters.private & (admins_filter | devs_filter))
async def delete_links_handle(client: Client, message: Message):
    """
    Handles the /adduser command to add a new user with a subscription to a channel.
    """
    try:
        LOGGER.info("Received /deletelinks command.")
        with next(get_db()) as session:
            # Fetch the list of channels
            channels = get_all_channels(session)
            if not channels:
                LOGGER.warning("No managed channels found in the database.")
                await message.reply_text("No managed channels available.")
                return

            # Display channels as inline buttons
            buttons = [
                [InlineKeyboardButton(channel["name"], callback_data=f"deletelinks_{channel['id']}_{channel['name']}")]
                for channel in channels
            ]
            LOGGER.info(f"Displaying channels for selection to deletelinks: {[channel['id'] for channel in channels]}")
            await message.reply_text(
                "Select a channel to start deleting links:",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
    except Exception as e:
        LOGGER.error(f"Error in /deletelinks handler: {e}")
        await message.reply_text("❌ An error occurred while processing the command /deletelinks.")

@Bot.on_callback_query(filters.regex(r"deletelinks_-\d+"))
async def callback_delete_link(client: Client, callback_query: CallbackQuery):
    """
    Handles subscription updates for a selected channel.
    """
    try:
        await callback_query.answer()
        channel_id = int(callback_query.data.split("_")[1])
        channel_name = callback_query.data.split("_")[2]
        admin_id = callback_query.message.chat.id
        Bot.state.set_state("delete_links",admin_id,{
            "channel_id" : channel_id,
            "channel_name" : channel_name
        })
        await callback_query.message.reply_text(f'Please send all links of **{channel_name}** (ID:{channel_id}), each in seperate lines. Or use "done" or "stop" to exit process.')

    except Exception as e:
        LOGGER.error(f"Error in callback_delete_link: {e}")
        await callback_query.message.reply_text("❌ An error occurred while trying to show info about delete links.")

@Bot.on_message(is_deleting_channel_links_filter)
async def delete_multiple_links(client: Client, message: Message):
    admin_id = message.from_user.id
    channel_data = Bot.state.get_state("delete_links",admin_id)
    channel_id = channel_data['channel_id']
    channel_name = channel_data['channel_name']
    
    if message.text.strip().lower() in ['done', 'stop']:
        Bot.state.delete_state("delete_links",admin_id)
        await message.reply_text("Process Succesfully stopped")
        return
    # Step 1: Clean up the input message
    cleaned_lines = [
        line.strip() for line in message.text.strip().splitlines() if line.strip()
    ]  # Stripping each line and removing empty lines

    # This will track the results of the revoking and deletion of each link
    results = f"Status of deleting links from **{channel_name}** (ID:{channel_id})\n\n"

    bot_instance = await get_bot_instance()

    # Step 2: Loop through each cleaned line (which should be a link)
    for link in cleaned_lines:
        try:
            # Step 3: Revoke the invite link
            revoke_result = await bot_instance.revoke_chat_invite_link(chat_id=channel_id,invite_link=link)
            LOGGER.info(f"Revoked channel {channel_id} chat link {link}")

            # Step 5: Keep track of successful revocation and deletion
            results +=f"Successfully revoked link: {link}\n"
            if link in ["done", "stop", "cancel"]:
                Bot.state.delete_state("delete_links",admin_id)
                await message.reply_text("Process Succesfully stopped")
                await message.reply_text(results)
                return
        
        except BadRequest as e:
            # Handle known exceptions, such as invalid links
            results +=f"Failed for link: {link} - BadRequest: {e}"
        except FloodWait as e:
            # Handle flood wait (we wait for the required time, then continue)
            results +=f"FloodWait for link: {link} - Waiting for {e.value} seconds"
            await asyncio.sleep(e.value)
        except Exception as e:
            # Catch any other errors, log them, and continue
            results.append(f"Error for link: {link} - {str(e)}")

    # Step 6: Return the final result summary
    await message.reply_text(results)

# --------------------------------- Regenerate links --------------------------------------

@Bot.on_message(filters.command("regenlink") & filters.private & admins_filter)
async def regen_link_handler(client: Client, message: Message):
    """
    Handles the /regenlink command to regenerate invite links for the channels.
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
                [InlineKeyboardButton(channel["name"], callback_data=f"regen_{channel['id']}")]
                for channel in channels
            ]
            await message.reply_text(
                "Select a channel to regenerate invite link:",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
    except Exception as e:
        LOGGER.error(f"Error in /regenlink: {e}")
        await message.reply_text("❌ An error occurred while processing the command.")

@Bot.on_callback_query(filters.regex(r"regen_-\d+"))
async def handle_link_regeneration(client: Client, callback_query: CallbackQuery):
    """
    Handles the regeneration of invite links for a selected channel.
    """
    try:
        # Extract channel_id from the callback data
        channel_id = int(callback_query.data.split("_")[1])
        admin_id = callback_query.message.chat.id
        
        # Acknowledge the callback query (to prevent "loading" circle on the client)
        await callback_query.answer()

        # Fetch the current link from the database
        with next(get_db()) as db:
            existing_link = get_channel_link(db, channel_id)
            if not existing_link:
                await callback_query.message.reply_text("❌ No link found for this channel.")
                return

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
            with next(get_db()) as db:
                if update_channel_link(db, channel_id, invite_link):
                    LOGGER.info(f"New invite link for channel {channel_id} generated: {new_link}")
                    await callback_query.message.reply_text(f"✅ New invite link for channel {channel_id} generated:\n{invite_link}")
                else:
                    LOGGER.error(f" Failed to update the link for channel {channel_id}.")
                    await callback_query.message.reply_text(f"❌ Failed to update the link for channel {channel_id}.")
    except ChatAdminRequired as e:
        LOGGER.warning("ChatAdminRequired to regen links")
        await callback_query.message.reply_text("⚠️ Bot must be admin in the channel to perform the action. ")
    except PeerIdInvalid as e:
        LOGGER.warning("PeerIdInvalid in regen links")
        await callback_query.message.reply_text("⚠️ Please chack if Bot is present in channel and interact with the chanel once before you use this command. This is only needed on new startup of bot.")
    except Exception as e:
        LOGGER.error(f"Error type: {type(e)} | Message: {str(e)}")
        LOGGER.error(f"Error in /regenlink callback: {e}")
        await callback_query.message.reply_text("❌ An error occurred while processing the link regeneration.")