import sqlite3
import datetime
import pandas as pd
from .database import get_db_connection
from .activity_logs import log_activity # Assuming this module has been created

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