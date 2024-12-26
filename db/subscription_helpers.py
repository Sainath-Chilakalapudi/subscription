from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import NoResultFound
from sqlalchemy import select, delete, func
from datetime import datetime, timedelta
from db.models import User, AdminChannel, Subscription, Channel
from db.user_helpers import delete_user_from_channel, get_user_mention
from db.admin_helpers import is_channel_admin
from helpers.additional_bot_to_db_helper import kick_and_unban_user
from pyrogram.errors import FloodWait, ChatAdminRequired, UserNotParticipant, PeerIdInvalid, UserBannedInChannel
from db.channel_helpers import get_channel_mention
from utils.logger import LOGGER


def is_valid_date(date_str: str) -> bool:
    """Checks if the given date string is in DD-MM-YYYY format and valid."""
    try:
        datetime.strptime(date_str, "%d-%m-%Y")
        return True
    except ValueError:
        return False

def add_subscription(session: Session, user_id: int, channel_id: int, admin_id: int, days: int = 30):
    """Add subscription with admin verification"""
    try:
        # Verify admin has rights to this channel
        if not is_channel_admin(session, admin_id, channel_id):
            raise ValueError(f"Admin {admin_id} does not have rights to this channel {channel_id}")

        subscription = (
            session.query(Subscription)
            .filter(Subscription.user_id == user_id, 
                   Subscription.channel_id == channel_id)
            .first()
        )
        
        if not subscription:
            expiry_date = datetime.now().date() + timedelta(days=days)
            subscription = Subscription(
                user_id=user_id, 
                channel_id=channel_id, 
                expiry_date=expiry_date
            )
            session.add(subscription)
            session.commit()
            LOGGER.info(f"Admin {admin_id} added subscription for user {user_id} to channel {channel_id}")
        return subscription
    except Exception as e:
        session.rollback()
        LOGGER.error(f"Error adding subscription: {e}")
        return None

def get_subscriptions(session: Session, channel_id: int):
    """
    Fetches all users subscribed to a specific channel along with their subscription details.

    Args:
        channel_id (int): The ID of the channel to fetch subscriptions for.
        session (Session): The active SQLAlchemy session.

    Returns:
        list: A list of dictionaries containing user details and subscription info.
    """
    try:
        # Query subscriptions for the given channel ID
        subscriptions = (
            session.query(Subscription)
            .join(User, Subscription.user_id == User.user_id)
            .filter(Subscription.channel_id == channel_id)
            .all()
        )

        # Build the result list
        subscription_list = [
            {
                "user_id": sub.user.user_id,
                # "username": sub.user.username,
                "fullname": sub.user.fullname,
                "expiry_date": sub.expiry_date,
            }
            for sub in subscriptions
        ]

        return subscription_list

    except Exception as e:
        LOGGER.error(f"Error fetching subscriptions for channel {channel_id}: {e}")
        return []

# async def update_subscription(session: Session, user_id: int, channel_id: int, duration_text: str):
#     """
#     Update the subscription duration for a given user and channel.

#     Args:
#         session (Session): The SQLAlchemy session object.
#         user_id (int): ID of the user whose subscription is being updated.
#         channel_id (int): ID of the channel for the subscription.
#         duration_text (str): The duration to add or 'kick' to remove the user.
#                              Supported formats:
#                              - "20d" for 20 days
#                              - "2w" for 2 weeks
#                              - "3m" for 3 months
#                              - "1y" for 1 year
#                              - "kick" to remove the user from the channel.

#     Raises:
#         ValueError: If the `duration_text` is invalid.
#         NoResultFound: If no subscription exists for the given user and channel.
#         ChatAdminRequired: Bot doesnot have restric_user permission in channel
#         PeerIdInvalid: The Group isnt interacted by the bot
#     """
#     try:
#         LOGGER.info(f"update subscripton for {user_id} - {channel_id} - {duration_text}")
#         # Fetch the subscription
#         subscription = (
#             session.query(Subscription)
#             .filter(
#                 Subscription.user_id == user_id,
#                 Subscription.channel_id == channel_id
#             )
#             .one()
#         )
#     except NoResultFound:
#         raise NoResultFound("No subscription exists for the given user and channel.")

#     # Handle 'kick' command
#     if duration_text.strip().lower() == "kick":
#         try:
#             print(f"I was asked to kick user {user_id}")
#             await kick_and_unban_user(user_id, channel_id)
#         except ChatAdminRequired as e:
#             LOGGER.warning(f"Caught ChatAdminRequired exception: {e}")
#             raise ChatAdminRequired(e)
#         except PeerIdInvalid as e:
#             LOGGER.warning(f"Caught PeerIdInvalid exception: {e}")
#             raise PeerIdInvalid(e)
#         except Exception as e:
#             LOGGER.warning(f"Caught generic exception: {e}")
#             return str(e)

