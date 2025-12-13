from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone, timedelta

from ..database import get_db
from ..models.visitor import Visitor, VisitorStatus
from ..models.entry_log import EntryLog, EntryStatus
from ..models.watchlist import WatchlistAlert
from ..models.incident import Incident, IncidentStatus, IncidentSeverity
from ..schemas.schemas import DashboardStats, DashboardRecentActivity, DashboardResponse

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get dashboard statistics"""
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    
    # Visitor stats
    total_visitors_today = db.query(Visitor).filter(
        Visitor.created_at >= today_start
    ).count()
    
    pending_approvals = db.query(Visitor).filter(
        Visitor.status == VisitorStatus.PENDING
    ).count()
    
    active_visitors = db.query(Visitor).filter(
        Visitor.status == VisitorStatus.CHECKED_IN
    ).count()
    
    # Entry stats
    total_entries_today = db.query(EntryLog).filter(
        EntryLog.timestamp >= today_start
    ).count()
    
    denied_entries_today = db.query(EntryLog).filter(
        EntryLog.timestamp >= today_start,
        EntryLog.status == EntryStatus.DENIED
    ).count()
    
    # Alert stats
    active_watchlist_alerts = db.query(WatchlistAlert).filter(
        WatchlistAlert.is_resolved == False
    ).count()
    
    # Incident stats
    open_incidents = db.query(Incident).filter(
        Incident.status.in_([
            IncidentStatus.OPEN,
            IncidentStatus.IN_PROGRESS,
            IncidentStatus.ESCALATED
        ])
    ).count()
    
    critical_incidents = db.query(Incident).filter(
        Incident.severity == IncidentSeverity.CRITICAL,
        Incident.status.in_([
            IncidentStatus.OPEN,
            IncidentStatus.IN_PROGRESS
        ])
    ).count()
    
    return {
        "total_visitors_today": total_visitors_today,
        "pending_approvals": pending_approvals,
        "active_visitors": active_visitors,
        "total_entries_today": total_entries_today,
        "denied_entries_today": denied_entries_today,
        "active_watchlist_alerts": active_watchlist_alerts,
        "open_incidents": open_incidents,
        "critical_incidents": critical_incidents
    }


@router.get("/recent-activity")
def get_recent_activity(db: Session = Depends(get_db)):
    """Get recent activity for dashboard"""
    # Recent entries (last 10)
    recent_entries = db.query(EntryLog).order_by(
        EntryLog.timestamp.desc()
    ).limit(10).all()
    
    # Recent incidents (last 10)
    recent_incidents = db.query(Incident).order_by(
        Incident.created_at.desc()
    ).limit(10).all()
    
    # Active alerts
    active_alerts = db.query(WatchlistAlert).filter(
        WatchlistAlert.is_resolved == False
    ).order_by(WatchlistAlert.created_at.desc()).all()
    
    # Enrich alerts with person info
    enriched_alerts = []
    for alert in active_alerts:
        enriched_alerts.append({
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
        })
    
    return {
        "recent_entries": recent_entries,
        "recent_incidents": recent_incidents,
        "active_alerts": enriched_alerts
    }


@router.get("/entry-trends")
def get_entry_trends(
    days: int = 7,
    db: Session = Depends(get_db)
):
    """Get entry trends for the last N days"""
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Get entries grouped by date and status
    entries = db.query(
        func.date(EntryLog.timestamp).label('date'),
        EntryLog.status,
        func.count().label('count')
    ).filter(
        EntryLog.timestamp >= start_date
    ).group_by(
        func.date(EntryLog.timestamp),
        EntryLog.status
    ).all()
    
    # Process into chart-friendly format
    trends = {}
    for entry in entries:
        date_str = str(entry.date)
        if date_str not in trends:
            trends[date_str] = {
                "date": date_str,
                "allowed": 0,
                "denied": 0,
                "watchlist_alerts": 0,
                "manual_verification": 0
            }
        
        status_key = entry.status.value.lower().replace(" ", "_")
        if status_key in trends[date_str]:
            trends[date_str][status_key] = entry.count
    
    # Sort by date
    sorted_trends = sorted(trends.values(), key=lambda x: x['date'])
    
    return {"trends": sorted_trends, "days": days}


@router.get("/incident-summary")
def get_incident_summary(db: Session = Depends(get_db)):
    """Get incident summary by category and severity"""
    # By category
    by_category = db.query(
        Incident.category,
        func.count().label('count')
    ).filter(
        Incident.status.in_([
            IncidentStatus.OPEN,
            IncidentStatus.IN_PROGRESS
        ])
    ).group_by(Incident.category).all()
    
    # By severity
    by_severity = db.query(
        Incident.severity,
        func.count().label('count')
    ).filter(
        Incident.status.in_([
            IncidentStatus.OPEN,
            IncidentStatus.IN_PROGRESS
        ])
    ).group_by(Incident.severity).all()
    
    return {
        "by_category": [{"category": c.category.value, "count": c.count} for c in by_category],
        "by_severity": [{"severity": s.severity.value, "count": s.count} for s in by_severity]
    }


@router.get("/visitor-analytics")
def get_visitor_analytics(
    days: int = 7,
    db: Session = Depends(get_db)
):
    """Get visitor analytics"""
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Visitors by type
    by_type = db.query(
        Visitor.visitor_type,
        func.count().label('count')
    ).filter(
        Visitor.created_at >= start_date
    ).group_by(Visitor.visitor_type).all()
    
    # Visitors by unit (top 10)
    by_unit = db.query(
        Visitor.visiting_unit,
        func.count().label('count')
    ).filter(
        Visitor.created_at >= start_date
    ).group_by(Visitor.visiting_unit).order_by(
        func.count().desc()
    ).limit(10).all()
    
    # Daily visitor count
    daily_count = db.query(
        func.date(Visitor.created_at).label('date'),
        func.count().label('count')
    ).filter(
        Visitor.created_at >= start_date
    ).group_by(func.date(Visitor.created_at)).all()
    
    return {
        "by_type": [{"type": t.visitor_type.value, "count": t.count} for t in by_type],
        "by_unit": [{"unit": u.visiting_unit, "count": u.count} for u in by_unit],
        "daily_count": [{"date": str(d.date), "count": d.count} for d in daily_count]
    }


@router.get("/")
def get_full_dashboard(db: Session = Depends(get_db)):
    """Get complete dashboard data"""
    stats = get_dashboard_stats(db)
    recent = get_recent_activity(db)
    
    return {
        "stats": stats,
        "recent_activity": recent,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
