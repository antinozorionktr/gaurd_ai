import enum
from sqlalchemy import Column, Integer, String, DateTime, Enum, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class VisitorStatus(str, enum.Enum):
    PENDING = "pending"      # Awaiting approval
    APPROVED = "approved"    # Pre-approved, can enter
    CHECKED_IN = "checked_in"  # Currently inside
    CHECKED_OUT = "checked_out"  # Left the premises
    EXPIRED = "expired"      # Approval time expired
    REJECTED = "rejected"    # Denied entry
    CANCELLED = "cancelled"  # Cancelled by resident


class VisitorType(str, enum.Enum):
    GUEST = "guest"
    DELIVERY = "delivery"
    SERVICE = "service"      # Plumber, electrician, etc.
    CAB = "cab"
    VENDOR = "vendor"
    OTHER = "other"


class Visitor(Base):
    """
    Pre-approved visitors to the community
    """
    __tablename__ = "visitors"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Visitor Information
    full_name = Column(String(255), nullable=False)
    phone = Column(String(20), index=True)
    email = Column(String(255))
    visitor_type = Column(Enum(VisitorType), default=VisitorType.GUEST)
    
    # Purpose & Destination
    purpose = Column(String(255))
    visiting_unit = Column(String(50))  # Unit they're visiting
    visiting_block = Column(String(50))
    
    # Approval Details
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    approval_code = Column(String(20), unique=True, index=True)  # OTP or unique code
    
    # Time Window
    valid_from = Column(DateTime(timezone=True), nullable=False)
    valid_until = Column(DateTime(timezone=True), nullable=False)
    
    # Face Recognition
    face_id = Column(String(255))  # AWS Rekognition Face ID
    face_image_url = Column(String(500))  # S3 URL for visitor's photo
    
    # Vehicle (optional)
    vehicle_number = Column(String(20))
    vehicle_type = Column(String(50))
    
    # Status
    status = Column(Enum(VisitorStatus), default=VisitorStatus.APPROVED)
    
    # Additional Notes
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    checked_in_at = Column(DateTime(timezone=True))
    checked_out_at = Column(DateTime(timezone=True))
    
    # Relationships
    approved_by_user = relationship("User", back_populates="approved_visitors")
    entry_logs = relationship("EntryLog", back_populates="visitor")
    
    def __repr__(self):
        return f"<Visitor {self.full_name} - {self.status.value}>"
    
    @property
    def is_valid(self):
        """Check if visitor approval is currently valid"""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        return (
            self.status == VisitorStatus.APPROVED and
            self.valid_from <= now <= self.valid_until
        )
