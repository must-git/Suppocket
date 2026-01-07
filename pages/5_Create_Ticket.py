import streamlit as st
from db.tickets import create_ticket
from db.users import get_user, get_all_customers
from db.categories_priorities import get_categories, get_priorities, add_category
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
    priority = None
    
    if current_user['role'] in ['admin', 'agent']:
        # Dynamically fetch priorities
        priorities_df = get_priorities()
        priority_names = priorities_df['name'].tolist()
        priority = st.selectbox("Priority", priority_names)

    # Dynamically fetch categories and add "Add New..." option
    categories_df = get_categories(include_archived=False)
    category_names = categories_df['name'].tolist()
    category_options_for_select = ['Add New...'] + category_names
    selected_category_option = st.selectbox("Category", category_options_for_select)

    new_category_name = None
    if selected_category_option == 'Add New...':
        new_category_name = st.text_input("New Category Name", help="Enter a new category name. It will be created if it doesn't exist.")
        category_to_use = new_category_name
    else:
        category_to_use = selected_category_option

    submitted = st.form_submit_button("Submit Ticket")

    if submitted:
        if not title or not description:
            st.error("Title and Description cannot be empty.")
        elif customer_id_for_ticket is None:
            st.error("Please select a customer for the ticket.")
        elif not category_to_use:
            st.error("Please select a category or provide a new one.")
        else:
            final_category_name = category_to_use

            # Handle new category creation if applicable
            if selected_category_option == 'Add New...' and new_category_name:
                if new_category_name not in category_names:
                    # Try to add the new category with default description and color
                    # For simplicity, using a generic description and color here. Admin can refine later.
                    added_cat_id = add_category(new_category_name, "User-created category", "#CCCCCC")
                    if added_cat_id:
                        st.success(f"New category '{new_category_name}' created.")
                        final_category_name = new_category_name
                    else:
                        st.error(f"Failed to create new category '{new_category_name}'. It might already exist.")
                        st.stop() # Stop execution if category creation fails

            ticket_id = create_ticket(
                customer_id=customer_id_for_ticket,
                title=title,
                description=description,
                priority_name=priority, # Pass priority name
                category_name=final_category_name # Pass category name
            )
            if ticket_id:
                st.success(f"Ticket '{ticket_id}' created successfully!")
            else:
                st.error("Failed to create ticket. Please check category/priority names or other details.")
