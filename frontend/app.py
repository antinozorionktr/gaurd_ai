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
    st.session_state.api_base_url = "http://localhost:8000"

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
</style>
""", unsafe_allow_html=True)


def get_role_display(role: str) -> str:
    """Get display name for role"""
    role_names = {
        "super_admin": "🔴 Super Admin",
        "admin": "🟠 Admin",
        "security_manager": "🔵 Security Manager",
        "security_guard": "🟢 Security Guard",
        "resident": "🟣 Resident",
        "receptionist": "🟢 Receptionist"
    }
    return role_names.get(role, role)


def check_permission(permission: str) -> bool:
    """Check if current user has permission"""
    permissions = st.session_state.get("permissions", [])
    return permission in permissions


def main():
    """Main application entry point"""
    
    # Check authentication
    if not st.session_state.get("authenticated"):
        # Show login prompt
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
        
        return
    
    # ==================== AUTHENTICATED USER VIEW ====================
    
    # Sidebar
    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/security-checked.png", width=80)
        st.title("Smart Gate Security")
        st.markdown("---")
        
        # User info
        st.subheader("👤 Current User")
        st.markdown(f"**{st.session_state.get('user_name', 'User')}**")
        
        role = st.session_state.get('user_role', 'unknown')
        st.markdown(f"""
        <div class="user-badge role-{role}">
            {get_role_display(role)}
        </div>
        """, unsafe_allow_html=True)
        
        st.caption(st.session_state.get('user_email', ''))
        
        st.markdown("---")
        
        # Navigation info
        st.info("👆 Use the sidebar to navigate")
        
        st.markdown("---")
        
        # Logout button
        if st.button("🚪 Logout", use_container_width=True):
            for key in ["authenticated", "access_token", "refresh_token", "user_id", 
                       "user_name", "user_role", "user_email", "permissions"]:
                st.session_state.pop(key, None)
            st.rerun()
        
        st.markdown("---")
        st.caption("© 2024 Smart Gate Security")
    
    # Main content
    st.title("🔐 Security Command Center")
    st.markdown(f"Welcome back, **{st.session_state.get('user_name', 'User')}**!")
    
    st.markdown("---")
    
    # Quick navigation cards based on permissions
    st.markdown("### 🚀 Quick Navigation")
    
    # Determine which cards to show based on permissions
    permissions = st.session_state.get("permissions", [])
    
    cols = st.columns(5)
    
    # Dashboard - visible to most roles
    if "dashboard:view" in permissions:
        with cols[0]:
            st.markdown("""
            <div class="card">
                <h3>🏠</h3>
                <p>Dashboard</p>
                <small>Overview & Analytics</small>
            </div>
            """, unsafe_allow_html=True)
    
    # Visitors
    if "visitor:read" in permissions:
        with cols[1]:
            st.markdown("""
            <div class="card" style="background: linear-gradient(145deg, #4a148c, #7b1fa2);">
                <h3>👤</h3>
                <p>Visitors</p>
                <small>Pre-approvals</small>
            </div>
            """, unsafe_allow_html=True)
    
    # Gate
    if "gate:verify" in permissions:
        with cols[2]:
            st.markdown("""
            <div class="card" style="background: linear-gradient(145deg, #e65100, #ff9800);">
                <h3>🚪</h3>
                <p>Gate</p>
                <small>Verification</small>
            </div>
            """, unsafe_allow_html=True)
    
    # Watchlist
    if "watchlist:read" in permissions:
        with cols[3]:
            st.markdown("""
            <div class="card" style="background: linear-gradient(145deg, #b71c1c, #e53935);">
                <h3>⚠️</h3>
                <p>Watchlist</p>
                <small>Alerts</small>
            </div>
            """, unsafe_allow_html=True)
    
    # Incidents
    if "incident:read" in permissions:
        with cols[4]:
            st.markdown("""
            <div class="card" style="background: linear-gradient(145deg, #1b5e20, #388e3c);">
                <h3>📋</h3>
                <p>Incidents</p>
                <small>Management</small>
            </div>
            """, unsafe_allow_html=True)
    
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
    
    st.markdown("---")
    
    # Role-based features info
    st.markdown("### 📌 Your Access Level")
    
    role = st.session_state.get('user_role', 'unknown')
    
    role_features = {
        "super_admin": [
            "Full system access",
            "Manage all users and roles",
            "System configuration",
            "All security features"
        ],
        "admin": [
            "Manage users",
            "View all reports",
            "Configure settings",
            "All operational features"
        ],
        "security_manager": [
            "Manage security staff",
            "View reports and analytics",
            "Watchlist management",
            "Incident assignment"
        ],
        "security_guard": [
            "Gate verification",
            "View watchlist alerts",
            "Report incidents",
            "View entry logs"
        ],
        "resident": [
            "Pre-approve visitors",
            "View your visitors",
            "Report incidents",
            "Update profile"
        ],
        "receptionist": [
            "Manage visitors",
            "View entry logs",
            "Report incidents",
            "Dashboard view"
        ]
    }
    
    features = role_features.get(role, ["Basic access"])
    
    st.markdown(f"""
    <div class="feature-card">
        <h4>{get_role_display(role)}</h4>
        <ul>
            {"".join([f"<li>{f}</li>" for f in features])}
        </ul>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
