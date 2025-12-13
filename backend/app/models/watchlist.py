import enum
from sqlalchemy import Column, Integer, String, DateTime, Enum, Text, Boolean, Float, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class AlertSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class WatchlistCategory(str, enum.Enum):
    BANNED = "banned"           # Permanently banned
    SUSPICIOUS = "suspicious"   # Suspicious activity
    TRESPASSER = "trespasser"   # Previous trespassing
    THEFT = "theft"             # Theft related
    HARASSMENT = "harassment"   # Harassment cases
    FRAUD = "fraud"             # Fraud/scam
    VIOLENCE = "violence"       # Violence related
    OTHER = "other"


class WatchlistPerson(Base):
    """
    Flagged individuals to watch for at entry points
    """
    __tablename__ = "watchlist_persons"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Person Information
    full_name = Column(String(255), nullable=False)
    alias = Column(String(255))  # Known aliases
    phone = Column(String(20))
    
    # Face Recognition
    face_id = Column(String(255))  # AWS Rekognition Face ID
    face_image_url = Column(String(500))  # S3 URL
    
    # Watchlist Details
    category = Column(Enum(WatchlistCategory), nullable=False)
    severity = Column(Enum(AlertSeverity), default=AlertSeverity.MEDIUM)
    reason = Column(Text, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Additional Details
    last_known_address = Column(String(500))
    physical_description = Column(Text)
    
    # Added By
    added_by = Column(Integer, ForeignKey("users.id"))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    expires_at = Column(DateTime(timezone=True))  # Optional expiry
    
    # Relationships
    added_by_user = relationship("User")
    alerts = relationship("WatchlistAlert", back_populates="watchlist_person")
    
    def __repr__(self):
        return f"<WatchlistPerson {self.full_name} - {self.category.value}>"


class WatchlistAlert(Base):
    """
    Alerts generated when watchlist person is detected
    """
    __tablename__ = "watchlist_alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Watchlist Reference
    watchlist_person_id = Column(Integer, ForeignKey("watchlist_persons.id"), nullable=False)
    
    # Detection Details
    entry_log_id = Column(Integer, ForeignKey("entry_logs.id"))
    gate_id = Column(String(50))
    confidence_score = Column(Float, nullable=False)
    
    # Captured Evidence
    captured_image_url = Column(String(500))
    
    # Alert Status
    severity = Column(Enum(AlertSeverity), nullable=False)
    is_acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(Integer, ForeignKey("users.id"))
    acknowledged_at = Column(DateTime(timezone=True))
    
    # Resolution
    is_resolved = Column(Boolean, default=False)
    resolution_notes = Column(Text)
    resolved_by = Column(Integer, ForeignKey("users.id"))
    resolved_at = Column(DateTime(timezone=True))
    
    # Was it a false positive?
    is_false_positive = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    watchlist_person = relationship("WatchlistPerson", back_populates="alerts")
    acknowledged_by_user = relationship("User", foreign_keys=[acknowledged_by])
    resolved_by_user = relationship("User", foreign_keys=[resolved_by])
    
    def __repr__(self):
        return f"<WatchlistAlert {self.id} - {self.severity.value}>"
