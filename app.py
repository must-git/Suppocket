import streamlit as st
import data

st.set_page_config(
    page_title="Support Ticket App",
    page_icon="🎟️",
    layout="wide"
)

# Initialize session state for authentication
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
if 'user' not in st.session_state:
    st.session_state['user'] = None

st.sidebar.title("Navigation")

if st.session_state['authenticated']:
    st.sidebar.success(f"Logged in as {st.session_state['user']['name']} ({st.session_state['user']['role']})")
    
    st.sidebar.page_link("app.py", label="Home", icon="🏠")
    st.sidebar.page_link("pages/3_Dashboard.py", label="Dashboard", icon="📊")
    st.sidebar.page_link("pages/4_Create_Ticket.py", label="Create Ticket", icon="📝")
    # st.sidebar.page_link("pages/5_Ticket_Details.py", label="Ticket Details", icon="🎫", disabled=True) # Will be accessed via dashboard
    
    if st.sidebar.button("Logout"):
        st.session_state['authenticated'] = False
        st.session_state['user'] = None
        st.info("You have been logged out.")
        st.rerun()
else:
    st.sidebar.info("Please log in or register.")
    st.sidebar.page_link("app.py", label="Home", icon="🏠")
    st.sidebar.page_link("pages/1_Login.py", label="Login", icon="🔑")
    st.sidebar.page_link("pages/2_Register.py", label="Register", icon="✍️")

st.title("Welcome to the Support Ticket Application 🎟️")

if not st.session_state['authenticated']:
    st.write("Please use the sidebar to log in or register to access the application features.")
else:
    st.write("You are logged in. Use the sidebar to navigate to the Dashboard or create a new ticket.")

