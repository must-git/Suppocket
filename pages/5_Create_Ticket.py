import streamlit as st
from db.database import create_ticket, get_user, get_all_customers
from auth_utils import render_sidebar

st.set_page_config(
    page_title="Create Ticket",
    page_icon="📝"
)

render_sidebar()

st.title("Create New Ticket")

# Authentication check
if not st.session_state.get('authenticated'):
    st.error("Please log in to access this page.")
    st.page_link("pages/1_Login.py", label="Login")
    st.stop()

current_user = st.session_state['user']

customer_id_for_ticket = None
if current_user['role'] == 'customer':
    customer_id_for_ticket = current_user['id']
else:
    st.subheader("Creating ticket (for an existing customer)")
    customers = get_all_customers()
    customer_options = {customer['username']: customer['id'] for customer in customers}
    
    selected_customer_username = st.selectbox("Select Customer for Ticket", list(customer_options.keys()))
    customer_id_for_ticket = customer_options.get(selected_customer_username)


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
        elif customer_id_for_ticket is None:
            st.error("Please select a customer for the ticket.")
        else:
            ticket_id = create_ticket(
                customer_id=customer_id_for_ticket,
                title=title,
                description=description,
                priority=priority,
                category=category
            )
            if ticket_id:
                st.success(f"Ticket '{ticket_id}' created successfully!")
                st.markdown(f"You can view it on the [Dashboard](/Dashboard).")
                # st.rerun()
            else:
                st.error("Failed to create ticket. Please try again.")
