"""
Provides functions for analyzing ticket data from the Suppocket database.
Returns data ready for visualization with Plotly and Altair.
"""

import sqlite3
import pandas as pd
from datetime import datetime
from db.users import get_user
import re
from collections import Counter
import streamlit as st

DATABASE_NAME = "suppocket.db"


def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DATABASE_NAME, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    return conn


def _execute_query(
    query: str, params: tuple = ()
) -> pd.DataFrame:
    """
    Executes a SQL query and returns the result as a pandas DataFrame.
    Includes error handling and ensures the connection is closed.
    """
    try:
        conn = get_db_connection()
        df = pd.read_sql_query(
            query, conn, params=params,
            parse_dates=['created_at', 'resolved_at', 'updated_at']
        )
        conn.close()
        return df
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return pd.DataFrame()
    except Exception as e:
        print(f"An error occurred: {e}")
        return pd.DataFrame()


def calculate_average_resolution_time(
    df: pd.DataFrame = None, start_date: str = None, end_date: str = None
) -> float:
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

    if (df.empty or 'resolved_at' not in df.columns or
            'created_at' not in df.columns):
        return 0.0

    # Ensure columns are datetime objects
    df['resolved_at'] = pd.to_datetime(df['resolved_at'])
    df['created_at'] = pd.to_datetime(df['created_at'])

    resolved_df = df[
        df['status'].isin(['Resolved', 'Closed']) & df['resolved_at'].notna()
    ]
    if resolved_df.empty:
        return 0.0

    resolution_time = (
        resolved_df['resolved_at'] - resolved_df['created_at']
    ).dt.total_seconds() / 3600  # in hours
    return resolution_time.mean()


