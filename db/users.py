import sqlite3
import hashlib
import pandas as pd
from .database import get_db_connection
from .activity_logs import log_activity # Assuming this module will be created and contain log_activity

# --- User CRUD Functions (including Admin) ---

def create_user(username, email, password, role='customer', status='active', conn=None):
    """Creates a new user in the database."""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    try:
        cursor = conn.cursor()
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, role, status) VALUES (?, ?, ?, ?, ?)",
            (username, email, password_hash, role, status)
        )
        user_id = cursor.lastrowid
        conn.commit()
        log_activity(None, "user_created", "users", user_id, f"User '{username}' created with role '{role}'.")
        return user_id
    except sqlite3.IntegrityError:
        return None
    finally:
        if close_conn: conn.close()

def get_user(user_id=None, email=None, username=None, conn=None):
    """Retrieves a user by their ID, email, or username."""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    try:
        cursor = conn.cursor()
        if user_id:
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        elif email:
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        elif username:
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        else:
            return None
        user_row = cursor.fetchone()
        return dict(user_row) if user_row else None
    finally:
        if close_conn: conn.close()
        
def get_all_users():
    """Retrieves all users for the admin panel."""
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT id, username, email, role, status, created_at FROM users", conn)
    conn.close()
    return df

def update_user_admin(user_id, username, email, role, status):
    """Updates a user's details from the admin panel."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET username = ?, email = ?, role = ?, status = ? WHERE id = ?",
            (username, email, role, status, user_id)
        )
        conn.commit()
        log_activity(None, "user_updated", "users", user_id, f"User ID {user_id} details updated.")
        return cursor.rowcount > 0
    except sqlite3.IntegrityError:
        return False # Unique constraint failed
    finally:
        conn.close()

def delete_user(user_id):
    """Deletes a user if they have no associated tickets."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # Check for associated tickets as customer or agent
        cursor.execute("SELECT 1 FROM tickets WHERE customer_id = ? OR agent_id = ? LIMIT 1", (user_id, user_id))
        if cursor.fetchone():
            return "has_tickets" # Cannot delete user with tickets
        
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        if cursor.rowcount > 0:
            log_activity(None, "user_deleted", "users", user_id, f"User ID {user_id} deleted.")
            return True
        return False
    finally:
        conn.close()

def update_password_hash(user_id, new_password):
    """Updates a user's password hash."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        new_password_hash = hashlib.sha256(new_password.encode()).hexdigest()
        cursor.execute( "UPDATE users SET password_hash = ? WHERE id = ?", (new_password_hash, user_id) )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()

def get_all_agents(conn=None):
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    try:
        return pd.read_sql("SELECT id, username FROM users WHERE role = 'agent' AND status = 'active'", conn)
    finally:
        if close_conn: conn.close()

def get_all_customers(conn=None):
    """Retrieves all users with the 'customer' role."""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    try:
        # Returns a list of dicts to be compatible with UI components
        cursor = conn.cursor()
        cursor.execute("SELECT id, username FROM users WHERE role = 'customer' AND status = 'active' ORDER BY username")
        return [dict(row) for row in cursor.fetchall()]
    finally:
        if close_conn: conn.close()

def update_user(user_id, username, email):
    """Updates a user's own username and email. Not for admin use."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET username = ?, email = ? WHERE id = ?",
            (username, email, user_id)
        )
        conn.commit()
        if cursor.rowcount > 0:
            log_activity(user_id, "profile_updated", "users", user_id, "User updated their own profile.")
            return True
        return True # Return True even if no rows changed
    except sqlite3.IntegrityError:
        return False # Unique constraint failed
    finally:
        conn.close()
