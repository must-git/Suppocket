import streamlit as st
import pandas as pd
import re # For email validation
import pytz # For timezone selection

from auth_utils import render_sidebar
from db.database import (
    get_all_users, create_user, get_user, update_user_admin, delete_user,
    get_tickets_for_reassignment, reassign_ticket, get_all_agents, get_tickets,
    get_categories, add_category, update_category, archive_category,
    get_priorities, update_priority, get_sla_settings, update_sla_settings,
    get_ticket_counts_by_category, get_system_settings, update_system_setting,
    get_distinct_activity_users, get_distinct_action_types, get_activity_logs
)

st.set_page_config(
    page_title="Admin Panel",
    page_icon="👑",
    layout="wide"
)

render_sidebar()

st.title("Admin Panel")

# --- Authentication Check ---
if not st.session_state.get('authenticated') or st.session_state.get('user', {}).get('role') != 'admin':
    st.error("Access Denied: You must be an administrator to view this page.")
    if st.button("Go to Login"):
        st.switch_page("pages/1_Login.py")
    st.stop()

# --- Constants ---
ROLES = ['admin', 'agent', 'customer']
USER_STATUSES = ['active', 'inactive']
PASSWORD_MIN_LENGTH = 8

# --- Helper Functions ---
def is_valid_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

