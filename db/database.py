import sqlite3
import datetime
import hashlib
import pandas as pd

DATABASE_NAME = "suppocket.db"

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;") # Enforce foreign keys
    return conn

def initialize_database():
    """
    Initializes and upgrades the database schema idempotently.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # --- Create Users Table (with status if not exists) ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'agent', 'customer')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    # Add status column to users if it doesn't exist
    cursor.execute("PRAGMA table_info(users)")
    if 'status' not in [col[1] for col in cursor.fetchall()]:
        cursor.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'active' NOT NULL CHECK(status IN ('active', 'inactive'))")

    # --- Create Categories Table ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            color TEXT,
            archived INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    # Seed default categories
    default_categories = [
        ('Technical', 'Issues related to technical problems.', '#3B82F6'),
        ('Billing', 'Billing and payment questions.', '#F59E0B'),
        ('General Inquiry', 'General questions about products or services.', '#10B981'),
        ('Bug Report', 'Reporting software bugs.', '#EF4444'),
        ('Feature Request', 'Requesting new features.', '#A855F7')
    ]
    cursor.execute("SELECT COUNT(*) FROM categories")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO categories (name, description, color) VALUES (?, ?, ?)", default_categories)

    # --- Create Priorities Table ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS priorities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            color TEXT,
            sort_order INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    # Seed default priorities
    default_priorities = [
        ('Low', 'Non-critical issues.', '#22C55E', 1),
        ('Medium', 'Standard issues.', '#F59E0B', 2),
        ('High', 'Urgent issues.', '#F97316', 3),
        ('Critical', 'System-down or critical impact issues.', '#EF4444', 4)
    ]
    cursor.execute("SELECT COUNT(*) FROM priorities")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO priorities (name, description, color, sort_order) VALUES (?, ?, ?, ?)", default_priorities)

    # --- Create Tickets Table ---
    # NOTE: Existing schema. No changes needed for now to maintain compatibility.
    # Future state: category and priority columns should be foreign keys.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT,
            priority TEXT CHECK(priority IN ('Low', 'Medium', 'High', 'Critical')),
            status TEXT CHECK(status IN ('Open', 'In Progress', 'Resolved', 'Closed')),
            customer_id INTEGER NOT NULL,
            agent_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP,
            resolved_at TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES users (id),
            FOREIGN KEY (agent_id) REFERENCES users (id)
        );
    """)

    # --- Create SLA Settings Table ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sla_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            priority_id INTEGER NOT NULL UNIQUE,
            response_time_hours INTEGER NOT NULL,
            resolution_time_hours INTEGER NOT NULL,
            updated_at TIMESTAMP,
            FOREIGN KEY (priority_id) REFERENCES priorities (id)
        );
    """)

    # --- Create System Settings Table ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_settings (
            setting_key TEXT PRIMARY KEY,
            setting_value TEXT,
            updated_at TIMESTAMP,
            updated_by INTEGER,
            FOREIGN KEY (updated_by) REFERENCES users (id)
        );
    """)

    # --- Create Activity Logs Table ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action_type TEXT NOT NULL,
            resource_type TEXT,
            resource_id INTEGER,
            details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        );
    """)

    conn.commit()
    conn.close()
    print("Database initialized/updated successfully.")

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

# --- Category & Priority CRUD ---
def get_categories(include_archived=False):
    conn = get_db_connection()
    query = "SELECT * FROM categories"
    if not include_archived:
        query += " WHERE archived = 0"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def add_category(name, description, color):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO categories (name, description, color) VALUES (?, ?, ?)", (name, description, color))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def update_category(cat_id, name, description, color):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE categories SET name=?, description=?, color=? WHERE id=?", (name, description, color, cat_id))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def archive_category(cat_id, archived=True):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE categories SET archived = ? WHERE id = ?", (1 if archived else 0, cat_id))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0

def get_priorities():
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM priorities ORDER BY sort_order", conn)
    conn.close()
    return df

def update_priority(prio_id, name, description, color):
    # In this implementation, only description and color are editable. Name is fixed.
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE priorities SET description=?, color=? WHERE id=?", (description, color, prio_id))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0
    
# --- Ticket CRUD Functions (Unchanged for now) ---
def create_ticket(title, description, customer_id, category, priority, conn=None):
    """Creates a new support ticket."""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    try:
        cursor = conn.cursor()
        now = datetime.datetime.now()
        cursor.execute(
            """
            INSERT INTO tickets (title, description, customer_id, category, priority, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 'Open', ?, ?)
            """,
            (title, description, customer_id, category, priority, now, now)
        )
        ticket_id = cursor.lastrowid
        conn.commit()
        log_activity(customer_id, "ticket_created", "tickets", ticket_id, f"Ticket '{title}' created.")
        return ticket_id
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None
    finally:
        if close_conn and conn:
            conn.close()
            
def get_ticket_by_id(ticket_id):
    conn = get_db_connection()
    # Join with users to get names
    query = """
    SELECT t.*, c.username as customer_name, a.username as agent_name
    FROM tickets t
    JOIN users c ON t.customer_id = c.id
    LEFT JOIN users a ON t.agent_id = a.id
    WHERE t.id = ?
    """
    row = conn.execute(query, (ticket_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_tickets_for_reassignment():
    conn = get_db_connection()
    query = """
    SELECT t.id, t.title, a.username as agent_name
    FROM tickets t
    LEFT JOIN users a ON t.agent_id = a.id
    WHERE t.status NOT IN ('Resolved', 'Closed')
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df
    
