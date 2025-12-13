from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timezone
import logging

from ..database import get_db
from ..models.entry_log import EntryLog, EntryStatus, EntryType, VerificationMethod
from ..models.visitor import Visitor, VisitorStatus
from ..schemas.schemas import (
    GateVerificationRequest, GateVerificationResponse,
    EntryLogResponse, EntryLogListResponse
)
from ..services.face_recognition import face_service
from ..services.visitor_service import visitor_service
from ..services.watchlist_service import watchlist_service

router = APIRouter(prefix="/gate", tags=["Gate Verification"])
logger = logging.getLogger(__name__)


@router.post("/verify", response_model=GateVerificationResponse)
def verify_entry(
    request: GateVerificationRequest,
    verified_by: int = Query(..., description="Security personnel ID"),
    db: Session = Depends(get_db)
):
    """
    Verify a person at the gate using face recognition.
    
    Process:
    1. Check against watchlist first
    2. Search for face in registered visitors/residents
    3. Log the entry attempt
    4. Return verification result
    """
    captured_image_url = None
    watchlist_alert_data = None
    
    # Step 1: Check against watchlist FIRST
    watchlist_result = face_service.search_watchlist(request.face_image_base64)
    
    if watchlist_result.get('watchlist_match') and watchlist_result.get('best_match'):
        match = watchlist_result['best_match']
        confidence = match['confidence']
        
        # Get watchlist person from DB using face_id
        from ..models.watchlist import WatchlistPerson
        face_id = match.get('face_id')
        
        logger.info(f"Watchlist match found - face_id: {face_id}, confidence: {confidence}")
        
        person = db.query(WatchlistPerson).filter(
            WatchlistPerson.face_id == face_id,
            WatchlistPerson.is_active == True
        ).first()
        
        if person:
            # Create alert
            alert = watchlist_service.create_alert(
                db=db,
                watchlist_person_id=person.id,
                confidence_score=confidence,
                gate_id=request.gate_id,
                captured_image_url=captured_image_url
            )
            
            # Log the entry attempt
            entry_log = EntryLog(
                entry_type=EntryType.ENTRY,
                gate_id=request.gate_id,
                person_name=person.full_name,
                status=EntryStatus.WATCHLIST_ALERT,
                verification_method=VerificationMethod.FACE_RECOGNITION,
                face_match_confidence=confidence,
                captured_image_url=captured_image_url,
                verified_by=verified_by,
                watchlist_match_id=person.id,
                watchlist_confidence=confidence,
                is_flagged=True,
                notes=f"WATCHLIST MATCH: {person.category.value} - {person.reason}"
            )
            db.add(entry_log)
            db.commit()
            
            # Update alert with entry log ID
            alert.entry_log_id = entry_log.id
            db.commit()
            db.refresh(entry_log)
            
            watchlist_alert_data = {
                "alert_id": alert.id,
                "person_name": person.full_name,
                "category": person.category.value,
                "severity": person.severity.value,
                "reason": person.reason,
                "confidence": confidence
            }
            
            return GateVerificationResponse(
                status=EntryStatus.WATCHLIST_ALERT,
                message=f"⚠️ WATCHLIST ALERT: {person.full_name} - {person.category.value}",
                confidence=confidence,
                entry_log_id=entry_log.id,
                watchlist_alert=watchlist_alert_data,
                requires_manual_check=True
            )
    
    # Step 2: Search for visitor/resident matches
    search_result = face_service.search_face(
        image_base64=request.face_image_base64,
        person_types=['visitor', 'resident'],
        top_k=5
    )
    
    # If no face detected
    if not search_result.get("success"):
        entry_log = EntryLog(
            entry_type=EntryType.ENTRY,
            gate_id=request.gate_id,
            status=EntryStatus.MANUAL_VERIFICATION,
            verification_method=VerificationMethod.MANUAL,
            captured_image_url=captured_image_url,
            denial_reason=search_result.get("error", "Face not detected"),
            verified_by=verified_by,
            notes="Face detection failed"
        )
        db.add(entry_log)
        db.commit()
        db.refresh(entry_log)
        
        return GateVerificationResponse(
            status=EntryStatus.MANUAL_VERIFICATION,
            message="Face could not be detected. Manual verification required.",
            entry_log_id=entry_log.id,
            requires_manual_check=True
        )
    
    # Check if we have a match
    if search_result.get('match_found') and search_result.get('best_match'):
        match = search_result['best_match']
        person_type = match.get('person_type')
        confidence = match.get('confidence', 0)
        face_id = match.get('face_id')
        person_name = match.get('person_name', 'Unknown')
        
        logger.info(f"Match found - type: {person_type}, face_id: {face_id}, name: {person_name}, confidence: {confidence}")
        
        if person_type == 'visitor':
            # Get visitor from DB using face_id
            # IMPORTANT: face_id in FAISS metadata should match face_id in Visitor table
            visitor = db.query(Visitor).filter(Visitor.face_id == face_id).first()
            
            # DEBUG: If not found by face_id, log all visitors with their face_ids
            if not visitor:
                logger.warning(f"Visitor not found by face_id: {face_id}")
                
                # Try to find by name as fallback (not ideal but helps debugging)
                all_visitors = db.query(Visitor).filter(Visitor.face_id.isnot(None)).all()
                logger.debug(f"All visitors with face_id: {[(v.id, v.full_name, v.face_id) for v in all_visitors]}")
                
                # Attempt lookup by name match (temporary workaround)
                if person_name:
                    visitor = db.query(Visitor).filter(
                        Visitor.full_name == person_name,
                        Visitor.face_id.isnot(None)
                    ).first()
                    if visitor:
                        logger.info(f"Found visitor by name match: {visitor.full_name} (id: {visitor.id})")
            
            if visitor:
                # Validate visitor entry
                is_valid, message = visitor_service.validate_visitor_entry(db, visitor.id)
                
                if is_valid:
                    # Allow entry
                    entry_log = EntryLog(
                        entry_type=EntryType.ENTRY,
                        gate_id=request.gate_id,
                        visitor_id=visitor.id,
                        person_name=visitor.full_name,
                        status=EntryStatus.ALLOWED,
                        verification_method=VerificationMethod.FACE_RECOGNITION,
                        face_match_confidence=confidence,
                        captured_image_url=captured_image_url,
                        verified_by=verified_by
                    )
                    db.add(entry_log)
                    
                    # Update visitor status
                    visitor_service.check_in_visitor(db, visitor.id)
                    
                    db.commit()
                    db.refresh(entry_log)
                    
                    return GateVerificationResponse(
                        status=EntryStatus.ALLOWED,
                        message=f"✅ Entry allowed for {visitor.full_name}",
                        visitor_name=visitor.full_name,
                        visitor_id=visitor.id,
                        confidence=confidence,
                        entry_log_id=entry_log.id
                    )
                else:
                    # Deny entry
                    entry_log = EntryLog(
                        entry_type=EntryType.ENTRY,
                        gate_id=request.gate_id,
                        visitor_id=visitor.id,
                        person_name=visitor.full_name,
                        status=EntryStatus.DENIED,
                        verification_method=VerificationMethod.FACE_RECOGNITION,
                        face_match_confidence=confidence,
                        captured_image_url=captured_image_url,
                        denial_reason=message,
                        verified_by=verified_by
                    )
                    db.add(entry_log)
                    db.commit()
                    db.refresh(entry_log)
                    
                    return GateVerificationResponse(
                        status=EntryStatus.DENIED,
                        message=f"❌ Entry denied: {message}",
                        visitor_name=visitor.full_name,
                        visitor_id=visitor.id,
                        confidence=confidence,
                        denial_reason=message,
                        entry_log_id=entry_log.id
                    )
            else:
                # Face matched but visitor record not found in DB
                # This could happen if face was indexed but DB record was deleted
                logger.warning(f"Face matched ({person_name}) but no visitor record found for face_id: {face_id}")
                
                # Still show as recognized but require manual verification
                entry_log = EntryLog(
                    entry_type=EntryType.ENTRY,
                    gate_id=request.gate_id,
                    person_name=person_name,
                    status=EntryStatus.MANUAL_VERIFICATION,
                    verification_method=VerificationMethod.FACE_RECOGNITION,
                    face_match_confidence=confidence,
                    captured_image_url=captured_image_url,
                    verified_by=verified_by,
                    notes=f"Face recognized as {person_name} (confidence: {confidence:.1%}) but visitor record not found"
                )
                db.add(entry_log)
                db.commit()
                db.refresh(entry_log)
                
                return GateVerificationResponse(
                    status=EntryStatus.MANUAL_VERIFICATION,
                    message=f"⚠️ Face recognized as {person_name} ({confidence:.1%}) but record not found. Manual verification required.",
                    visitor_name=person_name,
                    confidence=confidence,
                    entry_log_id=entry_log.id,
                    requires_manual_check=True
                )
        
        elif person_type == 'resident':
            # Resident entry - always allowed
            person_name = match.get('person_name', 'Resident')
            person_id_str = match.get('person_id', '')
            
            # Try to extract numeric resident_id if the format allows
            resident_id = None
            if person_id_str:
                try:
                    resident_id = int(person_id_str)
                except ValueError:
                    pass
            
            entry_log = EntryLog(
                entry_type=EntryType.ENTRY,
                gate_id=request.gate_id,
                resident_id=resident_id,
                person_name=person_name,
                status=EntryStatus.ALLOWED,
                verification_method=VerificationMethod.FACE_RECOGNITION,
                face_match_confidence=confidence,
                captured_image_url=captured_image_url,
                verified_by=verified_by
            )
            db.add(entry_log)
            db.commit()
            db.refresh(entry_log)
            
            return GateVerificationResponse(
                status=EntryStatus.ALLOWED,
                message=f"✅ Resident entry allowed for {person_name}",
                visitor_name=person_name,
                confidence=confidence,
                entry_log_id=entry_log.id
            )
    
    # No matches found - manual verification needed
    # Include best score for debugging
    best_score = search_result.get('best_score', 0)
    threshold = search_result.get('threshold', 0)
    
    entry_log = EntryLog(
        entry_type=EntryType.ENTRY,
        gate_id=request.gate_id,
        status=EntryStatus.MANUAL_VERIFICATION,
        verification_method=VerificationMethod.MANUAL,
        captured_image_url=captured_image_url,
        verified_by=verified_by,
        denial_reason=f"No matching face found (best score: {best_score:.3f}, threshold: {threshold})",
        notes="Person not recognized - manual verification required"
    )
    db.add(entry_log)
    db.commit()
    db.refresh(entry_log)
    
    return GateVerificationResponse(
        status=EntryStatus.MANUAL_VERIFICATION,
        message=f"⚠️ Person not recognized (best match: {best_score:.1%}). Manual verification required.",
        entry_log_id=entry_log.id,
        requires_manual_check=True
    )


