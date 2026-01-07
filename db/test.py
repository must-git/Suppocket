from database import *
import pandas as pd

conn = get_db_connection()
try:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM system_settings",
    )
    slas = cursor.fetchall()
    df = pd.DataFrame(slas, columns=[desc[0] for desc in cursor.description])
    print("System Settings:")
    print(df)
except sqlite3.IntegrityError:
    conn.rollback()
finally:
    conn.close()
