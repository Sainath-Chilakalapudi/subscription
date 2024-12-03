from sqlalchemy.orm import Session
from sqlalchemy import select, delete, func
from datetime import datetime, timedelta
from db.models import User, Subscription, VerificationCode
from db.pendingrequest_helpers import add_pending_request
from utils.logger import LOGGER
import hashlib


# Helper function to generate a verification code
def generate_verification_code(session: Session, admin_id: int, channel_id: int):
    # Create a unique code based on user ID, channel ID, and the current timestamp
    timestamp = int(datetime.now().timestamp() * 1000)  # Get the current timestamp in milliseconds
    code = hashlib.sha256(f"{channel_id}{timestamp}".encode()).hexdigest()[:8]
    
    expires_at = datetime.now() + timedelta(minutes=10)
    verification_code = VerificationCode(
        code=code, admin_id=admin_id, channel_id=channel_id, expires_at=expires_at
    )
    session.add(verification_code)
    session.commit()
    return verification_code


def validate_and_add_user(session: Session, user_id: int, code: str, username: str, fullname: str):
    """
    Validates a verification code and adds the user to the subscriptions.
    - Deletes the verification code after validation.
    - Adds the user and subscription if valid.

    Returns:
        status (bool): Whether the validation and addition were successful.
        channel_id (int): The channel ID associated with the verification code.
        is_new_to_channel (bool): Whether the user was newly added to the channel.
        admin_id (int): The admin's ID who created the verification code
    """
    try:
        # Step 1: Validate the verification code
        LOGGER.info(f"Validating verification code '{code}' for user '{username}' (ID: {user_id}).")
        verified_code = (
            session.query(VerificationCode)
            .filter(VerificationCode.code == code, VerificationCode.expires_at > datetime.now())
            .first()
        )

        if not verified_code:
            LOGGER.warning(f"Verification code '{code}' for user '{username}' (ID: {user_id}) is invalid or expired.")
            # Code invalid; delete the expired codes (if any exist)
            cleanup_expired_verification_codes(session)
            return False, None, False  # Validation failed

        # Step 2: Add the user to the Users table (if not already present)
        user = session.query(User).filter(User.user_id == user_id).first()
        if not user:
            LOGGER.info(f"Adding new user '{username}' (ID: {user_id}) to the Users table.")
            user = User(user_id=user_id, username=username, fullname=fullname)
            session.add(user)
        else:
            LOGGER.info(f"User '{username}' (ID: {user_id}) already exists in the Users table.")

        is_new_to_channel = False
        channel_id = verified_code.channel_id
        admin_id = verified_code.admin_id

        # Step 3: Add the subscription for the verified channel
        subscription = (
            session.query(Subscription)
            .filter(Subscription.user_id == user_id, Subscription.channel_id == channel_id)
            .first()
        )
        if not subscription:
            if not add_pending_request(session, user_id, channel_id, admin_id):
                LOGGER.info(f"A request for user '{username}' (ID: {user_id}) to channel ID '{channel_id}' already exists !")
            is_new_to_channel = True
        else:
            LOGGER.info(f"User '{username}' (ID: {user_id}) is already subscribed to channel ID '{channel_id}'.")


        # Step 4: Delete the verification code entry
        LOGGER.info(f"Deleting verification code '{code}' for user '{username}' (ID: {user_id}).")
        session.delete(verified_code)

        # Commit the changes to the database
        session.commit()
        LOGGER.info(f"User '{username}' (ID: {user_id}) successfully within channel ID '{channel_id}'.")
        return True, channel_id, is_new_to_channel, admin_id  # Validation succeeded

    except Exception as e:
        # Log the exception and rollback the transaction
        LOGGER.error(f"An error occurred while validating and adding user '{username}' (ID: {user_id}): {e}")
        session.rollback()  # Rollback the transaction to avoid partial commits
        return False, None, False

def cleanup_expired_verification_codes(session: Session):
    """
    Removes expired verification codes from the `VerificationCodes` table.
    """
    session.query(VerificationCode).filter(VerificationCode.expires_at <= datetime.now()).delete()
    session.commit()

