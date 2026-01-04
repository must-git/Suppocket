import sqlite3
import hashlib
from db.database import create_user, get_db_connection, initialize_database

def hash_password(password):
    """Hashes a password using SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()

def seed_users():
    """Seeds the database with default users if they don't exist."""
    
    # Initialize the database to ensure tables are created
    initialize_database()
    
    users_to_add = [
        {"username": "admin", "email": "admin@suppocket.com", "password": "123", "role": "admin"},
        {"username": "agent1", "email": "agent1@suppocket.com", "password": "123", "role": "agent"},
        {"username": "agent2", "email": "agent2@suppocket.com", "password": "123", "role": "agent"},
    ]

    conn = get_db_connection()
    cursor = conn.cursor()

    for user_data in users_to_add:
        # Check if user already exists
        cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", (user_data["username"], user_data["email"]))
        if cursor.fetchone():
            print(f"User {user_data['username']} or email {user_data['email']} already exists. Skipping.")
            continue

        # If user doesn't exist, create them
        password_hash = hash_password(user_data["password"])
        user_id = create_user(
            username=user_data["username"],
            email=user_data["email"],
            password_hash=password_hash,
            role=user_data["role"]
        )
        if user_id:
            print(f"Successfully created user: {user_data['username']} (ID: {user_id})")
        else:
            print(f"Failed to create user: {user_data['username']}")
    
    conn.close()

if __name__ == "__main__":
    print("Seeding database with initial users...")
    seed_users()
    print("Database seeding complete.")
