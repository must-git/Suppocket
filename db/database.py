import sqlite3
import datetime
import hashlib
import pandas as pd
import pytz

DATABASE_NAME = "suppocket.db"

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;") # Enforce foreign keys
    return conn

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
    
# --- Ticket CRUD Functions ---
def create_ticket(title, description, customer_id, category_name, priority_name, conn=None):
    """
    Creates a new support ticket.
    Validates category and priority names against existing tables.
    """
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    try:
        cursor = conn.cursor()
        now = datetime.datetime.now()

        # Validate Category
        cursor.execute("SELECT id FROM categories WHERE name = ? AND archived = 0", (category_name,))
        if cursor.fetchone() is None:
            print(f"Validation Error: Category '{category_name}' not found or is archived.")
            return None # Category not found or archived

        # Validate Priority
        if priority_name:
            cursor.execute("SELECT id FROM priorities WHERE name = ?", (priority_name,))
            if cursor.fetchone() is None:
                print(f"Validation Error: Priority '{priority_name}' not found.")
                return None # Priority not found

        cursor.execute(
            """
            INSERT INTO tickets (title, description, customer_id, category, priority, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 'Open', ?, ?)
            """,
            (title, description, customer_id, category_name, priority_name, now, now)
        )
        ticket_id = cursor.lastrowid
        conn.commit()
        log_activity(customer_id, "ticket_created", "tickets", ticket_id, f"Ticket '{title}' created with category '{category_name}' and priority '{priority_name}'.")
        
        # --- Send Email Notification ---
        try:
            from email_utils import send_ticket_created_notification
            send_ticket_created_notification(ticket_id)
        except Exception as e:
            print(f"Failed to send ticket creation email for ticket {ticket_id}: {e}")

        return ticket_id
    except sqlite3.Error as e:
        print(f"Database error in create_ticket: {e}")
        return None
    finally:
        if close_conn and conn:
            conn.close()

def get_tickets(customer_id=None, agent_id=None, include_unassigned=False, filters=None, order_by=None):
    """
    Retrieves tickets from the database with optional filtering and sorting.
    - customer_id: retrieves all tickets for that customer.
    - agent_id: retrieves tickets for that agent.
    - include_unassigned: for agents, also includes unassigned tickets.
    - filters: dictionary for additional filtering, e.g., {'status': 'Open'}.
    - order_by: string for ordering, e.g., 'created_at DESC'.
    - For agents/admins, includes SLA information.
    Returns a list of dictionaries.
    """
    conn = get_db_connection()
    is_customer = customer_id is not None
    try:
        query = """
            SELECT
                t.*,
                c.username as customer_name,
                a.username as agent_name,
                c_obj.id as category_id,
                c_obj.description as category_description,
                c_obj.color as category_color,
                p_obj.id as priority_id,
                p_obj.description as priority_description,
                p_obj.color as priority_color,
                p_obj.sort_order as priority_sort_order
        """
        if not is_customer:
            query += """,
                sla.response_time_hours,
                sla.resolution_time_hours
            """

        query += """
            FROM tickets t
            JOIN users c ON t.customer_id = c.id
            LEFT JOIN users a ON t.agent_id = a.id
            LEFT JOIN categories c_obj ON t.category = c_obj.name
            LEFT JOIN priorities p_obj ON t.priority = p_obj.name
        """
        if not is_customer:
            query += " LEFT JOIN sla_settings sla ON p_obj.id = sla.priority_id"

        params = []
        conditions = []

        # Role-based base filtering
        if customer_id:
            conditions.append("t.customer_id = ?")
            params.append(customer_id)
        elif agent_id:
            if include_unassigned:
                conditions.append("(t.agent_id = ? OR t.agent_id IS NULL)")
                params.append(agent_id)
            else:
                conditions.append("t.agent_id = ?")
                params.append(agent_id)

        # Apply additional filters from UI
        if filters:
            allowed_filter_keys = ['status', 'priority', 'category']
            for key, value in filters.items():
                if key in allowed_filter_keys and value:
                    conditions.append(f"t.{key} = ?")
                    params.append(value)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        # Apply sorting
        if order_by:
            allowed_order_by = {
                'created_at DESC': 't.created_at DESC',
                'created_at ASC': 't.created_at ASC',
                'updated_at DESC': 't.updated_at DESC',
                'updated_at ASC': 't.updated_at ASC',
            }
            if order_by in allowed_order_by:
                 query += f" ORDER BY {allowed_order_by[order_by]}"
            else:
                query += " ORDER BY t.updated_at DESC"
        else:
            query += " ORDER BY t.updated_at DESC"

        cursor = conn.cursor()
        cursor.execute(query, tuple(params))
        tickets = [dict(row) for row in cursor.fetchall()]

        if not is_customer:
            from sla_utils import get_business_hours_settings, calculate_sla_due_date, check_resolution_sla_status, check_response_sla_status
            sla_settings = get_business_hours_settings()
            for ticket in tickets:
                created_at_utc = datetime.datetime.fromisoformat(ticket['created_at']).replace(tzinfo=pytz.utc)

                # Resolution SLA
                resolution_due = calculate_sla_due_date(created_at_utc, ticket.get('resolution_time_hours'), sla_settings)
                ticket['resolution_due'] = resolution_due.isoformat() if resolution_due else None
                ticket['resolution_status'] = check_resolution_sla_status(ticket, resolution_due)

                # Response SLA
                response_due = calculate_sla_due_date(created_at_utc, ticket.get('response_time_hours'), sla_settings)
                ticket['response_due'] = response_due.isoformat() if response_due else None
                ticket['response_status'] = check_response_sla_status(ticket, response_due)
        return tickets
    finally:
        conn.close()

