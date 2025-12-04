# app.py - COMPLETE VERSION WITH OPERATOR LOGIN
import streamlit as st
from db import init_db, verify_user, create_user
from auth_utils import safe_rerun, do_logout, set_sidebar_visibility

# Page config MUST be first
st.set_page_config(
    page_title="Transport Management Software",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize DB once
init_db()

# Session state defaults
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None
    st.session_state.office = None
    st.session_state.combined_page = "home"

# Hide Streamlit's default navigation
st.markdown("""
    <style>
    div[data-testid="stSidebarNav"] { display:none !important; }
    button[kind="header"] { display:none !important; }
    </style>
""", unsafe_allow_html=True)

# =====================================
# LOGIN HANDLERS
# =====================================
def handle_admin_login():
    """Process admin login - sets session state only"""
    username = st.session_state.get("admin_username", "").strip()
    password = st.session_state.get("admin_password", "")
    
    if not username or not password:
        st.session_state.login_error = "Please enter username and password"
        return
    
    user = verify_user(username, password)
    if user and user.get("role") == "ADMIN":
        st.session_state.logged_in = True
        st.session_state.username = user["username"]
        st.session_state.role = "ADMIN"
        st.session_state.office = user.get("office_location")
        st.session_state.combined_page = "home"
        st.session_state.login_error = None
    else:
        st.session_state.login_error = "❌ Invalid admin credentials"

def handle_operator_login():
    """Process operator login - sets session state only"""
    username = st.session_state.get("operator_username", "").strip()
    password = st.session_state.get("operator_password", "")
    
    if not username or not password:
        st.session_state.login_error = "Please enter username and password"
        return
    
    user = verify_user(username, password)
    if user and user.get("role") == "OPERATOR":
        st.session_state.logged_in = True
        st.session_state.username = user["username"]
        st.session_state.role = "OPERATOR"
        st.session_state.office = user.get("office_location")
        st.session_state.combined_page = "token"
        st.session_state.login_error = None
    else:
        st.session_state.login_error = "❌ Invalid operator credentials"

# =====================================
# LOGIN SCREEN
# =====================================
if not st.session_state.logged_in:
    set_sidebar_visibility(False)
    
    st.title("🔐 Transport Management System")
    st.markdown("### Login / लॉगिन करें")
    
    # Show login error if exists
    if "login_error" in st.session_state and st.session_state.login_error:
        st.error(st.session_state.login_error)
    
    role = st.selectbox("Select Role / भूमिका चुनें", ["Operator", "Admin"], index=0)
    
    if role == "Admin":
        st.markdown("---")
        st.subheader("🔑 Admin Login")
        
        st.text_input("Username", key="admin_username", placeholder="Enter username")
        st.text_input("Password", type="password", key="admin_password", placeholder="Enter password")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔓 Login as Admin", use_container_width=True, type="primary"):
                handle_admin_login()
                if st.session_state.logged_in:
                    st.rerun()
        
        with col2:
            if st.button("➕ Create Default Admin", use_container_width=True):
                try:
                    create_user("admin", "admin123", "ADMIN", None)
                    st.success("✅ Admin created: admin/admin123")
                except Exception:
                    st.info("ℹ️ Admin already exists")
        
        st.caption("Default credentials: **admin / admin123**")
    
    else:  # Operator
        st.markdown("---")
        st.subheader("👷 Operator Login")
        
        st.text_input("Username", key="operator_username", placeholder="Enter operator username")
        st.text_input("Password", type="password", key="operator_password", placeholder="Enter password")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔓 Login as Operator", use_container_width=True, type="primary"):
                handle_operator_login()
                if st.session_state.logged_in:
                    st.rerun()
        
        with col2:
            if st.button("➕ Create Test Operators", use_container_width=True):
                try:
                    # Create Mumbai operator
                    create_user("mumbai_op", "mumbai123", role="OPERATOR", office="MUMBAI")
                    # Create Delhi operator
                    create_user("delhi_op", "delhi123", role="OPERATOR", office="DELHI")
                    st.success("✅ Operators created:\n- Mumbai: mumbai_op / mumbai123\n- Delhi: delhi_op / delhi123")
                except Exception as e:
                    st.info(f"ℹ️ {str(e)}")
        
        st.caption("**Test Credentials:**")
        st.caption("• Mumbai Operator: **mumbai_op / mumbai123**")
        st.caption("• Delhi Operator: **delhi_op / delhi123**")
    
    st.stop()

# =====================================
# AFTER LOGIN - LOAD MAIN APP
# =====================================
set_sidebar_visibility(st.session_state.role == "ADMIN")

# Show logout button at top
col1, col2 = st.columns([4, 1])
with col1:
    st.markdown(f"**User:** {st.session_state.username} | **Role:** {st.session_state.role} | **Office:** {st.session_state.office or 'N/A'}")
with col2:
    if st.button("🚪 Logout", use_container_width=True):
        do_logout()
        st.rerun()

st.markdown("---")

# Import the combined modules
from pages import combined_all_part2 as part2

# CRITICAL: Run the app router
part2.run_app()