#         if delete_user_from_channel(session, user_id, channel_id):
#             return f"User {user_id} has been removed from channel {channel_id}."

#     # Calculate the new expiry date
#     duration_map = {
#         'd': 'days',
#         'w': 'weeks',
#         'm': 'months',
#         'y': 'years'
#     }

#     # Parse the duration_text
#     try:
#         value = int(duration_text[:-1])  # Get the numeric part
#         unit = duration_text[-1].lower()  # Get the unit part (d, w, m, y)

#         if unit not in duration_map:
#             raise ValueError("Invalid duration unit. Use 'd', 'w', 'm', or 'y'.")
#     except (ValueError, IndexError):
#         raise ValueError("Invalid duration format. Use formats like '20d', '2w', '3m', '1y', or 'kick'.")

#     # Compute new expiry date
#     current_expiry = subscription.expiry_date
#     if unit == 'd':
#         new_expiry = current_expiry + timedelta(days=value)
#     elif unit == 'w':
#         new_expiry = current_expiry + timedelta(weeks=value)
#     elif unit == 'm':
#         # Add months (approximation: 30 days per month)
#         new_expiry = current_expiry + timedelta(days=value * 30)
#     elif unit == 'y':
#         # Add years (approximation: 365 days per year)
#         new_expiry = current_expiry + timedelta(days=value * 365)

#     # Update the subscription
#     subscription.expiry_date = new_expiry
#     session.commit()

#     return f"Subscription for user {get_user_mention(session,user_id)} in channel {get_channel_mention(session,channel_id)} updated to expire on {new_expiry}."

async def update_subscription(session: Session, user_id: int, channel_id: int, admin_id: int, duration_text: str):
    """
    Update the subscription duration for a given user and channel.

    Args:
        session (Session): The SQLAlchemy session object.
        user_id (int): ID of the user whose subscription is being updated.
        channel_id (int): ID of the channel for the subscription.
        duration_text (str): The duration to add, a specific date, or 'kick' to remove the user.
                             Supported formats:
                             - "20d" for 20 days (e.g., 'd' for days)
                             - "2w" for 2 weeks (e.g., 'w' for weeks)
                             - "3m" for 3 months (e.g., 'm' for months)
                             - "1y" for 1 year (e.g., 'y' for years)
                             - "DD-MM-YYYY" for a specific expiry date (e.g., '25-12-2024')
                             - "kick" to remove the user from the channel.

    Raises:
        ValueError: If the `duration_text` is invalid.
        NoResultFound: If no subscription exists for the given user and channel.
        ChatAdminRequired: Bot does not have restric_user permission in channel.
        PeerIdInvalid: The Group isn't interacted by the bot.

    Returns:
        str: A message indicating the outcome of the update (e.g., updated expiry date or user removal).
    """
    try:
        LOGGER.info(f"update subscription for {user_id} - {channel_id} - {duration_text}")
        # Verify admin has rights to this channel
        if not is_channel_admin(session, admin_id, channel_id):
            raise ValueError(f"Admin {admin_id} does not have rights to this channel {channel_id}")

        # Fetch the subscription or create a new one if not found
        subscription = (
            session.query(Subscription)
            .filter(
                Subscription.user_id == user_id,
                Subscription.channel_id == channel_id
            )
            .first()
        )
        
        if not subscription:
            # If subscription doesn't exist, create a new one
            subscription = Subscription(user_id=user_id, channel_id=channel_id, expiry_date=datetime.now())
            session.add(subscription)
        
    except NoResultFound:
        raise NoResultFound("No subscription exists for the given user and channel.")
    
    # Handle 'kick' action
    action, value = parse_duration(duration_text)
    if action == "kick":
        return await handle_kick_action(session, user_id, channel_id)

    # Handle valid date string (DD-MM-YYYY format)
    if action == "date":
        expiry_date = value  # Already a datetime object
        subscription.expiry_date = expiry_date
        session.commit()
        return f"Subscription for user {get_user_mention(session, user_id)} in channel {get_channel_mention(session, channel_id)} updated to expire on `{subscription.expiry_date}`."

    # Compute the new expiry date based on the parsed duration
    new_expiry = calculate_new_expiry(subscription.expiry_date, action, value)
    subscription.expiry_date = new_expiry
    session.commit()
    return f"Subscription for user {get_user_mention(session, user_id)} in channel {get_channel_mention(session, channel_id)} updated to expire on `{subscription.expiry_date}`."



