"""
Authentication Schemas - Pydantic models for auth endpoints
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from enum import Enum


class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    SECURITY_MANAGER = "security_manager"
    SECURITY_GUARD = "security_guard"
    RESIDENT = "resident"
    RECEPTIONIST = "receptionist"


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
    UserRole.SUPER_ADMIN: list(Permission),  # All permissions
    
    UserRole.ADMIN: [
        Permission.DASHBOARD_VIEW,
        Permission.DASHBOARD_ANALYTICS,
        Permission.VISITOR_CREATE,
        Permission.VISITOR_READ,
        Permission.VISITOR_UPDATE,
        Permission.VISITOR_DELETE,
        Permission.VISITOR_APPROVE,
        Permission.GATE_VERIFY,
        Permission.GATE_MANUAL_OVERRIDE,
        Permission.GATE_LOGS_VIEW,
        Permission.WATCHLIST_READ,
        Permission.WATCHLIST_CREATE,
        Permission.WATCHLIST_UPDATE,
        Permission.WATCHLIST_DELETE,
        Permission.WATCHLIST_ALERTS,
        Permission.INCIDENT_CREATE,
        Permission.INCIDENT_READ,
        Permission.INCIDENT_UPDATE,
        Permission.INCIDENT_ASSIGN,
        Permission.USER_READ,
        Permission.USER_UPDATE,
    ],
    
    UserRole.SECURITY_MANAGER: [
        Permission.DASHBOARD_VIEW,
        Permission.DASHBOARD_ANALYTICS,
        Permission.VISITOR_READ,
        Permission.VISITOR_APPROVE,
        Permission.GATE_VERIFY,
        Permission.GATE_MANUAL_OVERRIDE,
        Permission.GATE_LOGS_VIEW,
        Permission.WATCHLIST_READ,
        Permission.WATCHLIST_CREATE,
        Permission.WATCHLIST_UPDATE,
        Permission.WATCHLIST_ALERTS,
        Permission.INCIDENT_CREATE,
        Permission.INCIDENT_READ,
        Permission.INCIDENT_UPDATE,
        Permission.INCIDENT_ASSIGN,
    ],
    
    UserRole.SECURITY_GUARD: [
        Permission.DASHBOARD_VIEW,
        Permission.VISITOR_READ,
        Permission.GATE_VERIFY,
        Permission.GATE_LOGS_VIEW,
        Permission.WATCHLIST_READ,
        Permission.WATCHLIST_ALERTS,
        Permission.INCIDENT_CREATE,
        Permission.INCIDENT_READ,
    ],
    
    UserRole.RESIDENT: [
        Permission.DASHBOARD_VIEW,
        Permission.VISITOR_CREATE,  # Can pre-approve their own visitors
        Permission.VISITOR_READ,    # Can view their own visitors only
        Permission.INCIDENT_CREATE, # Can report incidents
        Permission.INCIDENT_READ,   # Can view their own incidents
    ],
    
    UserRole.RECEPTIONIST: [
        Permission.DASHBOARD_VIEW,
        Permission.VISITOR_CREATE,
        Permission.VISITOR_READ,
        Permission.VISITOR_UPDATE,
        Permission.VISITOR_APPROVE,
        Permission.GATE_VERIFY,
        Permission.GATE_LOGS_VIEW,
        Permission.INCIDENT_CREATE,
        Permission.INCIDENT_READ,
    ],
}


# ==================== Request Schemas ====================

class UserSignup(BaseModel):
    """User self-registration"""
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2)
    phone: Optional[str] = None
    role: UserRole = UserRole.RESIDENT
    unit_number: Optional[str] = None  # Required for residents
    block: Optional[str] = None


class UserLogin(BaseModel):
    """User login request"""
    email: EmailStr
    password: str


class UserCreate(BaseModel):
    """Admin creates user"""
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2)
    phone: Optional[str] = None
    role: UserRole
    unit_number: Optional[str] = None
    block: Optional[str] = None
    is_active: bool = True


class UserUpdate(BaseModel):
    """Update user details"""
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[UserRole] = None
    unit_number: Optional[str] = None
    block: Optional[str] = None
    is_active: Optional[bool] = None


class PasswordChange(BaseModel):
    """Change password request"""
    current_password: str
    new_password: str = Field(..., min_length=8)


class PasswordReset(BaseModel):
    """Request password reset"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Confirm password reset"""
    token: str
    new_password: str = Field(..., min_length=8)


class TokenRefresh(BaseModel):
    """Refresh token request"""
    refresh_token: str


# ==================== Response Schemas ====================

class UserResponse(BaseModel):
    """User response (public info)"""
    id: int
    email: str
    full_name: str
    phone: Optional[str] = None
    role: UserRole
    unit_number: Optional[str] = None  # Include for residents
    block: Optional[str] = None        # Include for residents
    is_active: bool
    is_verified: bool
    permissions: List[str]
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Token response with user info"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class UserListResponse(BaseModel):
    """Paginated user list"""
    users: List[UserResponse]
    total: int
    page: int
    page_size: int