def get_ticket_counts_by_category(
    df: pd.DataFrame = None, start_date: str = None, end_date: str = None
) -> pd.DataFrame:
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
            ORDER BY
                count DESC
        """
        df = _execute_query(query, (start_date, end_date))

    if df.empty:
        return pd.DataFrame()

    return df['category'].value_counts().reset_index()


def get_ticket_counts_by_priority(
    df: pd.DataFrame = None, start_date: str = None, end_date: str = None
) -> pd.DataFrame:
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


def get_ticket_trends(
    df: pd.DataFrame = None, start_date: str = None, end_date: str = None,
    grouping: str = 'daily'
) -> pd.DataFrame:
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
            SELECT STRFTIME('{date_format}', created_at) as date,
            COUNT(id) as count
            FROM tickets
            WHERE created_at BETWEEN ? AND ?
            GROUP BY date
            ORDER BY
                date ASC
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


@st.cache_data
def get_created_vs_resolved_trends(
    start_date: str, end_date: str, grouping: str = 'daily', user_id: int = None
) -> pd.DataFrame:
    """
    Compares created vs. resolved tickets over time.

    Args:
        start_date (str): The start date of the range (YYYY-MM-DD).
        end_date (str): The end date of the range (YYYY-MM-DD).
        grouping (str): The time grouping ('daily', 'weekly', 'monthly').
        user_id (int, optional): The ID of the user for filtering tickets.

    Returns:
        pd.DataFrame: DataFrame with 'date', 'created', and 'resolved' columns.
    """
    group_formats = {
        'daily': '%Y-%m-%d',
        'weekly': '%Y-%W',
        'monthly': '%Y-%m'
    }
    date_format = group_formats.get(grouping, '%Y-%m-%d')

    user_role = None
    if user_id:
        user = get_user(user_id=user_id)
        if user:
            user_role = user['role']

    created_query_parts = [
        f"SELECT STRFTIME('{date_format}', created_at) as date, "
        "COUNT(id) as created",
        "FROM tickets",
        "WHERE created_at BETWEEN ? AND ?"
    ]
    resolved_query_parts = [
        f"SELECT STRFTIME('{date_format}', resolved_at) as date, "
        "COUNT(id) as resolved",
        "FROM tickets",
        "WHERE resolved_at IS NOT NULL AND resolved_at BETWEEN ? AND ?"
    ]
    
    created_params = [start_date, end_date]
    resolved_params = [start_date, end_date]

    if user_role == 'customer':
        created_query_parts.append("AND customer_id = ?")
        resolved_query_parts.append("AND customer_id = ?")
        created_params.append(user_id)
        resolved_params.append(user_id)
    elif user_role == 'agent':
        created_query_parts.append("AND agent_id = ?")
        resolved_query_parts.append("AND agent_id = ?")
        created_params.append(user_id)
        resolved_params.append(user_id)

    created_query_parts.append("GROUP BY date")
    resolved_query_parts.append("GROUP BY date")

    created_query = " ".join(created_query_parts)
    resolved_query = " ".join(resolved_query_parts)
    
    created_df = _execute_query(created_query, tuple(created_params))
    resolved_df = _execute_query(resolved_query, tuple(resolved_params))

    if created_df.empty and resolved_df.empty:
        return pd.DataFrame(columns=['date', 'created', 'resolved'])

    merged_df = pd.merge(
        created_df, resolved_df, on='date', how='outer'
    ).fillna(0)
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
    df = get_ticket_counts_by_category(
        start_date, end_date
    )
    return df.head(top_n)


@st.cache_data
def get_agent_performance_metrics(
    start_date: str, end_date: str, user_id: int = None
) -> pd.DataFrame:
    """
    Gets performance metrics for each agent.

    Args:
        start_date (str): The start date of the range (YYYY-MM-DD).
        end_date (str): The end date of the range (YYYY-MM-DD).
        user_id (int, optional): The ID of the user for filtering agents.

    Returns:
        pd.DataFrame: DataFrame with agent performance data including
                      'agent_name', 'tickets_assigned', 'tickets_resolved',
                      and 'avg_resolution_time_hours'.
    """
    user_role = None
    if user_id:
        user = get_user(user_id=user_id)
        if user:
            user_role = user['role']

    query_parts = [
        "SELECT u.username as agent_name, t.agent_id, t.status, "
        "t.created_at, t.resolved_at",
        "FROM tickets t JOIN users u ON t.agent_id = u.id",
        "WHERE t.agent_id IS NOT NULL AND t.created_at BETWEEN ? AND ?"
    ]
    params = [start_date, end_date]

    if user_role == 'agent':
        query_parts.append("AND t.agent_id = ?")
        params.append(user_id)
    
    query = " ".join(query_parts)
    df = _execute_query(query, tuple(params))

    if df.empty:
        return pd.DataFrame(columns=['agent_name', 'tickets_assigned', 'tickets_resolved', 'avg_resolution_time_hours'])

    df_resolved = df[df['resolved_at'].notna()].copy()
    df_resolved['resolution_time_hours'] = (
        df_resolved['resolved_at'] - df_resolved['created_at']
    ).dt.total_seconds() / 3600

    assigned_counts = df.groupby('agent_name').size().reset_index(
        name='tickets_assigned'
    )
    resolved_counts = df[
        df['status'].isin(['Resolved', 'Closed'])
    ].groupby('agent_name').size().reset_index(name='tickets_resolved')
    avg_resolution = df_resolved.groupby('agent_name')[
        'resolution_time_hours'
    ].mean().reset_index(name='avg_resolution_time_hours')

    perf_df = pd.merge(
        assigned_counts, resolved_counts, on='agent_name', how='left'
    )
    perf_df = pd.merge(perf_df, avg_resolution, on='agent_name', how='left')

    return perf_df.fillna(0)


@st.cache_data
def get_resolution_time_by_category(
    start_date: str, end_date: str, user_id: int = None
) -> pd.DataFrame:
    """
    Calculates the average resolution time for each ticket category.

    Args:
        start_date (str): The start date of the range (YYYY-MM-DD).
        end_date (str): The end date of the range (YYYY-MM-DD).
        user_id (int, optional): The ID of the user for filtering tickets.

    Returns:
        pd.DataFrame: DataFrame with 'category' and 'avg_resolution_hours'.
    """
    user_role = None
    if user_id:
        user = get_user(user_id=user_id)
        if user:
            user_role = user['role']

    query_parts = [
        "SELECT category, JULIANDAY(resolved_at) - "
        "JULIANDAY(created_at) as resolution_days",
        "FROM tickets",
        "WHERE status IN ('Resolved', 'Closed') AND resolved_at IS NOT NULL "
        "AND resolved_at BETWEEN ? AND ?"
    ]
    params = [start_date, end_date]

    if user_role == 'customer':
        query_parts.append("AND customer_id = ?")
        params.append(user_id)
    elif user_role == 'agent':
        query_parts.append("AND agent_id = ?")
        params.append(user_id)

    query = " ".join(query_parts)
    df = _execute_query(query, tuple(params))

    if df.empty:
        return pd.DataFrame()

    df['avg_resolution_hours'] = df['resolution_days'] * 24
    return df.groupby('category')['avg_resolution_hours'].mean() \
        .reset_index().sort_values('avg_resolution_hours', ascending=False)


@st.cache_data
def get_resolution_time_by_priority(
    start_date: str, end_date: str, user_id: int = None
) -> pd.DataFrame:
    """
    Calculates the average resolution time for each ticket priority.

    Args:
        start_date (str): The start date of the range (YYYY-MM-DD).
        end_date (str): The end date of the range (YYYY-MM-DD).
        user_id (int, optional): The ID of the user for filtering tickets.

    Returns:
        pd.DataFrame: DataFrame with 'priority' and 'avg_resolution_hours'.
    """
    user_role = None
    if user_id:
        user = get_user(user_id=user_id)
        if user:
            user_role = user['role']

    query_parts = [
        "SELECT priority, JULIANDAY(resolved_at) - "
        "JULIANDAY(created_at) as resolution_days",
        "FROM tickets",
        "WHERE status IN ('Resolved', 'Closed') AND resolved_at IS NOT NULL "
        "AND resolved_at BETWEEN ? AND ?"
    ]
    params = [start_date, end_date]

    if user_role == 'customer':
        query_parts.append("AND customer_id = ?")
        params.append(user_id)
    elif user_role == 'agent':
        query_parts.append("AND agent_id = ?")
        params.append(user_id)

    query = " ".join(query_parts)
    df = _execute_query(query, tuple(params))

    if df.empty:
        return pd.DataFrame()

    df['avg_resolution_hours'] = df['resolution_days'] * 24
    return df.groupby('priority')['avg_resolution_hours'].mean() \
        .reset_index().sort_values('avg_resolution_hours', ascending=False)


@st.cache_data
def get_tickets_for_analytics(
    start_date: str, end_date: str, user_role: str = None, user_id: int = None
) -> pd.DataFrame:
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
    base_query = (
        "SELECT * FROM tickets "
        "WHERE created_at BETWEEN ? AND ?"
    )
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
    Calculates the age of open tickets and returns them with title and category.

    Args:
        df (pd.DataFrame): DataFrame containing ticket data.
                           Must include 'status', 'created_at', 'title', 
                           and 'category' columns.

    Returns:
        pd.DataFrame: A DataFrame with columns 'title', 'category', and 'age_days' 
                      for open tickets. Returns an empty DataFrame if no open 
                      tickets are found.
    """
    open_tickets = df[df['status'].isin(['Open', 'In Progress'])].copy()
    if open_tickets.empty:
        return pd.DataFrame({'title': [], 'category': [], 'age_days': []})

    open_tickets['created_at'] = pd.to_datetime(open_tickets['created_at'])
    now = datetime.now()
    open_tickets['age'] = now - open_tickets['created_at']
    open_tickets['age_days'] = open_tickets['age'].dt.days

    return open_tickets[['title', 'category', 'age_days']]


