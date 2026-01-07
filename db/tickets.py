import sqlite3
import datetime
import pytz
import pandas as pd
from .database import get_db_connection
from .activity_logs import log_activity
from email_utils import send_ticket_created_notification, send_ticket_assigned_notification, send_ticket_resolved_notification
from sla_utils import get_business_hours_settings, calculate_sla_due_date, check_resolution_sla_status, check_response_sla_status

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
                    send_ticket_assigned_notification(ticket_id)
                except Exception as e:
                    print(f"Failed to send ticket assignment email for ticket {ticket_id}: {e}")
            # --- End Email ---

            # --- Send Email Notification on Resolution ---
            if 'status' in kwargs and kwargs['status'] == 'Resolved' and old_status != 'Resolved':
                try:
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
            send_ticket_assigned_notification(ticket_id)
        except Exception as e:
            print(f"Failed to send ticket reassignment email for ticket {ticket_id}: {e}")
    # --- End Email ---

    conn.close()
    return cursor.rowcount > 0
