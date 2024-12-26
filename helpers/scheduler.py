from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pyrogram.errors import PeerIdInvalid, ChatAdminRequired
from datetime import datetime
from db.connection import get_db
from db.admin_helpers import get_admin_for_channel, list_admins
from db.subscription_helpers import fetch_soon_to_expire_subscriptions, fetch_expired_subscriptions
from helpers.text_helper import send_long_message, create_user_mention, create_channel_mention
from helpers.additional_bot_helpers import check_status
from helpers.additional_bot_to_db_helper import kick_and_unban_user
from bot.bot_instance import get_bot_instance
from db.user_helpers import delete_user_from_channel
from utils.config import Config
from utils.logger import LOGGER
from datetime import timedelta

async def daily_routine(admin_id: int = None):
    try:
        LOGGER.info("Daily routine started")
        
        bot_instance = await get_bot_instance()
        LOGGER.info("Entering Checking status")
        admin_status_reports, can_proceed = await check_status(admin_id) # Get admin-specific status reports
        LOGGER.info("Completed Checking status")

        
        # If admin_id is provided, only process for that admin
        if admin_id:
            if admin_id in admin_status_reports:
                await send_long_message(bot_instance, admin_id, admin_status_reports[admin_id])
            else:
                LOGGER.warning(f"No status report found for admin_id: {admin_id}")
        elif admin_id is None:
            # Process all admins if no specific admin_id is provided
            for admin_id, status_report in admin_status_reports.items():
                await send_long_message(bot_instance, admin_id, status_report)

        if can_proceed:
            with next(get_db()) as session:
                # Fetch and process soon to expire subscriptions
                LOGGER.info("Trying to fetch soon to expire subscriptions")
                soon_to_expire = fetch_soon_to_expire_subscriptions(session, admin_id)
                LOGGER.info("Done fetching soon to expire subscriptions")
                
                # Group subscriptions by channel
                channel_subscriptions = {}
                for subscription in soon_to_expire:
                    channel_id = subscription.channel.channel_id
                    if channel_id not in channel_subscriptions:
                        channel_subscriptions[channel_id] = []
                    channel_subscriptions[channel_id].append(subscription)
                
                # Send notifications to relevant channel admins
                for channel_id, subscriptions in channel_subscriptions.items():
                    message = "Subscriptions that are soon to expire:\n\n"
                    for subscription in subscriptions:
                        user_mention = create_user_mention(subscription.user.user_id, subscription.user.fullname)
                        channel_mention = create_channel_mention(subscription.channel.channel_name, subscription.channel.channel_id)
                        message += f"User: {user_mention}, Channel: {channel_mention}\n Expiry Date: {subscription.expiry_date}\n\n"
                    
                    # Get admins for this channel and send them the message
                    channel_admins = get_admin_for_channel(session, channel_id)
                    for admin in channel_admins:
                        await send_long_message(bot_instance, admin.admin_id, message)
                
                # Handle expired subscriptions
                expired_subscriptions = fetch_expired_subscriptions(session, admin_id)
                
                if expired_subscriptions:
                    # Group expired subscriptions by channel
                    expired_by_channel = {}
                    for subscription in expired_subscriptions:
                        channel_id = subscription['channel_id']
                        if channel_id not in expired_by_channel:
                            expired_by_channel[channel_id] = []
                        expired_by_channel[channel_id].append(subscription)
                    
                    # Process each channel's expired subscriptions
                    for channel_id, channel_expired in expired_by_channel.items():
                        expired_users = []
                        error_messages = []
                        
                        # Process removals
                        for subscription in channel_expired:
                            try:
                                await kick_and_unban_user(subscription['user_id'], channel_id)
                                if delete_user_from_channel(session, subscription['user_id'], channel_id):
                                    expired_users.append((subscription['user_id'], subscription['user_fullname']))
                                else:
                                    error_messages.append(
                                        f"Error removing user {subscription['user_id']} from channel {channel_id}: "
                                        f"Failed to remove from database."
                                    )
                            except ChatAdminRequired:
                                error_messages.append(
                                    f"Error removing user {subscription['user_id']} from channel {channel_id}: "
                                    f"Bot should be admin in this channel to remove users. Please kick and unban manually."
                                )
                            except (PeerIdInvalid, ValueError):
                                error_messages.append(
                                    f"Error removing user {subscription['user_id']} from channel {channel_id}: "
                                    f"Let there be some interaction in the channel before using this feature. Please kick and unban manually."
                                )
                            except Exception as e:
                                error_messages.append(
                                    f"Error removing user {subscription['user_id']} from channel {channel_id}: "
                                    f"{e}. Please kick and unban manually."
                                )

                        # Create report message
                        message = "Users that have been removed due to expired subscriptions:\n\n"
                        for user_id, user_fullname in expired_users:
                            user_mention = create_user_mention(user_id, user_fullname)
                            message += f"{user_mention}\n\n"

                        if error_messages:
                            message += "\nErrors occurred while removing users:\n\n"
                            for error_message in error_messages:
                                message += f"{error_message}\n\n"
                        
                        # Send report to channel admins
                        channel_admins = get_admin_for_channel(session, channel_id)
                        for admin in channel_admins:
                            await send_long_message(bot_instance, admin.admin_id, message)
                
                LOGGER.info("Daily routine completed")
    except Exception as e:
        LOGGER.error(f"Error in daily_routine : {e}")


async def start_scheduler():
    scheduler = AsyncIOScheduler()
    current_date = datetime.now()
    next_run_time = current_date.replace(hour=0, minute=0, second=0, microsecond=0)
    if next_run_time < current_date:
        next_run_time += timedelta(days=1)
    scheduler.add_job(daily_routine, 'interval', minutes=1440, start_date=next_run_time)
    scheduler.start()
    LOGGER.info("Scheduler started")

async def run_daily_routine_manually(admin_id):
    await daily_routine(admin_id)
