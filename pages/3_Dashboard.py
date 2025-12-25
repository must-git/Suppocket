import streamlit as st
import pandas as pd
import data

st.set_page_config(
    page_title="Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("Ticket Dashboard")

# Authentication check
if 'authenticated' not in st.session_state or not st.session_state['authenticated']:
    st.error("Please log in to access this page.")
    st.page_link("pages/1_Login.py", label="Login")
    st.stop()

tickets_df = pd.DataFrame(data.mock_tickets)

# Add customer name to DataFrame for better display
customer_names = {user['id']: user['name'] for user in data.mock_users if user['role'] == 'Customer'}
tickets_df['customerName'] = tickets_df['customerId'].map(customer_names)

# Filter tickets based on user role
if st.session_state['user']['role'] == 'Customer':
    tickets_df = tickets_df[tickets_df['customerId'] == st.session_state['user']['id']]
elif st.session_state['user']['role'] == 'Support Agent':
    # Agents see tickets assigned to them or unassigned
    tickets_df = tickets_df[(tickets_df['assignedTo'] == st.session_state['user']['id']) | (tickets_df['assignedTo'].isnull())]

st.subheader("Your Tickets")

if not tickets_df.empty:
    # Prepare DataFrame for display
    display_df = tickets_df[['id', 'customerName', 'title', 'priority', 'category', 'status', 'createdAt']]
    display_df.columns = ['Ticket ID', 'Customer Name', 'Title', 'Priority', 'Category', 'Status', 'Created At']

    st.dataframe(
        display_df,
        key="dashboard_tickets_df", # Add a key to the dataframe
        use_container_width=True,
        hide_row_index=True,
        selection_mode="single-row"
    )

    selected_rows = st.session_state.dashboard_tickets_df.get('selection', {}).get('rows', [])
    if selected_rows:
        selected_row_index = selected_rows[0]
        selected_ticket_id = display_df.iloc[selected_row_index]['Ticket ID']
        st.info(f"Selected Ticket ID: {selected_ticket_id}")
        if st.button(f"View Details for {selected_ticket_id}"):
            st.session_state['selected_ticket_id'] = selected_ticket_id # Store in session state
            st.switch_page("pages/5_Ticket_Details.py")

else:
    st.info("No tickets to display.")