def update_ticket(ticket_id, user_id_for_log=None, **kwargs):
    """
    Updates a ticket's properties dynamically using keyword arguments.
    `user_id_for_log` should be passed to log who made the change.
    `kwargs` can contain: status, agent_id, category, priority.
    Validates category and priority names if they are being updated.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get old agent_id and status for email notification logic
    cursor.execute("SELECT agent_id, status FROM tickets WHERE id = ?", (ticket_id,))
    row = cursor.fetchone()
    old_agent_id = row['agent_id'] if row else None
    old_status = row['status'] if row else None

    allowed_fields = ['status', 'agent_id', 'category', 'priority']
    updates = []
    params = []
    now = datetime.datetime.now()
    details_for_log = []

    # Validate category and priority if they are in kwargs
    if 'category' in kwargs:
        category_name = kwargs['category']
        cursor.execute("SELECT id FROM categories WHERE name = ? AND archived = 0", (category_name,))
        if cursor.fetchone() is None:
            print(f"Validation Error: Category '{category_name}' not found or is archived for ticket update.")
            conn.close()
            return False
        
    if 'priority' in kwargs:
        priority_name = kwargs['priority']
        cursor.execute("SELECT id FROM priorities WHERE name = ?", (priority_name,))
        if cursor.fetchone() is None:
            print(f"Validation Error: Priority '{priority_name}' not found for ticket update.")
            conn.close()
            return False

    for key, value in kwargs.items():
        if key in allowed_fields:
            updates.append(f"{key} = ?")
            params.append(value)
            details_for_log.append(f"{key} to '{value}'")
            if key == 'status' and value in ['Resolved', 'Closed']:
                # Only set resolved_at if it is not already set
                cursor.execute("SELECT resolved_at FROM tickets WHERE id = ?", (ticket_id,))
                if cursor.fetchone()['resolved_at'] is None:
                    updates.append("resolved_at = ?")
                    params.append(now)

    if not updates:
        conn.close()
        return True # Nothing to update, but operation is successful

    updates.append("updated_at = ?")
    params.append(now)
    params.append(ticket_id)

    query = f"UPDATE tickets SET {', '.join(updates)} WHERE id = ?"

    try:
        cursor.execute(query, tuple(params))
        conn.commit()
        if cursor.rowcount > 0:
            log_activity(user_id_for_log, "ticket_updated", "tickets", ticket_id, f"Updated ticket: {', '.join(details_for_log)}.")
            
            # --- Send Email Notification on Assignment ---
            if 'agent_id' in kwargs and kwargs['agent_id'] is not None and kwargs['agent_id'] != old_agent_id:
                try:
                    from email_utils import send_ticket_assigned_notification
                    send_ticket_assigned_notification(ticket_id)
                except Exception as e:
                    print(f"Failed to send ticket assignment email for ticket {ticket_id}: {e}")
            # --- End Email ---

            # --- Send Email Notification on Resolution ---
            if 'status' in kwargs and kwargs['status'] == 'Resolved' and old_status != 'Resolved':
                try:
                    from email_utils import send_ticket_resolved_notification
                    send_ticket_resolved_notification(ticket_id)
                except Exception as e:
                    print(f"Failed to send ticket resolved email for ticket {ticket_id}: {e}")
            # --- End Email ---

            return True
        return False # No row was updated
    except sqlite3.Error as e:
        print(f"Database error on ticket update: {e}")
        return False
    finally:
        conn.close()

def delete_ticket(ticket_id, user_id_for_log=None):
    """Deletes a ticket from the database."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # We might want to add checks here later (e.g., only closed tickets can be deleted)
        cursor.execute("DELETE FROM tickets WHERE id = ?", (ticket_id,))
        conn.commit()
        if cursor.rowcount > 0:
            log_activity(user_id_for_log, "ticket_deleted", "tickets", ticket_id, f"Ticket ID {ticket_id} deleted.")
            return True
        return False
    finally:
        conn.close()
            