def display_user_management_tab():
    st.header("User Management")

    # --- Add New User Section ---
    with st.expander("➕ Add New User"):
        with st.form("add_user_form", clear_on_submit=True):
            st.subheader("New User Details")
            new_username = st.text_input("Username", key="new_username_input")
            new_email = st.text_input("Email", key="new_email_input")
            new_password = st.text_input("Password", type="password", key="new_password_input")
            new_role = st.selectbox("Role", ROLES, key="new_role_select")
            new_status = st.selectbox("Status", USER_STATUSES, key="new_status_select")

            add_user_submitted = st.form_submit_button("Add User")

            if add_user_submitted:
                if not new_username or not new_email or not new_password:
                    st.error("All fields are required.")
                elif not is_valid_email(new_email):
                    st.error("Invalid email format.")
                elif len(new_password) < PASSWORD_MIN_LENGTH:
                    st.error(f"Password must be at least {PASSWORD_MIN_LENGTH} characters long.")
                else:
                    user_id = create_user(new_username, new_email, new_password, new_role, new_status)
                    if user_id:
                        st.success(f"User '{new_username}' added successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to add user. Username or Email might already exist.")

    st.markdown("---")

    # --- Existing Users Display and Actions ---
    st.subheader("Existing Users")

    users_df = get_all_users()

    if users_df.empty:
        st.info("No users found in the system.")
    else:
        # Search and Filter
        col_search, col_role_filter, col_status_filter = st.columns([3, 1, 1])
        with col_search:
            search_query = st.text_input("Search by Username or Email", "")
        with col_role_filter:
            filter_role = st.selectbox("Filter by Role", ['All'] + ROLES)
        with col_status_filter:
            filter_status = st.selectbox("Filter by Status", ['All'] + USER_STATUSES)

        filtered_users_df = users_df.copy()

        # Apply search filter
        if search_query:
            filtered_users_df = filtered_users_df[
                filtered_users_df['username'].str.contains(search_query, case=False, na=False) |
                filtered_users_df['email'].str.contains(search_query, case=False, na=False)
            ]

        # Apply role filter
        if filter_role != 'All':
            filtered_users_df = filtered_users_df[filtered_users_df['role'] == filter_role]

        # Apply status filter
        if filter_status != 'All':
            filtered_users_df = filtered_users_df[filtered_users_df['status'] == filter_status]

        st.dataframe(filtered_users_df[['id', 'username', 'email', 'role', 'status', 'created_at']], use_container_width=True)

        st.markdown("##### User Actions")
        # --- User Actions: Edit, Activate/Deactivate, Delete ---
        for index, user in filtered_users_df.iterrows():
            user_id = user['id']
            current_status = user['status']
            
            with st.expander(f"⚙️ Actions for {user['username']} (ID: {user_id})"):
                # --- Edit User ---
                st.subheader("Edit User Details")
                with st.form(f"edit_user_form_{user_id}"):
                    edited_username = st.text_input("Username", value=user['username'], key=f"edit_username_{user_id}")
                    edited_email = st.text_input("Email", value=user['email'], key=f"edit_email_{user_id}")
                    edited_role = st.selectbox("Role", ROLES, index=ROLES.index(user['role']), key=f"edit_role_{user_id}")
                    edited_status = st.selectbox("Status", USER_STATUSES, index=USER_STATUSES.index(user['status']), key=f"edit_status_{user_id}")
                    
                    edit_submitted = st.form_submit_button("Update User")

                    if edit_submitted:
                        if not edited_username or not edited_email:
                            st.error("Username and Email cannot be empty.")
                        elif not is_valid_email(edited_email):
                            st.error("Invalid email format.")
                        else:
                            # Check for uniqueness, excluding the current user
                            existing_user_by_username = get_user(username=edited_username)
                            existing_user_by_email = get_user(email=edited_email)

                            if existing_user_by_username and existing_user_by_username['id'] != user_id:
                                st.error("This username is already taken by another user.")
                            elif existing_user_by_email and existing_user_by_email['id'] != user_id:
                                st.error("This email is already taken by another user.")
                            else:
                                if update_user_admin(user_id, edited_username, edited_email, edited_role, edited_status):
                                    st.success(f"User {edited_username} updated successfully!")
                                    st.rerun()
                                else:
                                    st.error("Failed to update user. Please try again.")

                st.markdown("---")

                # --- Activate/Deactivate Toggle ---
                new_toggle_status = 'inactive' if current_status == 'active' else 'active'
                if st.button(f"Toggle Status to '{new_toggle_status.capitalize()}'", key=f"toggle_status_{user_id}"):
                    if update_user_admin(user_id, user['username'], user['email'], user['role'], new_toggle_status):
                        st.success(f"User {user['username']} status changed to '{new_toggle_status}'.")
                        st.rerun()
                    else:
                        st.error("Failed to change user status.")

                st.markdown("---")

                # --- Delete User ---
                st.subheader("Delete User")
                st.warning(f"Deleting {user['username']} (ID: {user_id}) is irreversible.")
                if st.button("Confirm Delete User", key=f"delete_user_{user_id}"):
                    delete_result = delete_user(user_id)
                    if delete_result is True:
                        st.success(f"User {user['username']} deleted successfully.")
                        st.rerun()
                    elif delete_result == "has_tickets":
                        st.error(f"Cannot delete user {user['username']}. They have associated tickets.")
                    else:
                        st.error(f"Failed to delete user {user['username']}.")

    st.markdown("---")

    # --- Agent Workload and Reassignment (To be implemented) ---
    # --- Agent Workload and Reassignment ---
    st.subheader("Agent Workload & Ticket Reassignment")

    # Fetch all tickets to determine agent workload
    all_active_tickets = get_tickets(filters={'status': 'Open'}) # Get open tickets
    
    if all_active_tickets:
        tickets_df = pd.DataFrame(all_active_tickets)
        agent_workload = tickets_df['agent_name'].value_counts().reset_index()
        agent_workload.columns = ['Agent', 'Assigned Tickets']

        # Get all agents to include those with 0 tickets
        all_agents_df = get_all_agents()
        all_agent_names = all_agents_df['username'].tolist()

        # Merge to ensure all agents are in the workload, filling 0 for unassigned
        full_workload_df = pd.DataFrame({'Agent': all_agent_names}).merge(
            agent_workload, on='Agent', how='left'
        ).fillna(0)
        full_workload_df['Assigned Tickets'] = full_workload_df['Assigned Tickets'].astype(int)

        st.markdown("##### Current Agent Workload")
        fig = st.bar_chart(full_workload_df.set_index('Agent'))
        
    else:
        st.info("No active tickets to display agent workload.")

    st.markdown("---")
    st.subheader("Reassign Tickets")

    tickets_for_reassignment = get_tickets_for_reassignment() # Tickets not resolved/closed
    all_agents = get_all_agents()

    if tickets_for_reassignment.empty:
        st.info("No tickets currently available for reassignment.")
    elif all_agents.empty:
        st.warning("No agents found to reassign tickets to.")
    else:
        # Prepare options for selectboxes
        ticket_options = {f"#{ticket['id']} - {ticket['title']} (Assigned to: {ticket['agent_name'] or 'Unassigned'})": ticket['id'] for index, ticket in tickets_for_reassignment.iterrows()}
        agent_options = {agent['username']: agent['id'] for index, agent in all_agents.iterrows()}
        agent_options["Unassign"] = None # Option to unassign a ticket

        with st.form("reassign_ticket_form"):
            selected_ticket_display = st.selectbox("Select Ticket to Reassign", list(ticket_options.keys()))
            selected_new_agent_name = st.selectbox("Assign To", list(agent_options.keys()))

            reassign_submitted = st.form_submit_button("Reassign Ticket")

            if reassign_submitted:
                ticket_id_to_reassign = ticket_options[selected_ticket_display]
                new_agent_id = agent_options[selected_new_agent_name]
                
                # Admin ID for logging activity
                admin_id = st.session_state['user']['id']

                if reassign_ticket(ticket_id_to_reassign, new_agent_id, admin_id):
                    st.success(f"Ticket #{ticket_id_to_reassign} reassigned successfully to {selected_new_agent_name or 'Unassigned'}.")
                    st.rerun()
                else:
                    st.error("Failed to reassign ticket. Please try again.")

    st.info("This section is under construction.")

