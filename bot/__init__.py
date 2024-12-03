from pyrogram import Client
from utils.config import Config
from statemanager import StateManager
from utils.logger import LOGGER
import os
import sqlite3

class Bot(Client):
    # Class-level (shared across all bot instances)
    state = StateManager()

    def __init__(self):
        if not os.path.exists(Config.WORK_DIR):
            os.makedirs(Config.WORK_DIR)
            print(f"{Config.WORK_DIR} Directory created.")
        
        super().__init__(
            name="telegram_subscription_bot",
            api_hash=Config.API_HASH,
            api_id=Config.API_ID,
            plugins={
                "root": "bot/plugins"
            },
            workers=Config.TG_BOT_WORKERS,
            workdir=Config.WORK_DIR,
            bot_token=Config.BOT_TOKEN
        )
        self._username = None # Bot username instance variable


    # Class method to update state when admin wants to update subscriptions
    # Usage - Bot.add_bulk_update_state(admin_id,subscriptions)
    @classmethod
    def add_bulk_update_state(cls, admin_id, subscriptions):
        cls.state.set_state("bulk_update", admin_id, subscriptions)

    # Class method to get subscriptions that admin wants to update
    @classmethod
    def get_bulk_update_state(cls, admin_id):
        return cls.state.get_state("bulk_update", admin_id)        
    # Class method to delete state for admin as he have completed updating subscriptions
    
    @classmethod
    def delete_bulk_update_state(cls, admin_id):
        return cls.state.delete_state("bulk_update", admin_id)
    
    
    @classmethod
    def add_single_update_state(cls, admin_id, subscription):
        cls.state.set_state("new_update", admin_id, subscription) 
    
    @classmethod
    def get_single_update_state(cls, admin_id):
        return cls.state.get_state("new_update", admin_id)
    
    # Class method to delete state for admin as he have completed updating subscription of user
    @classmethod
    def delete_single_update_state(cls, admin_id):
        return cls.state.delete_state("new_update", admin_id)

    # --- Additional to get to know how to use state manager for non keyvalue types -----

    @classmethod
    def add_boolean_flag(cls, flag_name, value):
        """
        Add a boolean flag in the 'other_values' category.
        """
        cls._state_manager.set_state("other_values", flag_name, value)

    @classmethod
    def get_boolean_flag(cls, flag_name):
        """
        Get a boolean flag from the 'other_values' category.
        """
        return cls._state_manager.get_state("other_values", flag_name)


    async def start(self):
        await super().start()
        await self._set_username()  # Call _set_username after bot starts
        # Wait until the bot is ready to interact
        await self.get_me()
        # Fetch members from the channel using async for loop
        # try:
        #     async for member in self.get_chat_members(Config.CHANNEL_ID):
        #         LOGGER.info(f"Member ID: {member.user.id}, Member Username: {member.user.username}")
        #     LOGGER.info(f"Successfully synced channel members.")
        # except Exception as e:
        #     LOGGER.error(f"Error syncing channel: {str(e)}")
        LOGGER.info("Bot is currently running.. Username: %s", self.username)

    async def idle(self):
        await super().idle()

    async def stop(self, *args):
        await super().stop()
        LOGGER.info("Bot stopped.")
    
    async def _set_username(self):
        """Sets the bot's username using client.get_me()."""
        try:
            me = await self.get_me()
            self._username = me.username
        except Exception as e:
            LOGGER.error(f"Error getting bot username: {e}")
            self._username = None  # Set to None on error

    @property
    def username(self):
        """Getter function for the bot's username.
        You can access the username using 'bot.username'."""
        return self._username