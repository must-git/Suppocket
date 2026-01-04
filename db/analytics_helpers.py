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

def calculate_average_resolution_time(df: pd.DataFrame = None, start_date: str = None, end_date: str = None) -> float:
    """
    Calculates the average resolution time for tickets.
    If a DataFrame is provided, it calculates the metric based on it.
    Otherwise, it fetches data within the given date range.
    """
    if df is None:
        if not start_date or not end_date:
            return 0.0
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

    # Ensure columns are datetime objects
    df['resolved_at'] = pd.to_datetime(df['resolved_at'])
    df['created_at'] = pd.to_datetime(df['created_at'])

    resolved_df = df[df['status'].isin(['Resolved', 'Closed']) & df['resolved_at'].notna()]
    if resolved_df.empty:
        return 0.0

    resolution_time = (resolved_df['resolved_at'] - resolved_df['created_at']).dt.total_seconds() / 3600  # in hours
    return resolution_time.mean()

def get_ticket_counts_by_category(df: pd.DataFrame = None, start_date: str = None, end_date: str = None) -> pd.DataFrame:
    """
    Gets the count of tickets for each category.
    If a DataFrame is provided, it calculates the metric based on it.
    """
    if df is None:
        if not start_date or not end_date:
            return pd.DataFrame()
        query = """
            SELECT category, COUNT(id) as count
            FROM tickets
            WHERE created_at BETWEEN ? AND ?
            GROUP BY category
            ORDER BY count DESC
        """
        df = _execute_query(query, (start_date, end_date))

    if df.empty:
        return pd.DataFrame()

    return df['category'].value_counts().reset_index()

def get_ticket_counts_by_priority(df: pd.DataFrame = None, start_date: str = None, end_date: str = None) -> pd.DataFrame:
    """
    Gets the count of tickets for each priority level.
    If a DataFrame is provided, it calculates the metric based on it.
    """
    if df is None:
        if not start_date or not end_date:
            return pd.DataFrame()
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
        df = _execute_query(query, (start_date, end_date))
    
    if df.empty:
        return pd.DataFrame()

    return df['priority'].value_counts().reset_index()

def get_ticket_trends(df: pd.DataFrame = None, start_date: str = None, end_date: str = None, grouping: str = 'daily') -> pd.DataFrame:
    """
    Gets ticket creation trends over time.
    If a DataFrame is provided, it calculates the trend based on it.
    """
    if df is None:
        if not start_date or not end_date:
            return pd.DataFrame()
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
        df = _execute_query(query, (start_date, end_date))
        return df

    if df.empty:
        return pd.DataFrame()
        
    df['created_at'] = pd.to_datetime(df['created_at'])
    
    # Resample based on the grouping
    if grouping == 'daily':
        resampler = 'D'
    elif grouping == 'weekly':
        resampler = 'W'
    elif grouping == 'monthly':
        resampler = 'M'
    else:
        resampler = 'D'
        
    trends = df.set_index('created_at').resample(resampler).size().reset_index(name='count')
    trends = trends.rename(columns={'created_at': 'date'})
    return trends

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

def get_tickets_for_analytics(start_date: str, end_date: str, user_role: str = None, user_id: int = None) -> pd.DataFrame:
    """
    Fetches tickets within a date range, with filtering based on user role.

    Args:
        start_date (str): The start date of the range (YYYY-MM-DD).
        end_date (str): The end date of the range (YYYY-MM-DD).
        user_role (str, optional): The role of the user ('admin', 'agent', 'customer').
        user_id (int, optional): The ID of the user.

    Returns:
        pd.DataFrame: A DataFrame containing the filtered tickets.
    """
    base_query = "SELECT * FROM tickets WHERE created_at BETWEEN ? AND ?"
    params = [start_date, end_date]

    if user_role == 'customer' and user_id:
        base_query += " AND customer_id = ?"
        params.append(user_id)
    elif user_role == 'agent' and user_id:
        base_query += " AND agent_id = ?"
        params.append(user_id)
    
    return _execute_query(base_query, tuple(params))

def get_status_breakdown_per_category(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates the count of tickets per status for each category.
    """
    if df.empty:
        return pd.DataFrame()

    return df.groupby(['category', 'status']).size().reset_index(name='count')

def get_open_ticket_age_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates the age of open tickets.
    """
    if df.empty:
        return pd.DataFrame()
        
    open_tickets = df[df['status'].isin(['Open', 'In Progress'])].copy()
    if open_tickets.empty:
        return pd.DataFrame()
        
    open_tickets['created_at'] = pd.to_datetime(open_tickets['created_at'])
    open_tickets['age_days'] = (datetime.now() - open_tickets['created_at']).dt.days
    return open_tickets[['age_days']]

