from pyrogram import Client, filters
from pyrogram.types import Message
from utils.config import Config
from bot import Bot

def dev_users(_, __, message: Message) -> bool:
    return message.from_user.id in Config.DEV_IDS if message.from_user else False

def admin_users(_, __, message: Message) -> bool:
    return message.from_user.id in Config.ADMIN_IDS if message.from_user else False

def normal_users(_, __, message: Message) -> bool:
    return message.from_user.id not in Config.ADMIN_IDS if message.from_user else False

def whitelisted_chats(_, __, message: Message) -> bool:
    return message.chat.id in Config.WHITELISTED_CHATS if message.chat else False

def blacklisted_chats(_, __, message: Message) -> bool:
    return message.chat.id in Config.BLACKLISTED_CHATS if message.chat else False

# State checking for Admin if he has requested for bulk updates
def is_bulk_update_state_chats(_, __, message: Message) -> bool:
    return Bot.state.has_state("bulk_update", message.chat.id) if message.from_user else False

# State checking for Admin if he is updating stae of new user subscription 
def is_new_user_update_state_chats(_, __, message: Message) -> bool:
    return Bot.state.has_state("new_update", message.chat.id) if message.from_user else False

def is_deleting_channel_links(_, __, message: Message) -> bool:
    return Bot.state.has_state("delete_links", message.chat.id) if message.from_user else False

# Custom filter function to check if the command is directed at the bot
def calling_bot(bot: Bot, _, message: Message) -> bool:
    if not message.text:
        return False
    command_parts = message.text.split("@", 1)  # Split only once at @
    if len(command_parts) == 2:
        command, bot_username = command_parts
        if Bot.username == Bot.username:
            return True

    return False

# Check if the message is from channel (posts) or group itself, that is msgs from admins when they use anonymous mode
def channel_or_group_anonymous_messages(_, __, message: Message) -> bool:
    return True if message.sender_chat else False




anonymous_message_filter = filters.create(channel_or_group_anonymous_messages)
calling_bot_filter = filters.create(calling_bot)

devs_filter = filters.create(dev_users)
admins_filter = filters.create(admin_users)
normal_filter = filters.create(normal_users)

is_bulk_updating = filters.create(is_bulk_update_state_chats)
is_new_user_updating = filters.create(is_new_user_update_state_chats)
is_deleting_channel_links_filter = filters.create(is_deleting_channel_links)

whitelisted_chats_filter = filters.create(whitelisted_chats)
blacklisted_chats_filter = filters.create(blacklisted_chats)