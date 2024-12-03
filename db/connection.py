from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from utils.config import Config
from db.initialize import initialize_database

# Database connection settings
DB_CONFIG = {
    "dbname": Config.DB_DATABASE,
    "user": Config.DB_USER,
    "password": Config.DB_PASS,
    "host": Config.DB_HOST,
    "port": Config.DB_PORT,
    "sslmode": "verify-full",
    "sslrootcert": Config.CA_CERT_PATH,
}

# Build the PostgreSQL URL with SSL parameters
DB_URL = (
    f"postgresql+psycopg2://{DB_CONFIG['user']}:{DB_CONFIG['password']}@"
    f"{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}?"
    f"sslmode={DB_CONFIG['sslmode']}&sslrootcert={DB_CONFIG['sslrootcert']}"
)

# Initialize SQLAlchemy engine
engine = create_engine(DB_URL, pool_pre_ping=True)


# Base class for ORM models
Base = declarative_base()

# Import models to register them with Base ---- Or can place this in initialize.py and remove from here
from db.models import Channel, User, Subscription, VerificationCode  # Import all models


# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Initialize the database when the module is imported
initialize_database(engine, Base)

def get_db():
    """Provide a session for database interaction."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