@router.post("/verify-code")
def verify_by_code(
    approval_code: str = Query(..., description="Visitor approval code"),
    gate_id: str = Query("MAIN_GATE"),
    verified_by: int = Query(..., description="Security personnel ID"),
    db: Session = Depends(get_db)
):
    """Verify visitor by approval code (fallback method)"""
    visitor = visitor_service.get_visitor_by_code(db, approval_code)
    
    if not visitor:
        entry_log = EntryLog(
            entry_type=EntryType.ENTRY,
            gate_id=gate_id,
            status=EntryStatus.DENIED,
            verification_method=VerificationMethod.APPROVAL_CODE,
            approval_code_used=approval_code,
            denial_reason="Invalid approval code",
            verified_by=verified_by
        )
        db.add(entry_log)
        db.commit()
        
        raise HTTPException(status_code=404, detail="Invalid approval code")
    
    # Validate visitor entry
    is_valid, message = visitor_service.validate_visitor_entry(db, visitor.id)
    
    entry_log = EntryLog(
        entry_type=EntryType.ENTRY,
        gate_id=gate_id,
        visitor_id=visitor.id,
        person_name=visitor.full_name,
        status=EntryStatus.ALLOWED if is_valid else EntryStatus.DENIED,
        verification_method=VerificationMethod.APPROVAL_CODE,
        approval_code_used=approval_code,
        denial_reason=None if is_valid else message,
        verified_by=verified_by
    )
    db.add(entry_log)
    
    if is_valid:
        visitor_service.check_in_visitor(db, visitor.id)
    
    db.commit()
    db.refresh(entry_log)
    
    if is_valid:
        return {
            "status": "allowed",
            "message": f"Entry allowed for {visitor.full_name}",
            "visitor": {
                "id": visitor.id,
                "full_name": visitor.full_name,
                "visiting_unit": visitor.visiting_unit,
                "purpose": visitor.purpose
            },
            "entry_log_id": entry_log.id
        }
    else:
        return {
            "status": "denied",
            "message": message,
            "visitor": {
                "id": visitor.id,
                "full_name": visitor.full_name,
                "visiting_unit": visitor.visiting_unit
            },
            "entry_log_id": entry_log.id
        }


