import streamlit as st
from auth_utils import render_sidebar
from db.database import update_user, get_user

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

with st.form("profile_form"):
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
                # Fetch updated user details from DB to refresh session state
                updated_user_from_db = get_user(user_id=user['id'])
                if updated_user_from_db:
                    st.session_state['user'] = updated_user_from_db
                    st.success("Your profile has been updated successfully!")
                    st.rerun()
                else:
                    st.error("Failed to retrieve updated user data.")
            else:
                st.error("An error occurred while updating your profile.")
