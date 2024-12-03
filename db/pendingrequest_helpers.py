from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from db.models import PendingRequest
from utils.logger import LOGGER

def add_pending_request(session: Session, user_id: int, channel_id: int, admin_id: int) -> bool:
    try:
        # Check if the pair already exists
        existing_request = session.query(PendingRequest).filter(
            PendingRequest.user_id == user_id,
            PendingRequest.channel_id == channel_id
        ).first()

        if existing_request:
            return False  # The pair already exists, no need to add

        LOGGER.info(f"Adding new request for user (ID: {user_id}) to channel ID '{channel_id}'.")
        new_request = PendingRequest(user_id=user_id, channel_id=channel_id, admin_id=admin_id)
        session.add(new_request)
        session.commit()
        return True  # Successfully added the request
    except Exception as e:
        session.rollback()
        print(f"Error adding pending request: {e}")
        return False

def delete_pending_request(session: Session, user_id: int, channel_id: int) -> bool:
    try:
        # Find the request
        request = session.query(PendingRequest).filter(
            PendingRequest.user_id == user_id,
            PendingRequest.channel_id == channel_id
        ).first()

        if request:
            session.delete(request)
            session.commit()
            LOGGER.info(f"successfully deleted pending request of {user_id}")
            return True  # Successfully deleted the request
        else:
            LOGGER.info(f"Failed to delete pending request of {user_id}")
            return False  # No request found to delete
    except Exception as e:
        session.rollback()
        LOGGER.error(f"Error deleting pending request: {e}")
        return False

def check_pending_request(session: Session, user_id: int, channel_id: int) -> bool:
    try:
        # Check if the user-channel pair exists
        request = session.query(PendingRequest).filter(
            PendingRequest.user_id == user_id,
            PendingRequest.channel_id == channel_id
        ).first()
        
        # Return True if found, False if not
        return ( True, request.admin_id ) if request is not None else (False, None)
    except Exception as e:
        print(f"Error checking pending request: {e}")
        return False, None