# List of common English stop words (can be expanded)
STOP_WORDS = set([
    "a", "an", "the", "and", "but", "or", "for", "nor", "on", "at", "to",
    "from", "by", "with", "about", "as", "is", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "not", "no", "don",
    "t", "s", "m", "ll", "ve", "re", "just", "can", "will", "would",
    "should", "could", "get", "go", "make", "know", "see", "take", "come",
    "think", "look", "want", "give", "use", "find", "tell", "ask", "work",
    "seem", "feel", "try", "leave", "call", "good", "new", "first", "last",
    "long", "great", "little", "own", "other", "old", "right", "big",
    "high", "different", "small", "large", "next", "early", "important",
    "few", "public", "bad", "same", "able", "back", "any", "each", "every",
    "many", "much", "some", "such", "up", "down", "out", "in", "off",
    "over", "under", "again", "further", "then", "once", "here", "there",
    "when", "where", "why", "how", "all", "any", "both", "each", "few",
    "more", "mocouldst", "other", "some", "such", "no", "nor", "not", "only",
    "own", "same", "so", "than", "too", "very", "can", "will", "just",
    "don't", "shouldn't", "now", "i", "me", "my", "myself", "we", "our",
    "ours", "ourselves", "you", "your", "yours", "yourself", "yourselves",
    "he", "him", "his", "himself", "she", "her", "hers", "herself", "it",
    "its", "itself", "they", "them", "their", "theirs", "themselves",
    "what", "which", "who", "whom", "this", "that", "these", "those", "am",
    "is", "are", "was", "were", "be", "been", "being", "have", "has",
    "had", "having", "do", "does", "did", "doing", "said", "from", "into",
    "through", "during", "before", "after", "above", "below", "to", "from",
    "up", "down", "in", "out", "on", "off", "over", "under", "again",
    "further", "then", "once", "here", "there", "when", "where", "why",
    "how", "all", "any", "both", "each", "few", "more", "most", "other",
    "some", "such", "no", "nor", "not", "only", "own", "same", "so", "than",
    "too", "very", "s", "t", "can", "will", "just", "don", "should", "now",
    "id", "im", "youre", "dont", "cant", "wouldnt", "nt", "shoudnt",
    "mustnt", "like", "get", "go", "one", "two", "three", "four", "five",
    "six", "seven", "eight", "nine", "ten", "day", "week", "month", "year",
    "issue", "problem", "report", "request", "ticket", "service", "support"
])


def get_top_keywords(
    df: pd.DataFrame, top_n: int = 10
) -> pd.DataFrame:
    """
    Extracts and counts the most frequent keywords from ticket titles and descriptions.

    Args:
        df (pd.DataFrame): DataFrame containing ticket data with 'title' and 'description' columns.
        top_n (int): The number of top keywords to return.

    Returns:
        pd.DataFrame: DataFrame with 'keyword' and 'count' of top keywords.
    """
    if df.empty or 'title' not in df.columns or 'description' not in df.columns:
        return pd.DataFrame(columns=['keyword', 'count'])

    # Combine title and description
    text_data = (
        df['title'] + " " + df['description'].fillna('')
    ).str.lower()

    # Tokenize, remove punctuation, filter stop words and short words
    all_words = []
    for text in text_data:
        # Remove non-alphabetic characters and split into words
        words = re.findall(r'[a-z]+', text)
        filtered_words = [
            word for word in words
            if word not in STOP_WORDS and len(word) > 2
        ]
        all_words.extend(filtered_words)

    # Count word frequencies
    word_counts = Counter(all_words)

    # Convert to DataFrame
    keywords_df = pd.DataFrame(word_counts.most_common(top_n),
                               columns=['keyword', 'count'])
    return keywords_df
