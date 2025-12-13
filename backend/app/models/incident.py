import enum
from sqlalchemy import Column, Integer, String, DateTime, Enum, Text, Boolean, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class IncidentCategory(str, enum.Enum):
    UNAUTHORIZED_ENTRY = "unauthorized_entry"
    THEFT = "theft"
    VANDALISM = "vandalism"
    HARASSMENT = "harassment"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    PARKING_VIOLATION = "parking_violation"
    NOISE_COMPLAINT = "noise_complaint"
    FIRE_SAFETY = "fire_safety"
    MEDICAL_EMERGENCY = "medical_emergency"
    VISITOR_ISSUE = "visitor_issue"
    EQUIPMENT_FAILURE = "equipment_failure"
    OTHER = "other"


class IncidentSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    PENDING_REVIEW = "pending_review"
    RESOLVED = "resolved"
    CLOSED = "closed"
    ESCALATED = "escalated"


class Incident(Base):
    """
    Security incidents reported and tracked
    """
    __tablename__ = "incidents"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Incident Reference
    incident_number = Column(String(50), unique=True, index=True)  # e.g., INC-2024-001
    
    # Incident Details
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(Enum(IncidentCategory), nullable=False)
    severity = Column(Enum(IncidentSeverity), default=IncidentSeverity.MEDIUM)
    
    # Location
    location = Column(String(255))  # e.g., "Block A - Ground Floor"
    location_coordinates = Column(String(100))  # Optional GPS coordinates
    
    # Status
    status = Column(Enum(IncidentStatus), default=IncidentStatus.OPEN)
    
    # People Involved
    reported_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_to = Column(Integer, ForeignKey("users.id"))
    
    # Related Records
    related_visitor_id = Column(Integer, ForeignKey("visitors.id"))
    related_entry_log_id = Column(Integer, ForeignKey("entry_logs.id"))
    related_watchlist_alert_id = Column(Integer, ForeignKey("watchlist_alerts.id"))
    
    # Evidence (stored as JSON array of URLs)
    evidence_urls = Column(Text)  # JSON array of S3 URLs
    
    # Resolution
    resolution_notes = Column(Text)
    resolved_at = Column(DateTime(timezone=True))
    resolved_by = Column(Integer, ForeignKey("users.id"))
    
    # Priority Score (can be computed)
    priority_score = Column(Float)
    
    # Timestamps
    incident_time = Column(DateTime(timezone=True))  # When incident occurred
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    reported_by_user = relationship("User", back_populates="reported_incidents", foreign_keys=[reported_by])
    assigned_to_user = relationship("User", back_populates="assigned_incidents", foreign_keys=[assigned_to])
    resolved_by_user = relationship("User", foreign_keys=[resolved_by])
    related_visitor = relationship("Visitor")
    related_entry_log = relationship("EntryLog")
    related_watchlist_alert = relationship("WatchlistAlert")
    timeline_events = relationship("IncidentTimeline", back_populates="incident", order_by="IncidentTimeline.created_at")
    
    def __repr__(self):
        return f"<Incident {self.incident_number} - {self.status.value}>"


class IncidentTimeline(Base):
    """
    Timeline of events/updates for an incident
    """
    __tablename__ = "incident_timeline"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Incident Reference
    incident_id = Column(Integer, ForeignKey("incidents.id"), nullable=False)
    
    # Event Details
    event_type = Column(String(50))  # e.g., "status_change", "comment", "evidence_added"
    description = Column(Text, nullable=False)
    
    # Who made this update
    created_by = Column(Integer, ForeignKey("users.id"))
    
    # Additional Data (JSON)
    extra_data = Column(Text)  # JSON for additional event data
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    incident = relationship("Incident", back_populates="timeline_events")
    created_by_user = relationship("User")
    
    def __repr__(self):
        return f"<IncidentTimeline {self.id} - {self.event_type}>"
