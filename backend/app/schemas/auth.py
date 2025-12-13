"""
Authentication and Authorization Schemas
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    """User roles for RBAC"""
    SUPER_ADMIN = "super_admin"      # Full system access
    ADMIN = "admin"                   # Manage users, settings, view all
    SECURITY_MANAGER = "security_manager"  # Manage security staff, view reports
    SECURITY_GUARD = "security_guard"      # Gate operations, basic incident reporting
    RESIDENT = "resident"             # Pre-approve visitors, view own data
    RECEPTIONIST = "receptionist"     # Visitor management, no security features


class Permission(str, Enum):
    """System permissions"""
    # User Management
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    
    # Visitor Management
    VISITOR_CREATE = "visitor:create"
    VISITOR_READ = "visitor:read"
    VISITOR_UPDATE = "visitor:update"
    VISITOR_DELETE = "visitor:delete"
    VISITOR_APPROVE = "visitor:approve"
    
    # Gate Operations
    GATE_VERIFY = "gate:verify"
    GATE_MANUAL_OVERRIDE = "gate:manual_override"
    GATE_VIEW_LOGS = "gate:view_logs"
    
    # Watchlist Management
    WATCHLIST_CREATE = "watchlist:create"
    WATCHLIST_READ = "watchlist:read"
    WATCHLIST_UPDATE = "watchlist:update"
    WATCHLIST_DELETE = "watchlist:delete"
    WATCHLIST_ALERTS = "watchlist:alerts"
    
    # Incident Management
    INCIDENT_CREATE = "incident:create"
    INCIDENT_READ = "incident:read"
    INCIDENT_UPDATE = "incident:update"
    INCIDENT_DELETE = "incident:delete"
    INCIDENT_ASSIGN = "incident:assign"
    INCIDENT_RESOLVE = "incident:resolve"
    
    # Dashboard & Reports
    DASHBOARD_VIEW = "dashboard:view"
    REPORTS_VIEW = "reports:view"
    REPORTS_EXPORT = "reports:export"
    
    # Settings
    SETTINGS_VIEW = "settings:view"
    SETTINGS_UPDATE = "settings:update"


# Role-Permission Mapping
ROLE_PERMISSIONS = {
    UserRole.SUPER_ADMIN: list(Permission),  # All permissions
    
    UserRole.ADMIN: [
        Permission.USER_CREATE, Permission.USER_READ, Permission.USER_UPDATE,
        Permission.VISITOR_CREATE, Permission.VISITOR_READ, Permission.VISITOR_UPDATE,
        Permission.VISITOR_DELETE, Permission.VISITOR_APPROVE,
        Permission.GATE_VERIFY, Permission.GATE_MANUAL_OVERRIDE, Permission.GATE_VIEW_LOGS,
        Permission.WATCHLIST_CREATE, Permission.WATCHLIST_READ, Permission.WATCHLIST_UPDATE,
        Permission.WATCHLIST_DELETE, Permission.WATCHLIST_ALERTS,
        Permission.INCIDENT_CREATE, Permission.INCIDENT_READ, Permission.INCIDENT_UPDATE,
        Permission.INCIDENT_ASSIGN, Permission.INCIDENT_RESOLVE,
        Permission.DASHBOARD_VIEW, Permission.REPORTS_VIEW, Permission.REPORTS_EXPORT,
        Permission.SETTINGS_VIEW, Permission.SETTINGS_UPDATE,
    ],
    
    UserRole.SECURITY_MANAGER: [
        Permission.USER_READ,
        Permission.VISITOR_READ, Permission.VISITOR_APPROVE,
        Permission.GATE_VERIFY, Permission.GATE_MANUAL_OVERRIDE, Permission.GATE_VIEW_LOGS,
        Permission.WATCHLIST_CREATE, Permission.WATCHLIST_READ, Permission.WATCHLIST_UPDATE,
        Permission.WATCHLIST_ALERTS,
        Permission.INCIDENT_CREATE, Permission.INCIDENT_READ, Permission.INCIDENT_UPDATE,
        Permission.INCIDENT_ASSIGN, Permission.INCIDENT_RESOLVE,
        Permission.DASHBOARD_VIEW, Permission.REPORTS_VIEW,
    ],
    
    UserRole.SECURITY_GUARD: [
        Permission.VISITOR_READ,
        Permission.GATE_VERIFY, Permission.GATE_VIEW_LOGS,
        Permission.WATCHLIST_READ, Permission.WATCHLIST_ALERTS,
        Permission.INCIDENT_CREATE, Permission.INCIDENT_READ,
        Permission.DASHBOARD_VIEW,
    ],
    
    UserRole.RESIDENT: [
        Permission.VISITOR_CREATE, Permission.VISITOR_READ, Permission.VISITOR_UPDATE,
        Permission.VISITOR_APPROVE,
        Permission.INCIDENT_CREATE, Permission.INCIDENT_READ,
    ],
    
    UserRole.RECEPTIONIST: [
        Permission.VISITOR_CREATE, Permission.VISITOR_READ, Permission.VISITOR_UPDATE,
        Permission.VISITOR_APPROVE,
        Permission.GATE_VIEW_LOGS,
        Permission.INCIDENT_CREATE, Permission.INCIDENT_READ,
        Permission.DASHBOARD_VIEW,
    ],
}


# ==================== Auth Schemas ====================

class UserSignup(BaseModel):
    """User registration schema"""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 characters")
    full_name: str = Field(..., min_length=2, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    unit_number: Optional[str] = Field(None, description="For residents")
    block: Optional[str] = None
    role: UserRole = UserRole.RESIDENT  # Default role


class UserLogin(BaseModel):
    """User login schema"""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """JWT token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: "UserResponse"


class TokenRefresh(BaseModel):
    """Token refresh request"""
    refresh_token: str


class PasswordChange(BaseModel):
    """Password change request"""
    current_password: str
    new_password: str = Field(..., min_length=8)


class PasswordReset(BaseModel):
    """Password reset request"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation"""
    token: str
    new_password: str = Field(..., min_length=8)


# ==================== User Schemas ====================

class UserCreate(BaseModel):
    """Admin user creation schema"""
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str
    phone: Optional[str] = None
    role: UserRole
    unit_number: Optional[str] = None
    block: Optional[str] = None
    is_active: bool = True


class UserUpdate(BaseModel):
    """User update schema"""
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[UserRole] = None
    unit_number: Optional[str] = None
    block: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    """User response schema"""
    id: int
    email: str
    full_name: str
    phone: Optional[str]
    role: UserRole
    unit_number: Optional[str]
    block: Optional[str]
    is_active: bool
    is_verified: bool
    permissions: List[str]
    created_at: datetime
    last_login: Optional[datetime]
    
    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Paginated user list response"""
    users: List[UserResponse]
    total: int
    page: int
    page_size: int


# Forward reference update
TokenResponse.model_rebuild()
