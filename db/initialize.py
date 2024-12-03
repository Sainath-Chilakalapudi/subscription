from sqlalchemy.exc import SQLAlchemyError
from utils.logger import LOGGER


def initialize_database(engine, Base):
    """
    Initializes the database by creating all tables defined in the models
    if they do not already exist.
    Displays the list of tables and their definitions after initialization.
    """
    try:
        LOGGER.info("Initializing the database...")
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        # Log the list of tables and their definitions
        LOGGER.info("Database initialization complete. All tables are up-to-date.")
        LOGGER.info("Current tables in the database:")
        
        for table_name, table in Base.metadata.tables.items():
            LOGGER.info(f"Table: {table_name}")
            LOGGER.info(f"Columns:")
            for column in table.columns:
                LOGGER.info(
                    f" - {column.name} ({column.type}) "
                    f"{'PRIMARY KEY' if column.primary_key else ''}"
                )
            LOGGER.info("\n")

    except SQLAlchemyError as e:
        LOGGER.error(f"Database initialization failed: {e}")
        raise
