import streamlit as st
import data
from datetime import datetime

st.set_page_config(
    page_title="Ticket Details",
    page_icon="🎫",
    layout="wide"
)

st.title("Ticket Details")

# Authentication check
if 'authenticated' not in st.session_state or not st.session_state['authenticated']:
    st.error("Please log in to access this page.")
    st.page_link("pages/1_Login.py", label="Login")
    st.stop()

# Get ticket ID from session state
ticket_id = st.session_state.get('selected_ticket_id')

if not ticket_id:
    st.error("No ticket selected. Please go to the Dashboard to select a ticket.")
    st.page_link("pages/3_Dashboard.py", label="Go to Dashboard", icon="📊")
    st.stop()

ticket = data.get_ticket_by_id(ticket_id)

if not ticket:
    st.error(f"Ticket with ID '{ticket_id}' not found.")
    st.page_link("pages/3_Dashboard.py", label="Go to Dashboard", icon="📊")
    st.stop()

st.subheader(f"Ticket: {ticket['id']} - {ticket['title']}")

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f"**Customer:** {data.get_user_by_id(ticket['customerId'])['name']}")
    st.markdown(f"**Status:** {ticket['status']}")
    st.markdown(f"**Priority:** {ticket['priority']}")
with col2:
    st.markdown(f"**Category:** {ticket['category']}")
    st.markdown(f"**Created At:** {ticket['createdAt']}")
    st.markdown(f"**Updated At:** {ticket['updatedAt']}")
with col3:
    assigned_agent = data.get_user_by_id(ticket['assignedTo'])
    st.markdown(f"**Assigned To:** {assigned_agent['name'] if assigned_agent else 'Unassigned'}")

st.markdown("---")
st.subheader("Description")
st.write(ticket['description'])

st.markdown("---")
st.subheader("Comments")

if ticket['comments']:
    for comment in ticket['comments']:
        commenter = data.get_user_by_id(comment['userId'])
        st.info(f"**{commenter['name']}** on {comment['createdAt']}: {comment['comment']}")
else:
    st.info("No comments yet.")

st.markdown("---")
st.subheader("Add a Comment")
new_comment_text = st.text_area("Your Comment")
if st.button("Post Comment"):
    if new_comment_text:
        ticket['comments'].append({
            'userId': st.session_state['user']['id'],
            'comment': new_comment_text,
            'createdAt': datetime.now().isoformat() + "Z"
        })
        st.success("Comment added!")
        st.rerun()
    else:
        st.error("Comment cannot be empty.")

# Status and Assignment Update for Agents/Admins
if st.session_state['user']['role'] in ['Support Agent', 'Admin']:
    st.markdown("---")
    st.subheader("Update Ticket")

    with st.form("update_ticket_form"):
        new_status = st.selectbox("Update Status", ['Open', 'In Progress', 'Resolved', 'Closed'], index=['Open', 'In Progress', 'Resolved', 'Closed'].index(ticket['status']))
        
        agent_options = {u['name']: u['id'] for u in data.mock_users if u['role'] in ['Support Agent', 'Admin']}
        current_assigned_name = data.get_user_by_id(ticket['assignedTo'])['name'] if ticket['assignedTo'] else "Unassigned"
        
        selected_agent_name = st.selectbox("Assign To", ["Unassigned"] + list(agent_options.keys()), index=(["Unassigned"] + list(agent_options.keys())).index(current_assigned_name))
        new_assigned_to = agent_options.get(selected_agent_name) # Will be None if "Unassigned" is selected

        update_submitted = st.form_submit_button("Update Ticket")

        if update_submitted:
            ticket['status'] = new_status
            ticket['assignedTo'] = new_assigned_to
            ticket['updatedAt'] = datetime.now().isoformat() + "Z"
            st.success("Ticket updated successfully!")
            st.rerun()

