from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ==================== Enums ====================

class UserRole(str, Enum):
    ADMIN = "admin"
    SECURITY = "security"
    RESIDENT = "resident"


class VisitorStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    CHECKED_IN = "checked_in"
    CHECKED_OUT = "checked_out"
    EXPIRED = "expired"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class VisitorType(str, Enum):
    GUEST = "guest"
    DELIVERY = "delivery"
    SERVICE = "service"
    CAB = "cab"
    VENDOR = "vendor"
    OTHER = "other"


class EntryStatus(str, Enum):
    ALLOWED = "allowed"
    DENIED = "denied"
    MANUAL_VERIFICATION = "manual_verification"
    WATCHLIST_ALERT = "watchlist_alert"


class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class WatchlistCategory(str, Enum):
    BANNED = "banned"
    SUSPICIOUS = "suspicious"
    TRESPASSER = "trespasser"
    THEFT = "theft"
    HARASSMENT = "harassment"
    FRAUD = "fraud"
    VIOLENCE = "violence"
    OTHER = "other"


class IncidentCategory(str, Enum):
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


class IncidentSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    PENDING_REVIEW = "pending_review"
    RESOLVED = "resolved"
    CLOSED = "closed"
    ESCALATED = "escalated"


# ==================== User Schemas ====================

class UserBase(BaseModel):
    email: EmailStr
    phone: Optional[str] = None
    full_name: str
    role: UserRole = UserRole.RESIDENT
    unit_number: Optional[str] = None
    block: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    unit_number: Optional[str] = None
    block: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: int
    is_active: bool
    is_verified: bool
    face_image_url: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


# ==================== Visitor Schemas ====================

class VisitorBase(BaseModel):
    full_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    visitor_type: VisitorType = VisitorType.GUEST
    purpose: Optional[str] = None
    visiting_unit: str
    visiting_block: Optional[str] = None
    vehicle_number: Optional[str] = None
    vehicle_type: Optional[str] = None
    notes: Optional[str] = None


class VisitorCreate(VisitorBase):
    valid_from: datetime
    valid_until: datetime
    face_image_base64: Optional[str] = None  # Base64 encoded image


class VisitorUpdate(BaseModel):
    status: Optional[VisitorStatus] = None
    valid_until: Optional[datetime] = None
    notes: Optional[str] = None


class VisitorResponse(VisitorBase):
    id: int
    approved_by: int
    approval_code: str
    valid_from: datetime
    valid_until: datetime
    status: VisitorStatus
    face_image_url: Optional[str] = None
    created_at: datetime
    checked_in_at: Optional[datetime] = None
    checked_out_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class VisitorListResponse(BaseModel):
    visitors: List[VisitorResponse]
    total: int
    page: int
    page_size: int


# ==================== Gate Verification Schemas ====================

class GateVerificationRequest(BaseModel):
    face_image_base64: str  # Base64 encoded captured image
    gate_id: str = "MAIN_GATE"
    approval_code: Optional[str] = None  # Optional manual code entry


class GateVerificationResponse(BaseModel):
    status: EntryStatus
    message: str
    visitor_name: Optional[str] = None
    visitor_id: Optional[int] = None
    confidence: Optional[float] = None
    denial_reason: Optional[str] = None
    entry_log_id: int
    watchlist_alert: Optional[dict] = None
    requires_manual_check: bool = False


class EntryLogResponse(BaseModel):
    id: int
    entry_type: str
    gate_id: str
    visitor_id: Optional[int] = None
    person_name: Optional[str] = None
    verification_method: Optional[str] = None
    face_match_confidence: Optional[float] = None
    status: EntryStatus
    denial_reason: Optional[str] = None
    captured_image_url: Optional[str] = None
    is_flagged: bool
    timestamp: datetime
    
    class Config:
        from_attributes = True


class EntryLogListResponse(BaseModel):
    logs: List[EntryLogResponse]
    total: int
    page: int
    page_size: int


# ==================== Watchlist Schemas ====================

class WatchlistPersonBase(BaseModel):
    full_name: str
    alias: Optional[str] = None
    phone: Optional[str] = None
    category: WatchlistCategory
    severity: AlertSeverity = AlertSeverity.MEDIUM
    reason: str
    last_known_address: Optional[str] = None
    physical_description: Optional[str] = None


class WatchlistPersonCreate(WatchlistPersonBase):
    face_image_base64: Optional[str] = None
    expires_at: Optional[datetime] = None


class WatchlistPersonUpdate(BaseModel):
    category: Optional[WatchlistCategory] = None
    severity: Optional[AlertSeverity] = None
    reason: Optional[str] = None
    is_active: Optional[bool] = None
    expires_at: Optional[datetime] = None


class WatchlistPersonResponse(WatchlistPersonBase):
    id: int
    face_image_url: Optional[str] = None
    is_active: bool
    added_by: Optional[int] = None
    created_at: datetime
    expires_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class WatchlistAlertResponse(BaseModel):
    id: int
    watchlist_person_id: int
    watchlist_person_name: Optional[str] = None
    gate_id: Optional[str] = None
    confidence_score: float
    severity: AlertSeverity
    captured_image_url: Optional[str] = None
    is_acknowledged: bool
    is_resolved: bool
    is_false_positive: bool
    created_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class WatchlistAlertAcknowledge(BaseModel):
    notes: Optional[str] = None


class WatchlistAlertResolve(BaseModel):
    resolution_notes: str
    is_false_positive: bool = False


# ==================== Incident Schemas ====================

class IncidentBase(BaseModel):
    title: str
    description: str
    category: IncidentCategory
    severity: IncidentSeverity = IncidentSeverity.MEDIUM
    location: Optional[str] = None
    incident_time: Optional[datetime] = None


class IncidentCreate(IncidentBase):
    related_visitor_id: Optional[int] = None
    related_entry_log_id: Optional[int] = None
    evidence_base64: Optional[List[str]] = None  # List of base64 encoded images


class IncidentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[IncidentCategory] = None
    severity: Optional[IncidentSeverity] = None
    status: Optional[IncidentStatus] = None
    assigned_to: Optional[int] = None
    resolution_notes: Optional[str] = None


class IncidentResponse(IncidentBase):
    id: int
    incident_number: str
    status: IncidentStatus
    reported_by: int
    assigned_to: Optional[int] = None
    evidence_urls: Optional[str] = None
    resolution_notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class IncidentTimelineResponse(BaseModel):
    id: int
    incident_id: int
    event_type: str
    description: str
    created_by: Optional[int] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class IncidentDetailResponse(IncidentResponse):
    timeline: List[IncidentTimelineResponse] = []
    reporter_name: Optional[str] = None
    assignee_name: Optional[str] = None


class IncidentListResponse(BaseModel):
    incidents: List[IncidentResponse]
    total: int
    page: int
    page_size: int


# ==================== Dashboard Schemas ====================

class DashboardStats(BaseModel):
    total_visitors_today: int
    pending_approvals: int
    active_visitors: int
    total_entries_today: int
    denied_entries_today: int
    active_watchlist_alerts: int
    open_incidents: int
    critical_incidents: int


class DashboardRecentActivity(BaseModel):
    recent_entries: List[EntryLogResponse]
    recent_incidents: List[IncidentResponse]
    active_alerts: List[WatchlistAlertResponse]


class DashboardResponse(BaseModel):
    stats: DashboardStats
    recent_activity: DashboardRecentActivity
