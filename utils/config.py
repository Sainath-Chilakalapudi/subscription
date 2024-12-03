from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

class Config:
    PORT = os.getenv("PORT", 8080)
    API_HASH = os.getenv("API_HASH")
    API_ID = int(os.getenv("API_ID"))
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    DB_URI = os.getenv("DATABASE_URI")
    ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS").split(",")))
    DEV_IDS = list(map(int, os.getenv("DEV_IDS", "0,0").split(",")))
    MY_ID = os.getenv("MY_ID")
    LOGGER_NAME = "Auto kicker bot logger"
    TG_BOT_WORKERS = 4
    WORK_DIR = "sessions"

    # Get database connection details from environment variables
    DB_USER = os.getenv("BD_USER")
    DB_PASS = os.getenv("DB_PASS")
    DB_DATABASE = os.getenv("DB_DATABASE")
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT")
    DB_SSL = os.getenv("DB_SSL")
    CONNECTION_STRING = os.getenv("CONNECTION_STRING")
    CA_CERT_PATH = os.getenv("DB_CA_CERT_PATH","utils/ca.pem")

    # Optional
    WHITELISTED_CHATS = list(map(int, os.getenv("WHITELISTED_CHATS", "0").split(",")))
    BLACKLISTED_CHATS = list(map(int, os.getenv("WHITELISTED_CHATS", "0").split(",")))
    
    # Testing
    CHANNEL_ID = -1002264564657

if __name__ == "__main__": 
    print(f"Admins - {Config.ADMIN_IDS}")
    print(f"Devs - {Config.DEV_IDS}")