# ---------- supporting helper functions start

async def handle_kick_action(session, user_id: int, channel_id: int) -> str:
    """Handle the 'kick' action."""
    LOGGER.info(f"Entering handle_kick_action with user_id={user_id}, channel_id={channel_id}")
    try:
        user_mention = get_user_mention(session, user_id)
        channel_mention = get_channel_mention(session, channel_id)
        await kick_and_unban_user(user_id, channel_id)
    except ChatAdminRequired as e:
        LOGGER.warning(f"Caught ChatAdminRequired exception: {e}")
        return ("⚠️ **Warning**: The bot needs admin privileges on {channel_mention} to perform this action.\n\n"
        "**What to do?**\n"
        "1. Make sure the bot is added as an admin to the channel or group.\n"
        "2. Grant the bot the necessary admin permissions (e.g., posting messages, managing users, etc.).\n"
        "3. Try again after the bot is properly set up as an admin.")
    except (ValueError, PeerIdInvalid) as e:
        LOGGER.warning(f"Caught PeerIdInvalid exception: {e}")
        return (f"⚠️ **Warning**: It looks like you need to interact with the channel {channel_mention} first before you can proceed.\n\n"
                "**What to do?**\n"
                "1. Visit the channel.\n"
                "2. Quick React to any random message in the channel.\n"
                "3. Try again – the bot needs this interaction to reconnect properly.")
    except Exception as e:
        LOGGER.warning(f"Caught generic exception: {e}")
        return str(e)
    
    # Log whether the user was successfully removed or not
    if delete_user_from_channel(session, user_id, channel_id):
        result = f"User {user_mention}(`{user_id}`) has been removed from channel {channel_mention}."
    else:
        result = "Error removing user from channel."
    
    LOGGER.info(f"Exiting handle_kick_action with result: {result}")
    return result

def is_valid_date(date_str: str) -> bool:
    """Checks if the given date string is in DD-MM-YYYY format and valid."""
    LOGGER.info(f"Entering is_valid_date with date_str={date_str}")
    try:
        datetime.strptime(date_str, "%d-%m-%Y")
        LOGGER.info(f"Exiting is_valid_date: True (valid date format)")
        return True
    except ValueError:
        LOGGER.warning(f"Exiting is_valid_date: False (invalid date format)")
        return False

def calculate_new_expiry(current_expiry: datetime, unit: str, value: int) -> datetime:
    """Calculate the new expiry date based on unit and value."""
    LOGGER.info(f"Entering calculate_new_expiry with current_expiry={current_expiry}, unit={unit}, value={value}")

    # Map units to their respective multipliers in days
    unit_to_days = {
        'd': 1,          # days
        'w': 7,          # weeks
        'm': 30,         # months (approx)
        'y': 365         # years (approx)
    }

    # Check if the unit is valid and calculate the new expiry
    if unit in unit_to_days:
        try:
            new_expiry = current_expiry + timedelta(days=value * unit_to_days[unit])
            LOGGER.info(f"Exiting calculate_new_expiry with new_expiry={new_expiry}")
            return new_expiry
        except Exception as e:
            LOGGER.error(f"Error calculating new expiry: {e}")  

    LOGGER.warning(f"Exiting calculate_new_expiry with no changes to expiry (invalid unit)")
    return current_expiry

def parse_duration(duration_text: str) -> tuple:
    """Parse the duration_text and return value and unit or a date."""
    LOGGER.info(f"Entering parse_duration with duration_text={duration_text}")
    
    # Check for 'kick' command
    if duration_text.strip().lower() == "kick":
        LOGGER.info("Exiting parse_duration: 'kick' action detected.")
        return "kick", None

    # Check for valid date format (DD-MM-YYYY or YYYY-MM-DD)
    for date_format in ["%d-%m-%Y", "%Y-%m-%d"]:
        try:
            expiry_date = datetime.strptime(duration_text, date_format)
            LOGGER.info(f"Exiting parse_duration: Valid date format detected: {duration_text}")
            return "date", expiry_date
        except ValueError:
            continue  # Try the next format

    # Handle duration formats like 20d, 3w, etc.
    duration_map = {
        'd': 'days',
        'w': 'weeks',
        'm': 'months',
        'y': 'years'
    }

    try:
        value = int(duration_text[:-1])  # Get the numeric part
        unit = duration_text[-1].lower()  # Get the unit part (d, w, m, y)

        if unit not in duration_map:
            raise ValueError("Invalid duration unit. Use 'd', 'w', 'm', or 'y'.")
        
        LOGGER.info(f"Exiting parse_duration with parsed values: unit={unit}, value={value}")
        return unit, value
    except (ValueError, IndexError):
        LOGGER.warning("Exiting parse_duration: Invalid duration format.")
        raise ValueError("Invalid duration format. Use formats like '20d', '2w', '3m', '1y', 'DD-MM-YYYY' or 'YYYY-MM-DD'.")



