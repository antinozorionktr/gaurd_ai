from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..schemas.schemas import (
    WatchlistPersonCreate, WatchlistPersonUpdate, WatchlistPersonResponse,
    WatchlistAlertResponse, WatchlistAlertAcknowledge, WatchlistAlertResolve,
    AlertSeverity, WatchlistCategory
)
from ..services.watchlist_service import watchlist_service

router = APIRouter(prefix="/watchlist", tags=["Watchlist"])


# ==================== Watchlist Persons ====================

@router.post("/persons", response_model=WatchlistPersonResponse)
def add_to_watchlist(
    person_data: WatchlistPersonCreate,
    added_by: int = Query(..., description="ID of user adding to watchlist"),
    db: Session = Depends(get_db)
):
    """Add a person to the watchlist"""
    person, details = watchlist_service.add_person(db, person_data, added_by)
    
    if not person:
        raise HTTPException(status_code=400, detail=details.get("error", "Failed to add to watchlist"))
    
    return person


@router.get("/persons")
def get_watchlist(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    category: Optional[WatchlistCategory] = None,
    severity: Optional[AlertSeverity] = None,
    is_active: bool = True,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get watchlist with filters"""
    persons, total = watchlist_service.get_watchlist(
        db, skip, limit, 
        category.value if category else None,
        severity.value if severity else None,
        is_active, search
    )
    
    return {
        "persons": persons,
        "total": total,
        "page": skip // limit + 1,
        "page_size": limit
    }


@router.get("/persons/active")
def get_active_watchlist(db: Session = Depends(get_db)):
    """Get all active watchlist entries"""
    persons = watchlist_service.get_all_active(db)
    return {"persons": persons, "count": len(persons)}


@router.get("/persons/{person_id}", response_model=WatchlistPersonResponse)
def get_watchlist_person(person_id: int, db: Session = Depends(get_db)):
    """Get watchlist person by ID"""
    person = watchlist_service.get_person(db, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found in watchlist")
    return person


@router.patch("/persons/{person_id}", response_model=WatchlistPersonResponse)
def update_watchlist_person(
    person_id: int,
    update_data: WatchlistPersonUpdate,
    db: Session = Depends(get_db)
):
    """Update watchlist person"""
    person = watchlist_service.update_person(db, person_id, update_data)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found in watchlist")
    return person


@router.delete("/persons/{person_id}")
def remove_from_watchlist(person_id: int, db: Session = Depends(get_db)):
    """Remove person from watchlist (deactivate)"""
    success = watchlist_service.remove_person(db, person_id)
    if not success:
        raise HTTPException(status_code=404, detail="Person not found in watchlist")
    return {"message": "Person removed from watchlist"}


# ==================== Alerts ====================

@router.get("/alerts")
def get_alerts(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    is_resolved: Optional[bool] = None,
    severity: Optional[AlertSeverity] = None,
    db: Session = Depends(get_db)
):
    """Get watchlist alerts with filters"""
    alerts, total = watchlist_service.get_alerts(
        db, skip, limit, is_resolved,
        severity.value if severity else None
    )
    
    # Enrich with person names
    enriched_alerts = []
    for alert in alerts:
        alert_dict = {
            "id": alert.id,
            "watchlist_person_id": alert.watchlist_person_id,
            "watchlist_person_name": alert.watchlist_person.full_name if alert.watchlist_person else None,
            "gate_id": alert.gate_id,
            "confidence_score": alert.confidence_score,
            "severity": alert.severity,
            "captured_image_url": alert.captured_image_url,
            "is_acknowledged": alert.is_acknowledged,
            "is_resolved": alert.is_resolved,
            "is_false_positive": alert.is_false_positive,
            "created_at": alert.created_at,
            "acknowledged_at": alert.acknowledged_at,
            "resolved_at": alert.resolved_at
        }
        enriched_alerts.append(alert_dict)
    
    return {
        "alerts": enriched_alerts,
        "total": total,
        "page": skip // limit + 1,
        "page_size": limit
    }


@router.get("/alerts/active")
def get_active_alerts(db: Session = Depends(get_db)):
    """Get all unresolved alerts"""
    alerts = watchlist_service.get_active_alerts(db)
    
    # Enrich with person names
    enriched_alerts = []
    for alert in alerts:
        alert_dict = {
            "id": alert.id,
            "watchlist_person_id": alert.watchlist_person_id,
            "watchlist_person_name": alert.watchlist_person.full_name if alert.watchlist_person else None,
            "category": alert.watchlist_person.category.value if alert.watchlist_person else None,
            "gate_id": alert.gate_id,
            "confidence_score": alert.confidence_score,
            "severity": alert.severity.value,
            "captured_image_url": alert.captured_image_url,
            "is_acknowledged": alert.is_acknowledged,
            "created_at": alert.created_at
        }
        enriched_alerts.append(alert_dict)
    
    return {"alerts": enriched_alerts, "count": len(alerts)}


@router.get("/alerts/{alert_id}")
def get_alert(alert_id: int, db: Session = Depends(get_db)):
    """Get specific alert details"""
    alerts, _ = watchlist_service.get_alerts(db, skip=0, limit=1)
    alert = next((a for a in alerts if a.id == alert_id), None)
    
    # Try direct query
    from ..models.watchlist import WatchlistAlert
    alert = db.query(WatchlistAlert).filter(WatchlistAlert.id == alert_id).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return {
        "id": alert.id,
        "watchlist_person_id": alert.watchlist_person_id,
        "watchlist_person": alert.watchlist_person,
        "entry_log_id": alert.entry_log_id,
        "gate_id": alert.gate_id,
        "confidence_score": alert.confidence_score,
        "severity": alert.severity.value,
        "captured_image_url": alert.captured_image_url,
        "is_acknowledged": alert.is_acknowledged,
        "acknowledged_by": alert.acknowledged_by,
        "acknowledged_at": alert.acknowledged_at,
        "is_resolved": alert.is_resolved,
        "resolution_notes": alert.resolution_notes,
        "resolved_by": alert.resolved_by,
        "resolved_at": alert.resolved_at,
        "is_false_positive": alert.is_false_positive,
        "created_at": alert.created_at
    }


@router.post("/alerts/{alert_id}/acknowledge")
def acknowledge_alert(
    alert_id: int,
    acknowledged_by: int = Query(..., description="User ID acknowledging the alert"),
    notes: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Acknowledge an alert"""
    alert = watchlist_service.acknowledge_alert(db, alert_id, acknowledged_by, notes)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"message": "Alert acknowledged", "alert_id": alert.id}


@router.post("/alerts/{alert_id}/resolve")
def resolve_alert(
    alert_id: int,
    resolve_data: WatchlistAlertResolve,
    resolved_by: int = Query(..., description="User ID resolving the alert"),
    db: Session = Depends(get_db)
):
    """Resolve an alert"""
    alert = watchlist_service.resolve_alert(
        db, alert_id, resolved_by,
        resolve_data.resolution_notes,
        resolve_data.is_false_positive
    )
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"message": "Alert resolved", "alert_id": alert.id}
