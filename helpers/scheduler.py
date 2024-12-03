from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pyrogram.errors import PeerIdInvalid, ChatAdminRequired
from datetime import datetime
from db.connection import get_db
from db.subscription_helpers import fetch_soon_to_expire_subscriptions, fetch_expired_subscriptions
from helpers.text_helper import send_long_message, create_user_mention, create_channel_mention
from helpers.additional_bot_helpers import check_status
from helpers.additional_bot_to_db_helper import kick_and_unban_user
from bot.bot_instance import get_bot_instance
from db.user_helpers import delete_user_from_channel
from utils.config import Config
from utils.logger import LOGGER
from datetime import timedelta
async def daily_routine():
    LOGGER.info("Daily routine started")
    
    bot_instance = await get_bot_instance()
    response, can_procced = await check_status()
    for admin_id in Config.ADMIN_IDS:
        await send_long_message(bot_instance,admin_id,response)

    if can_procced:
        with next(get_db()) as session:
            # Fetch soon to expire subscriptions
            soon_to_expire = fetch_soon_to_expire_subscriptions(session)
            
            if soon_to_expire:
                # Create a message to send to the admin
                message = "Subscriptions that are soon to expire:\n\n"
                for subscription in soon_to_expire:
                    user_mention = create_user_mention(subscription.user.user_id, subscription.user.fullname)
                    channel_mention = create_channel_mention(subscription.channel.channel_name, subscription.channel.channel_id)
                    message += f"User: {user_mention}, Channel: {channel_mention}\n Expiry Date: {subscription.expiry_date}\n\n"
                
                # Send the message to the admin
                await send_long_message(bot_instance, Config.ADMIN_IDS[0], message)
            
            # Fetch expired subscriptions
            expired_subscriptions = fetch_expired_subscriptions(session)

            if expired_subscriptions:
                # Create a message to send to the admin
                message = "Subscriptions that have expired:\n\n"
                for subscription in expired_subscriptions:
                    user_mention = create_user_mention(subscription['user_id'], subscription['user_fullname'])
                    channel_mention = create_channel_mention(subscription['channel_name'], subscription['channel_id'])
                    message += f"User: {user_mention}, Channel: {channel_mention}, Expiry Date: {subscription['expiry_date']}\n\n"
                
                # Send the message to the admin
                await send_long_message(bot_instance, Config.ADMIN_IDS[0], message)
                
                # Remove expired subscriptions
                expired_users = []
                error_messages = []
                for subscription in expired_subscriptions:
                    try:
                        await kick_and_unban_user(subscription['user_id'], subscription['channel_id'])
                        if delete_user_from_channel(session, subscription['user_id'], subscription['channel_id']):
                            expired_users.append((subscription['user_id'], subscription['user_fullname']))
                        else:
                            error_messages.append(
                                f"Error removing user {subscription['user_id']} from channel {subscription['channel_id']}: "
                                f"Failed to remove from database."
                            )
                    except ChatAdminRequired:
                        error_messages.append(
                            f"Error removing user {subscription['user_id']} from channel {subscription['channel_id']}: "
                            f"Bot should be admin in this channel to remove users. Please kick and unban manually."
                        )
                    except (PeerIdInvalid, ValueError):
                        error_messages.append(
                            f"Error removing user {subscription['user_id']} from channel {subscription['channel_id']}: "
                            f"Let there be some interaction in the channel before using this feature. Please kick and unban manually."
                        )
                    except Exception as e:
                        error_messages.append(
                            f"Error removing user {subscription['user_id']} from channel {subscription['channel_id']}: "
                            f"{e}. Please kick and unban manually."
                        )

                # Create a message to send to the admin
                message = "Users that have been removed due to expired subscriptions:\n\n"
                for user_id, user_fullname in expired_users:
                    user_mention = create_user_mention(user_id, user_fullname)
                    message += f"{user_mention}\n\n"

                if error_messages:
                    message += "\nErrors occurred while removing users:\n\n"
                    for error_message in error_messages:
                        message += f"{error_message}\n\n"
                
                # Send the message to the admin
                await send_long_message(bot_instance, Config.ADMIN_IDS[0], message)
            
            LOGGER.info("Daily routine completed")

async def start_scheduler():
    scheduler = AsyncIOScheduler()
    current_date = datetime.now()
    next_run_time = current_date.replace(hour=0, minute=0, second=0, microsecond=0)
    if next_run_time < current_date:
        next_run_time += timedelta(days=1)
    scheduler.add_job(daily_routine, 'interval', minutes=1440, start_date=next_run_time)
    scheduler.start()
    LOGGER.info("Scheduler started")

async def run_daily_routine_manually():
    await daily_routine()