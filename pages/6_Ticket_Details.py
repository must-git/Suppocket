import streamlit as st
from db.tickets import update_ticket, get_ticket_by_id
from db.users import get_user, get_all_agents
from db.categories_priorities import get_priorities
from datetime import datetime
from auth_utils import render_sidebar

st.set_page_config(
    page_title="Ticket Details",
    page_icon="🎫",
    layout="wide"
)
render_sidebar()

st.title("Ticket Details")

if not st.session_state.get('authenticated'):
    st.error("Please log in to access this page.")
    st.page_link("pages/1_Login.py", label="Login")
    st.stop()

ticket_id = st.session_state.get('selected_ticket_id')

if not ticket_id:
    st.error("No ticket selected. Please go to the Tickets list to select a ticket.")
    st.page_link("pages/4_Tickets.py", label="Go to Tickets list", icon="📋")
    st.stop()

ticket = get_ticket_by_id(ticket_id)

if not ticket:
    st.error(f"Ticket with ID '{ticket_id}' not found.")
    st.page_link("pages/4_Tickets.py", label="Go to Tickets list", icon="📋")
    st.stop()

st.subheader(f"Ticket #{ticket['id']} - {ticket['title']}")

col1, col2, col3 = st.columns(3)
with col1:
    customer_info = get_user(user_id=ticket['customer_id'])
    st.markdown(f"**Customer:** {customer_info['username'] if customer_info else 'Unknown'}")
    if st.markdown(f"**Status:** {ticket['status']}") and ticket['status'] in ['Resolved', 'Closed']:
        st.markdown(f"**Resolved At:** {ticket['resolved_at']}")
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
        priority = st.selectbox("Priority", [priorities_df['name'] for _, priorities_df in get_priorities().iterrows()])
        
        if st.session_state['user']['role'] == 'admin':
            agents = get_all_agents()
            # Correctly iterate over DataFrame rows to create options
            agent_options = {row['username']: row['id'] for index, row in agents.iterrows()}
            
            current_assigned_agent = get_user(user_id=ticket['agent_id'])
            current_assigned_username = current_assigned_agent['username'] if current_assigned_agent else "Unassigned"

            # Create a list of usernames for the selectbox
            agent_usernames = ["Unassigned"] + list(agent_options.keys())
            
            # Find the index of the currently assigned agent
            try:
                current_agent_index = agent_usernames.index(current_assigned_username)
            except ValueError:
                current_agent_index = 0 # Default to "Unassigned" if agent not in list

            selected_agent_username = st.selectbox("Assign To", agent_usernames, index=current_agent_index)
            new_assigned_to = agent_options.get(selected_agent_username)
        else:
            # For agents, don't show the assignment dropdown, just keep the value
            new_assigned_to = ticket['agent_id']

        update_submitted = st.form_submit_button("Update Ticket")

        if update_submitted:
            if update_ticket(ticket_id=ticket['id'], user_id_for_log=st.session_state['user']['id'], status=new_status, agent_id=new_assigned_to, priority=priority):
                st.success("Ticket updated successfully!")
                # Re-fetch ticket data to show updated info
                ticket = get_ticket_by_id(ticket_id) 
            else:
                st.error("Failed to update ticket. Please try again.")