# --- Category & Priority Management Tab Function ---
def display_category_priority_management_tab():
    st.header("Category Management")

    # --- Add New Category Form ---
    with st.expander("➕ Add New Category"):
        with st.form("add_category_form", clear_on_submit=True):
            new_cat_name = st.text_input("Category Name")
            new_cat_description = st.text_area("Description")
            new_cat_color = st.color_picker("Color", "#000000") # Default to black
            
            add_cat_submitted = st.form_submit_button("Add Category")

            if add_cat_submitted:
                if not new_cat_name:
                    st.error("Category Name cannot be empty.")
                else:
                    cat_id = add_category(new_cat_name, new_cat_description, new_cat_color)
                    if cat_id:
                        st.success(f"Category '{new_cat_name}' added successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to add category. Name might already exist.")

    st.markdown("---")

    # --- Display Categories ---
    st.subheader("Current Categories")
    categories = get_categories(include_archived=True) # Get all categories, including archived
    ticket_counts = get_ticket_counts_by_category() # Get a dictionary of category_name: count

    if categories.empty:
        st.info("No categories defined.")
    else:
        for index, cat in categories.iterrows():
            cat_id = cat['id']
            cat_name = cat['name']
            current_archived_status = cat['archived']
            
            # Count for this category, defaulting to 0 if no tickets
            count_for_cat = ticket_counts.get(cat_name, 0)

            with st.expander(f"📚 {cat_name} (ID: {cat_id}) - Tickets: {count_for_cat} ({'Archived' if current_archived_status else 'Active'})"):
                st.write(f"**Description:** {cat['description']}")
                st.write(f"**Color:** <span style='color:{cat['color']};'>{cat['color']}</span>", unsafe_allow_html=True)

                # --- Edit Category ---
                st.markdown("##### Edit Category Details")
                with st.form(f"edit_category_form_{cat_id}"):
                    edited_cat_name = st.text_input("Name", value=cat_name, key=f"edit_cat_name_{cat_id}")
                    edited_cat_description = st.text_area("Description", value=cat['description'], key=f"edit_cat_desc_{cat_id}")
                    edited_cat_color = st.color_picker("Color", value=cat['color'], key=f"edit_cat_color_{cat_id}")
                    
                    edit_cat_submitted = st.form_submit_button("Update Category")

                    if edit_cat_submitted:
                        if not edited_cat_name:
                            st.error("Category Name cannot be empty.")
                        else:
                            if update_category(cat_id, edited_cat_name, edited_cat_description, edited_cat_color):
                                st.success(f"Category '{edited_cat_name}' updated successfully!")
                                st.rerun()
                            else:
                                st.error("Failed to update category. Name might already exist.")
                
                st.markdown("---")

                # --- Archive/Unarchive Category ---
                if current_archived_status:
                    if st.button(f"Unarchive Category", key=f"unarchive_cat_{cat_id}"):
                        if archive_category(cat_id, archived=False):
                            st.success(f"Category '{cat_name}' unarchived.")
                            st.rerun()
                        else:
                            st.error("Failed to unarchive category.")
                else:
                    st.warning(f"Archiving '{cat_name}' will hide it from new ticket creation forms. Existing tickets will retain their category.")
                    if st.button(f"Archive Category", key=f"archive_cat_{cat_id}"):
                        if count_for_cat > 0:
                            # Optional: Add a confirmation if there are active tickets
                            st.info("Category has associated tickets. Proceeding with archive.")
                        if archive_category(cat_id, archived=True):
                            st.success(f"Category '{cat_name}' archived.")
                            st.rerun()
                        else:
                            st.error("Failed to archive category.")

    st.markdown("---")

    st.header("Priority Management")

    priorities_df = get_priorities() # Has id, name, description, color, sort_order
    sla_df = get_sla_settings()      # Has priority_id, name, sort_order, response_time_hours, resolution_time_hours

    # Merge the two DataFrames
    # Left merge to keep all priorities, even if they don't have SLA settings yet.
    merged_priorities_df = pd.merge(
        priorities_df,
        sla_df,
        left_on='id',
        right_on='priority_id',
        how='left',
        suffixes=('_prio', '_sla')
    )
    
    # Fill NaN values for SLA columns if a priority has no SLA settings yet
    merged_priorities_df['response_time_hours'] = merged_priorities_df['response_time_hours'].fillna(24).astype(int)
    merged_priorities_df['resolution_time_hours'] = merged_priorities_df['resolution_time_hours'].fillna(48).astype(int)


    if merged_priorities_df.empty:
        st.info("No priorities defined.")
    else:
        # Ensure correct sorting
        merged_priorities_df = merged_priorities_df.sort_values(by='sort_order_prio')

        for index, prio in merged_priorities_df.iterrows():
            prio_id = prio['id'] # This should be the original ID from priorities_df
            prio_name = prio['name_prio']
            
            with st.expander(f"⭐ {prio_name} (Order: {prio['sort_order_prio']})"):
                st.write(f"**Description:** {prio['description']}")
                st.write(f"**Color:** <span style='color:{prio['color']};'>{prio['color']}</span>", unsafe_allow_html=True)
                
                st.markdown("##### Edit Priority Details")
                with st.form(f"edit_priority_form_{prio_id}"):
                    edited_prio_description = st.text_area("Description", value=prio['description'], key=f"edit_prio_desc_{prio_id}")
                    edited_prio_color = st.color_picker("Color", value=prio['color'], key=f"edit_prio_color_{prio_id}")
                    
                    edit_prio_submitted = st.form_submit_button("Update Priority")

                    if edit_prio_submitted:
                        if update_priority(prio_id, prio_name, edited_prio_description, edited_prio_color):
                            st.success(f"Priority '{prio_name}' updated successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to update priority.")

                st.markdown("---")
                st.markdown("##### SLA Settings")
                col_sla1, col_sla2 = st.columns(2)
                with col_sla1:
                    st.metric("Response Time (hours)", prio['response_time_hours'])
                with col_sla2:
                    st.metric("Resolution Time (hours)", prio['resolution_time_hours'])

                with st.form(f"edit_sla_form_{prio_id}"):
                    new_response_time = st.number_input(
                        "Response Time (hours)", 
                        min_value=0, 
                        value=prio['response_time_hours'], 
                        key=f"edit_resp_time_{prio_id}"
                    )
                    new_resolution_time = st.number_input(
                        "Resolution Time (hours)", 
                        min_value=0, 
                        value=prio['resolution_time_hours'], 
                        key=f"edit_res_time_{prio_id}"
                    )
                    
                    edit_sla_submitted = st.form_submit_button("Update SLA")

                    if edit_sla_submitted:
                        admin_id = st.session_state['user']['id']
                        if update_sla_settings([(prio_id, new_response_time, new_resolution_time)], admin_id):
                            st.success(f"SLA for '{prio_name}' updated successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to update SLA settings.")

