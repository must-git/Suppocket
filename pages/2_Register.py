import streamlit as st
import data

st.set_page_config(
    page_title="Register",
    page_icon="✍️"
)

st.title("Register")

if st.session_state['authenticated']:
    st.warning("You are already logged in. Please logout to register a new account.")
    st.page_link("pages/3_Dashboard.py", label="Go to Dashboard", icon="📊")
    st.stop()

with st.form("register_form"):
    name = st.text_input("Name")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")
    submitted = st.form_submit_button("Register")

    if submitted:
        if not name or not email or not password or not confirm_password:
            st.error("Please fill in all fields.")
        elif password != confirm_password:
            st.error("Passwords do not match.")
        elif data.get_user_by_email(email):
            st.error("An account with this email already exists.")
        else:
            new_user = data.add_user(email, password, name, role='Customer')
            st.success(f"Account created for {new_user['name']}! Please log in.")
            st.page_link("pages/1_Login.py", label="Go to Login Page", icon="🔑")
            st.rerun()
