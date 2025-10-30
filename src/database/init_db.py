"""Initialize the database."""

from src.database.operations import init_database

if __name__ == "__main__":
    print("Initializing database...")
    init_database()
    print("Database initialized successfully!")