# --- Page Structure ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "👤 User Management",
    "🗂️ Category & Priority Management",
    "⏱️ SLA Configuration",
    "⚙️ System Settings",
    "📜 Activity Logs"
])

with tab1:
    display_user_management_tab()

with tab2:
    display_category_priority_management_tab()

# --- SLA Configuration Tab Function ---
def display_sla_configuration_tab():
    st.header("SLA Settings by Priority")
    # Fetch priorities with their current SLA settings
    merged_priorities_df = pd.merge(
        get_priorities(), # Has id, name, description, color, sort_order
        get_sla_settings(), # Has priority_id, name, sort_order, response_time_hours, resolution_time_hours
        left_on='id',
        right_on='priority_id',
        how='left',
        suffixes=('_prio', '_sla')
    )
    # Fill NaN values for SLA columns if a priority has no SLA settings yet
    merged_priorities_df['response_time_hours'] = merged_priorities_df['response_time_hours'].fillna(24).astype(int)
    merged_priorities_df['resolution_time_hours'] = merged_priorities_df['resolution_time_hours'].fillna(48).astype(int)

    if merged_priorities_df.empty:
        st.info("No priorities defined to configure SLA.")
    else:
        st.write("Configure default response and resolution times for each priority level.")
        with st.form("priority_sla_form"):
            updated_sla_settings = []
            for index, prio in merged_priorities_df.iterrows():
                prio_id = prio['id']
                prio_name = prio['name_prio']
                
                st.subheader(f"Priority: {prio_name}")
                col1, col2 = st.columns(2)
                with col1:
                    response_time = st.number_input(
                        f"Response Time (hours) for {prio_name}",
                        min_value=0,
                        value=prio['response_time_hours'],
                        key=f"prio_resp_time_{prio_id}"
                    )
                with col2:
                    resolution_time = st.number_input(
                        f"Resolution Time (hours) for {prio_name}",
                        min_value=0,
                        value=prio['resolution_time_hours'],
                        key=f"prio_res_time_{prio_id}"
                    )
                updated_sla_settings.append((prio_id, response_time, resolution_time))
            
            sla_submitted = st.form_submit_button("Save Priority SLA Settings")

            if sla_submitted:
                admin_id = st.session_state['user']['id']
                if update_sla_settings(updated_sla_settings, admin_id):
                    st.success("Priority-based SLA settings updated successfully!")
                    st.rerun()
                else:
                    st.error("Failed to update priority-based SLA settings.")

    st.markdown("---")
    st.header("SLA Overrides by Category (Under Construction)")
    st.info("This feature will allow setting custom SLA targets for specific categories, overriding priority-based settings.")

    st.markdown("---")
    st.header("Business Hours Configuration")

    # Fetch existing settings
    system_settings = get_system_settings()
    
    # Default values if settings not found
    default_start_time = system_settings.get('working_hour_start', '09:00')
    default_end_time = system_settings.get('working_hour_end', '17:00')
    default_working_days_str = system_settings.get('working_days', 'Mon,Tue,Wed,Thu,Fri')
    default_timezone = system_settings.get('timezone', 'UTC')

    # Convert default times to datetime.time objects for st.time_input
    import datetime
    try:
        default_start_time_obj = datetime.time.fromisoformat(default_start_time)
    except ValueError:
        default_start_time_obj = datetime.time(9, 0) # Fallback
    try:
        default_end_time_obj = datetime.time.fromisoformat(default_end_time)
    except ValueError:
        default_end_time_obj = datetime.time(17, 0) # Fallback

    with st.form("business_hours_form"):
        st.subheader("Set Working Hours and Days")
        
        col_time1, col_time2 = st.columns(2)
        with col_time1:
            working_hour_start = st.time_input("Working Hour Start", value=default_start_time_obj, key="start_time_input")
        with col_time2:
            working_hour_end = st.time_input("Working Hour End", value=default_end_time_obj, key="end_time_input")
        
        st.markdown("##### Working Days")
        all_days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        current_working_days = default_working_days_str.split(',')
        selected_working_days = []
        
        cols = st.columns(7) # 7 columns for 7 days
        for i, day in enumerate(all_days):
            with cols[i]:
                if st.checkbox(day, value=(day in current_working_days), key=f"day_checkbox_{day}"):
                    selected_working_days.append(day)
        
        st.markdown("---")
        st.subheader("Timezone Configuration")
        timezone_list = pytz.all_timezones
        selected_timezone = st.selectbox("Select Timezone", timezone_list, index=timezone_list.index(default_timezone) if default_timezone in timezone_list else timezone_list.index('UTC'))

        business_hours_submitted = st.form_submit_button("Save Business Hours & Timezone")

        if business_hours_submitted:
            admin_id = st.session_state['user']['id']
            # Save working hours
            update_system_setting('working_hour_start', working_hour_start.isoformat(), admin_id)
            update_system_setting('working_hour_end', working_hour_end.isoformat(), admin_id)
            # Save working days
            update_system_setting('working_days', ','.join(selected_working_days), admin_id)
            # Save timezone
            update_system_setting('timezone', selected_timezone, admin_id)

            st.success("Business hours and timezone settings updated successfully!")
            st.rerun()

    st.markdown("---")
    st.header("SLA Compliance Overview (Under Construction)")
    st.info("Display overall SLA compliance rate and identify tickets at risk of breaching SLA.")


