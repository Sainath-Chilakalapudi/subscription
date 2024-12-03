from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from db.models import User, Subscription, Channel, PendingRequest
from sqlalchemy import and_
from utils.logger import LOGGER

# Helper function to add a new user
def add_user(session: Session, user_id: int, username: str = None, fullname: str = None):
    try:
        # Corrected the filter condition to use the correct model field: User.user_id
        user = session.query(User).filter(User.user_id == user_id).first()
        if not user:
            # If the user does not exist, create a new user
            user = User(user_id=user_id, username=username, fullname=fullname)
            session.add(user)
            session.commit()
            LOGGER.info(f"successfully added new user : {user_id}")
        return user
    except Exception as e:
        LOGGER.error(f"Error adding user {user_id} : {e}")

def get_userfull(session: Session, user_id: int):
    try:
        user = session.query(User).filter(User.user_id == user_id).first()
        if user:
          return user.to_dict()
        else:
            return None
    except Exception as e:
        LOGGER.error(f"Error fetching user: {e}")
        return None

def get_user_mention(session: Session, user_id: int) -> str:
    try:
        user = session.query(User).filter(User.user_id == user_id).one_or_none()

        if user:
            formatted_string = f"[{user.fullname}](tg://user?id={user.user_id})"
            return formatted_string
        else:
            return None  # Or raise an exception if appropriate

    except Exception as e:
        LOGGER.error(f"Error retrieving user: {e}")
        return None

def get_user_subscription(session: Session, user_id: int, channel_id: int):
    try:
        # Query the Subscription, User, and Channel tables in one go
        subscription = session.query(
           User.fullname.label('user_fullname'),
           User.user_id.label('user_id'),
           Subscription.expiry_date.label('expiry_date')
        ).join(User, Subscription.user_id == User.user_id)\
         .join(Channel, Subscription.channel_id == Channel.channel_id)\
         .filter(
            Subscription.user_id == user_id,
            Subscription.channel_id == channel_id
         ).first()
        
        if subscription:
            return {
                'user_fullname': subscription.user_fullname,
                'user_id': subscription.user_id,
                'expiry_date': subscription.expiry_date
            }
        else:
            return None
    except Exception as e:
        LOGGER.error(f"Error fetching subscription: {e}")
        return None

def get_user_channels(session: Session, user_id: int):
    """
    Fetch all channels a user is subscribed to, including channel_id and channel_name.
    Returns:
        list: A list of dictionaries containing channel_id and channel_name.
    """
    # Perform a query to fetch the channels a user is subscribed to
    try:
        result = (
            session.query(Channel.channel_id, Channel.channel_name)
            .join(Subscription, Subscription.channel_id == Channel.channel_id)
            .filter(Subscription.user_id == user_id)
            .all()
        )
        channels = [{"channel_id": channel.channel_id, "channel_name": channel.channel_name} for channel in result]
        return channels
    except Exception as e:
        LOGGER.error(f"Error fetching Channels: {e}")
        return None

def remove_extra_users(session: Session):
    """
    Removes users from the `users` table who have no subscriptions left.
    """
    try:
        # Delete users who do not have any related subscriptions or pending requests
        session.query(User).filter(
            ~session.query(Subscription.user_id).filter(Subscription.user_id == User.user_id).exists(),
            ~session.query(PendingRequest.user_id).filter(PendingRequest.user_id == User.user_id).exists()
        ).delete(synchronize_session=False)
        
        session.commit()
        LOGGER.info("Removed Extra user.")
        return True
    except Exception as e:
        LOGGER.error(f"Error Removing Extra Users: {e}")
        return None

def delete_user_from_channel(session: Session, user_id: int, channel_id: int):
    """
    Deletes the relationship between a user and a channel from the subscriptions table.
    Removes the user from the `users` table if they have no other subscriptions.
    """
    try:
        subscription = session.query(Subscription).filter(Subscription.user_id == user_id, Subscription.channel_id == channel_id).first()
        if subscription:
            session.delete(subscription)
            session.commit()

            # Check if the user has any remaining subscriptions and remove if none exist
            remove_extra_users(session)
            LOGGER.info(f"User {user_id} subscription from channel - {channel_id} has been successfully deleted")
        return True
    except Exception as e:
        LOGGER.error(f"Error Deleting User from channel: {e}")
        return False