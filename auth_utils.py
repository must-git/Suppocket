import streamlit as st
import hashlib

def verify_password(plain_password, hashed_password):
    return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password 

def render_sidebar():
    """Renders the sidebar with navigation links based on authentication status."""
    st.sidebar.title("Navigation")

    # Ensure session state keys exist
    if 'authenticated' not in st.session_state:
        st.session_state['authenticated'] = False
    if 'user' not in st.session_state:
        st.session_state['user'] = None

    if st.session_state.get('authenticated'):
        st.sidebar.success(f"Logged in as {st.session_state['user']['username']}")
        
        st.sidebar.page_link("app.py", label="Home", icon="🏠")
        st.sidebar.page_link("pages/3_Dashboard.py", label="Dashboard", icon="📊")
        st.sidebar.page_link("pages/4_Tickets.py", label="Tickets", icon="🎫")
        st.sidebar.page_link("pages/5_Create_Ticket.py", label="Create Ticket", icon="📝")
        st.sidebar.page_link("pages/8_Profile.py", label="Profile", icon="👤")
        if st.session_state.get('user')['role'] == 'admin':
            st.sidebar.page_link("pages/_Admin.py", label="Admin Panel", icon="🛠️")
            st.sidebar.page_link("pages/_Reports.py", label="Reports", icon="📈")
        
        if st.sidebar.button("Logout"):
            st.session_state['authenticated'] = False
            st.session_state['user'] = None
            st.session_state['selected_ticket_id'] = None
            st.info("You have been logged out.")
            st.switch_page("pages/1_Login.py")
    else:
        st.sidebar.info("Please log in or register.")
        st.sidebar.page_link("app.py", label="Home", icon="🏠")
        st.sidebar.page_link("pages/1_Login.py", label="Login", icon="🔑")
        st.sidebar.page_link("pages/2_Register.py", label="Register", icon="✍️")