@router.post("/manual-allow/{entry_log_id}")
def manual_allow_entry(
    entry_log_id: int,
    person_name: str = Query(...),
    notes: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Manually allow entry (for manual verification cases)"""
    entry_log = db.query(EntryLog).filter(EntryLog.id == entry_log_id).first()
    if not entry_log:
        raise HTTPException(status_code=404, detail="Entry log not found")
    
    entry_log.status = EntryStatus.ALLOWED
    entry_log.person_name = person_name
    entry_log.notes = f"Manual approval: {notes}" if notes else "Manual approval"
    
    db.commit()
    db.refresh(entry_log)
    
    return {"message": "Entry manually allowed", "entry_log_id": entry_log.id}


@router.post("/manual-deny/{entry_log_id}")
def manual_deny_entry(
    entry_log_id: int,
    denial_reason: str = Query(...),
    db: Session = Depends(get_db)
):
    """Manually deny entry"""
    entry_log = db.query(EntryLog).filter(EntryLog.id == entry_log_id).first()
    if not entry_log:
        raise HTTPException(status_code=404, detail="Entry log not found")
    
    entry_log.status = EntryStatus.DENIED
    entry_log.denial_reason = denial_reason
    
    db.commit()
    db.refresh(entry_log)
    
    return {"message": "Entry manually denied", "entry_log_id": entry_log.id}


@router.get("/logs", response_model=EntryLogListResponse)
def get_entry_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    gate_id: Optional[str] = None,
    status: Optional[EntryStatus] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """Get entry logs with filters"""
    query = db.query(EntryLog)
    
    if gate_id:
        query = query.filter(EntryLog.gate_id == gate_id)
    if status:
        query = query.filter(EntryLog.status == status)
    if date_from:
        query = query.filter(EntryLog.timestamp >= date_from)
    if date_to:
        query = query.filter(EntryLog.timestamp <= date_to)
    
    total = query.count()
    logs = query.order_by(EntryLog.timestamp.desc()).offset(skip).limit(limit).all()
    
    return EntryLogListResponse(
        logs=logs,
        total=total,
        page=skip // limit + 1,
        page_size=limit
    )


@router.get("/logs/today")
def get_todays_logs(db: Session = Depends(get_db)):
    """Get all entry logs for today"""
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    
    logs = db.query(EntryLog).filter(
        EntryLog.timestamp >= today_start
    ).order_by(EntryLog.timestamp.desc()).all()
    
    # Calculate stats
    total = len(logs)
    allowed = sum(1 for l in logs if l.status == EntryStatus.ALLOWED)
    denied = sum(1 for l in logs if l.status == EntryStatus.DENIED)
    alerts = sum(1 for l in logs if l.status == EntryStatus.WATCHLIST_ALERT)
    
    return {
        "logs": logs,
        "stats": {
            "total": total,
            "allowed": allowed,
            "denied": denied,
            "watchlist_alerts": alerts
        }
    }


@router.get("/logs/{entry_log_id}", response_model=EntryLogResponse)
def get_entry_log(entry_log_id: int, db: Session = Depends(get_db)):
    """Get specific entry log"""
    log = db.query(EntryLog).filter(EntryLog.id == entry_log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Entry log not found")
    return log


# Debug endpoint to check face_id mapping
@router.get("/debug/face-mapping")
def debug_face_mapping(db: Session = Depends(get_db)):
    """Debug endpoint to check face_id mapping between FAISS and DB"""
    
    # Get all visitors with face_ids
    visitors = db.query(Visitor).filter(Visitor.face_id.isnot(None)).all()
    visitor_face_ids = {v.face_id: {"name": v.full_name, "id": v.id} for v in visitors}
    
    # Get FAISS stats
    faiss_stats = face_service.get_stats()
    
    # Get FAISS metadata
    faiss_metadata = {}
    if hasattr(face_service, 'faiss') and hasattr(face_service.faiss, 'metadata'):
        for idx, meta in face_service.faiss.metadata.items():
            faiss_metadata[meta.get('face_id', f'unknown_{idx}')] = {
                "person_name": meta.get('person_name'),
                "person_type": meta.get('person_type'),
                "person_id": meta.get('person_id')
            }
    
    # Find mismatches
    db_only = set(visitor_face_ids.keys()) - set(faiss_metadata.keys())
    faiss_only = set(faiss_metadata.keys()) - set(visitor_face_ids.keys())
    
    return {
        "db_visitors_with_face": len(visitor_face_ids),
        "faiss_faces": faiss_stats.get('total_faces', 0),
        "db_face_ids": list(visitor_face_ids.keys()),
        "faiss_face_ids": list(faiss_metadata.keys()),
        "in_db_not_faiss": list(db_only),
        "in_faiss_not_db": list(faiss_only),
        "faiss_metadata_sample": dict(list(faiss_metadata.items())[:5])
    }