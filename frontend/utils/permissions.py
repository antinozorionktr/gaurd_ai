"""
Permission utilities for role-based access control in Streamlit UI
"""

import streamlit as st
from enum import Enum
from typing import List, Optional

class Permission(str, Enum):
    # Dashboard
    DASHBOARD_VIEW = "dashboard:view"
    DASHBOARD_ANALYTICS = "dashboard:analytics"
    
    # Visitor Management
    VISITOR_CREATE = "visitor:create"
    VISITOR_READ = "visitor:read"
    VISITOR_UPDATE = "visitor:update"
    VISITOR_DELETE = "visitor:delete"
    VISITOR_APPROVE = "visitor:approve"
    
    # Gate Operations
    GATE_VERIFY = "gate:verify"
    GATE_MANUAL_OVERRIDE = "gate:manual_override"
    GATE_LOGS_VIEW = "gate:logs_view"
    
    # Watchlist
    WATCHLIST_READ = "watchlist:read"
    WATCHLIST_CREATE = "watchlist:create"
    WATCHLIST_UPDATE = "watchlist:update"
    WATCHLIST_DELETE = "watchlist:delete"
    WATCHLIST_ALERTS = "watchlist:alerts"
    
    # Incidents
    INCIDENT_CREATE = "incident:create"
    INCIDENT_READ = "incident:read"
    INCIDENT_UPDATE = "incident:update"
    INCIDENT_DELETE = "incident:delete"
    INCIDENT_ASSIGN = "incident:assign"
    
    # User Management
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"


# Role-based permission mapping
ROLE_PERMISSIONS = {
    "super_admin": [p.value for p in Permission],  # All permissions
    
    "admin": [
        Permission.DASHBOARD_VIEW.value,
        Permission.DASHBOARD_ANALYTICS.value,
        Permission.VISITOR_CREATE.value,
        Permission.VISITOR_READ.value,
        Permission.VISITOR_UPDATE.value,
        Permission.VISITOR_DELETE.value,
        Permission.VISITOR_APPROVE.value,
        Permission.GATE_VERIFY.value,
        Permission.GATE_MANUAL_OVERRIDE.value,
        Permission.GATE_LOGS_VIEW.value,
        Permission.WATCHLIST_READ.value,
        Permission.WATCHLIST_CREATE.value,
        Permission.WATCHLIST_UPDATE.value,
        Permission.WATCHLIST_DELETE.value,
        Permission.WATCHLIST_ALERTS.value,
        Permission.INCIDENT_CREATE.value,
        Permission.INCIDENT_READ.value,
        Permission.INCIDENT_UPDATE.value,
        Permission.INCIDENT_ASSIGN.value,
        Permission.USER_READ.value,
        Permission.USER_UPDATE.value,
    ],
    
    "security_manager": [
        Permission.DASHBOARD_VIEW.value,
        Permission.DASHBOARD_ANALYTICS.value,
        Permission.VISITOR_READ.value,
        Permission.VISITOR_APPROVE.value,
        Permission.GATE_VERIFY.value,
        Permission.GATE_MANUAL_OVERRIDE.value,
        Permission.GATE_LOGS_VIEW.value,
        Permission.WATCHLIST_READ.value,
        Permission.WATCHLIST_CREATE.value,
        Permission.WATCHLIST_UPDATE.value,
        Permission.WATCHLIST_ALERTS.value,
        Permission.INCIDENT_CREATE.value,
        Permission.INCIDENT_READ.value,
        Permission.INCIDENT_UPDATE.value,
        Permission.INCIDENT_ASSIGN.value,
    ],
    
    "security_guard": [
        Permission.DASHBOARD_VIEW.value,
        Permission.VISITOR_READ.value,
        Permission.GATE_VERIFY.value,
        Permission.GATE_LOGS_VIEW.value,
        Permission.WATCHLIST_READ.value,
        Permission.WATCHLIST_ALERTS.value,
        Permission.INCIDENT_CREATE.value,
        Permission.INCIDENT_READ.value,
    ],
    
    "resident": [
        Permission.DASHBOARD_VIEW.value,
        Permission.VISITOR_CREATE.value,  # Can pre-approve their own visitors
        Permission.VISITOR_READ.value,    # Can view their own visitors only
        Permission.INCIDENT_CREATE.value, # Can report incidents
        Permission.INCIDENT_READ.value,   # Can view their own incidents
    ],
    
    "receptionist": [
        Permission.DASHBOARD_VIEW.value,
        Permission.VISITOR_CREATE.value,
        Permission.VISITOR_READ.value,
        Permission.VISITOR_UPDATE.value,
        Permission.VISITOR_APPROVE.value,
        Permission.GATE_VERIFY.value,
        Permission.GATE_LOGS_VIEW.value,
        Permission.INCIDENT_CREATE.value,
        Permission.INCIDENT_READ.value,
    ],
}


