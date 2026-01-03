"""
This module provides functions for analyzing ticket data from the Suppocket database.
The functions are designed to return data in a format ready for visualization with
libraries like Plotly and Altair.
"""

import sqlite3
import pandas as pd
from datetime import datetime

DATABASE_NAME = "suppocket.db"

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DATABASE_NAME, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    return conn

def _execute_query(query: str, params: tuple = ()) -> pd.DataFrame:
    """
    Executes a SQL query and returns the result as a pandas DataFrame.
    Includes error handling and ensures the connection is closed.
    """
    try:
        conn = get_db_connection()
        df = pd.read_sql_query(query, conn, params=params, parse_dates=['created_at', 'resolved_at', 'updated_at'])
        conn.close()
        return df
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return pd.DataFrame()
    except Exception as e:
        print(f"An error occurred: {e}")
        return pd.DataFrame()

def calculate_average_resolution_time(start_date: str, end_date: str) -> float:
    """
    Calculates the average resolution time for tickets resolved within a date range.

    Args:
        start_date (str): The start date of the range (YYYY-MM-DD).
        end_date (str): The end date of the range (YYYY-MM-DD).

    Returns:
        float: The average resolution time in hours, or 0.0 if no tickets are found.
    """
    query = """
        SELECT created_at, resolved_at
        FROM tickets
        WHERE status IN ('Resolved', 'Closed')
          AND resolved_at IS NOT NULL
          AND resolved_at BETWEEN ? AND ?
    """
    df = _execute_query(query, (start_date, end_date))

    if df.empty or 'resolved_at' not in df.columns or 'created_at' not in df.columns:
        return 0.0

    df['resolution_time'] = (df['resolved_at'] - df['created_at']).dt.total_seconds() / 3600  # in hours
    return df['resolution_time'].mean()

def get_ticket_counts_by_category(start_date: str, end_date: str) -> pd.DataFrame:
    """
    Gets the count of tickets for each category within a given date range.

    Args:
        start_date (str): The start date of the range (YYYY-MM-DD).
        end_date (str): The end date of the range (YYYY-MM-DD).

    Returns:
        pd.DataFrame: DataFrame with 'category' and 'count' columns.
    """
    query = """
        SELECT category, COUNT(id) as count
        FROM tickets
        WHERE created_at BETWEEN ? AND ?
        GROUP BY category
        ORDER BY count DESC
    """
    return _execute_query(query, (start_date, end_date))

def get_ticket_counts_by_priority(start_date: str, end_date: str) -> pd.DataFrame:
    """
    Gets the count of tickets for each priority level within a given date range.

    Args:
        start_date (str): The start date of the range (YYYY-MM-DD).
        end_date (str): The end date of the range (YYYY-MM-DD).

    Returns:
        pd.DataFrame: DataFrame with 'priority' and 'count' columns.
    """
    query = """
        SELECT priority, COUNT(id) as count
        FROM tickets
        WHERE created_at BETWEEN ? AND ?
        GROUP BY priority
        ORDER BY
            CASE priority
                WHEN 'Critical' THEN 1
                WHEN 'High' THEN 2
                WHEN 'Medium' THEN 3
                WHEN 'Low' THEN 4
                ELSE 5
            END
    """
    return _execute_query(query, (start_date, end_date))

def get_ticket_trends(start_date: str, end_date: str, grouping: str = 'daily') -> pd.DataFrame:
    """
    Gets ticket creation trends over time, grouped by day, week, or month.

    Args:
        start_date (str): The start date of the range (YYYY-MM-DD).
        end_date (str): The end date of the range (YYYY-MM-DD).
        grouping (str): The time grouping ('daily', 'weekly', 'monthly').

    Returns:
        pd.DataFrame: DataFrame with 'date' and 'count' columns.
    """
    group_formats = {
        'daily': '%Y-%m-%d',
        'weekly': '%Y-%W',
        'monthly': '%Y-%m'
    }
    date_format = group_formats.get(grouping, '%Y-%m-%d')

    query = f"""
        SELECT STRFTIME('{date_format}', created_at) as date, COUNT(id) as count
        FROM tickets
        WHERE created_at BETWEEN ? AND ?
        GROUP BY date
        ORDER BY date ASC
    """
    return _execute_query(query, (start_date, end_date))

def get_created_vs_resolved_trends(start_date: str, end_date: str, grouping: str = 'daily') -> pd.DataFrame:
    """
    Compares created vs. resolved tickets over time.

    Args:
        start_date (str): The start date of the range (YYYY-MM-DD).
        end_date (str): The end date of the range (YYYY-MM-DD).
        grouping (str): The time grouping ('daily', 'weekly', 'monthly').

    Returns:
        pd.DataFrame: DataFrame with 'date', 'created', and 'resolved' columns.
    """
    group_formats = {
        'daily': '%Y-%m-%d',
        'weekly': '%Y-%W',
        'monthly': '%Y-%m'
    }
    date_format = group_formats.get(grouping, '%Y-%m-%d')

    created_query = f"""
        SELECT STRFTIME('{date_format}', created_at) as date, COUNT(id) as created
        FROM tickets
        WHERE created_at BETWEEN ? AND ?
        GROUP BY date
    """
    resolved_query = f"""
        SELECT STRFTIME('{date_format}', resolved_at) as date, COUNT(id) as resolved
        FROM tickets
        WHERE resolved_at IS NOT NULL
          AND resolved_at BETWEEN ? AND ?
        GROUP BY date
    """
    created_df = _execute_query(created_query, (start_date, end_date))
    resolved_df = _execute_query(resolved_query, (start_date, end_date))

    if created_df.empty and resolved_df.empty:
        return pd.DataFrame(columns=['date', 'created', 'resolved'])

    merged_df = pd.merge(created_df, resolved_df, on='date', how='outer').fillna(0)
    merged_df['created'] = merged_df['created'].astype(int)
    merged_df['resolved'] = merged_df['resolved'].astype(int)
    return merged_df.sort_values('date').reset_index(drop=True)

