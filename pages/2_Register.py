import streamlit as st
from db.database import create_user, get_user
from auth_utils import render_sidebar

st.set_page_config(
    page_title="Register",
    page_icon="✍️"
)

render_sidebar()

st.title("Register")

if st.session_state.get('authenticated'):
    st.warning("You are already logged in. Please logout to register a new account.")
    st.page_link("pages/3_Dashboard.py", label="Go to Dashboard", icon="📊")
    st.stop()

with st.form("register_form"):
    username = st.text_input("Username")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")
    submitted = st.form_submit_button("Register")

    if submitted:
        if not username or not email or not password or not confirm_password:
            st.error("Please fill in all fields.")
        elif password != confirm_password:
            st.error("Passwords do not match.")
        elif get_user(email=email) or get_user(username=username):
            st.error("An account with this email or username already exists.")
        else:
            user_id = create_user(username, email, password, role='customer')
            
            if user_id:
                st.success(f"Account created for {username}! Please log in.")
                st.page_link("pages/1_Login.py", label="Go to Login Page", icon="🔑")
            else:
                st.error("An error occurred during registration. Please try again.")
