import streamlit as st
import pandas as pd
import datetime
import pytz
from db.tickets import get_tickets
from auth_utils import render_sidebar
from sla_utils import get_business_hours_settings

st.set_page_config(
    page_title="Dashboard",
    page_icon="🎫",
    layout="wide"
)

render_sidebar()

st.title("Ticket Dashboard")

if not st.session_state.get('authenticated'):
    st.error("Please log in to access this page.")
    st.page_link("pages/1_Login.py", label="Login")
    st.stop()

current_user = st.session_state['user']
user_role = current_user['role']

all_tickets = []
assigned_tickets = []
if user_role == 'customer':
    all_tickets = get_tickets(customer_id=current_user['id'])
elif user_role == 'agent':
    all_tickets = get_tickets(agent_id=current_user['id'], include_unassigned=True)
    assigned_tickets = [ticket for ticket in all_tickets if ticket['agent_id'] == current_user['id']]
elif user_role == 'admin':
    all_tickets = get_tickets()

st.markdown("---")

if user_role == 'agent' and assigned_tickets:
    st.subheader("My Assigned Tickets")
    assigned_df = pd.DataFrame(assigned_tickets)
    st.dataframe(assigned_df[['id', 'title', 'status', 'priority', 'created_at']], use_container_width=True)
    st.markdown("---")

# At-risk tickets for agents and admins
if user_role in ['agent', 'admin'] and all_tickets:
    sla_settings = get_business_hours_settings()
    mode_display = "Business Hours" if sla_settings.get('mode') == 'business_hours' else "Calendar Hours (24/7)"
    st.info(f"SLA Calculation Mode: **{mode_display}** (Timezone: {sla_settings.get('timezone')})")

    at_risk_tickets = []
    now_utc = datetime.datetime.now(pytz.utc)
    threshold = datetime.timedelta(hours=24)

    for ticket in all_tickets:
        if ticket.get('resolution_status') == 'On Track' and ticket.get('resolution_due'):
            try:
                resolution_due_utc = datetime.datetime.fromisoformat(ticket['resolution_due'])
                if resolution_due_utc.tzinfo is None:
                    resolution_due_utc = pytz.utc.localize(resolution_due_utc)
                
                time_to_due = resolution_due_utc - now_utc
                
                if datetime.timedelta(seconds=0) < time_to_due <= threshold:
                    ticket['time_left'] = str(time_to_due).split('.')[0]
                    at_risk_tickets.append(ticket)
            except (ValueError, TypeError):
                continue
    
    if at_risk_tickets:
        with st.expander("🔥 At-Risk Tickets (Resolution due within 24 hours)", expanded=True):
            at_risk_df = pd.DataFrame(at_risk_tickets)
            
            at_risk_df['resolution_due_display'] = pd.to_datetime(at_risk_df['resolution_due']).dt.tz_convert(sla_settings['timezone']).dt.strftime('%Y-%m-%d %H:%M')
            
            st.dataframe(
                at_risk_df[['id', 'title', 'status', 'priority', 'resolution_due_display', 'time_left']],
                column_config={
                    "id": "Ticket ID",
                    "resolution_due_display": "Resolution Due",
                    "time_left": "Time Left Until Breach"
                },
                use_container_width=True,
                hide_index=True
            )
        st.markdown("---")

if all_tickets:
    df = pd.DataFrame(all_tickets)

    # Key metrics
    total_tickets = len(df)
    open_tickets = len(df[df['status'] == 'Open'])
    in_progress_tickets = len(df[df['status'] == 'In Progress'])
    resolved_tickets = len(df[df['status'] == 'Resolved'])
    closed_tickets = len(df[df['status'] == 'Closed'])

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Tickets", total_tickets)
    with col2:
        st.metric("Open Tickets", open_tickets)
    with col3:
        st.metric("In Progress", in_progress_tickets)
    with col4:
        st.metric("Resolved Tickets", resolved_tickets)
    with col5:
        st.metric("Closed Tickets", closed_tickets)

    st.markdown("---")

    # Charts
    col1_chart, col2_chart = st.columns(2)

    with col1_chart:
        st.subheader("Tickets by Status")
        status_counts = df['status'].value_counts()
        st.bar_chart(status_counts)

    with col2_chart:
        st.subheader("Tickets by Priority")
        priority_counts = df['priority'].value_counts()
        st.bar_chart(priority_counts)

else:
    st.info("No tickets to display.")
