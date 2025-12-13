import json
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from ..models.incident import Incident, IncidentTimeline, IncidentStatus, IncidentSeverity
from ..schemas.schemas import IncidentCreate, IncidentUpdate
from .face_recognition import face_service
import logging

logger = logging.getLogger(__name__)


class IncidentService:
    """Service for incident management operations"""
    
    @staticmethod
    def generate_incident_number(db: Session) -> str:
        """Generate unique incident number"""
        year = datetime.now().year
        
        # Get count of incidents this year
        count = db.query(Incident).filter(
            Incident.incident_number.like(f"INC-{year}-%")
        ).count()
        
        return f"INC-{year}-{(count + 1):04d}"
    
    @staticmethod
    def calculate_priority_score(
        severity: IncidentSeverity,
        category: str
    ) -> float:
        """Calculate priority score based on severity and category"""
        severity_scores = {
            IncidentSeverity.LOW: 1.0,
            IncidentSeverity.MEDIUM: 2.0,
            IncidentSeverity.HIGH: 3.0,
            IncidentSeverity.CRITICAL: 4.0
        }
        
        # Higher priority categories
        high_priority_categories = [
            "unauthorized_entry", "theft", "fire_safety",
            "medical_emergency", "violence"
        ]
        
        base_score = severity_scores.get(severity, 2.0)
        
        if category in high_priority_categories:
            base_score *= 1.5
        
        return base_score
    
    @staticmethod
    def create_incident(
        db: Session,
        incident_data: IncidentCreate,
        reported_by: int
    ) -> Tuple[Optional[Incident], dict]:
        """Create a new incident"""
        try:
            incident_number = IncidentService.generate_incident_number(db)
            
            # Handle evidence uploads - save locally
            evidence_urls = []
            if incident_data.evidence_base64:
                for i, img_base64 in enumerate(incident_data.evidence_base64):
                    url = face_service.save_evidence_image(
                        img_base64,
                        f"incidents/{incident_number}"
                    )
                    if url:
                        evidence_urls.append(url)
            
            # Calculate priority
            priority_score = IncidentService.calculate_priority_score(
                incident_data.severity,
                incident_data.category.value
            )
            
            incident = Incident(
                incident_number=incident_number,
                title=incident_data.title,
                description=incident_data.description,
                category=incident_data.category,
                severity=incident_data.severity,
                location=incident_data.location,
                incident_time=incident_data.incident_time or datetime.now(timezone.utc),
                status=IncidentStatus.OPEN,
                reported_by=reported_by,
                related_visitor_id=incident_data.related_visitor_id,
                related_entry_log_id=incident_data.related_entry_log_id,
                evidence_urls=json.dumps(evidence_urls) if evidence_urls else None,
                priority_score=priority_score
            )
            
            db.add(incident)
            db.commit()
            db.refresh(incident)
            
            # Add initial timeline event
            timeline = IncidentTimeline(
                incident_id=incident.id,
                event_type="created",
                description="Incident reported",
                created_by=reported_by
            )
            db.add(timeline)
            db.commit()
            
            return incident, {
                "success": True,
                "incident_number": incident_number,
                "evidence_count": len(evidence_urls)
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create incident: {e}")
            return None, {"success": False, "error": str(e)}
    
    @staticmethod
    def get_incident(db: Session, incident_id: int) -> Optional[Incident]:
        """Get incident by ID"""
        return db.query(Incident).filter(Incident.id == incident_id).first()
    
    @staticmethod
    def get_incident_by_number(db: Session, incident_number: str) -> Optional[Incident]:
        """Get incident by incident number"""
        return db.query(Incident).filter(Incident.incident_number == incident_number).first()
    
    @staticmethod
    def get_incidents(
        db: Session,
        skip: int = 0,
        limit: int = 50,
        status: Optional[IncidentStatus] = None,
        severity: Optional[IncidentSeverity] = None,
        category: Optional[str] = None,
        reported_by: Optional[int] = None,
        assigned_to: Optional[int] = None,
        search: Optional[str] = None
    ) -> Tuple[List[Incident], int]:
        """Get incidents with filters"""
        query = db.query(Incident)
        
        if status:
            query = query.filter(Incident.status == status)
        if severity:
            query = query.filter(Incident.severity == severity)
        if category:
            query = query.filter(Incident.category == category)
        if reported_by:
            query = query.filter(Incident.reported_by == reported_by)
        if assigned_to:
            query = query.filter(Incident.assigned_to == assigned_to)
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Incident.title.ilike(search_term),
                    Incident.description.ilike(search_term),
                    Incident.incident_number.ilike(search_term)
                )
            )
        
        total = query.count()
        incidents = query.order_by(
            Incident.priority_score.desc(),
            Incident.created_at.desc()
        ).offset(skip).limit(limit).all()
        
        return incidents, total
    
    @staticmethod
    def get_open_incidents(db: Session) -> List[Incident]:
        """Get all open incidents"""
        return db.query(Incident).filter(
            Incident.status.in_([
                IncidentStatus.OPEN,
                IncidentStatus.IN_PROGRESS,
                IncidentStatus.ESCALATED
            ])
        ).order_by(Incident.priority_score.desc()).all()
    
    @staticmethod
    def get_critical_incidents(db: Session) -> List[Incident]:
        """Get critical open incidents"""
        return db.query(Incident).filter(
            and_(
                Incident.severity == IncidentSeverity.CRITICAL,
                Incident.status.in_([
                    IncidentStatus.OPEN,
                    IncidentStatus.IN_PROGRESS
                ])
            )
        ).all()
    
    @staticmethod
    def update_incident(
        db: Session,
        incident_id: int,
        update_data: IncidentUpdate,
        updated_by: int
    ) -> Optional[Incident]:
        """Update incident details"""
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            return None
        
        update_dict = update_data.model_dump(exclude_unset=True)
        changes = []
        
        for field, value in update_dict.items():
            old_value = getattr(incident, field)
            if old_value != value:
                changes.append(f"{field}: {old_value} → {value}")
                setattr(incident, field, value)
        
        # Handle status changes
        if 'status' in update_dict:
            if update_dict['status'] == IncidentStatus.RESOLVED:
                incident.resolved_at = datetime.now(timezone.utc)
                incident.resolved_by = updated_by
        
        # Recalculate priority if severity changed
        if 'severity' in update_dict:
            incident.priority_score = IncidentService.calculate_priority_score(
                update_dict['severity'],
                incident.category.value
            )
        
        db.commit()
        db.refresh(incident)
        
        # Add timeline event
        if changes:
            timeline = IncidentTimeline(
                incident_id=incident.id,
                event_type="updated",
                description=f"Updated: {', '.join(changes)}",
                created_by=updated_by
            )
            db.add(timeline)
            db.commit()
        
        return incident
    
    @staticmethod
    def assign_incident(
        db: Session,
        incident_id: int,
        assigned_to: int,
        assigned_by: int
    ) -> Optional[Incident]:
        """Assign incident to a user"""
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            return None
        
        incident.assigned_to = assigned_to
        if incident.status == IncidentStatus.OPEN:
            incident.status = IncidentStatus.IN_PROGRESS
        
        db.commit()
        db.refresh(incident)
        
        # Add timeline event
        timeline = IncidentTimeline(
            incident_id=incident.id,
            event_type="assigned",
            description=f"Assigned to user ID: {assigned_to}",
            created_by=assigned_by
        )
        db.add(timeline)
        db.commit()
        
        return incident
    
    @staticmethod
    def resolve_incident(
        db: Session,
        incident_id: int,
        resolved_by: int,
        resolution_notes: str
    ) -> Optional[Incident]:
        """Resolve an incident"""
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            return None
        
        incident.status = IncidentStatus.RESOLVED
        incident.resolution_notes = resolution_notes
        incident.resolved_by = resolved_by
        incident.resolved_at = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(incident)
        
        # Add timeline event
        timeline = IncidentTimeline(
            incident_id=incident.id,
            event_type="resolved",
            description=f"Resolved: {resolution_notes}",
            created_by=resolved_by
        )
        db.add(timeline)
        db.commit()
        
        return incident
    
    @staticmethod
    def add_comment(
        db: Session,
        incident_id: int,
        comment: str,
        created_by: int
    ) -> Optional[IncidentTimeline]:
        """Add a comment to incident timeline"""
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            return None
        
        timeline = IncidentTimeline(
            incident_id=incident_id,
            event_type="comment",
            description=comment,
            created_by=created_by
        )
        
        db.add(timeline)
        db.commit()
        db.refresh(timeline)
        
        return timeline
    
    @staticmethod
    def add_evidence(
        db: Session,
        incident_id: int,
        evidence_base64: str,
        added_by: int
    ) -> Tuple[Optional[str], dict]:
        """Add evidence to an incident"""
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            return None, {"success": False, "error": "Incident not found"}
        
        # Save image locally
        url = face_service.save_evidence_image(
            evidence_base64,
            f"incidents/{incident.incident_number}"
        )
        
        if not url:
            return None, {"success": False, "error": "Failed to upload evidence"}
        
        # Update evidence URLs
        current_urls = json.loads(incident.evidence_urls) if incident.evidence_urls else []
        current_urls.append(url)
        incident.evidence_urls = json.dumps(current_urls)
        
        db.commit()
        
        # Add timeline event
        timeline = IncidentTimeline(
            incident_id=incident_id,
            event_type="evidence_added",
            description="New evidence uploaded",
            created_by=added_by,
            extra_data=json.dumps({"url": url})
        )
        db.add(timeline)
        db.commit()
        
        return url, {"success": True}
    
    @staticmethod
    def get_incident_stats(db: Session) -> dict:
        """Get incident statistics"""
        total = db.query(Incident).count()
        
        open_count = db.query(Incident).filter(
            Incident.status.in_([
                IncidentStatus.OPEN,
                IncidentStatus.IN_PROGRESS
            ])
        ).count()
        
        critical_count = db.query(Incident).filter(
            and_(
                Incident.severity == IncidentSeverity.CRITICAL,
                Incident.status.in_([
                    IncidentStatus.OPEN,
                    IncidentStatus.IN_PROGRESS
                ])
            )
        ).count()
        
        resolved_today = db.query(Incident).filter(
            and_(
                Incident.status == IncidentStatus.RESOLVED,
                func.date(Incident.resolved_at) == func.current_date()
            )
        ).count()
        
        return {
            "total": total,
            "open": open_count,
            "critical": critical_count,
            "resolved_today": resolved_today
        }


incident_service = IncidentService()
