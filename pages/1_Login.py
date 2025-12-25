import streamlit as st
import data

st.set_page_config(
    page_title="Login",
    page_icon="🔑"
)

st.title("Login")

if st.session_state['authenticated']:
    st.warning("You are already logged in.")
    st.page_link("pages/3_Dashboard.py", label="Go to Dashboard", icon="📊")
    st.stop()

with st.form("login_form"):
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    submitted = st.form_submit_button("Login")

    if submitted:
        user = data.get_user_by_email(email)
        if user and user['password'] == password: # Simple password check
            st.session_state['authenticated'] = True
            st.session_state['user'] = user
            st.success(f"Welcome, {user['name']}!")
            st.rerun()
        else:
            st.error("Invalid email or password.")
