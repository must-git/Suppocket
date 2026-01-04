import sqlite3
import datetime
import hashlib

DATABASE_NAME = "suppocket.db"

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row  # This allows accessing columns by name
    return conn

def initialize_database():
    """
    Initializes the database by creating the 'users' and 'tickets' tables
    if they do not already exist.
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

    # --- Create Tickets Table ---
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

    conn.commit()
    conn.close()

# --- User CRUD Functions ---

def create_user(username, email, password, role='customer', conn=None):
    """Creates a new user in the database."""
    
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    try:
        cursor = conn.cursor()
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
            (username, email, password_hash, role)
        )
        user_id = cursor.lastrowid
        conn.commit()
        return user_id
    except sqlite3.IntegrityError:
        return None
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None
    finally:
        if close_conn and conn:
            conn.close()

def get_user(user_id=None, email=None, username=None, conn=None):
    """
    Retrieves a user by their ID, email address, or username.
    Returns a dictionary representing the user, or None if not found.
    """
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
        
        if user_row:
            return dict(user_row)
        return None
    finally:
        if close_conn and conn:
            conn.close()

def update_user(user_id, new_username, new_email):
    """
    Updates a user's username and email.
    Returns True on success, False on failure (e.g., duplicate username/email).
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET username = ?, email = ? WHERE id = ?",
            (new_username, new_email, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.IntegrityError:
        # This error occurs if the new username or email is not unique
        return False
    except sqlite3.Error as e:
        print(f"Database error during user update: {e}")
        return False
    finally:
        if conn:
            conn.close()

def update_password_hash(user_id, new_password):
    """
    Updates a user's password hash in the database.
    Returns True on success, False otherwise.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        new_password_hash = hashlib.sha256(new_password.encode()).hexdigest()
        cursor.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (new_password_hash, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error during password update: {e}")
        return False
    finally:
        if conn:
            conn.close()

def get_all_customers():
    """
    Retrieves all users with the role 'customer'.
    Returns a list of dictionaries, each representing a customer.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE role = 'customer'")
    customer_rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in customer_rows]

def get_all_agents(conn=None):
    """
    Retrieves all users with the role 'agent'.
    Returns a list of dictionaries, each representing an agent.
    """
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
        
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email FROM users WHERE role = 'agent'")
        agent_rows = cursor.fetchall()
        return [dict(row) for row in agent_rows]
    finally:
        if close_conn and conn:
            conn.close()

# --- Ticket CRUD Functions ---

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
        return ticket_id
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None
    finally:
        if close_conn and conn:
            conn.close()

def get_ticket_by_id(ticket_id):
    """
    Retrieves a single ticket by its ID.
    Returns a dictionary representing the ticket, or None if not found.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
    ticket_row = cursor.fetchone()
    conn.close()
    if ticket_row:
        return dict(ticket_row)
    return None

def get_tickets(customer_id=None, agent_id=None, status=None, include_unassigned=False):
    """
    Retrieves a list of tickets, with optional filtering.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM tickets"
    filters = []
    params = []

    if customer_id:
        filters.append("customer_id = ?")
        params.append(customer_id)
    if agent_id is not None:
        if include_unassigned:
            filters.append("(agent_id = ? OR agent_id IS NULL)")
            params.append(agent_id)
        else:
            filters.append("agent_id = ?")
            params.append(agent_id)
    if status:
        filters.append("status = ?")
        params.append(status)

    if filters:
        query += " WHERE " + " AND ".join(filters)

    cursor.execute(query, tuple(params))
    tickets = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return tickets

def update_ticket(ticket_id, status=None, priority=None, agent_id=None):
    """
    Updates a ticket's status, priority, or assigned agent.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if status:
            updates.append("status = ?")
            params.append(status)
            if status in ['Resolved', 'Closed']:
                updates.append("resolved_at = ?")
                params.append(datetime.datetime.now())
        if priority:
            updates.append("priority = ?")
            params.append(priority)
        if agent_id is not None: # Allow un-assigning
            updates.append("agent_id = ?")
            params.append(agent_id)

        if not updates:
            return False

        updates.append("updated_at = ?")
        params.append(datetime.datetime.now())
        
        query = f"UPDATE tickets SET {', '.join(updates)} WHERE id = ?"
        params.append(ticket_id)

        cursor.execute(query, tuple(params))
        conn.commit()
        
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return False
    finally:
        if conn:
            conn.close()

def delete_ticket(ticket_id):
    """Deletes a ticket from the database."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tickets WHERE id = ?", (ticket_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    print("Initializing the Suppocket database...")
    # initialize_database()
    print("Database initialized successfully.")
    # ts = get_tickets()
    # print(ts)
    
    # Example usage:
    # print("Creating a new user...")
    # user_id = create_user("testuser", "test@example.com", "hashed_password")
    # if user_id:
    #     print(f"User created with ID: {user_id}")
    #     retrieved_user = get_user(user_id=user_id)
    #     print(f"Retrieved user: {retrieved_user}")
    
    #     print("Creating a ticket...")
    #     ticket_id = create_ticket("Test Ticket", "This is a test description.", user_id, "General", "Medium")
    #     if ticket_id:
    #         print(f"Ticket created with ID: {ticket_id}")
    #         print("All tickets for user:", get_tickets(customer_id=user_id))
    #         update_ticket(ticket_id, status='In Progress')
    #         print("Updated tickets for user:", get_tickets(customer_id=user_id))
    #         # delete_ticket(ticket_id)
    #         # print("Tickets after deletion:", get_tickets(customer_id=user_id))
