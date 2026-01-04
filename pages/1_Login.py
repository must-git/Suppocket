import streamlit as st
from db.auth import login_user
from auth_utils import render_sidebar
from utils.theme import apply_theme

st.set_page_config(
    page_title="Login",
    page_icon="🔑"
)
apply_theme()

render_sidebar()

st.title("Login")

if st.session_state.get('authenticated'):
    st.warning("You are already logged in.")
    st.page_link("pages/3_Dashboard.py", label="Go to Dashboard", icon="📊")
    st.stop()

with st.form("login_form"):
    username_or_email = st.text_input("Username or Email")
    password = st.text_input("Password", type="password")
    submitted = st.form_submit_button("Login")

    if submitted:
        user = login_user(username_or_email, password)
        
        if user:
            st.session_state['authenticated'] = True
            st.session_state['user'] = user
            st.success(f"Welcome, {user['username']}!")
            st.switch_page("pages/3_Dashboard.py")
        else:
            st.error("Invalid username/email or password.")
