import streamlit as st
from auth_utils import render_sidebar
from utils.theme import apply_theme

# --- Page Configuration and Theme ---
st.set_page_config(
    page_title="Suppocket - Your Pocket Support Solution",
    page_icon="🎟️",
    layout="wide",
    initial_sidebar_state="expanded"
)
apply_theme()

# --- Sidebar ---
render_sidebar()

# --- Main Content ---
st.title("Welcome to Suppocket 🎟️")
st.markdown("### Your streamlined solution for managing support tickets efficiently.")

st.markdown(
    """
    Suppocket is a modern, easy-to-use support ticket system designed to help businesses
    manage customer inquiries and technical issues with ease. Our platform ensures that
    every ticket is tracked, managed, and resolved promptly, improving customer satisfaction
    and team productivity.
    """
)

st.divider()

# --- Key Features ---
st.header("Key Features")

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("📊 Centralized Dashboard")
    st.write(
        "Get a bird's-eye view of all your support tickets. "
        "Track statuses, priorities, and assignments in one place."
    )

with col2:
    st.subheader("📝 Effortless Ticket Creation")
    st.write(
        "Users can create detailed support tickets in seconds, "
        "providing all necessary information for a swift resolution."
    )

with col3:
    st.subheader("👤 User-Focused Profiles")
    st.write(
        "Manage your profile, track your ticket history, and "
        "update your information with ease."
    )

st.divider()

# --- Call to Action ---
if not st.session_state.get('authenticated'):
    st.header("Get Started")
    st.write("Join us today and take control of your support process.")

    cta_col1, cta_col2, _ = st.columns([1, 1, 4])

    with cta_col1:
        if st.button("Login", use_container_width=True, type="primary"):
            st.switch_page("pages/1_Login.py")

    with cta_col2:
        if st.button("Register", use_container_width=True):
            st.switch_page("pages/2_Register.py")
else:
    st.header("You're Logged In!")
    st.write("Use the sidebar to navigate to your Dashboard or create a new ticket.")
    if st.button("Go to Dashboard", use_container_width=False, type="primary"):
        st.switch_page("pages/3_Dashboard.py")