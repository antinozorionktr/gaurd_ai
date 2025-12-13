import enum
from sqlalchemy import Column, Integer, String, DateTime, Enum, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class UserRole(str, enum.Enum):
    """User roles for RBAC"""
    SUPER_ADMIN = "super_admin"      # Full system access
    ADMIN = "admin"                   # Manage users, settings, view all
    SECURITY_MANAGER = "security_manager"  # Manage security staff, view reports
    SECURITY_GUARD = "security_guard"      # Gate operations, basic incident reporting
    RESIDENT = "resident"             # Pre-approve visitors, view own data
    RECEPTIONIST = "receptionist"     # Visitor management, no security features


class User(Base):
    """
    Users of the system with Role-Based Access Control
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(20), unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    
    # Profile Information
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.RESIDENT, nullable=False)
    
    # For residents
    unit_number = Column(String(50))  # e.g., "A-101", "B-205"
    block = Column(String(50))  # e.g., "Block A", "Tower 1"
    
    # Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # Face Recognition (DeepFace)
    face_id = Column(String(255))  # DeepFace Face ID
    face_registered = Column(Boolean, default=False)
    
    # Security
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True))
    password_changed_at = Column(DateTime(timezone=True))
    
    # Tokens
    refresh_token = Column(Text)  # Hashed refresh token
    reset_token = Column(String(255))
    reset_token_expires = Column(DateTime(timezone=True))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))
    
    # Relationships
    approved_visitors = relationship("Visitor", back_populates="approved_by_user")
    reported_incidents = relationship("Incident", back_populates="reported_by_user", foreign_keys="Incident.reported_by")
    assigned_incidents = relationship("Incident", back_populates="assigned_to_user", foreign_keys="Incident.assigned_to")
    
    def __repr__(self):
        return f"<User {self.email} - {self.role.value}>"
