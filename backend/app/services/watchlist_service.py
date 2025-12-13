from datetime import datetime, timezone
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..models.watchlist import WatchlistPerson, WatchlistAlert, AlertSeverity
from ..schemas.schemas import WatchlistPersonCreate, WatchlistPersonUpdate
from .face_recognition import face_service
from ..config import settings
import logging

logger = logging.getLogger(__name__)


class WatchlistService:
    """Service for watchlist management and alert handling"""
    
    @staticmethod
    def add_person(
        db: Session,
        person_data: WatchlistPersonCreate,
        added_by: int
    ) -> Tuple[Optional[WatchlistPerson], dict]:
        """Add a person to the watchlist"""
        try:
            # Handle face image if provided
            face_id = None
            face_image_url = None
            face_details = {}
            
            if person_data.face_image_base64:
                face_result = face_service.index_face(
                    image_base64=person_data.face_image_base64,
                    person_id=f"watchlist_{person_data.full_name.replace(' ', '_')}",
                    person_type="watchlist",
                    person_name=person_data.full_name
                )
                
                if face_result.get("success"):
                    face_id = face_result["face_id"]
                    face_image_url = face_result["image_path"]
                    face_details = face_result
                else:
                    logger.warning(f"Face indexing failed for watchlist: {face_result.get('error')}")
                    face_details = face_result
            
            person = WatchlistPerson(
                full_name=person_data.full_name,
                alias=person_data.alias,
                phone=person_data.phone,
                category=person_data.category,
                severity=person_data.severity,
                reason=person_data.reason,
                last_known_address=person_data.last_known_address,
                physical_description=person_data.physical_description,
                face_id=face_id,
                face_image_url=face_image_url,
                added_by=added_by,
                expires_at=person_data.expires_at,
                is_active=True
            )
            
            db.add(person)
            db.commit()
            db.refresh(person)
            
            return person, {
                "success": True,
                "face_indexed": face_id is not None,
                "face_details": face_details
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to add watchlist person: {e}")
            return None, {"success": False, "error": str(e)}
    
    @staticmethod
    def get_person(db: Session, person_id: int) -> Optional[WatchlistPerson]:
        """Get watchlist person by ID"""
        return db.query(WatchlistPerson).filter(WatchlistPerson.id == person_id).first()
    
    @staticmethod
    def get_all_active(db: Session) -> List[WatchlistPerson]:
        """Get all active watchlist persons"""
        return db.query(WatchlistPerson).filter(
            WatchlistPerson.is_active == True
        ).all()
    
    @staticmethod
    def get_watchlist(
        db: Session,
        skip: int = 0,
        limit: int = 50,
        category: Optional[str] = None,
        severity: Optional[str] = None,
        is_active: bool = True,
        search: Optional[str] = None
    ) -> Tuple[List[WatchlistPerson], int]:
        """Get watchlist with filters"""
        query = db.query(WatchlistPerson)
        
        if is_active is not None:
            query = query.filter(WatchlistPerson.is_active == is_active)
        if category:
            query = query.filter(WatchlistPerson.category == category)
        if severity:
            query = query.filter(WatchlistPerson.severity == severity)
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    WatchlistPerson.full_name.ilike(search_term),
                    WatchlistPerson.alias.ilike(search_term),
                    WatchlistPerson.reason.ilike(search_term)
                )
            )
        
        total = query.count()
        persons = query.order_by(WatchlistPerson.created_at.desc()).offset(skip).limit(limit).all()
        
        return persons, total
    
    @staticmethod
    def update_person(
        db: Session,
        person_id: int,
        update_data: WatchlistPersonUpdate
    ) -> Optional[WatchlistPerson]:
        """Update watchlist person"""
        person = db.query(WatchlistPerson).filter(WatchlistPerson.id == person_id).first()
        if not person:
            return None
        
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(person, field, value)
        
        db.commit()
        db.refresh(person)
        return person
    
    @staticmethod
    def remove_person(db: Session, person_id: int) -> bool:
        """Deactivate watchlist person"""
        person = db.query(WatchlistPerson).filter(WatchlistPerson.id == person_id).first()
        if not person:
            return False
        
        person.is_active = False
        
        # Remove face from collection
        if person.face_id:
            face_service.delete_face(person.face_id)
        
        db.commit()
        return True
    
    @staticmethod
    def check_against_watchlist(
        db: Session,
        face_matches: List[dict]
    ) -> Optional[Tuple[WatchlistPerson, float]]:
        """
        Check if any face matches belong to watchlist
        Returns (matched_person, confidence) or None
        """
        watchlist_threshold = settings.WATCHLIST_ALERT_THRESHOLD
        
        for match in face_matches:
            if match['person_type'] == 'watchlist':
                # Get the watchlist person
                try:
                    # External ID format: watchlist_PersonName
                    external_id = match['external_id']
                    
                    # Find by face_id
                    person = db.query(WatchlistPerson).filter(
                        and_(
                            WatchlistPerson.face_id == match['face_id'],
                            WatchlistPerson.is_active == True
                        )
                    ).first()
                    
                    if person and match['confidence'] >= watchlist_threshold:
                        return person, match['confidence']
                        
                except Exception as e:
                    logger.error(f"Error checking watchlist match: {e}")
                    continue
        
        return None
    
    @staticmethod
    def create_alert(
        db: Session,
        watchlist_person_id: int,
        confidence_score: float,
        gate_id: str,
        entry_log_id: Optional[int] = None,
        captured_image_url: Optional[str] = None
    ) -> WatchlistAlert:
        """Create a watchlist alert"""
        # Get the person to determine severity
        person = db.query(WatchlistPerson).filter(
            WatchlistPerson.id == watchlist_person_id
        ).first()
        
        severity = person.severity if person else AlertSeverity.HIGH
        
        alert = WatchlistAlert(
            watchlist_person_id=watchlist_person_id,
            entry_log_id=entry_log_id,
            gate_id=gate_id,
            confidence_score=confidence_score,
            severity=severity,
            captured_image_url=captured_image_url,
            is_acknowledged=False,
            is_resolved=False
        )
        
        db.add(alert)
        db.commit()
        db.refresh(alert)
        
        logger.warning(
            f"WATCHLIST ALERT: Person ID {watchlist_person_id} detected at {gate_id} "
            f"with {confidence_score:.1f}% confidence"
        )
        
        return alert
    
    @staticmethod
    def get_active_alerts(db: Session) -> List[WatchlistAlert]:
        """Get all unresolved alerts"""
        return db.query(WatchlistAlert).filter(
            WatchlistAlert.is_resolved == False
        ).order_by(WatchlistAlert.created_at.desc()).all()
    
    @staticmethod
    def get_alerts(
        db: Session,
        skip: int = 0,
        limit: int = 50,
        is_resolved: Optional[bool] = None,
        severity: Optional[str] = None
    ) -> Tuple[List[WatchlistAlert], int]:
        """Get alerts with filters"""
        query = db.query(WatchlistAlert)
        
        if is_resolved is not None:
            query = query.filter(WatchlistAlert.is_resolved == is_resolved)
        if severity:
            query = query.filter(WatchlistAlert.severity == severity)
        
        total = query.count()
        alerts = query.order_by(WatchlistAlert.created_at.desc()).offset(skip).limit(limit).all()
        
        return alerts, total
    
    @staticmethod
    def acknowledge_alert(
        db: Session,
        alert_id: int,
        acknowledged_by: int,
        notes: Optional[str] = None
    ) -> Optional[WatchlistAlert]:
        """Acknowledge an alert"""
        alert = db.query(WatchlistAlert).filter(WatchlistAlert.id == alert_id).first()
        if not alert:
            return None
        
        alert.is_acknowledged = True
        alert.acknowledged_by = acknowledged_by
        alert.acknowledged_at = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(alert)
        return alert
    
    @staticmethod
    def resolve_alert(
        db: Session,
        alert_id: int,
        resolved_by: int,
        resolution_notes: str,
        is_false_positive: bool = False
    ) -> Optional[WatchlistAlert]:
        """Resolve an alert"""
        alert = db.query(WatchlistAlert).filter(WatchlistAlert.id == alert_id).first()
        if not alert:
            return None
        
        alert.is_resolved = True
        alert.resolved_by = resolved_by
        alert.resolved_at = datetime.now(timezone.utc)
        alert.resolution_notes = resolution_notes
        alert.is_false_positive = is_false_positive
        
        db.commit()
        db.refresh(alert)
        return alert


watchlist_service = WatchlistService()