def get_recurring_issues(start_date: str, end_date: str, top_n: int = 5) -> pd.DataFrame:
    """
    Analyzes recurring issues by finding the most common ticket categories.

    Args:
        start_date (str): The start date of the range (YYYY-MM-DD).
        end_date (str): The end date of the range (YYYY-MM-DD).
        top_n (int): The number of top categories to return.

    Returns:
        pd.DataFrame: DataFrame with the top N 'category' and their 'count'.
    """
    df = get_ticket_counts_by_category(start_date, end_date)
    return df.head(top_n)

def get_agent_performance_metrics(start_date: str, end_date: str) -> pd.DataFrame:
    """
    Gets performance metrics for each agent.

    Args:
        start_date (str): The start date of the range (YYYY-MM-DD).
        end_date (str): The end date of the range (YYYY-MM-DD).

    Returns:
        pd.DataFrame: DataFrame with agent performance data including
                      'agent_name', 'tickets_assigned', 'tickets_resolved',
                      and 'avg_resolution_time_hours'.
    """
    query = """
        SELECT
            u.username as agent_name,
            t.agent_id,
            t.status,
            t.created_at,
            t.resolved_at
        FROM tickets t
        JOIN users u ON t.agent_id = u.id
        WHERE t.agent_id IS NOT NULL
          AND t.created_at BETWEEN ? AND ?
    """
    df = _execute_query(query, (start_date, end_date))

    if df.empty:
        return pd.DataFrame(columns=['agent_name', 'tickets_assigned', 'tickets_resolved', 'avg_resolution_time_hours'])

    df_resolved = df[df['resolved_at'].notna()].copy()
    df_resolved['resolution_time_hours'] = (df_resolved['resolved_at'] - df_resolved['created_at']).dt.total_seconds() / 3600

    assigned_counts = df.groupby('agent_name').size().reset_index(name='tickets_assigned')
    resolved_counts = df[df['status'].isin(['Resolved', 'Closed'])].groupby('agent_name').size().reset_index(name='tickets_resolved')
    avg_resolution = df_resolved.groupby('agent_name')['resolution_time_hours'].mean().reset_index(name='avg_resolution_time_hours')

    perf_df = pd.merge(assigned_counts, resolved_counts, on='agent_name', how='left')
    perf_df = pd.merge(perf_df, avg_resolution, on='agent_name', how='left')

    return perf_df.fillna(0)

def get_resolution_time_by_category(start_date: str, end_date: str) -> pd.DataFrame:
    """
    Calculates the average resolution time for each ticket category.

    Args:
        start_date (str): The start date of the range (YYYY-MM-DD).
        end_date (str): The end date of the range (YYYY-MM-DD).

    Returns:
        pd.DataFrame: DataFrame with 'category' and 'avg_resolution_hours'.
    """
    query = """
        SELECT
            category,
            JULIANDAY(resolved_at) - JULIANDAY(created_at) as resolution_days
        FROM tickets
        WHERE status IN ('Resolved', 'Closed')
          AND resolved_at IS NOT NULL
          AND resolved_at BETWEEN ? AND ?
    """
    df = _execute_query(query, (start_date, end_date))

    if df.empty:
        return pd.DataFrame()

    df['avg_resolution_hours'] = df['resolution_days'] * 24
    return df.groupby('category')['avg_resolution_hours'].mean().reset_index().sort_values('avg_resolution_hours', ascending=False)

def get_resolution_time_by_priority(start_date: str, end_date: str) -> pd.DataFrame:
    """
    Calculates the average resolution time for each ticket priority.

    Args:
        start_date (str): The start date of the range (YYYY-MM-DD).
        end_date (str): The end date of the range (YYYY-MM-DD).

    Returns:
        pd.DataFrame: DataFrame with 'priority' and 'avg_resolution_hours'.
    """
    query = """
        SELECT
            priority,
            JULIANDAY(resolved_at) - JULIANDAY(created_at) as resolution_days
        FROM tickets
        WHERE status IN ('Resolved', 'Closed')
          AND resolved_at IS NOT NULL
          AND resolved_at BETWEEN ? AND ?
    """
    df = _execute_query(query, (start_date, end_date))

    if df.empty:
        return pd.DataFrame()

    df['avg_resolution_hours'] = df['resolution_days'] * 24
    return df.groupby('priority')['avg_resolution_hours'].mean().reset_index().sort_values('avg_resolution_hours', ascending=False)
