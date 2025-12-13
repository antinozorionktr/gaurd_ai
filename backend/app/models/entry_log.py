import enum
from sqlalchemy import Column, Integer, String, DateTime, Enum, Float, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class EntryStatus(str, enum.Enum):
    ALLOWED = "allowed"
    DENIED = "denied"
    MANUAL_VERIFICATION = "manual_verification"
    WATCHLIST_ALERT = "watchlist_alert"


class EntryType(str, enum.Enum):
    ENTRY = "entry"
    EXIT = "exit"


class VerificationMethod(str, enum.Enum):
    FACE_RECOGNITION = "face_recognition"
    APPROVAL_CODE = "approval_code"
    MANUAL = "manual"
    RESIDENT_FACE = "resident_face"


class EntryLog(Base):
    """
    Log of all gate entry/exit attempts
    """
    __tablename__ = "entry_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Entry Details
    entry_type = Column(Enum(EntryType), default=EntryType.ENTRY)
    gate_id = Column(String(50), default="MAIN_GATE")  # For multi-gate support
    
    # Person Identification
    visitor_id = Column(Integer, ForeignKey("visitors.id"), nullable=True)
    resident_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    person_name = Column(String(255))  # Name of person (visitor or resident)
    
    # Verification Details
    verification_method = Column(Enum(VerificationMethod))
    face_match_confidence = Column(Float)  # Confidence score from face recognition
    approval_code_used = Column(String(20))
    
    # Captured Image
    captured_image_url = Column(String(500))  # S3 URL of captured image at gate
    
    # Result
    status = Column(Enum(EntryStatus), nullable=False)
    denial_reason = Column(String(255))
    
    # Security Personnel
    verified_by = Column(Integer, ForeignKey("users.id"))  # Security who verified
    
    # Watchlist Match (if any)
    watchlist_match_id = Column(Integer, ForeignKey("watchlist_persons.id"))
    watchlist_confidence = Column(Float)
    
    # Additional Info
    notes = Column(Text)
    is_flagged = Column(Boolean, default=False)  # Manual flag by security
    
    # Timestamps
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    visitor = relationship("Visitor", back_populates="entry_logs")
    verified_by_user = relationship("User", foreign_keys=[verified_by])
    watchlist_match = relationship("WatchlistPerson")
    
    def __repr__(self):
        return f"<EntryLog {self.id} - {self.status.value} at {self.timestamp}>"
