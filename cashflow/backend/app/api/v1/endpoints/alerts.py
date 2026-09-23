from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import uuid

from app.db.session import get_db
from app.core.deps import get_current_user, get_current_active_business
from app.models.user import User
from app.models.alert import Alert, AlertType
from app.schemas.alert import AlertResponse
from app.services.alerts import generate_alerts

router = APIRouter()


@router.get("", response_model=list[AlertResponse])
def list_alerts(
    unread_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = get_current_active_business(None, current_user, db)
    q = db.query(Alert).filter(
        Alert.business_id == business.id,
        Alert.is_dismissed == False,
    )
    if unread_only:
        q = q.filter(Alert.is_read == False)
    return q.order_by(Alert.fired_at.desc()).all()


@router.post("/generate", response_model=list[AlertResponse])
def trigger_alert_generation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manually trigger alert generation (also runs automatically via scheduler)."""
    business = get_current_active_business(None, current_user, db)
    alerts = generate_alerts(db, business)
    return [a for a in alerts if a is not None]


@router.post("/{alert_id}/read", response_model=AlertResponse)
def mark_alert_read(
    alert_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = get_current_active_business(None, current_user, db)
    alert = db.query(Alert).filter(
        Alert.id == uuid.UUID(alert_id),
        Alert.business_id == business.id,
    ).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_read = True
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


@router.post("/{alert_id}/dismiss", response_model=AlertResponse)
def dismiss_alert(
    alert_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = get_current_active_business(None, current_user, db)
    alert = db.query(Alert).filter(
        Alert.id == uuid.UUID(alert_id),
        Alert.business_id == business.id,
    ).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_dismissed = True
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


@router.post("/{alert_id}/resolve", response_model=AlertResponse)
def resolve_alert(
    alert_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = get_current_active_business(None, current_user, db)
    alert = db.query(Alert).filter(
        Alert.id == uuid.UUID(alert_id),
        Alert.business_id == business.id,
    ).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_resolved = True
    alert.resolved_at = datetime.now(timezone.utc)
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


@router.get("/count")
def get_alert_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = get_current_active_business(None, current_user, db)
    count = db.query(Alert).filter(
        Alert.business_id == business.id,
        Alert.is_dismissed == False,
        Alert.is_read == False,
    ).count()
    return {"unread_count": count}
