from sqlalchemy.orm import Session
from sqlalchemy import select, delete, func
from datetime import datetime, timedelta
from db.models import Channel, Subscription
from db.user_helpers import remove_extra_users
from utils.logger import LOGGER

def get_channel_link(session: Session, channel_id: int) -> str:
    try:
        channel = session.query(Channel).filter(Channel.channel_id == channel_id).first()
        if channel:
            return channel.invite_link
        else:
            return None  # Return None if the channel is not found
    except Exception as e:
        session.rollback()
        print(f"Error fetching channel link: {e}")
        return None

def update_channel_link(session: Session, channel_id: int, new_link: str) -> bool:
    try:
        channel = session.query(Channel).filter(Channel.channel_id == channel_id).first()
        if channel:
            channel.invite_link = new_link
            session.commit()
            return True  # Successfully updated the link
        else:
            return False  # Channel not found
    except Exception as e:
        session.rollback()
        print(f"Error updating channel link: {e}")
        return False


# Helper function to add a new channel
def add_channel(session: Session, channel_id: int, channel_name: str, is_channel: bool = False):
    try:
        channel = session.query(Channel).filter_by(channel_id=channel_id).first()
        if not channel:
            channel = Channel(channel_id=channel_id, channel_name=channel_name, is_channel=is_channel)
            session.add(channel)
            session.commit()
            LOGGER.info(f"Created a new channel {channel_id}")
        return channel
    except Exception as e:
        session.rollback()
        LOGGER.error(f"Error adding channel {channel_id}: {e}")
        return None

def get_channel_name_by_id(session: Session, channel_id: int):
    channel = session.query(Channel).filter(Channel.channel_id == channel_id).first()
    if channel:
        return channel.channel_name + 'ᶜ' if channel.is_channel else 'ᴳ'
    else:
        LOGGER.info(f"No channel with channel id - {channel_id} found in the database.")
        return None

def get_channel_mention(session: Session, channel_id: int) -> str | None:
    try:
        channel = session.query(Channel).filter(Channel.channel_id == channel_id).one_or_none()

        if channel:
            channel_value = str(channel_id).lstrip('-100')
            mention = f"[{channel.channel_name}](https://t.me/c/{channel_value})"
            return mention
        else:
            return None

    except Exception as e:
        LOGGER.exception("Error retrieving channel")  # Using your LOGGER
        return None

# Get a list of dictionaries containing All channel IDs and names
def get_all_channels(session: Session):
    try:
        channels = session.query(Channel).all()
        if not channels:
            LOGGER.info("No channels found in the database.")
        channel_list = [{"id": channel.channel_id, "name": channel.channel_name + ('ᶜ' if channel.is_channel else 'ᴳ') } for channel in channels]
        return channel_list
    except Exception as e:
        LOGGER.error(f"Error retrieving channels: {e}")
        return []

def delete_channel(session: Session, channel_id: int):
    """
    Deletes a channel and all related subscriptions.
    Removes users who no longer have subscriptions as a result.
    """
    
    try:
        # Step 0: Find if channel_id is present in Channel table
        channel = session.query(Channel).filter(Channel.channel_id == channel_id).first()
        if not channel:
            LOGGER.warning(f"Channel {channel_id} not found in the database.")
            return False
        
        # Step 1: Delete all subscriptions related to the channel
        session.query(Subscription).filter(Subscription.channel_id == channel_id).delete()
        session.commit()

        # Step 2: Delete the channel itself
        session.query(Channel).filter(Channel.channel_id == channel_id).delete()
        session.commit()

        # Step 3: Remove orphaned users
        remove_extra_users(session)
        return True
    except Exception as e:
        session.rollback()
        LOGGER.error(f"Error deleting channel {channel_id}: {e}")
        return False

def add_or_update_channel_connection(session: Session, channel_id: int, channel_name: str, invite_link: str, is_channel: bool) -> bool:
    try:
        # Query for an existing channel with the given channel_id
        channel = session.query(Channel).filter_by(channel_id=channel_id).first()

        if channel:
            # Update existing channel details
            channel.channel_name = channel_name
            channel.invite_link = invite_link
            channel.is_channel = is_channel
        else:
            # Create a new channel record
            channel = Channel(
                channel_id=channel_id,
                channel_name=channel_name,
                invite_link=invite_link,
                is_channel=is_channel
            )
            session.add(channel)

        # Commit the transaction
        session.commit()
        return True
    except Exception as e:
        # Rollback in case of an error
        session.rollback()
        LOGGER.error(f"Error adding or updating channel {channel_id}: {e}")
        return False

def set_invite_link(session: Session, channel_id: int, invite_link: str) -> bool:
    """Sets the invite link for a channel, given its ID."""
    try:
        channel = session.query(Channel).filter(Channel.channel_id == channel_id).first()
        if channel:
            channel.invite_link = invite_link
            session.commit()
            return True
        return False
    except Exception as e:
        LOGGER.error(f"Error setting channel link {channel_id}: {e}")
        return False

def get_invite_link(session, channel_id: int) -> str | None:
    try:
        channel = session.query(Channel).filter(Channel.channel_id == channel_id).first()
        return channel.invite_link if channel else None
    except Exception as e:
        LOGGER.error(f"Error deleting channel link {channel_id}: {e}")
        return False

def delete_invite_link(session: Session, channel_id: int) -> bool:
    try:
        channel = session.query(Channel).filter(Channel.channel_id == channel_id).first()
        if channel and channel.invite_link is not None:
            channel.invite_link = None
            session.commit()
            return True
        return False
    except Exception as e:
        LOGGER.error(f"Error deleting channel link {channel_id}: {e}")
        return False