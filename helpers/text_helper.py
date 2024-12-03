import re
import asyncio
from unidecode import unidecode
from utils.logger import LOGGER
from pyrogram.errors import FloodWait

async def sanitize_fullname(first_name, last_name):
    """
    Sanitizes the full name by removing or replacing unknown symbols,
    and returns 'Unknown' if the sanitized name is empty or only contains whitespace.

    :param first_name: The first name of the user.
    :param last_name: The last name of the user.
    :return: Sanitized full name or 'Unknown'.
    """
    # Convert to ASCII if possible, removing diacritics and other non-ASCII characters
    first_name = unidecode(first_name) if first_name else ''
    last_name = unidecode(last_name) if last_name else ''

    # Remove all characters except letters, numbers, spaces, and some punctuation
    fullname = f"{first_name} {last_name}".strip()
    sanitized_fullname = re.sub(r'[^a-zA-Z0-9\s\.,_-]', '', fullname)

    # If after sanitization the name is empty or just whitespace, return 'Unknown'
    if not sanitized_fullname or sanitized_fullname.isspace():
        return "Unknown"
    
    return sanitized_fullname

async def send_long_message(client, chat_id: int, text: str):
    """Send a long message in multiple chunks to the chat."""
    
    # Check if chat_id is valid (positive number)
    if not isinstance(chat_id, int) or chat_id <= 0:
        LOGGER.error(f"Invalid chat ID: {chat_id}. Must be a positive integer.")
        return
    
    # Check if the text is empty
    if not text.strip():
        LOGGER.warning("Attempted to send an empty message.")
        return
    
    chunks = split_message(text)
    
    for idx, chunk in enumerate(chunks, start=1):
        while True:
            try:
                # Log the chunk being sent
                LOGGER.info(f"Sending chunk {idx}/{len(chunks)} to chat {chat_id}. Length: {len(chunk)} characters.")
                
                # Send the chunk to the chat
                await client.send_message(chat_id, chunk)
                
                # Log successful sending
                LOGGER.info(f"Chunk {idx} sent successfully.")
                break  # Exit the while loop if successful
            except FloodWait as e:
                # Handle FloodWait error
                wait_time = e.value
                LOGGER.warning(f"FloodWait error for chat {chat_id}. Waiting for {wait_time} seconds.")
                await asyncio.sleep(wait_time)
                # Retry sending the chunk after waiting

            except Exception as e:
                # Log any other exception that occurs while sending the message
                LOGGER.error(f"Error sending chunk {idx} to chat {chat_id}: {e}")
                break  # Stop further sending if a non-FloodWait error occurs


# supporting Helper function 
def split_message(text: str, max_length: int = 4096) -> list:
    """Splits the input text into chunks not exceeding max_length, avoiding breaking in the middle of words."""
    
    # Initialize a list to hold the chunks
    chunks = []
    
    # While there's still text to process
    while len(text) > max_length:
        # Try to find the last newline within the max length
        split_point = text.rfind('\n', 0, max_length)
        
        if split_point == -1:  # If no newline is found, split at max_length
            split_point = max_length
        
        # Append the chunk to the list
        chunks.append(text[:split_point].strip())
        
        # Reduce the text for the next iteration
        text = text[split_point:].strip()
    
    # Add any remaining text as the last chunk
    if text:
        chunks.append(text)
    
    return chunks

def create_channel_mention(channel_name, channel_id):
    """
    Creates a mention for a channel.

    Args:
        channel_name (str): The name of the channel.
        channel_id (int): The ID of the channel.

    Returns:
        str: The mention for the channel.
    """
    channel_value = str(channel_id).lstrip('-100')
    mention = f"[{channel_name}](https://t.me/c/{channel_value})"
    return mention

def create_user_mention(user_id, user_fullname):
    """
    Creates a mention for a user.

    Args:
        user_id (int): The ID of the user.
        user_fullname (str): The full name of the user.

    Returns:
        str: The mention for the user.
    """
    mention = f"[{user_fullname}](tg://user?id={user_id})"
    return mention