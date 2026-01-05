import streamlit as st
from auth_utils import render_sidebar

st.set_page_config(
    page_title="Admin Panel",
    page_icon="👑",
    layout="wide"
)

render_sidebar()

st.title("👑 Admin Panel")

# --- Authentication Check ---
if not st.session_state.get('authenticated') or st.session_state.get('user', {}).get('role') != 'admin':
    st.error("Access Denied: You must be an administrator to view this page.")
    if st.button("Go to Login"):
        st.switch_page("pages/1_Login.py")
    st.stop()

# --- Page Structure ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "👤 User Management",
    "🗂️ Category & Priority Management",
    "⏱️ SLA Configuration",
    "⚙️ System Settings",
    "📜 Activity Logs"
])

with tab1:
    st.header("User Management")
    st.info("This section is under construction.")

with tab2:
    st.header("Category & Priority Management")
    st.info("This section is under construction.")

with tab3:
    st.header("SLA Configuration")
    st.info("This section is under construction.")

with tab4:
    st.header("System Settings")
    st.info("This section is under construction.")

with tab5:
    st.header("Activity Logs")
    st.info("This section is under construction.")
