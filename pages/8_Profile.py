import streamlit as st
from auth_utils import render_sidebar, verify_password
from db.database import update_user, get_user, update_password_hash

st.set_page_config(
    page_title="Profile",
    page_icon="👤"
)

render_sidebar()

st.title("Your Profile")

if not st.session_state.get('authenticated'):
    st.error("You must be logged in to view this page.")
    st.page_link("pages/1_Login.py", label="Go to Login", icon="🔑")
    st.stop()

user = st.session_state['user']

# --- Profile Update Form ---
with st.form("profile_form"):
    st.subheader("Update Your Profile")
    st.write(f"**Role:** {user['role']}")
    new_username = st.text_input("Username", value=user['username'])
    new_email = st.text_input("Email", value=user['email'])
    
    submitted = st.form_submit_button("Update Profile")

    if submitted:
        # Check for uniqueness before updating
        existing_user_by_username = get_user(username=new_username)
        existing_user_by_email = get_user(email=new_email)
        
        if existing_user_by_username and existing_user_by_username['id'] != user['id']:
            st.error("This username is already taken. Please choose a different one.")
        elif existing_user_by_email and existing_user_by_email['id'] != user['id']:
            st.error("This email is already taken. Please use a different one.")
        else:
            if update_user(user['id'], new_username, new_email):
                updated_user_from_db = get_user(user_id=user['id'])
                if updated_user_from_db:
                    st.session_state['user'] = updated_user_from_db
                    st.success("Your profile has been updated successfully!")
                else:
                    st.error("Failed to retrieve updated user data.")
            else:
                st.error("An error occurred while updating your profile.")

st.markdown("---")

# --- Password Change Expander ---
with st.expander("Change Password"):
    with st.form("password_change_form"):
        current_password = st.text_input("Current Password", type="password")
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        
        password_submitted = st.form_submit_button("Change Password")

        if password_submitted:
            if not current_password or not new_password or not confirm_password:
                st.warning("Please fill in all password fields.")
            elif new_password != confirm_password:
                st.error("New passwords do not match.")
            else:
                # Verify the current password
                user_from_db = get_user(user_id=user['id'])
                if verify_password(current_password, user_from_db['password_hash']):
                    # Hash the new password
                    if update_password_hash(user['id'], new_password):
                        st.success("Your password has been changed successfully.")
                    else:
                        st.error("Failed to update password. Please try again.")
                else:
                    st.error("Incorrect current password.")
