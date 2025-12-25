import streamlit as st
import data
from datetime import datetime

st.set_page_config(
    page_title="Create Ticket",
    page_icon="📝"
)

st.title("Create New Ticket")

# Authentication check
if 'authenticated' not in st.session_state or not st.session_state['authenticated']:
    st.error("Please log in to access this page.")
    st.page_link("pages/1_Login.py", label="Login")
    st.stop()

# Only customers can create tickets, or agents/admins on behalf of a customer
# For simplicity, let's assume currently logged-in user is the customer for now.
# Future: A dropdown to select customer for agents/admins.
current_user = st.session_state['user']

if current_user['role'] == 'Customer':
    st.subheader(f"Creating ticket as: {current_user['name']} (Customer ID: {current_user['id']})")
    customer_id_for_ticket = current_user['id']
else:
    st.subheader("Creating ticket (for an existing customer)")
    customer_emails = [u['email'] for u in data.mock_users if u['role'] == 'Customer']
    selected_customer_email = st.selectbox("Select Customer for Ticket", customer_emails)
    customer_id_for_ticket = data.get_user_by_email(selected_customer_email)['id']


with st.form("create_ticket_form"):
    title = st.text_input("Ticket Title")
    description = st.text_area("Description")
    
    priority_options = ['Low', 'Medium', 'High', 'Critical']
    priority = st.selectbox("Priority", priority_options)

    category_options = ['Technical Issue', 'Billing Issue', 'Feature Request', 'General Inquiry']
    category = st.selectbox("Category", category_options)

    submitted = st.form_submit_button("Submit Ticket")

    if submitted:
        if not title or not description:
            st.error("Title and Description cannot be empty.")
        else:
            new_ticket = data.add_ticket(
                customer_id=customer_id_for_ticket,
                title=title,
                description=description,
                priority=priority,
                category=category
            )
            st.success(f"Ticket '{new_ticket['id']}' created successfully!")
            st.markdown(f"You can view it on the [Dashboard](/Dashboard).")
            # Optionally, clear form fields after submission
            st.rerun() # Rerun to clear form values and potentially show updated dashboard link
