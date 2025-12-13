import os
import streamlit as st

# Page configuration - must be first Streamlit command
st.set_page_config(
    page_title="Smart Gate Security",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Base URL configuration
if "api_base_url" not in st.session_state:
    st.session_state.api_base_url = os.environ.get("API_BASE_URL", "http://backend:8000")

# Import permissions after session state is available
from utils.permissions import (
    get_user_role, has_permission, get_accessible_pages,
    get_role_display_name, is_resident, is_receptionist,
    is_security_staff, is_admin, Permission
)

# Custom CSS for dark mode compatible styling
st.markdown("""
<style>
    /* Main container */
    .main > div {
        padding-top: 1rem;
    }
    
    /* Metric cards */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: bold;
    }
    
    /* Card style containers - Dark mode compatible */
    .card {
        background: linear-gradient(145deg, #1e3a5f, #2d5a87);
        padding: 1.5rem;
        border-radius: 12px;
        margin-bottom: 1rem;
        border: 1px solid #3d7ab5;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    
    .card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.4);
    }
    
    .card h3 {
        margin-bottom: 0.5rem;
        font-size: 2.5rem;
    }
    
    .card p {
        color: #ffffff !important;
        font-weight: 600;
        margin-bottom: 0.25rem;
    }
    
    .card small {
        color: #a0c4e8 !important;
    }
    
    /* Feature cards */
    .feature-card {
        background: linear-gradient(145deg, #1a1a2e, #16213e);
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #0f3460;
        margin-bottom: 1rem;
    }
    
    .feature-card h4 {
        color: #00d9ff !important;
        margin-bottom: 1rem;
    }
    
    .feature-card p, .feature-card li {
        color: #e0e0e0 !important;
    }
    
    /* User badge */
    .user-badge {
        background: linear-gradient(145deg, #4a148c, #7b1fa2);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        display: inline-block;
        margin: 0.5rem 0;
    }
    
    /* Role colors */
    .role-super_admin { background: linear-gradient(145deg, #b71c1c, #e53935); }
    .role-admin { background: linear-gradient(145deg, #e65100, #ff9800); }
    .role-security_manager { background: linear-gradient(145deg, #1565c0, #1976d2); }
    .role-security_guard { background: linear-gradient(145deg, #2e7d32, #43a047); }
    .role-resident { background: linear-gradient(145deg, #4a148c, #7b1fa2); }
    .role-receptionist { background: linear-gradient(145deg, #00695c, #009688); }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Improve sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1117, #161b22);
    }
    
    /* Resident specific styling */
    .resident-welcome {
        background: linear-gradient(145deg, #4a148c, #7b1fa2);
        padding: 2rem;
        border-radius: 16px;
        color: white;
        margin-bottom: 1.5rem;
    }
    
    /* Receptionist specific styling */
    .receptionist-welcome {
        background: linear-gradient(145deg, #00695c, #009688);
        padding: 2rem;
        border-radius: 16px;
        color: white;
        margin-bottom: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)


def show_login_page():
    """Show login prompt for unauthenticated users"""
    st.markdown("""
    <div style="text-align: center; padding: 2rem;">
        <img src="https://img.icons8.com/fluency/96/security-checked.png" width="80">
        <h1>🔐 Smart Gate Security</h1>
        <p style="color: #888; margin-bottom: 2rem;">AI-Powered Security Command Center</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.warning("⚠️ Please login to access the system")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔑 Go to Login", use_container_width=True, type="primary"):
            st.switch_page("pages/0_🔑_Login.py")
    
    # Show features preview
    st.markdown("---")
    st.markdown("### System Features")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        **🎫 Visitor Management**
        - Digital visitor pre-approval
        - Face recognition registration
        - Time-bound access control
        """)
        
        st.markdown("""
        **🚪 Gate Verification**
        - AI-powered face verification
        - Approval code fallback
        - Real-time entry logging
        """)
    
    with col2:
        st.markdown("""
        **⚠️ Watchlist & Alerts**
        - Flagged individuals database
        - Real-time threat detection
        - Severity-based alerts
        """)
        
        st.markdown("""
        **📋 Incident Management**
        - Security incident reporting
        - Status tracking
        - Evidence management
        """)


def show_resident_dashboard():
    """Show resident-specific dashboard"""
    user_name = st.session_state.get('user_name', 'Resident')
    unit = st.session_state.get('unit_number', 'N/A')
    
    st.markdown(f"""
    <div class="resident-welcome">
        <h2>🏠 Welcome Home, {user_name}!</h2>
        <p>Unit: {unit}</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 🎯 Quick Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="card" style="background: linear-gradient(145deg, #4a148c, #7b1fa2);">
            <h3>👤</h3>
            <p>Pre-Approve Visitor</p>
            <small>Register expected guests</small>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Add Visitor", key="res_add_visitor", use_container_width=True):
            st.switch_page("pages/2_👤_Visitor_Approval.py")
    
    with col2:
        st.markdown("""
        <div class="card" style="background: linear-gradient(145deg, #1565c0, #1976d2);">
            <h3>📋</h3>
            <p>My Visitors</p>
            <small>View visitor history</small>
        </div>
        """, unsafe_allow_html=True)
        if st.button("View Visitors", key="res_view_visitors", use_container_width=True):
            st.switch_page("pages/2_👤_Visitor_Approval.py")
    
    with col3:
        st.markdown("""
        <div class="card" style="background: linear-gradient(145deg, #b71c1c, #e53935);">
            <h3>🚨</h3>
            <p>Report Issue</p>
            <small>Security concerns</small>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Report Incident", key="res_report", use_container_width=True):
            st.switch_page("pages/5_📋_Incidents.py")
    
    st.markdown("---")
    
    # Resident-specific info
    st.markdown("### 📌 Resident Guidelines")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("""
        **Pre-Approving Visitors:**
        - Register visitors before they arrive
        - Share the approval code with your guest
        - Visitors can use code or face recognition at gate
        - Approvals are time-bound for security
        """)
    
    with col2:
        st.info("""
        **Security Tips:**
        - Always verify delivery personnel
        - Report suspicious activity immediately
        - Keep your approval codes private
        - Update visitor details if plans change
        """)


def show_receptionist_dashboard():
    """Show receptionist-specific dashboard"""
    user_name = st.session_state.get('user_name', 'Receptionist')
    
    st.markdown(f"""
    <div class="receptionist-welcome">
        <h2>👋 Welcome, {user_name}!</h2>
        <p>Front Desk Operations Center</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 🎯 Quick Actions")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="card" style="background: linear-gradient(145deg, #00695c, #009688);">
            <h3>👤</h3>
            <p>New Visitor</p>
            <small>Register walk-in</small>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Register", key="rec_new_visitor", use_container_width=True):
            st.switch_page("pages/2_👤_Visitor_Approval.py")
    
    with col2:
        st.markdown("""
        <div class="card" style="background: linear-gradient(145deg, #e65100, #ff9800);">
            <h3>🚪</h3>
            <p>Gate Verify</p>
            <small>Check visitor</small>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Verify", key="rec_verify", use_container_width=True):
            st.switch_page("pages/3_🚪_Gate_Verification.py")
    
    with col3:
        st.markdown("""
        <div class="card" style="background: linear-gradient(145deg, #1565c0, #1976d2);">
            <h3>📋</h3>
            <p>All Visitors</p>
            <small>View & manage</small>
        </div>
        """, unsafe_allow_html=True)
        if st.button("View All", key="rec_all_visitors", use_container_width=True):
            st.switch_page("pages/2_👤_Visitor_Approval.py")
    
    with col4:
        st.markdown("""
        <div class="card" style="background: linear-gradient(145deg, #b71c1c, #e53935);">
            <h3>🚨</h3>
            <p>Report</p>
            <small>Log incident</small>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Report", key="rec_report", use_container_width=True):
            st.switch_page("pages/5_📋_Incidents.py")
    
    st.markdown("---")
    
    # Today's summary
    st.markdown("### 📊 Today's Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # These would come from API in production
    with col1:
        st.metric("Expected Visitors", "12", "+3 from yesterday")
    with col2:
        st.metric("Checked In", "8", "67%")
    with col3:
        st.metric("Pending", "4")
    with col4:
        st.metric("Issues", "0", "All clear", delta_color="off")
    
    st.markdown("---")
    
    # Receptionist-specific tools
    st.markdown("### 🛠️ Tools")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **📞 Quick Contact:**
        - Security Office: Ext. 100
        - Emergency: Ext. 911
        - Management: Ext. 200
        """)
    
    with col2:
        st.markdown("""
        **📝 Common Tasks:**
        - Register walk-in visitors
        - Verify pre-approved guests
        - Handle delivery personnel
        - Log incidents/complaints
        """)


def show_security_dashboard():
    """Show security staff dashboard"""
    user_name = st.session_state.get('user_name', 'Security')
    role = get_user_role()
    
    st.title("🛡️ Security Command Center")
    st.markdown(f"Welcome, **{user_name}** ({get_role_display_name(role)})")
    
    st.markdown("---")
    
    # Quick action cards
    st.markdown("### 🎯 Quick Actions")
    
    cols = st.columns(5)
    
    with cols[0]:
        st.markdown("""
        <div class="card">
            <h3>🏠</h3>
            <p>Dashboard</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("View", key="sec_dashboard", use_container_width=True):
            st.switch_page("pages/1_🏠_Dashboard.py")
    
    with cols[1]:
        st.markdown("""
        <div class="card" style="background: linear-gradient(145deg, #e65100, #ff9800);">
            <h3>🚪</h3>
            <p>Gate</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Verify", key="sec_gate", use_container_width=True):
            st.switch_page("pages/3_🚪_Gate_Verification.py")
    
    with cols[2]:
        st.markdown("""
        <div class="card" style="background: linear-gradient(145deg, #b71c1c, #e53935);">
            <h3>⚠️</h3>
            <p>Watchlist</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Alerts", key="sec_watchlist", use_container_width=True):
            st.switch_page("pages/4_⚠️_Watchlist.py")
    
    with cols[3]:
        st.markdown("""
        <div class="card" style="background: linear-gradient(145deg, #4a148c, #7b1fa2);">
            <h3>👤</h3>
            <p>Visitors</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("View", key="sec_visitors", use_container_width=True):
            st.switch_page("pages/2_👤_Visitor_Approval.py")
    
    with cols[4]:
        st.markdown("""
        <div class="card" style="background: linear-gradient(145deg, #1b5e20, #388e3c);">
            <h3>📋</h3>
            <p>Incidents</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Manage", key="sec_incidents", use_container_width=True):
            st.switch_page("pages/5_📋_Incidents.py")
    
    st.markdown("---")
    
    # System status
    st.markdown("### 🖥️ System Status")
    
    status_col1, status_col2, status_col3 = st.columns(3)
    
    with status_col1:
        st.success("✅ Face Recognition: Online")
    with status_col2:
        st.success("✅ Database: Connected")
    with status_col3:
        st.success("✅ Alert System: Active")


def show_admin_dashboard():
    """Show admin dashboard"""
    user_name = st.session_state.get('user_name', 'Admin')
    role = get_user_role()
    
    st.title("⚙️ Admin Control Panel")
    st.markdown(f"Welcome, **{user_name}** ({get_role_display_name(role)})")
    
    st.markdown("---")
    
    # Admin has access to everything
    st.markdown("### 🎯 Full System Access")
    
    cols = st.columns(5)
    
    pages = [
        ("🏠", "Dashboard", "pages/1_🏠_Dashboard.py"),
        ("👤", "Visitors", "pages/2_👤_Visitor_Approval.py"),
        ("🚪", "Gate", "pages/3_🚪_Gate_Verification.py"),
        ("⚠️", "Watchlist", "pages/4_⚠️_Watchlist.py"),
        ("📋", "Incidents", "pages/5_📋_Incidents.py"),
    ]
    
    for i, (icon, name, page) in enumerate(pages):
        with cols[i]:
            st.markdown(f"""
            <div class="card">
                <h3>{icon}</h3>
                <p>{name}</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"Open", key=f"admin_{name}", use_container_width=True):
                st.switch_page(page)
    
    st.markdown("---")
    
    # Admin-specific features
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 👥 User Management")
        st.info("Manage users, roles, and permissions")
        # This would link to a user management page
    
    with col2:
        st.markdown("### 📊 Analytics")
        st.info("View detailed reports and analytics")


def main():
    """Main application entry point"""
    
    # Check authentication
    if not st.session_state.get("authenticated"):
        show_login_page()
        return
    
    # ==================== AUTHENTICATED USER VIEW ====================
    
    role = get_user_role()
    
    # Sidebar (common for all authenticated users)
    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/security-checked.png", width=80)
        st.title("Smart Gate Security")
        st.markdown("---")
        
        # User info
        st.subheader("👤 Current User")
        st.markdown(f"**{st.session_state.get('user_name', 'User')}**")
        
        st.markdown(f"""
        <div class="user-badge role-{role}">
            {get_role_display_name(role)}
        </div>
        """, unsafe_allow_html=True)
        
        st.caption(st.session_state.get('user_email', ''))
        
        if st.session_state.get('unit_number'):
            st.caption(f"Unit: {st.session_state.get('unit_number')}")
        
        st.markdown("---")
        
        # Navigation based on role
        st.subheader("📍 Navigation")
        
        accessible_pages = get_accessible_pages()
        for page in accessible_pages:
            if st.button(f"{page['icon']} {page['name']}", key=f"nav_{page['name']}", use_container_width=True):
                st.switch_page(page['file'])
        
        st.markdown("---")
        
        # Logout button
        if st.button("🚪 Logout", use_container_width=True):
            for key in ["authenticated", "access_token", "refresh_token", "user_id", 
                       "user_name", "user_role", "user_email", "permissions", "unit_number", "block"]:
                st.session_state.pop(key, None)
            st.rerun()
        
        st.markdown("---")
        st.caption("© 2024 Smart Gate Security")
    
    # Main content based on role
    if is_resident():
        show_resident_dashboard()
    elif is_receptionist():
        show_receptionist_dashboard()
    elif is_security_staff():
        show_security_dashboard()
    elif is_admin():
        show_admin_dashboard()
    else:
        # Fallback for unknown roles
        st.title("🔐 Smart Gate Security")
        st.warning("Unknown role. Please contact administrator.")


if __name__ == "__main__":
    main()