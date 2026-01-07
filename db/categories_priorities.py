import sqlite3
import pandas as pd
from .database import get_db_connection

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