def reassign_ticket(ticket_id, new_agent_id, admin_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE tickets SET agent_id = ? WHERE id = ?", (new_agent_id, ticket_id))
    conn.commit()
    log_activity(admin_id, "ticket_reassigned", "tickets", ticket_id, f"Ticket reassigned to agent ID {new_agent_id}.")
    conn.close()
    return cursor.rowcount > 0

# --- Activity Log ---
def log_activity(user_id, action_type, resource_type=None, resource_id=None, details=""):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO activity_logs (user_id, action_type, resource_type, resource_id, details) VALUES (?, ?, ?, ?, ?)",
            (user_id, action_type, resource_type, resource_id, details)
        )
        conn.commit()
    except Exception as e:
        print(f"Failed to log activity: {e}") # Don't crash app if logging fails
    finally:
        conn.close()

def get_activity_logs(limit=50, offset=0):
    conn = get_db_connection()
    query = """
    SELECT a.*, u.username
    FROM activity_logs a
    LEFT JOIN users u ON a.user_id = u.id
    ORDER BY a.timestamp DESC
    LIMIT ? OFFSET ?
    """
    df = pd.read_sql_query(query, conn, params=(limit, offset))
    conn.close()
    return df

# --- System Settings ---
def get_system_settings():
    conn = get_db_connection()
    # Return as a dictionary
    settings = {}
    for row in conn.execute("SELECT setting_key, setting_value FROM system_settings").fetchall():
        settings[row['setting_key']] = row['setting_value']
    conn.close()
    return settings

def update_system_setting(key, value, admin_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.datetime.now()
    cursor.execute(
        "INSERT OR REPLACE INTO system_settings (setting_key, setting_value, updated_at, updated_by) VALUES (?, ?, ?, ?)",
        (key, value, now, admin_id)
    )
    conn.commit()
    log_activity(admin_id, "setting_updated", "system_settings", None, f"Setting '{key}' updated.")
    conn.close()

# --- SLA Settings ---
def get_sla_settings():
    """
    Retrieves SLA settings joined with priority names.
    Returns a DataFrame with priority_id, name, response_time_hours, resolution_time_hours.
    """
    conn = get_db_connection()
    # Join with priorities to get names and ensure all priorities are represented
    query = """
    SELECT
        p.id as priority_id,
        p.name,
        p.sort_order,
        s.response_time_hours,
        s.resolution_time_hours
    FROM priorities p
    LEFT JOIN sla_settings s ON p.id = s.priority_id
    ORDER BY p.sort_order
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def update_sla_settings(settings_list, admin_id):
    """
    Updates multiple SLA settings at once.
    `settings_list` is a list of tuples: (priority_id, response_time, resolution_time)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.datetime.now()
    
    # Use INSERT OR REPLACE to handle both new and existing SLA settings
    query = """
    INSERT OR REPLACE INTO sla_settings (priority_id, response_time_hours, resolution_time_hours, updated_at)
    VALUES (?, ?, ?, ?)
    """
    # Augment the list with the timestamp
    data_to_insert = [(p_id, resp, reso, now) for p_id, resp, reso in settings_list]
    
    cursor.executemany(query, data_to_insert)
    conn.commit()
    log_activity(admin_id, "sla_updated", "sla_settings", None, f"SLA settings updated for {len(settings_list)} priorities.")
    conn.close()

if __name__ == '__main__':
    print("Initializing/updating the Suppocket database...")
    initialize_database()

    # You can add test code here
    # e.g. print(get_all_users())
    # e.g. print(get_categories())
    # e.g. print(get_priorities())