def get_ticket_counts_by_category():
    """Retrieves the count of tickets for each category."""
    conn = get_db_connection()
    try:
        query = """
            SELECT
                category,
                COUNT(id) as ticket_count
            FROM tickets
            GROUP BY category
            ORDER BY ticket_count DESC
        """
        cursor = conn.cursor()
        cursor.execute(query)
        return {row['category']: row['ticket_count'] for row in cursor.fetchall()}
    finally:
        conn.close()

def get_ticket_by_id(ticket_id):
    conn = get_db_connection()
    # Join with users, categories, and priorities to get all names and details
    query = """
    SELECT
        t.*,
        c.username as customer_name,
        a.username as agent_name,
        c_obj.id as category_id,
        c_obj.description as category_description,
        c_obj.color as category_color,
        p_obj.id as priority_id,
        p_obj.description as priority_description,
        p_obj.color as priority_color,
        p_obj.sort_order as priority_sort_order
    FROM tickets t
    JOIN users c ON t.customer_id = c.id
    LEFT JOIN users a ON t.agent_id = a.id
    LEFT JOIN categories c_obj ON t.category = c_obj.name
    LEFT JOIN priorities p_obj ON t.priority = p_obj.name
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
    
    # --- Send Email Notification ---
    if new_agent_id is not None:
        try:
            from email_utils import send_ticket_assigned_notification
            send_ticket_assigned_notification(ticket_id)
        except Exception as e:
            print(f"Failed to send ticket reassignment email for ticket {ticket_id}: {e}")
    # --- End Email ---

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

def get_activity_logs(start_date=None, end_date=None, user_id=None, action_type=None, limit=50, offset=0):
    """
    Retrieves activity logs with optional filtering and pagination.
    - start_date, end_date: filter by timestamp range (YYYY-MM-DD).
    - user_id: filter by a specific user.
    - action_type: filter by a specific action type.
    - limit, offset: for pagination.
    Returns a DataFrame and the total count of filtered logs.
    """
    conn = get_db_connection()
    conditions = []
    params = []

    query_base = """
    SELECT a.*, u.username
    FROM activity_logs a
    LEFT JOIN users u ON a.user_id = u.id
    """

    if start_date:
        conditions.append("DATE(a.timestamp) >= ?")
        params.append(start_date)
    if end_date:
        conditions.append("DATE(a.timestamp) <= ?")
        params.append(end_date)
    if user_id:
        conditions.append("a.user_id = ?")
        params.append(user_id)
    if action_type:
        conditions.append("a.action_type = ?")
        params.append(action_type)

    if conditions:
        query_base += " WHERE " + " AND ".join(conditions)

    query_base += " ORDER BY a.timestamp DESC"

    # Parameters for filtering only (used for count_query)
    filter_params = list(params) # Create a copy for the count query

    # For getting total count (for pagination info)
    count_query = "SELECT COUNT(*) FROM (" + query_base + ") AS sub"
    total_count_df = pd.read_sql_query(count_query, conn, params=filter_params)
    total_count = total_count_df.iloc[0, 0] if not total_count_df.empty else 0

    # Parameters for data retrieval (filters + limit/offset)
    data_params = list(params) # Create a new list, starting with filter params
    
    data_query = query_base
    if limit is not None and offset is not None:
        data_query += " LIMIT ? OFFSET ?"
        data_params.extend([limit, offset])

    df = pd.read_sql_query(data_query, conn, params=data_params)
    conn.close()
    return df, total_count

def get_distinct_activity_users():
    """Retrieves distinct user IDs and usernames from activity logs."""
    conn = get_db_connection()
    try:
        query = """
            SELECT DISTINCT a.user_id, u.username
            FROM activity_logs a
            JOIN users u ON a.user_id = u.id
            WHERE a.user_id IS NOT NULL
            ORDER BY u.username
        """
        cursor = conn.cursor()
        cursor.execute(query)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def get_distinct_action_types():
    """Retrieves distinct action types from activity logs."""
    conn = get_db_connection()
    try:
        query = "SELECT DISTINCT action_type FROM activity_logs ORDER BY action_type"
        cursor = conn.cursor()
        cursor.execute(query)
        return [row['action_type'] for row in cursor.fetchall()]
    finally:
        conn.close()

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
    try:
        cursor.executemany(query, data_to_insert)
        conn.commit()
        log_activity(admin_id, "sla_updated", "sla_settings", None, f"SLA settings updated for {len(settings_list)} priorities.")
        return cursor.rowcount > 0
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

if __name__ == '__main__':
    pass
    # You can add test code here
    # e.g. print(get_all_users())
    # e.g. print(get_categories())
    # e.g. print(get_priorities())
