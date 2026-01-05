import streamlit as st
from db.database import get_tickets, get_user, update_ticket, delete_ticket
from auth_utils import render_sidebar

st.set_page_config(
    page_title="All Tickets",
    page_icon="🎫",
    layout="wide"
)

render_sidebar()

st.title("All Tickets")

if not st.session_state.get('authenticated'):
    st.error("Please log in to access this page.")
    st.page_link("pages/1_Login.py", label="Login")
    st.stop()

current_user = st.session_state['user']
user_role = current_user['role']


# Filter and Sort controls
with st.expander("Filter and Sort", expanded=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        priority_options = ['All', 'Low', 'Medium', 'High', 'Critical']
        filter_priority = st.selectbox("Priority", priority_options)

    with col2:
        status_options = ['All', 'Open', 'In Progress', 'Resolved', 'Closed']
        filter_status = st.selectbox("Status", status_options)

    with col3:
        sort_options = {
            "Recently Updated": "updated_at DESC",
            "Newest First": "created_at DESC",
            "Oldest First": "created_at ASC"
        }
        selected_sort = st.selectbox("Sort by", list(sort_options.keys()))
        order_by = sort_options[selected_sort]


# Build filters
filters = {}
if filter_priority != 'All':
    filters['priority'] = filter_priority
if filter_status != 'All':
    filters['status'] = filter_status

all_tickets = []
if user_role == 'customer':
    all_tickets = get_tickets(customer_id=current_user['id'], filters=filters, order_by=order_by)
elif user_role == 'agent':
    all_tickets = get_tickets(agent_id=current_user['id'], include_unassigned=True, filters=filters, order_by=order_by)
elif user_role == 'admin':
    all_tickets = get_tickets(filters=filters, order_by=order_by)

st.markdown("---")

if all_tickets:
    # Display headers
    col1_h, col2_h, col3_h, col4_h, col5_h, col6_h = st.columns([1, 2, 3, 1, 1, 2])
    with col1_h:
        st.markdown("##### ID")
    with col2_h:
        st.markdown("##### Customer")
    with col3_h:
        st.markdown("##### Title")
    with col4_h:
        st.markdown("##### Priority")
    with col5_h:
        st.markdown("##### Status")
    with col6_h:
        st.markdown("##### Action")
    st.markdown("---")

    for ticket in all_tickets:
        col1, col2, col3, col4, col5, col6 = st.columns([1, 2, 3, 1, 1, 2])
        
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
                    update_ticket(ticket_id=ticket['id'], user_id_for_log=current_user['id'], agent_id=current_user['id'])
                    st.rerun()
            else:
                col_view, col_delete = st.columns(2)
                with col_view:
                    if st.button("View", key=f"view_{ticket['id']}"):
                        st.session_state['selected_ticket_id'] = ticket['id']
                        st.switch_page("pages/6_Ticket_Details.py")
                with col_delete:
                    if st.button("Delete", key=f"delete_{ticket['id']}"):
                        delete_ticket(ticket_id=ticket['id'], user_id_for_log=current_user['id'])
                        st.rerun()
else:
    st.info("No tickets to display. Try adjusting the filters.")
