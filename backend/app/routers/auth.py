"""
Authentication Router - Login, Signup, Token management
"""

from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional, List

from ..database import get_db
from ..models.user import User, UserRole
from ..schemas.auth import (
    UserSignup, UserLogin, TokenResponse, TokenRefresh,
    PasswordChange, PasswordReset, PasswordResetConfirm,
    UserCreate, UserUpdate, UserResponse, UserListResponse,
    Permission, ROLE_PERMISSIONS
)
from ..services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Security scheme
security = HTTPBearer()


# ==================== Dependency Functions ====================

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    token = credentials.credentials
    user = auth_service.get_current_user(db, token)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return user


def require_permissions(*permissions: Permission):
    """Dependency to check user permissions"""
    def permission_checker(current_user: User = Depends(get_current_user)):
        user_permissions = ROLE_PERMISSIONS.get(current_user.role, [])
        
        for perm in permissions:
            if perm not in user_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {perm.value}"
                )
        
        return current_user
    
    return permission_checker


def require_roles(*roles: UserRole):
    """Dependency to check user role"""
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {[r.value for r in roles]}"
            )
        return current_user
    
    return role_checker


# ==================== Helper Functions ====================

def user_to_response(user: User) -> UserResponse:
    """Convert User model to UserResponse"""
    permissions = [p.value for p in ROLE_PERMISSIONS.get(user.role, [])]
    
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        role=user.role,
        unit_number=user.unit_number,
        block=user.block,
        is_active=user.is_active,
        is_verified=user.is_verified,
        permissions=permissions,
        created_at=user.created_at,
        last_login=user.last_login
    )


# ==================== Public Endpoints ====================

@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(signup_data: UserSignup, db: Session = Depends(get_db)):
    """
    Register a new user account
    
    Default role is 'resident'. Only admins can create users with elevated roles.
    """
    # Only allow resident and receptionist signup publicly
    if signup_data.role not in [UserRole.RESIDENT, UserRole.RECEPTIONIST]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot self-register with this role. Contact admin."
        )
    
    user, error = auth_service.register_user(db, signup_data)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    tokens = auth_service.create_tokens(user)
    
    return TokenResponse(
        **tokens,
        user=user_to_response(user)
    )


@router.post("/login", response_model=TokenResponse)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    """
    Login with email and password
    
    Returns JWT access and refresh tokens
    """
    user, error = auth_service.authenticate_user(db, login_data.email, login_data.password)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error,
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    tokens = auth_service.create_tokens(user)
    
    return TokenResponse(
        **tokens,
        user=user_to_response(user)
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(refresh_data: TokenRefresh, db: Session = Depends(get_db)):
    """Refresh access token using refresh token"""
    tokens, error = auth_service.refresh_tokens(db, refresh_data.refresh_token)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error
        )
    
    # Get user for response
    payload = auth_service.decode_token(tokens["access_token"])
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    
    return TokenResponse(
        **tokens,
        user=user_to_response(user)
    )


@router.post("/password-reset")
def request_password_reset(reset_data: PasswordReset, db: Session = Depends(get_db)):
    """
    Request password reset
    
    Sends reset token (in production, would send email)
    """
    token, _ = auth_service.initiate_password_reset(db, reset_data.email)
    
    # Always return success to prevent email enumeration
    return {
        "message": "If the email exists, a reset link has been sent",
        # In development, return token. Remove in production!
        "debug_token": token
    }


@router.post("/password-reset/confirm")
def confirm_password_reset(
    reset_data: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """Confirm password reset with token"""
    success, message = auth_service.confirm_password_reset(
        db, reset_data.token, reset_data.new_password
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    return {"message": message}


# ==================== Protected Endpoints ====================

@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    return user_to_response(current_user)


@router.put("/me", response_model=UserResponse)
def update_current_user_profile(
    update_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user profile (limited fields)"""
    # Users can only update certain fields
    allowed_updates = UserUpdate(
        full_name=update_data.full_name,
        phone=update_data.phone
    )
    
    user, error = auth_service.update_user(db, current_user.id, allowed_updates, current_user.id)
    
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    
    return user_to_response(user)


@router.post("/me/change-password")
def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change current user's password"""
    success, message = auth_service.change_password(
        db,
        current_user.id,
        password_data.current_password,
        password_data.new_password
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    return {"message": message}


@router.get("/permissions")
def get_my_permissions(current_user: User = Depends(get_current_user)):
    """Get current user's permissions"""
    permissions = ROLE_PERMISSIONS.get(current_user.role, [])
    
    return {
        "role": current_user.role.value,
        "permissions": [p.value for p in permissions]
    }


# ==================== Admin Endpoints ====================

@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_data: UserCreate,
    current_user: User = Depends(require_permissions(Permission.USER_CREATE)),
    db: Session = Depends(get_db)
):
    """Create a new user (Admin only)"""
    # Only super_admin can create other admins
    if user_data.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
        if current_user.role != UserRole.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only super admin can create admin accounts"
            )
    
    user, error = auth_service.create_user_admin(db, user_data, current_user.id)
    
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    
    return user_to_response(user)


@router.get("/users", response_model=UserListResponse)
def list_users(
    skip: int = 0,
    limit: int = 50,
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    current_user: User = Depends(require_permissions(Permission.USER_READ)),
    db: Session = Depends(get_db)
):
    """List all users (Admin only)"""
    users, total = auth_service.list_users(
        db, skip=skip, limit=limit,
        role=role, is_active=is_active, search=search
    )
    
    return UserListResponse(
        users=[user_to_response(u) for u in users],
        total=total,
        page=skip // limit + 1,
        page_size=limit
    )


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    current_user: User = Depends(require_permissions(Permission.USER_READ)),
    db: Session = Depends(get_db)
):
    """Get user by ID (Admin only)"""
    user = auth_service.get_user_by_id(db, user_id)
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    return user_to_response(user)


@router.put("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    update_data: UserUpdate,
    current_user: User = Depends(require_permissions(Permission.USER_UPDATE)),
    db: Session = Depends(get_db)
):
    """Update user (Admin only)"""
    # Only super_admin can modify admin roles
    if update_data.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
        if current_user.role != UserRole.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only super admin can set admin roles"
            )
    
    user, error = auth_service.update_user(db, user_id, update_data, current_user.id)
    
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    
    return user_to_response(user)


@router.delete("/users/{user_id}")
def deactivate_user(
    user_id: int,
    current_user: User = Depends(require_permissions(Permission.USER_DELETE)),
    db: Session = Depends(get_db)
):
    """Deactivate user account (Admin only)"""
    target_user = auth_service.get_user_by_id(db, user_id)
    
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Only super_admin can deactivate admins
    if target_user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
        if current_user.role != UserRole.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only super admin can deactivate admin accounts"
            )
    
    success, message = auth_service.deactivate_user(db, user_id, current_user.id)
    
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    
    return {"message": message}


# ==================== Role Information ====================

@router.get("/roles")
def list_roles(current_user: User = Depends(get_current_user)):
    """List all available roles and their permissions"""
    roles_info = {}
    
    for role in UserRole:
        permissions = ROLE_PERMISSIONS.get(role, [])
        roles_info[role.value] = {
            "name": role.value,
            "permissions": [p.value for p in permissions],
            "permission_count": len(permissions)
        }
    
    return {"roles": roles_info}
