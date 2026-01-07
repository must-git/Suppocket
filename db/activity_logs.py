import sqlite3
import pandas as pd
from .database import get_db_connection

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
