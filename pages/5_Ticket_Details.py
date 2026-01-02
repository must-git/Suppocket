import streamlit as st
from db.database import get_ticket_by_id, get_user, update_ticket, get_all_customers
from datetime import datetime

st.set_page_config(
    page_title="Ticket Details",
    page_icon="🎫",
    layout="wide"
)

st.title("Ticket Details")

if not st.session_state.get('authenticated'):
    st.error("Please log in to access this page.")
    st.page_link("pages/1_Login.py", label="Login")
    st.stop()

ticket_id = st.session_state.get('selected_ticket_id')

if not ticket_id:
    st.error("No ticket selected. Please go to the Dashboard to select a ticket.")
    st.page_link("pages/3_Dashboard.py", label="Go to Dashboard", icon="📊")
    st.stop()

ticket = get_ticket_by_id(ticket_id)

if not ticket:
    st.error(f"Ticket with ID '{ticket_id}' not found.")
    st.page_link("pages/3_Dashboard.py", label="Go to Dashboard", icon="📊")
    st.stop()

st.subheader(f"Ticket #{ticket['id']} - {ticket['title']}")

col1, col2, col3 = st.columns(3)
with col1:
    customer_info = get_user(user_id=ticket['customer_id'])
    st.markdown(f"**Customer:** {customer_info['username'] if customer_info else 'Unknown'}")
    st.markdown(f"**Status:** {ticket['status']}")
    st.markdown(f"**Priority:** {ticket['priority']}")
with col2:
    st.markdown(f"**Category:** {ticket['category']}")
    st.markdown(f"**Created At:** {ticket['created_at']}")
    st.markdown(f"**Updated At:** {ticket['updated_at']}")
with col3:
    assigned_agent_info = get_user(user_id=ticket['agent_id'])
    st.markdown(f"**Assigned To:** {assigned_agent_info['username'] if assigned_agent_info else 'Unassigned'}")

st.markdown("---")
st.subheader("Description")
st.write(ticket['description'])

# Removed comment functionality for now

if st.session_state['user']['role'] in ['agent', 'admin']:
    st.markdown("---")
    st.subheader("Update Ticket")

    with st.form("update_ticket_form"):
        new_status = st.selectbox("Update Status", ['Open', 'In Progress', 'Resolved', 'Closed'], index=['Open', 'In Progress', 'Resolved', 'Closed'].index(ticket['status']))
        
        agents = [u for u in get_all_customers() if u['role'] in ['agent', 'admin']] # Get all potential agents
        agent_options = {u['username']: u['id'] for u in agents}
        
        current_assigned_username = get_user(user_id=ticket['agent_id'])['username'] if ticket['agent_id'] else "Unassigned"
        
        selected_agent_username = st.selectbox("Assign To", ["Unassigned"] + list(agent_options.keys()), index=(["Unassigned"] + list(agent_options.keys())).index(current_assigned_username))
        new_assigned_to = agent_options.get(selected_agent_username) # Will be None if "Unassigned" is selected

        update_submitted = st.form_submit_button("Update Ticket")

        if update_submitted:
            if update_ticket(ticket['id'], status=new_status, agent_id=new_assigned_to):
                st.success("Ticket updated successfully!")
                st.rerun()
            else:
                st.error("Failed to update ticket. Please try again.")
