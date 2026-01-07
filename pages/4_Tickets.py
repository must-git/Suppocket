import streamlit as st
from db.database import get_tickets, get_user, update_ticket, delete_ticket
from auth_utils import render_sidebar
from sla_utils import get_business_hours_settings
import datetime
import pytz

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

if user_role in ['agent', 'admin']:
    sla_settings = get_business_hours_settings()
    mode_display = "Business Hours" if sla_settings.get('mode') == 'business_hours' else "Calendar Hours (24/7)"
    st.info(f"SLA Calculation Mode: **{mode_display}** (Timezone: {sla_settings.get('timezone')})")

st.markdown("---")

if all_tickets:
    # Helper function for SLA status
    def display_sla_status(status):
        colors = {
            'Breached': '🔴',
            'On Track': '🟢',
            'Pending': '🟡',
            'Met': '🟢',
            'N/A': '⚪'
        }
        return f"{colors.get(status, '⚪')} {status}"

    # Define columns based on user role
    if user_role in ['agent', 'admin']:
        # Wider layout for agents/admins with SLA info
        header_cols = st.columns([1, 2, 3, 1.5, 1, 1.5, 1.5, 2])
        column_weights = [1, 2, 3, 1.5, 1, 1.5, 1.5, 2]
        column_headers = ["ID", "Customer", "Title", "Priority", "Status", "Response SLA", "Resolution SLA", "Action"]
    else: # Customer view
        header_cols = st.columns([1, 2, 3, 1, 1, 2])
        column_weights = [1, 2, 3, 1, 1, 2]
        column_headers = ["ID", "Customer", "Title", "Priority", "Status", "Action"]

    for col, header in zip(header_cols, column_headers):
        with col:
            st.markdown(f"##### {header}")
    st.markdown("---")

    for ticket in all_tickets:
        cols = st.columns(column_weights)
        
        customer_info = get_user(user_id=ticket['customer_id'])
        customer_name = customer_info['username'] if customer_info else "Unknown"

        # --- Common columns for all roles ---
        cols[0].write(f"**#{ticket['id']}**")
        cols[1].write(customer_name)
        cols[2].write(ticket['title'])
        
        priority_colors = {'Low': '🟢', 'Medium': '🟡', 'High': '🔴', 'Critical': '🔴'}
        cols[3].write(f"{priority_colors.get(ticket['priority'], '⚪')} {ticket['priority']}")
        cols[4].write(ticket['status'])

        # --- Role-specific columns ---
        if user_role in ['agent', 'admin']:
            with cols[5]:
                st.write(display_sla_status(ticket.get('response_status', 'N/A')))
                if ticket.get('response_due'):
                    due_date_utc = datetime.datetime.fromisoformat(ticket['response_due'])
                    due_date_local = due_date_utc.astimezone(sla_settings['timezone'])
                    st.caption(f"Due: {due_date_local.strftime('%b %d, %H:%M')}")
            
            with cols[6]:
                st.write(display_sla_status(ticket.get('resolution_status', 'N/A')))
                if ticket.get('resolution_due'):
                    due_date_utc = datetime.datetime.fromisoformat(ticket['resolution_due'])
                    due_date_local = due_date_utc.astimezone(sla_settings['timezone'])
                    st.caption(f"Due: {due_date_local.strftime('%b %d, %H:%M')}")

            action_col = cols[7]
        else: # Customer
            action_col = cols[5]

        # --- Action buttons ---
        with action_col:
            # "Take On" button for unassigned tickets for agents
            if user_role == 'agent' and ticket['agent_id'] is None:
                if st.button("Take On", key=f"take_on_{ticket['id']}", use_container_width=True):
                    update_ticket(ticket_id=ticket['id'], user_id_for_log=current_user['id'], agent_id=current_user['id'])
                    st.rerun()
            else:
                # "View" and "Delete" buttons
                action_button_cols = st.columns(2)
                with action_button_cols[0]:
                    if st.button("View", key=f"view_{ticket['id']}", use_container_width=True):
                        st.session_state['selected_ticket_id'] = ticket['id']
                        st.switch_page("pages/6_Ticket_Details.py")
                
                # Only admins can delete
                if user_role == 'admin':
                    with action_button_cols[1]:
                        if st.button("Delete", key=f"delete_{ticket['id']}", use_container_width=True):
                            if delete_ticket(ticket_id=ticket['id'], user_id_for_log=current_user['id']):
                                st.success(f"Ticket #{ticket['id']} deleted.")
                                st.rerun()
                            else:
                                st.error("Failed to delete ticket.")
else:
    st.info("No tickets to display. Try adjusting the filters.")
