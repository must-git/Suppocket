import streamlit as st
import pandas as pd
from db.database import get_tickets
from auth_utils import render_sidebar

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

if all_tickets:
    df = pd.DataFrame(all_tickets)

    # Key metrics
    total_tickets = len(df)
    open_tickets = len(df[df['status'] == 'Open'])
    in_progress_tickets = len(df[df['status'] == 'In Progress'])
    closed_tickets = len(df[df['status'] == 'Closed'])

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Tickets", total_tickets)
    with col2:
        st.metric("Open Tickets", open_tickets)
    with col3:
        st.metric("In Progress", in_progress_tickets)
    with col4:
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