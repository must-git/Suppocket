import streamlit as st

def render_sidebar():
    """Renders the sidebar with navigation links based on authentication status."""
    st.sidebar.title("Navigation")

    # Ensure session state keys exist
    if 'authenticated' not in st.session_state:
        st.session_state['authenticated'] = False
    if 'user' not in st.session_state:
        st.session_state['user'] = None

    if st.session_state.get('authenticated'):
        st.sidebar.success(f"Logged in as {st.session_state['user']['username']} ({st.session_state['user']['role']})")
        
        st.sidebar.page_link("app.py", label="Home", icon="🏠")
        st.sidebar.page_link("pages/3_Dashboard.py", label="Dashboard", icon="📊")
        st.sidebar.page_link("pages/7_Tickets.py", label="Tickets", icon="🎫")
        st.sidebar.page_link("pages/4_Create_Ticket.py", label="Create Ticket", icon="📝")
        st.sidebar.page_link("pages/6_Profile.py", label="Profile", icon="👤")
        
        if st.sidebar.button("Logout"):
            st.session_state['authenticated'] = False
            st.session_state['user'] = None
            st.info("You have been logged out.")
            st.switch_page("pages/1_Login.py")
    else:
        st.sidebar.info("Please log in or register.")
        st.sidebar.page_link("app.py", label="Home", icon="🏠")
        st.sidebar.page_link("pages/1_Login.py", label="Login", icon="🔑")
        st.sidebar.page_link("pages/2_Register.py", label="Register", icon="✍️")
