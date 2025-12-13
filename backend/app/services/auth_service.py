"""
Authentication Service - JWT tokens, password hashing, RBAC
"""

import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, List
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import JWTError, jwt

from ..models.user import User, UserRole
from ..schemas.auth import (
    UserSignup, UserCreate, UserUpdate,
    Permission, ROLE_PERMISSIONS
)
from ..config import settings

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Settings
SECRET_KEY = getattr(settings, 'SECRET_KEY', 'your-super-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


class AuthService:
    """Authentication and Authorization Service"""
    
    # ==================== Password Handling ====================
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    # ==================== Token Handling ====================
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
        to_encode.update({
            "exp": expire,
            "type": "access"
        })
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    @staticmethod
    def create_refresh_token(data: dict) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({
            "exp": expire,
            "type": "refresh"
        })
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    @staticmethod
    def decode_token(token: str) -> Optional[dict]:
        """Decode and validate JWT token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError as e:
            logger.warning(f"Token decode failed: {e}")
            return None
    
    @staticmethod
    def generate_reset_token() -> str:
        """Generate password reset token"""
        return secrets.token_urlsafe(32)
    
    # ==================== User Authentication ====================
    
    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> Tuple[Optional[User], str]:
        """
        Authenticate user with email and password
        
        Returns:
            Tuple of (User or None, error_message)
        """
        user = db.query(User).filter(User.email == email.lower()).first()
        
        if not user:
            return None, "Invalid email or password"
        
        # Check if account is locked
        if user.locked_until and user.locked_until > datetime.now(timezone.utc):
            remaining = (user.locked_until - datetime.now(timezone.utc)).seconds // 60
            return None, f"Account locked. Try again in {remaining} minutes"
        
        # Check if account is active
        if not user.is_active:
            return None, "Account is deactivated"
        
        # Verify password
        if not AuthService.verify_password(password, user.hashed_password):
            # Increment failed attempts
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            
            # Lock account after 5 failed attempts
            if user.failed_login_attempts >= 5:
                user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)
                db.commit()
                return None, "Account locked due to too many failed attempts"
            
            db.commit()
            return None, "Invalid email or password"
        
        # Reset failed attempts on successful login
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login = datetime.now(timezone.utc)
        db.commit()
        
        return user, ""
    
    @staticmethod
    def create_tokens(user: User) -> dict:
        """Create access and refresh tokens for user"""
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value
        }
        
        access_token = AuthService.create_access_token(token_data)
        refresh_token = AuthService.create_refresh_token(token_data)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    
    @staticmethod
    def refresh_tokens(db: Session, refresh_token: str) -> Tuple[Optional[dict], str]:
        """Refresh access token using refresh token"""
        payload = AuthService.decode_token(refresh_token)
        
        if not payload:
            return None, "Invalid refresh token"
        
        if payload.get("type") != "refresh":
            return None, "Invalid token type"
        
        user_id = payload.get("sub")
        user = db.query(User).filter(User.id == int(user_id)).first()
        
        if not user or not user.is_active:
            return None, "User not found or inactive"
        
        return AuthService.create_tokens(user), ""
    
    # ==================== User Registration ====================
    
    @staticmethod
    def register_user(db: Session, signup_data: UserSignup) -> Tuple[Optional[User], str]:
        """
        Register a new user
        
        Returns:
            Tuple of (User or None, error_message)
        """
        # Check if email already exists
        existing = db.query(User).filter(User.email == signup_data.email.lower()).first()
        if existing:
            return None, "Email already registered"
        
        # Check phone if provided
        if signup_data.phone:
            existing_phone = db.query(User).filter(User.phone == signup_data.phone).first()
            if existing_phone:
                return None, "Phone number already registered"
        
        try:
            user = User(
                email=signup_data.email.lower(),
                hashed_password=AuthService.hash_password(signup_data.password),
                full_name=signup_data.full_name,
                phone=signup_data.phone,
                role=signup_data.role,
                unit_number=signup_data.unit_number,
                block=signup_data.block,
                is_active=True,
                is_verified=False,  # Require email verification in production
                password_changed_at=datetime.now(timezone.utc)
            )
            
            db.add(user)
            db.commit()
            db.refresh(user)
            
            logger.info(f"New user registered: {user.email} with role {user.role.value}")
            return user, ""
            
        except Exception as e:
            db.rollback()
            logger.error(f"Registration failed: {e}")
            return None, f"Registration failed: {str(e)}"
    
    @staticmethod
    def create_user_admin(db: Session, user_data: UserCreate, created_by: int) -> Tuple[Optional[User], str]:
        """Admin creates a new user with specific role"""
        # Check if email already exists
        existing = db.query(User).filter(User.email == user_data.email.lower()).first()
        if existing:
            return None, "Email already registered"
        
        try:
            user = User(
                email=user_data.email.lower(),
                hashed_password=AuthService.hash_password(user_data.password),
                full_name=user_data.full_name,
                phone=user_data.phone,
                role=user_data.role,
                unit_number=user_data.unit_number,
                block=user_data.block,
                is_active=user_data.is_active,
                is_verified=True,  # Admin-created users are pre-verified
                password_changed_at=datetime.now(timezone.utc)
            )
            
            db.add(user)
            db.commit()
            db.refresh(user)
            
            logger.info(f"User created by admin {created_by}: {user.email} with role {user.role.value}")
            return user, ""
            
        except Exception as e:
            db.rollback()
            logger.error(f"User creation failed: {e}")
            return None, f"User creation failed: {str(e)}"
    
    # ==================== Password Management ====================
    
    @staticmethod
    def change_password(
        db: Session,
        user_id: int,
        current_password: str,
        new_password: str
    ) -> Tuple[bool, str]:
        """Change user password"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False, "User not found"
        
        if not AuthService.verify_password(current_password, user.hashed_password):
            return False, "Current password is incorrect"
        
        user.hashed_password = AuthService.hash_password(new_password)
        user.password_changed_at = datetime.now(timezone.utc)
        db.commit()
        
        return True, "Password changed successfully"
    
    @staticmethod
    def initiate_password_reset(db: Session, email: str) -> Tuple[Optional[str], str]:
        """Initiate password reset - returns reset token"""
        user = db.query(User).filter(User.email == email.lower()).first()
        if not user:
            # Don't reveal if email exists
            return None, ""
        
        reset_token = AuthService.generate_reset_token()
        user.reset_token = reset_token
        user.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        db.commit()
        
        # In production, send email with reset link
        return reset_token, ""
    
    @staticmethod
    def confirm_password_reset(
        db: Session,
        token: str,
        new_password: str
    ) -> Tuple[bool, str]:
        """Confirm password reset with token"""
        user = db.query(User).filter(User.reset_token == token).first()
        
        if not user:
            return False, "Invalid reset token"
        
        if user.reset_token_expires < datetime.now(timezone.utc):
            return False, "Reset token has expired"
        
        user.hashed_password = AuthService.hash_password(new_password)
        user.reset_token = None
        user.reset_token_expires = None
        user.password_changed_at = datetime.now(timezone.utc)
        db.commit()
        
        return True, "Password reset successfully"
    
    # ==================== RBAC - Permissions ====================
    
    @staticmethod
    def get_user_permissions(role: UserRole) -> List[Permission]:
        """Get all permissions for a role"""
        return ROLE_PERMISSIONS.get(role, [])
    
    @staticmethod
    def has_permission(role: UserRole, permission: Permission) -> bool:
        """Check if role has specific permission"""
        permissions = ROLE_PERMISSIONS.get(role, [])
        return permission in permissions
    
    @staticmethod
    def get_current_user(db: Session, token: str) -> Optional[User]:
        """Get current user from token"""
        payload = AuthService.decode_token(token)
        if not payload:
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user or not user.is_active:
            return None
        
        return user
    
    # ==================== User Management ====================
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Get user by email"""
        return db.query(User).filter(User.email == email.lower()).first()
    
    @staticmethod
    def list_users(
        db: Session,
        skip: int = 0,
        limit: int = 50,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None
    ) -> Tuple[List[User], int]:
        """List users with filters"""
        query = db.query(User)
        
        if role:
            query = query.filter(User.role == role)
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (User.full_name.ilike(search_term)) |
                (User.email.ilike(search_term)) |
                (User.phone.ilike(search_term))
            )
        
        total = query.count()
        users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
        
        return users, total
    
    @staticmethod
    def update_user(
        db: Session,
        user_id: int,
        update_data: UserUpdate,
        updated_by: int
    ) -> Tuple[Optional[User], str]:
        """Update user details"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None, "User not found"
        
        update_dict = update_data.model_dump(exclude_unset=True)
        
        for field, value in update_dict.items():
            setattr(user, field, value)
        
        db.commit()
        db.refresh(user)
        
        logger.info(f"User {user_id} updated by {updated_by}")
        return user, ""
    
    @staticmethod
    def deactivate_user(db: Session, user_id: int, deactivated_by: int) -> Tuple[bool, str]:
        """Deactivate a user account"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False, "User not found"
        
        if user.id == deactivated_by:
            return False, "Cannot deactivate your own account"
        
        user.is_active = False
        db.commit()
        
        logger.info(f"User {user_id} deactivated by {deactivated_by}")
        return True, "User deactivated"


# Create singleton instance
auth_service = AuthService()
