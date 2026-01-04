
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from db.analytics_helpers import (
    calculate_average_resolution_time,
    get_tickets_for_analytics,
    get_status_breakdown_per_category,
    get_resolution_time_by_category,
    get_resolution_time_by_priority,
    get_created_vs_resolved_trends,
    get_open_ticket_age_distribution,
    get_agent_performance_metrics
)
from auth_utils import render_sidebar
from utils.theme import apply_theme

st.set_page_config(
    page_title="Advanced Analytics",
    page_icon="📊",
    layout="wide"
)
apply_theme()
render_sidebar()

# Determine the plot template based on the session theme
plotly_template = "plotly_dark" if st.session_state.get('theme', 'light') == 'dark' else "plotly_white"

st.title("📊 Advanced Analytics Dashboard")
st.markdown("Deep dive into ticket trends, team performance, and resolution metrics.")

if not st.session_state.get('authenticated'):
    st.error("You must be logged in to view this page.")
    st.page_link("pages/1_Login.py", label="Login")
    st.stop()

current_user = st.session_state['user']
user_role = current_user['role']
user_id = current_user['id']

# --- Color Mappings ---
STATUS_COLORS = {
    'Open': '#3B82F6', 
    'In Progress': '#F59E0B',
    'Resolved': '#10B981', 
    'Closed': '#6B7280'
}
PRIORITY_COLORS = {
    'Critical': '#EF4444', 
    'High': '#F97316', 
    'Medium': '#F59E0B', 
    'Low': '#22C55E'
}

# --- Date Range and Filters ---
with st.expander("Filters", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        today = datetime.now()
        start_date = st.date_input("Start Date", today - timedelta(days=30))
    with col2:
        end_date = st.date_input("End Date", today)

    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")

    all_tickets_df = get_tickets_for_analytics(start_date_str, end_date_str, user_role, user_id)

    if all_tickets_df.empty:
        st.warning("No ticket data available for the selected date range and your permissions.")
        st.stop()

    category_options = all_tickets_df['category'].unique().tolist()
    priority_options = all_tickets_df['priority'].unique().tolist()
    status_options = all_tickets_df['status'].unique().tolist()

    col3, col4, col5 = st.columns(3)
    with col3:
        selected_categories = st.multiselect("Category", category_options, default=category_options)
    with col4:
        selected_priorities = st.multiselect("Priority", priority_options, default=priority_options)
    with col5:
        selected_statuses = st.multiselect("Status", status_options, default=status_options)

# --- Filtered Data ---
filtered_df = all_tickets_df[
    all_tickets_df['category'].isin(selected_categories) &
    all_tickets_df['priority'].isin(selected_priorities) &
    all_tickets_df['status'].isin(selected_statuses)
]

if filtered_df.empty:
    st.warning("No tickets match the current filter criteria.")
    st.stop()

# --- Key Metrics ---
total_tickets = len(filtered_df)
avg_resolution_time = calculate_average_resolution_time(df=filtered_df)
resolved_tickets = filtered_df[filtered_df['status'].isin(['Resolved', 'Closed'])]
resolution_rate = (len(resolved_tickets) / total_tickets * 100) if total_tickets > 0 else 0
open_tickets_count = len(filtered_df[filtered_df['status'].isin(['Open', 'In Progress'])])

st.markdown("### Key Metrics")
kpi_cols = st.columns(4)
kpi_cols[0].metric("Total Tickets", f"{total_tickets}")
kpi_cols[1].metric("Avg Resolution Time", f"{avg_resolution_time:.2f} hrs")
kpi_cols[2].metric("Resolution Rate", f"{resolution_rate:.2f}%")
kpi_cols[3].metric("Open Tickets", f"{open_tickets_count}")
st.markdown("---")

# --- Chart Section ---
with st.expander("Ticket Status & Trends", expanded=True):
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Status Breakdown by Category")
        status_breakdown_df = get_status_breakdown_per_category(filtered_df)
        if not status_breakdown_df.empty:
            fig = px.bar(
                status_breakdown_df,
                x="category",
                y="count",
                color="status",
                title="Status Breakdown per Category",
                labels={"count": "Number of Tickets", "category": "Category"},
                color_discrete_map=STATUS_COLORS,
                barmode="stack"
            )
            fig.update_layout(legend_title_text='Status', template=plotly_template)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data available for Status Breakdown.")

    with col2:
        st.subheader("Open Ticket Age Distribution")
        open_ticket_age_df = get_open_ticket_age_distribution(filtered_df)
        if not open_ticket_age_df.empty:
            fig = px.histogram(
                open_ticket_age_df,
                x="age_days",
                title="Open Ticket Age Distribution (Days)",
                labels={"age_days": "Age in Days"},
                nbins=int(max(open_ticket_age_df['age_days'].max() + 1, 1))
            )
            fig.update_layout(
                xaxis=dict(tick0=0, dtick=1),
                bargap=0.1,
                template=plotly_template
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No open tickets to show age distribution.")

with st.expander("Resolution & Performance Metrics", expanded=True):
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Average Resolution Time by Category")
        resolution_by_cat_df = get_resolution_time_by_category(start_date_str, end_date_str)
        if not resolution_by_cat_df.empty:
            fig = px.bar(
                resolution_by_cat_df,
                x="category",
                y="avg_resolution_hours",
                title="Avg. Resolution Time by Category",
                labels={"avg_resolution_hours": "Average Resolution (hours)", "category": "Category"},
                color="category"
            )
            fig.update_layout(template=plotly_template)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data available for Resolution Time by Category.")

    with col2:
        st.subheader("Average Resolution Time by Priority")
        resolution_by_prio_df = get_resolution_time_by_priority(start_date_str, end_date_str)
        if not resolution_by_prio_df.empty:
            fig = px.bar(
                resolution_by_prio_df,
                x="priority",
                y="avg_resolution_hours",
                title="Avg. Resolution Time by Priority",
                labels={"avg_resolution_hours": "Average Resolution (hours)", "priority": "Priority"},
                color="priority",
                color_discrete_map=PRIORITY_COLORS
            )
            fig.update_layout(template=plotly_template)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data available for Resolution Time by Priority.")

if user_role == 'admin':
    with st.expander("Agent Performance", expanded=True):
        st.subheader("Agent Performance: Tickets Resolved")
        agent_perf_df = get_agent_performance_metrics(start_date_str, end_date_str)
        if not agent_perf_df.empty:
            fig = px.bar(
                agent_perf_df,
                y="agent_name",
                x="tickets_resolved",
                orientation='h',
                title="Tickets Resolved per Agent",
                labels={"tickets_resolved": "Number of Tickets Resolved", "agent_name": "Agent"},
                color="agent_name"
            )
            fig.update_layout(template=plotly_template)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No agent performance data available.")

with st.expander("Ticket Volume Trends", expanded=True):
    st.subheader("Tickets Created vs. Resolved Trend")
    created_resolved_df = get_created_vs_resolved_trends(start_date_str, end_date_str)
    if not created_resolved_df.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=created_resolved_df['date'],
            y=created_resolved_df['created'],
            mode='lines+markers',
            name='Tickets Created',
            line=dict(color='royalblue')
        ))
        fig.add_trace(go.Scatter(
            x=created_resolved_df['date'],
            y=created_resolved_df['resolved'],
            mode='lines+markers',
            name='Tickets Resolved',
            line=dict(color='limegreen')
        ))
        fig.update_layout(
            title="Tickets Created vs. Resolved Trend",
            xaxis_title="Date",
            yaxis_title="Number of Tickets",
            legend_title="Metric",
            template=plotly_template
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data available for Created vs. Resolved trends.")

