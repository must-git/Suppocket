import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io
import plotly.express as px

from auth_utils import render_sidebar
from db.analytics_helpers import get_tickets_for_analytics, calculate_average_resolution_time

# Page config
st.set_page_config(
    page_title="Reports",
    page_icon="📄",
    layout="wide"
)

render_sidebar()

st.title("Report Generator")

# --- Authentication Check ---
if not st.session_state.get('authenticated') or st.session_state.get('user', {}).get('role') != 'admin':
    st.error("Access Denied: You must be an administrator to view this page.")
    if st.button("Go to Login"):
        st.switch_page("pages/1_Login.py")
    st.stop()

if not st.session_state.get('authenticated'):
    st.error("You must be logged in to view this page.")
    st.page_link("pages/1_Login.py", label="Login")
    st.stop()

# --- 1. REPORT BUILDER INTERFACE ---
st.header("1. Build Your Report")

with st.container(border=True):
    # Report Type
    report_type = st.selectbox(
        "Report Type",
        ["Summary", "Detailed", "Agent Performance", "Category Analysis", "SLA Compliance", "Trend", "Custom"],
        help="Select the type of report you want to generate."
    )

    # Date Range
    st.markdown("##### Date Range")
    date_presets = {
        "Today": (datetime.now().date(), datetime.now().date()),
        "This Week": (datetime.now().date() - timedelta(days=datetime.now().weekday()), datetime.now().date()),
        "This Month": (datetime.now().date().replace(day=1), datetime.now().date()),
        "Last Month": ((datetime.now().date().replace(day=1) - timedelta(days=1)).replace(day=1), (datetime.now().date().replace(day=1) - timedelta(days=1))),
        "This Quarter": (datetime(datetime.now().year, (datetime.now().month - 1) // 3 * 3 + 1, 1).date(), datetime.now().date()),
        "This Year": (datetime(datetime.now().year, 1, 1).date(), datetime.now().date()),
        "Custom Range": (datetime.now().date() - timedelta(days=30), datetime.now().date())
    }

    preset_selection = st.selectbox("Date Range Presets", list(date_presets.keys()), index=6)

    col1, col2 = st.columns(2)
    if preset_selection == "Custom Range":
        with col1:
            start_date = st.date_input("Start Date", date_presets["Custom Range"][0])
        with col2:
            end_date = st.date_input("End Date", date_presets["Custom Range"][1])
    else:
        start_date, end_date = date_presets[preset_selection]
        with col1:
            start_date = st.date_input("Start Date", start_date)
        with col2:
            end_date = st.date_input("End Date", end_date)


    # Filters
    st.markdown("##### Filters")
    
    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")
    user_role = st.session_state['user']['role']
    user_id = st.session_state['user']['id']

    @st.cache_data
    def load_filter_data(start, end, role, u_id):
        return get_tickets_for_analytics(start, end, role, u_id)

    all_tickets_df = load_filter_data(start_date_str, end_date_str, user_role, user_id)

    if all_tickets_df.empty:
        st.warning("No ticket data available for the selected date range to populate filters.")
        selected_categories, selected_priorities, selected_statuses, selected_agents, selected_customers = [], [], [], [], []
    else:
        category_options = all_tickets_df['category'].unique().tolist()
        priority_options = all_tickets_df['priority'].unique().tolist()
        status_options = all_tickets_df['status'].unique().tolist()
        agent_options = all_tickets_df['agent_id'].dropna().unique().tolist()
        customer_options = all_tickets_df['agent_id'].unique().tolist()

        f_col1, f_col2, f_col3 = st.columns(3)
        with f_col1:
            selected_categories = st.multiselect("Categories", category_options, default=category_options)
        with f_col2:
            selected_priorities = st.multiselect("Priorities", priority_options, default=priority_options)
        with f_col3:
            selected_statuses = st.multiselect("Status", status_options, default=status_options)

        f_col4, f_col5 = st.columns(2)
        with f_col4:
            selected_agents = st.multiselect("Agents", agent_options, default=agent_options)
        with f_col5:
            selected_customers = st.multiselect("Customers", customer_options, default=customer_options)

    # Metrics Selection
    st.markdown("##### Metrics")
    metrics_options = [
        "Total tickets", "Avg resolution time", "First response time",
        "Resolution rate", "SLA compliance %"
    ]
    selected_metrics = st.multiselect("Select metrics to include", metrics_options, default=["Total tickets", "Avg resolution time", "Resolution rate"])

    # Grouping and Sorting
    g_col1, g_col2 = st.columns(2)
    with g_col1:
        grouping_options = ["None", "Day", "Week", "Month", "Category", "Priority", "Agent"]
        selected_grouping = st.selectbox("Group By", grouping_options)
    with g_col2:
        sorting_options = ["created_at", "priority", "status", "resolved_at"]
        sort_map = {"Date": "created_at", "Priority": "priority", "Status": "status", "Resolution Time": "resolved_at"}
        selected_sorting = st.selectbox("Sort By", list(sort_map.keys()))

    # Generate Button
    if st.button("Generate Report", type="primary"):
        if all_tickets_df.empty:
            st.error("Cannot generate report, no initial data available for the selected date range.")
        else:
            filtered_df = all_tickets_df[
                all_tickets_df['category'].isin(selected_categories) &
                all_tickets_df['priority'].isin(selected_priorities) &
                all_tickets_df['status'].isin(selected_statuses) &
                (all_tickets_df['agent_id'].isin(selected_agents) | all_tickets_df['agent_id'].isnull()) &
                all_tickets_df['agent_id'].isin(selected_customers)
            ].copy()
            
            # Sorting
            filtered_df.sort_values(by=sort_map[selected_sorting], ascending=(selected_sorting != "Priority"), inplace=True)
            
            st.session_state['report_df'] = filtered_df
            st.session_state['report_generated'] = True


# --- 2. REPORT PREVIEW ---
st.header("2. Report Preview")
if st.session_state.get('report_generated', False):
    report_df = st.session_state.get('report_df')
    report_df = report_df.set_index('id')
    if report_df is None or report_df.empty:
        st.warning("No data matches the selected criteria.")
    else:
        st.success(f"Generated report for {len(report_df)} tickets.")
        st.markdown("#### Summary Metrics")
        
        # Calculate and display summary metrics
        num_metrics = len(selected_metrics)
        metric_cols = st.columns(num_metrics if num_metrics > 0 else 1)
        
        for i, metric in enumerate(selected_metrics):
            with metric_cols[i]:
                if metric == "Total tickets":
                    st.metric("Total Tickets", len(report_df))
                elif metric == "Avg resolution time":
                    avg_res_time = calculate_average_resolution_time(report_df)
                    st.metric("Avg Resolution Time", f"{avg_res_time:.2f} hrs")
                elif metric == "Resolution rate":
                    resolved_tickets = report_df[report_df['status'].isin(['Resolved', 'Closed'])]
                    resolution_rate = (len(resolved_tickets) / len(report_df) * 100) if len(report_df) > 0 else 0
                    st.metric("Resolution Rate", f"{resolution_rate:.2f}%")
                else:
                    st.metric(metric, "N/A")

        st.markdown("#### Data Table")
        st.dataframe(report_df)

        if report_type == "Category Analysis" or report_type == "Agent Performance":
            st.markdown("#### Charts")
            if report_type == "Category Analysis" and 'category' in report_df.columns:
                fig = px.bar(report_df['category'].value_counts(), title="Tickets per Category")
                st.plotly_chart(fig)
            elif report_type == "Agent Performance" and 'agent_id' in report_df.columns:
                fig = px.bar(report_df['agent_id'].value_counts(), title="Tickets per Agent")
                st.plotly_chart(fig)

# --- 3. EXPORT FUNCTIONALITY ---
st.header("3. Export Report")
with st.container(border=True):
    if st.session_state.get('report_generated', False) and st.session_state.get('report_df') is not None and not st.session_state.get('report_df').empty:
        report_df_to_export = st.session_state.get('report_df')
        e_col1, e_col2, e_col3 = st.columns(3)
        
        with e_col1:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                report_df_to_export.to_excel(writer, sheet_name='Detailed Data', index=False)
            excel_data = output.getvalue()
            st.download_button(
                label="📥 Export to Excel",
                data=excel_data,
                file_name="report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        with e_col2:
            csv = report_df_to_export.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export to CSV",
                data=csv,
                file_name="report.csv",
                mime="text/csv",
            )
        with e_col3:
            json_data = report_df_to_export.to_json(orient='records', indent=4).encode('utf-8')
            st.download_button(
                label="📥 Export to JSON",
                data=json_data,
                file_name="report.json",
                mime="application/json",
            )
    else:
        st.markdown("Generate a report to see export options.")