with tab3:
    display_sla_configuration_tab()

# --- System Settings Tab Function ---
def display_system_settings_tab():
    st.header("Ticket Settings")

    system_settings = get_system_settings()
    admin_id = st.session_state['user']['id']

    # --- Ticket Settings Form ---
    with st.form("ticket_settings_form"):
        st.subheader("General Ticket Configuration")

        # Ticket ID Prefix
        default_ticket_prefix = system_settings.get('ticket_id_prefix', 'SUP-')
        ticket_id_prefix = st.text_input("Ticket ID Prefix", value=default_ticket_prefix, help="Prefix for new ticket IDs (e.g., 'SUP-').")

        # Auto-close resolved tickets after X days
        default_auto_close_days = int(system_settings.get('auto_close_days', 7))
        auto_close_days = st.number_input(
            "Auto-close Resolved Tickets After (days)",
            min_value=0,
            value=default_auto_close_days,
            help="Resolved tickets will automatically close after this many days if no further action is taken."
        )

        # Required fields when creating tickets
        st.markdown("##### Required Fields for Ticket Creation")
        default_required_fields_str = system_settings.get('required_ticket_fields', 'title,description,category,priority')
        default_required_fields = default_required_fields_str.split(',')

        required_fields_options = ['title', 'description', 'category', 'priority']
        selected_required_fields = []
        cols = st.columns(len(required_fields_options))
        for i, field in enumerate(required_fields_options):
            with cols[i]:
                if st.checkbox(field.capitalize(), value=(field in default_required_fields), key=f"req_field_{field}"):
                    selected_required_fields.append(field)
        
        # Enable file attachments toggle
        default_enable_attachments = system_settings.get('enable_attachments', 'False').lower() == 'true'
        enable_attachments = st.checkbox("Enable File Attachments", value=default_enable_attachments, help="Allow users to attach files to tickets.")

        settings_submitted = st.form_submit_button("Save Ticket Settings")

        if settings_submitted:
            # Update each setting
            update_system_setting('ticket_id_prefix', ticket_id_prefix, admin_id)
            update_system_setting('auto_close_days', str(auto_close_days), admin_id)
            update_system_setting('required_ticket_fields', ','.join(selected_required_fields), admin_id)
            update_system_setting('enable_attachments', str(enable_attachments), admin_id)
            
            st.success("Ticket settings updated successfully!")
            st.rerun()

    st.markdown("---")
    st.header("Notification Settings")

    with st.form("notification_settings_form"):
        st.subheader("Email Notifications")

        # Enable/disable email notifications toggle
        default_email_notifications_enabled = system_settings.get('enable_email_notifications', 'False').lower() == 'true'
        enable_email_notifications = st.checkbox("Enable Email Notifications", value=default_email_notifications_enabled, help="Send email notifications for selected events.")

        st.markdown("##### Notification Events")
        notification_events_options = [
            'New ticket created',
            'Ticket assigned',
            'Ticket status changed',
            'Ticket resolved',
            'SLA breach warning'
        ]
        default_notification_events_str = system_settings.get('notification_events', '')
        default_notification_events = default_notification_events_str.split(',') if default_notification_events_str else []
        
        selected_notification_events = []
        for event_option in notification_events_options:
            if st.checkbox(event_option, value=(event_option in default_notification_events), key=f"notif_event_{event_option.replace(' ', '_')}"):
                selected_notification_events.append(event_option)
        
        notification_settings_submitted = st.form_submit_button("Save Notification Settings")

        if notification_settings_submitted:
            # Update each setting
            update_system_setting('enable_email_notifications', str(enable_email_notifications), admin_id)
            update_system_setting('notification_events', ','.join(selected_notification_events), admin_id)
            
            st.success("Notification settings updated successfully!")
            st.rerun()


    st.markdown("---")
    st.header("Other System Settings (Under Construction)")
    st.info("Further system-wide configurations will be available here.")

