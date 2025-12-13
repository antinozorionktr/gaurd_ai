from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..schemas.schemas import (
    IncidentCreate, IncidentUpdate, IncidentResponse,
    IncidentListResponse, IncidentDetailResponse,
    IncidentStatus, IncidentSeverity, IncidentCategory
)
from ..services.incident_service import incident_service

router = APIRouter(prefix="/incidents", tags=["Incidents"])


@router.post("/", response_model=IncidentResponse)
def create_incident(
    incident_data: IncidentCreate,
    reported_by: int = Query(..., description="ID of user reporting the incident"),
    db: Session = Depends(get_db)
):
    """Create a new incident"""
    incident, details = incident_service.create_incident(db, incident_data, reported_by)
    
    if not incident:
        raise HTTPException(status_code=400, detail=details.get("error", "Failed to create incident"))
    
    return incident


@router.get("/", response_model=IncidentListResponse)
def list_incidents(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[IncidentStatus] = None,
    severity: Optional[IncidentSeverity] = None,
    category: Optional[IncidentCategory] = None,
    reported_by: Optional[int] = None,
    assigned_to: Optional[int] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get incidents with filters"""
    incidents, total = incident_service.get_incidents(
        db, skip, limit, status, severity,
        category.value if category else None,
        reported_by, assigned_to, search
    )
    
    return IncidentListResponse(
        incidents=incidents,
        total=total,
        page=skip // limit + 1,
        page_size=limit
    )


@router.get("/open")
def get_open_incidents(db: Session = Depends(get_db)):
    """Get all open incidents (Open, In Progress, Escalated)"""
    incidents = incident_service.get_open_incidents(db)
    return {"incidents": incidents, "count": len(incidents)}


@router.get("/critical")
def get_critical_incidents(db: Session = Depends(get_db)):
    """Get critical open incidents"""
    incidents = incident_service.get_critical_incidents(db)
    return {"incidents": incidents, "count": len(incidents)}


@router.get("/stats")
def get_incident_stats(db: Session = Depends(get_db)):
    """Get incident statistics"""
    return incident_service.get_incident_stats(db)


@router.get("/number/{incident_number}", response_model=IncidentDetailResponse)
def get_incident_by_number(incident_number: str, db: Session = Depends(get_db)):
    """Get incident by incident number"""
    incident = incident_service.get_incident_by_number(db, incident_number)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    # Get timeline
    timeline = incident.timeline_events
    
    # Get reporter and assignee names
    reporter_name = incident.reported_by_user.full_name if incident.reported_by_user else None
    assignee_name = incident.assigned_to_user.full_name if incident.assigned_to_user else None
    
    return IncidentDetailResponse(
        id=incident.id,
        incident_number=incident.incident_number,
        title=incident.title,
        description=incident.description,
        category=incident.category,
        severity=incident.severity,
        status=incident.status,
        location=incident.location,
        incident_time=incident.incident_time,
        reported_by=incident.reported_by,
        assigned_to=incident.assigned_to,
        evidence_urls=incident.evidence_urls,
        resolution_notes=incident.resolution_notes,
        created_at=incident.created_at,
        updated_at=incident.updated_at,
        resolved_at=incident.resolved_at,
        timeline=timeline,
        reporter_name=reporter_name,
        assignee_name=assignee_name
    )


@router.get("/{incident_id}", response_model=IncidentDetailResponse)
def get_incident(incident_id: int, db: Session = Depends(get_db)):
    """Get incident by ID with full details"""
    incident = incident_service.get_incident(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    # Get timeline
    timeline = incident.timeline_events
    
    # Get reporter and assignee names
    reporter_name = incident.reported_by_user.full_name if incident.reported_by_user else None
    assignee_name = incident.assigned_to_user.full_name if incident.assigned_to_user else None
    
    return IncidentDetailResponse(
        id=incident.id,
        incident_number=incident.incident_number,
        title=incident.title,
        description=incident.description,
        category=incident.category,
        severity=incident.severity,
        status=incident.status,
        location=incident.location,
        incident_time=incident.incident_time,
        reported_by=incident.reported_by,
        assigned_to=incident.assigned_to,
        evidence_urls=incident.evidence_urls,
        resolution_notes=incident.resolution_notes,
        created_at=incident.created_at,
        updated_at=incident.updated_at,
        resolved_at=incident.resolved_at,
        timeline=timeline,
        reporter_name=reporter_name,
        assignee_name=assignee_name
    )


@router.patch("/{incident_id}", response_model=IncidentResponse)
def update_incident(
    incident_id: int,
    update_data: IncidentUpdate,
    updated_by: int = Query(..., description="ID of user updating the incident"),
    db: Session = Depends(get_db)
):
    """Update incident details"""
    incident = incident_service.update_incident(db, incident_id, update_data, updated_by)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.post("/{incident_id}/assign")
def assign_incident(
    incident_id: int,
    assigned_to: int = Query(..., description="User ID to assign to"),
    assigned_by: int = Query(..., description="User ID making the assignment"),
    db: Session = Depends(get_db)
):
    """Assign incident to a user"""
    incident = incident_service.assign_incident(db, incident_id, assigned_to, assigned_by)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {"message": "Incident assigned", "incident_id": incident.id, "assigned_to": assigned_to}


@router.post("/{incident_id}/resolve")
def resolve_incident(
    incident_id: int,
    resolution_notes: str = Query(..., description="Resolution notes"),
    resolved_by: int = Query(..., description="User ID resolving the incident"),
    db: Session = Depends(get_db)
):
    """Resolve an incident"""
    incident = incident_service.resolve_incident(db, incident_id, resolved_by, resolution_notes)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {"message": "Incident resolved", "incident_number": incident.incident_number}


@router.post("/{incident_id}/comment")
def add_comment(
    incident_id: int,
    comment: str = Query(..., description="Comment text"),
    created_by: int = Query(..., description="User ID adding the comment"),
    db: Session = Depends(get_db)
):
    """Add a comment to incident timeline"""
    timeline = incident_service.add_comment(db, incident_id, comment, created_by)
    if not timeline:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {"message": "Comment added", "timeline_id": timeline.id}


@router.post("/{incident_id}/evidence")
def add_evidence(
    incident_id: int,
    evidence_base64: str = Query(..., description="Base64 encoded image"),
    added_by: int = Query(..., description="User ID adding the evidence"),
    db: Session = Depends(get_db)
):
    """Add evidence image to incident"""
    url, details = incident_service.add_evidence(db, incident_id, evidence_base64, added_by)
    if not url:
        raise HTTPException(status_code=400, detail=details.get("error", "Failed to add evidence"))
    return {"message": "Evidence added", "url": url}
