import secrets
import string
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..models.visitor import Visitor, VisitorStatus
from ..schemas.schemas import VisitorCreate, VisitorUpdate
from .face_recognition import face_service
import logging

logger = logging.getLogger(__name__)


class VisitorService:
    """Service for visitor management operations"""
    
    @staticmethod
    def generate_approval_code(length: int = 6) -> str:
        """Generate a unique approval code"""
        characters = string.ascii_uppercase + string.digits
        return ''.join(secrets.choice(characters) for _ in range(length))
    
    @staticmethod
    def create_visitor(
        db: Session,
        visitor_data: VisitorCreate,
        approved_by: int
    ) -> Tuple[Optional[Visitor], dict]:
        """
        Create a new pre-approved visitor
        Returns (visitor, details)
        """
        try:
            # Generate unique approval code
            approval_code = VisitorService.generate_approval_code()
            while db.query(Visitor).filter(Visitor.approval_code == approval_code).first():
                approval_code = VisitorService.generate_approval_code()

            # Handle face image if provided
            face_id = None
            face_image_url = None
            face_details = {}

            if visitor_data.face_image_base64:
                face_result = face_service.index_face(
                    image_base64=visitor_data.face_image_base64,
                    person_id=f"visitor_{approval_code}",
                    person_type="visitor",
                    person_name=visitor_data.full_name
                )

                if face_result.get("success"):
                    face_id = face_result.get("face_id")
                    face_image_url = face_result.get("image_path")
                    face_details = face_result
                else:
                    logger.warning(f"Face indexing failed: {face_result}")
                    face_details = face_result
                    # Continue without face (allowed)

            # Create visitor record
            visitor = Visitor(
                full_name=visitor_data.full_name,
                phone=visitor_data.phone,
                email=visitor_data.email,
                visitor_type=visitor_data.visitor_type,
                purpose=visitor_data.purpose,
                visiting_unit=visitor_data.visiting_unit,
                visiting_block=visitor_data.visiting_block,
                approved_by=approved_by,
                approval_code=approval_code,
                valid_from=visitor_data.valid_from,
                valid_until=visitor_data.valid_until,
                face_id=face_id,
                face_image_url=face_image_url,
                vehicle_number=visitor_data.vehicle_number,
                vehicle_type=visitor_data.vehicle_type,
                notes=visitor_data.notes,
                status=VisitorStatus.APPROVED
            )

            db.add(visitor)
            db.commit()
            db.refresh(visitor)

            return visitor, {
                "success": True,
                "approval_code": approval_code,
                "face_indexed": face_id is not None,
                "face_details": face_details
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create visitor: {e}")
            return None, {"success": False, "error": str(e)}
    
    @staticmethod
    def get_visitor(db: Session, visitor_id: int) -> Optional[Visitor]:
        """Get visitor by ID"""
        return db.query(Visitor).filter(Visitor.id == visitor_id).first()
    
    @staticmethod
    def get_visitor_by_code(db: Session, approval_code: str) -> Optional[Visitor]:
        """Get visitor by approval code"""
        return db.query(Visitor).filter(Visitor.approval_code == approval_code).first()
    
    @staticmethod
    def get_visitors(
        db: Session,
        skip: int = 0,
        limit: int = 50,
        status: Optional[VisitorStatus] = None,
        approved_by: Optional[int] = None,
        visiting_unit: Optional[str] = None,
        search: Optional[str] = None
    ) -> Tuple[List[Visitor], int]:
        """Get list of visitors with filters"""
        query = db.query(Visitor)
        
        if status:
            query = query.filter(Visitor.status == status)
        if approved_by:
            query = query.filter(Visitor.approved_by == approved_by)
        if visiting_unit:
            query = query.filter(Visitor.visiting_unit == visiting_unit)
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Visitor.full_name.ilike(search_term),
                    Visitor.phone.ilike(search_term),
                    Visitor.approval_code.ilike(search_term)
                )
            )
        
        total = query.count()
        visitors = query.order_by(Visitor.created_at.desc()).offset(skip).limit(limit).all()
        
        return visitors, total
    
    @staticmethod
    def get_active_visitors(db: Session) -> List[Visitor]:
        """Get all currently active (checked-in) visitors"""
        return db.query(Visitor).filter(
            Visitor.status == VisitorStatus.CHECKED_IN
        ).all()
    
    @staticmethod
    def get_todays_visitors(db: Session) -> List[Visitor]:
        """Get all visitors for today"""
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return db.query(Visitor).filter(
            Visitor.created_at >= today_start
        ).all()
    
    @staticmethod
    def update_visitor(
        db: Session,
        visitor_id: int,
        update_data: VisitorUpdate
    ) -> Optional[Visitor]:
        """Update visitor details"""
        visitor = db.query(Visitor).filter(Visitor.id == visitor_id).first()
        if not visitor:
            return None
        
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(visitor, field, value)
        
        db.commit()
        db.refresh(visitor)
        return visitor
    
    @staticmethod
    def check_in_visitor(db: Session, visitor_id: int) -> Optional[Visitor]:
        """Mark visitor as checked in"""
        visitor = db.query(Visitor).filter(Visitor.id == visitor_id).first()
        if not visitor:
            return None
        
        visitor.status = VisitorStatus.CHECKED_IN
        visitor.checked_in_at = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(visitor)
        return visitor
    
    @staticmethod
    def check_out_visitor(db: Session, visitor_id: int) -> Optional[Visitor]:
        """Mark visitor as checked out"""
        visitor = db.query(Visitor).filter(Visitor.id == visitor_id).first()
        if not visitor:
            return None
        
        visitor.status = VisitorStatus.CHECKED_OUT
        visitor.checked_out_at = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(visitor)
        return visitor
    
    @staticmethod
    def cancel_visitor(db: Session, visitor_id: int) -> Optional[Visitor]:
        """Cancel a visitor's approval"""
        visitor = db.query(Visitor).filter(Visitor.id == visitor_id).first()
        if not visitor:
            return None
        
        visitor.status = VisitorStatus.CANCELLED
        
        # Remove face from collection if indexed
        if visitor.face_id:
            face_service.delete_face(visitor.face_id)
        
        db.commit()
        db.refresh(visitor)
        return visitor
    
    @staticmethod
    def expire_old_approvals(db: Session) -> int:
        """Expire all approvals past their valid_until time"""
        now = datetime.now(timezone.utc)
        
        result = db.query(Visitor).filter(
            and_(
                Visitor.status == VisitorStatus.APPROVED,
                Visitor.valid_until < now
            )
        ).update({"status": VisitorStatus.EXPIRED})
        
        db.commit()
        return result
    
    @staticmethod
    def validate_visitor_entry(
        db: Session,
        visitor_id: int
    ) -> Tuple[bool, str]:
        """
        Validate if a visitor can enter
        Returns (is_valid, message)
        """
        visitor = db.query(Visitor).filter(Visitor.id == visitor_id).first()
        
        if not visitor:
            return False, "Visitor not found"
        
        if visitor.status == VisitorStatus.CANCELLED:
            return False, "Visitor approval has been cancelled"
        
        if visitor.status == VisitorStatus.EXPIRED:
            return False, "Visitor approval has expired"
        
        if visitor.status == VisitorStatus.REJECTED:
            return False, "Visitor was previously rejected"
        
        if visitor.status == VisitorStatus.CHECKED_OUT:
            return False, "Visitor has already checked out"
        
        now = datetime.now(timezone.utc)
        if now < visitor.valid_from:
            return False, f"Approval not yet valid. Valid from: {visitor.valid_from}"
        
        if now > visitor.valid_until:
            visitor.status = VisitorStatus.EXPIRED
            db.commit()
            return False, "Visitor approval has expired"
        
        return True, "Valid"


visitor_service = VisitorService()
