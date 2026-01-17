from database import get_db_connection

def initialize_database():
    """
    Initializes and upgrades the database schema idempotently.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # --- Create Users Table ---
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
    
if __name__ == '__main__':
    print("Initializing/updating the Suppocket database...")
    initialize_database()