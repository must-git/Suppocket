import sqlite3
import datetime
from .database import get_db_connection
from .activity_logs import log_activity # Assuming this module has been created

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