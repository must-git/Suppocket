import streamlit as st
from db.database import get_tickets, get_user, update_ticket
from auth_utils import render_sidebar
from utils.theme import apply_theme

st.set_page_config(
    page_title="All Tickets",
    page_icon="🎫",
    layout="wide"
)
apply_theme()

render_sidebar()

st.title("All Tickets")

if not st.session_state.get('authenticated'):
    st.error("Please log in to access this page.")
    st.page_link("pages/1_Login.py", label="Login")
    st.stop()

current_user = st.session_state['user']
user_role = current_user['role']

all_tickets = []
if user_role == 'customer':
    all_tickets = get_tickets(customer_id=current_user['id'])
elif user_role == 'agent':
    all_tickets = get_tickets(agent_id=current_user['id'], include_unassigned=True)
elif user_role == 'admin':
    all_tickets = get_tickets()

st.markdown("---")

if all_tickets:
    # Display headers
    col1_h, col2_h, col3_h, col4_h, col5_h, col6_h = st.columns([1, 2, 3, 1, 1, 1])
    with col1_h:
        st.subheader("ID")
    with col2_h:
        st.subheader("Customer")
    with col3_h:
        st.subheader("Title")
    with col4_h:
        st.subheader("Priority")
    with col5_h:
        st.subheader("Status")
    with col6_h:
        st.subheader("Action")
    st.markdown("---")

    for ticket in all_tickets:
        col1, col2, col3, col4, col5, col6 = st.columns([1, 2, 3, 1, 1, 1])
        
        customer_info = get_user(user_id=ticket['customer_id'])
        customer_name = customer_info['username'] if customer_info else "Unknown"

        with col1:
            st.write(f"**#{ticket['id']}**")
        with col2:
            st.write(customer_name)
        with col3:
            st.write(ticket['title'])
        with col4:
            priority_colors = {'Low': '🟢', 'Medium': '🟡', 'High': '🔴', 'Critical': '🔴'}
            st.write(f"{priority_colors.get(ticket['priority'], '⚪')} {ticket['priority']}")
        with col5:
            st.write(ticket['status'])
        with col6:
            if user_role == 'agent' and ticket['agent_id'] is None:
                if st.button("Take On", key=f"take_on_{ticket['id']}"):
                    update_ticket(ticket_id=ticket['id'], agent_id=current_user['id'])
                    st.rerun()
            elif st.button("View", key=f"view_{ticket['id']}"):
                st.session_state['selected_ticket_id'] = ticket['id']
                st.switch_page("pages/6_Ticket_Details.py")
else:
    st.info("No tickets to display.")
