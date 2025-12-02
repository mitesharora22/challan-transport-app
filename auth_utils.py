# auth_utils.py - SHARED UTILITIES
import streamlit as st

def safe_rerun():
    """Try modern st.rerun(), fallback to experimental"""
    try:
        st.rerun()
    except Exception:
        try:
            st.experimental_rerun()
        except Exception:
            st.stop()

def do_logout():
    """Logout handler - sets session state only, NO rerun"""
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None
    st.session_state.office = None
    st.session_state.combined_page = "home"

def set_sidebar_visibility(visible: bool):
    """Show or hide sidebar"""
    if visible:
        st.markdown("<style>[data-testid='stSidebar']{display:block !important;}</style>", unsafe_allow_html=True)
    else:
        st.markdown("<style>[data-testid='stSidebar']{display:none !important;}</style>", unsafe_allow_html=True)

def hide_default_sidebar():
    """Hide sidebar (for operators)"""
    set_sidebar_visibility(False)

def show_default_sidebar():
    """Show sidebar (for admins)"""
    set_sidebar_visibility(True)