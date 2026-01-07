import sqlite3

DATABASE_NAME = "suppocket.db"

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;") # Enforce foreign keys
    return conn

if __name__ == '__main__':
    pass