from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..schemas.schemas import (
    VisitorCreate, VisitorUpdate, VisitorResponse,
    VisitorListResponse, VisitorStatus
)
from ..services.visitor_service import visitor_service

router = APIRouter(prefix="/visitors", tags=["Visitors"])


@router.post("/", response_model=VisitorResponse)
def create_visitor(
    visitor_data: VisitorCreate,
    approved_by: int = Query(..., description="ID of user approving the visitor"),
    db: Session = Depends(get_db)
):
    """
    Create a new pre-approved visitor.
    Optionally includes face image for recognition.
    """
    visitor, details = visitor_service.create_visitor(db, visitor_data, approved_by)
    
    if not visitor:
        raise HTTPException(status_code=400, detail=details.get("error", "Failed to create visitor"))
    
    return visitor


@router.get("/", response_model=VisitorListResponse)
def list_visitors(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[VisitorStatus] = None,
    approved_by: Optional[int] = None,
    visiting_unit: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get list of visitors with optional filters"""
    visitors, total = visitor_service.get_visitors(
        db, skip, limit, status, approved_by, visiting_unit, search
    )
    
    return VisitorListResponse(
        visitors=visitors,
        total=total,
        page=skip // limit + 1,
        page_size=limit
    )


@router.get("/active")
def get_active_visitors(db: Session = Depends(get_db)):
    """Get all currently checked-in visitors"""
    visitors = visitor_service.get_active_visitors(db)
    return {"visitors": visitors, "count": len(visitors)}


@router.get("/today")
def get_todays_visitors(db: Session = Depends(get_db)):
    """Get all visitors for today"""
    visitors = visitor_service.get_todays_visitors(db)
    return {"visitors": visitors, "count": len(visitors)}


@router.get("/code/{approval_code}", response_model=VisitorResponse)
def get_visitor_by_code(approval_code: str, db: Session = Depends(get_db)):
    """Get visitor by approval code"""
    visitor = visitor_service.get_visitor_by_code(db, approval_code)
    if not visitor:
        raise HTTPException(status_code=404, detail="Visitor not found")
    return visitor


@router.get("/{visitor_id}", response_model=VisitorResponse)
def get_visitor(visitor_id: int, db: Session = Depends(get_db)):
    """Get visitor by ID"""
    visitor = visitor_service.get_visitor(db, visitor_id)
    if not visitor:
        raise HTTPException(status_code=404, detail="Visitor not found")
    return visitor


@router.patch("/{visitor_id}", response_model=VisitorResponse)
def update_visitor(
    visitor_id: int,
    update_data: VisitorUpdate,
    db: Session = Depends(get_db)
):
    """Update visitor details"""
    visitor = visitor_service.update_visitor(db, visitor_id, update_data)
    if not visitor:
        raise HTTPException(status_code=404, detail="Visitor not found")
    return visitor


@router.post("/{visitor_id}/check-in", response_model=VisitorResponse)
def check_in_visitor(visitor_id: int, db: Session = Depends(get_db)):
    """Mark visitor as checked in"""
    visitor = visitor_service.check_in_visitor(db, visitor_id)
    if not visitor:
        raise HTTPException(status_code=404, detail="Visitor not found")
    return visitor


@router.post("/{visitor_id}/check-out", response_model=VisitorResponse)
def check_out_visitor(visitor_id: int, db: Session = Depends(get_db)):
    """Mark visitor as checked out"""
    visitor = visitor_service.check_out_visitor(db, visitor_id)
    if not visitor:
        raise HTTPException(status_code=404, detail="Visitor not found")
    return visitor


@router.post("/{visitor_id}/cancel", response_model=VisitorResponse)
def cancel_visitor(visitor_id: int, db: Session = Depends(get_db)):
    """Cancel visitor approval"""
    visitor = visitor_service.cancel_visitor(db, visitor_id)
    if not visitor:
        raise HTTPException(status_code=404, detail="Visitor not found")
    return visitor


@router.post("/expire-old")
def expire_old_approvals(db: Session = Depends(get_db)):
    """Expire all approvals past their valid_until time"""
    count = visitor_service.expire_old_approvals(db)
    return {"expired_count": count}