def get_user_role() -> str:
    """Get current user's role from session state"""
    return st.session_state.get("user_role", "unknown")


def get_user_permissions() -> List[str]:
    """Get current user's permissions from session state or derive from role"""
    # First check if permissions are stored in session
    stored_permissions = st.session_state.get("permissions", [])
    if stored_permissions:
        return stored_permissions
    
    # Otherwise derive from role
    role = get_user_role()
    return ROLE_PERMISSIONS.get(role, [])


def has_permission(permission: str) -> bool:
    """Check if current user has a specific permission"""
    permissions = get_user_permissions()
    return permission in permissions


def has_any_permission(*permissions: str) -> bool:
    """Check if current user has any of the specified permissions"""
    user_permissions = get_user_permissions()
    return any(p in user_permissions for p in permissions)


def has_all_permissions(*permissions: str) -> bool:
    """Check if current user has all of the specified permissions"""
    user_permissions = get_user_permissions()
    return all(p in user_permissions for p in permissions)


def require_permission(permission: str, show_error: bool = True) -> bool:
    """
    Check permission and optionally show error message
    Returns True if permitted, False otherwise
    """
    if not has_permission(permission):
        if show_error:
            st.error("🚫 Access Denied: You don't have permission to access this feature.")
        return False
    return True


def require_auth(redirect: bool = True) -> bool:
    """
    Check if user is authenticated
    Returns True if authenticated, False otherwise
    """
    if not st.session_state.get("authenticated"):
        if redirect:
            st.warning("⚠️ Please login to access this page")
            if st.button("🔑 Go to Login"):
                st.switch_page("pages/0_🔑_Login.py")
        return False
    return True


def is_resident() -> bool:
    """Check if current user is a resident"""
    return get_user_role() == "resident"


def is_receptionist() -> bool:
    """Check if current user is a receptionist"""
    return get_user_role() == "receptionist"


def is_security_staff() -> bool:
    """Check if current user is security staff (guard or manager)"""
    return get_user_role() in ["security_guard", "security_manager"]


def is_admin() -> bool:
    """Check if current user is an admin"""
    return get_user_role() in ["admin", "super_admin"]


def get_accessible_pages() -> List[dict]:
    """Get list of pages accessible to current user"""
    role = get_user_role()
    permissions = get_user_permissions()
    
    all_pages = [
        {
            "name": "Dashboard",
            "icon": "🏠",
            "file": "pages/1_🏠_Dashboard.py",
            "permission": Permission.DASHBOARD_VIEW.value,
        },
        {
            "name": "Visitor Approval",
            "icon": "👤",
            "file": "pages/2_👤_Visitor_Approval.py",
            "permission": Permission.VISITOR_CREATE.value,
        },
        {
            "name": "Gate Verification",
            "icon": "🚪",
            "file": "pages/3_🚪_Gate_Verification.py",
            "permission": Permission.GATE_VERIFY.value,
        },
        {
            "name": "Watchlist",
            "icon": "⚠️",
            "file": "pages/4_⚠️_Watchlist.py",
            "permission": Permission.WATCHLIST_READ.value,
        },
        {
            "name": "Incidents",
            "icon": "📋",
            "file": "pages/5_📋_Incidents.py",
            "permission": Permission.INCIDENT_READ.value,
        },
    ]
    
    return [page for page in all_pages if page["permission"] in permissions]


def get_role_display_name(role: str) -> str:
    """Get display name for role"""
    role_names = {
        "super_admin": "🔴 Super Admin",
        "admin": "🟠 Admin",
        "security_manager": "🔵 Security Manager",
        "security_guard": "🟢 Security Guard",
        "resident": "🟣 Resident",
        "receptionist": "🟢 Receptionist"
    }
    return role_names.get(role, role.title())


def show_permission_denied():
    """Show permission denied message with helpful info"""
    st.error("🚫 Access Denied")
    st.markdown("""
    You don't have permission to access this feature.
    
    If you believe this is an error, please contact your administrator.
    """)
    
    role = get_user_role()
    st.info(f"Your current role: **{get_role_display_name(role)}**")