with tab4:
    display_system_settings_tab()

# --- Activity Logs Tab Function ---
def display_activity_logs_tab():
    st.header("Activity Logs")

    # Initialize pagination in session state
    if 'activity_log_current_page' not in st.session_state:
        st.session_state['activity_log_current_page'] = 0

    logs_per_page = 50

    # --- Filters ---
    st.subheader("Filters")
    col_date1, col_date2, col_user, col_action = st.columns([2, 2, 2, 2])

    with col_date1:
        start_date = st.date_input("Start Date", value=None, key="log_start_date")
    with col_date2:
        end_date = st.date_input("End Date", value=None, key="log_end_date")

    # Fetch distinct users for filter
    distinct_users = get_distinct_activity_users()
    user_options = {user['username']: user['user_id'] for user in distinct_users}
    user_options_display = ['All'] + sorted(user_options.keys())

    with col_user:
        selected_username = st.selectbox("User", user_options_display, key="log_user_filter")
        filter_user_id = user_options[selected_username] if selected_username != 'All' else None

    # Fetch distinct action types for filter
    distinct_action_types = get_distinct_action_types()
    action_type_options_display = ['All'] + sorted(distinct_action_types)
    with col_action:
        filter_action_type = st.selectbox("Action Type", action_type_options_display, key="log_action_type_filter")
        filter_action_type = filter_action_type if filter_action_type != 'All' else None

    st.markdown("---")

    # --- Fetch and Display Logs ---
    st.subheader("Recent Activity")

    # Convert date objects to string for DB function
    start_date_str = start_date.isoformat() if start_date else None
    end_date_str = end_date.isoformat() if end_date else None

    # Fetch logs for the current page
    offset = st.session_state['activity_log_current_page'] * logs_per_page
    logs_df, total_logs = get_activity_logs(
        start_date=start_date_str,
        end_date=end_date_str,
        user_id=filter_user_id,
        action_type=filter_action_type,
        limit=logs_per_page,
        offset=offset
    )
    
    if logs_df.empty:
        st.info("No activity logs found matching the filters.")
    else:
        st.dataframe(logs_df[['timestamp', 'username', 'action_type', 'resource_type', 'resource_id', 'details']], use_container_width=True)

        # --- Pagination Controls ---
        total_pages = (total_logs + logs_per_page - 1) // logs_per_page
        current_page_display = st.session_state['activity_log_current_page'] + 1

        st.markdown(f"Page {current_page_display} of {total_pages} (Total Logs: {total_logs})")
        col_prev, col_next = st.columns(2)
        with col_prev:
            if st.button("Previous Page", disabled=(st.session_state['activity_log_current_page'] == 0)):
                st.session_state['activity_log_current_page'] -= 1
                st.rerun()
        with col_next:
            if st.button("Next Page", disabled=(st.session_state['activity_log_current_page'] >= total_pages - 1)):
                st.session_state['activity_log_current_page'] += 1
                st.rerun()

        st.markdown("---")
        # --- Export Logs Button (CSV) ---
        st.subheader("Export Logs")
        # Fetch all filtered logs (not just current page) for export
        all_filtered_logs_df, _ = get_activity_logs(
            start_date=start_date_str,
            end_date=end_date_str,
            user_id=filter_user_id,
            action_type=filter_action_type,
            limit=None, # No limit for export
            offset=0
        )

        if not all_filtered_logs_df.empty:
            csv_export = all_filtered_logs_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Export Filtered Logs to CSV",
                data=csv_export,
                file_name="activity_logs.csv",
                mime="text/csv",
            )
        else:
            st.info("No logs to export based on current filters.")

with tab5:
    display_activity_logs_tab()
