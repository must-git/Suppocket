import streamlit as st

def apply_theme():
    """
    Applies a custom light or dark theme to the Streamlit app and adds a theme toggle to the sidebar.
    """
    if 'theme' not in st.session_state:
        st.session_state.theme = 'light'
    
    # Sidebar toggle button
    with st.sidebar:
        theme_icon = '🌙 Dark Mode' if st.session_state.theme == 'light' else '☀️ Light Mode'
        if st.button(theme_icon, use_container_width=True):
            st.session_state.theme = 'dark' if st.session_state.theme == 'light' else 'light'
            st.rerun()

    # --- CSS Styles ---
    light_theme_css = """
    <style>
        :root {
            --background-color: #FFFFFF;
            --secondary-background-color: #F0F2F6;
            --text-color: #31333F;
            --primary-color: #1976D2;
            --input-background-color: #FFFFFF;
            --input-border-color: #BDBDBD;
        }
        .stApp {
            background-color: var(--background-color);
            color: var(--text-color);
        }
        .stTextInput input, .stTextArea textarea, .stDateInput input {
            background-color: var(--input-background-color);
            color: var(--text-color);
            border-color: var(--input-border-color);
        }
        .stButton > button {
            background-color: var(--primary-color);
            color: white;
            border: none;
        }
        .st-emotion-cache-183lzff { /* Expander header */
            background-color: var(--secondary-background-color);
        }
        [data-testid="stMetric"] {
            background-color: var(--secondary-background-color);
            padding: 1rem;
            border-radius: 0.5rem;
        }
    </style>
    """

    dark_theme_css = """
    <style>
        :root {
            --background-color: #0E1117;
            --secondary-background-color: #262730;
            --text-color: #FAFAFA;
            --primary-color: #1976D2;
            --input-background-color: #262730;
            --input-border-color: #424242;
        }
        .stApp {
            background-color: var(--background-color);
            color: var(--text-color);
        }
        h1, h2, h3, h4, h5, h6 {
            color: var(--text-color);
        }
        .stTextInput input, .stTextArea textarea, .stDateInput input, .stSelectbox > div[data-baseweb="select"] > div {
            background-color: var(--input-background-color) !important;
            color: var(--text-color) !important;
            border-color: var(--input-border-color) !important;
        }
        .stButton > button {
            background-color: var(--primary-color);
            color: white;
            border: none;
        }
        .st-emotion-cache-183lzff { /* Expander header */
            background-color: var(--secondary-background-color);
        }
        [data-testid="stMetric"] {
            background-color: var(--secondary-background-color);
            padding: 1rem;
            border-radius: 0.5rem;
        }
        /* Make Plotly charts theme-aware */
        .plotly-chart {
            background-color: var(--background-color);
        }
    </style>
    """
    
    # Apply the selected theme's CSS
    if st.session_state.theme == 'dark':
        st.markdown(dark_theme_css, unsafe_allow_html=True)
    else:
        st.markdown(light_theme_css, unsafe_allow_html=True)