# ---------- supporting helper functions end


# Fetch expired subscriptions
def fetch_expired_subscriptions(session: Session, admin_id: int = None):
    """
    Fetches expired subscriptions and returns tuples containing all necessary data.
    
    Args:
        session (Session): The database session
        
    Returns:
        List[Tuple]: List of tuples containing (user_id, user_fullname, channel_id, channel_name, expiry_date)
    """
    today = datetime.now().date()
    query = (
        select(
            Subscription.user_id,
            User.fullname,
            Subscription.channel_id,
            Channel.channel_name,
            Subscription.expiry_date
        )
        .join(User, Subscription.user_id == User.user_id)
        .join(Channel, Subscription.channel_id == Channel.channel_id)
        .where(Subscription.expiry_date <= today)
    )
    
    if admin_id:
        # Add a subquery to filter by admin's channels
        admin_channels_subquery = (
            select(AdminChannel.channel_id)
            .where(AdminChannel.admin_id == admin_id)
        )
        query = query.where(Subscription.channel_id.in_(admin_channels_subquery))

    results = session.execute(query).all()
    return [
        {
            'user_id': row.user_id,
            'user_fullname': row.fullname,
            'channel_id': row.channel_id,
            'channel_name': row.channel_name,
            'expiry_date': row.expiry_date
        }
        for row in results
    ]

# Fetches subscriptions that are about to expire within the next 3 days.
def fetch_soon_to_expire_subscriptions(session: Session, admin_id: int = None):
    """
    Fetches subscriptions that are expiring within the next 3 days,
    along with associated user and channel information as objects.

    Args:
        session: The SQLAlchemy database session.

    Returns:
        A list of Subscription objects, with user and channel relationships loaded.
    """
    today = datetime.now().date()
    soon_to_expire_date = today + timedelta(days=3)

    query = (
        select(Subscription)
        .options(joinedload(Subscription.user), joinedload(Subscription.channel))  # Eagerly load user and channel
        .where(
            (Subscription.expiry_date > today)
            & (Subscription.expiry_date <= soon_to_expire_date)
        )
    )

    if admin_id:
        # Add a subquery to filter by admin's channels
        admin_channels_subquery = (
            select(AdminChannel.channel_id)
            .where(AdminChannel.admin_id == admin_id)
        )
        query = query.where(Subscription.channel_id.in_(admin_channels_subquery))

    results = session.execute(query).scalars().all()

    if results:
        count = len(results)
        LOGGER.info(f"Found {count} soon-expiring subscriptions:")
        if count > 1:
            LOGGER.info("Multiple subscriptions expiring soon.")  # Log if more than one
        for subscription in results:  #Detailed logs to avoid clutter
          LOGGER.debug(f"Subscription: {subscription!r}, User: {subscription.user!r}, Channel: {subscription.channel!r}") #using repr to get str representation.

    else:
        LOGGER.info("No soon-expiring subscriptions found.")

    return results
""" Usage =>
f"User ID: {sub.user.user_id}, Full Name: {sub.user.fullname}, "
#               f"Channel ID: {sub.channel.channel_id}, Channel Name: {sub.channel.channel_name}, "
#               f"Expiry Date: {sub.expiry_date}"
"""



# Remove expired subscriptions
def remove_expired_subscriptions(session: Session, admin_id: int = None):
    """
    Removes expired subscriptions and optionally cleans up users with no active subscriptions.
    If an admin_id is provided, only remove expired subscriptions for channels
    associated with that admin.
    
    Args:
        session (Session): The database session
        admin_id (int, optional): The admin ID to filter by (optional)
        
    Returns:
        List[int]: List of user IDs whose subscriptions were removed
    """
    today = datetime.now().date()
    query = delete(Subscription).where(Subscription.expiry_date <= today)

    if admin_id:
        # Add a subquery to filter by admin's channels
        admin_channels_subquery = (
            select(AdminChannel.channel_id)
            .where(AdminChannel.admin_id == admin_id)
        )
        query = query.where(Subscription.channel_id.in_(admin_channels_subquery))

    expired_users = session.execute(query.returning(Subscription.user_id)).scalars().all()

    # Clean up users with no active subscriptions (only if no admin_id is provided)
    if not admin_id:
        session.execute(
            delete(User).where(~User.subscriptions.any())
        )

    session.commit()
    return expired_users
