from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date

from app.db.session import get_db
from app.core.deps import get_current_user, get_current_active_business
from app.models.user import User
from app.services.forecast import compute_and_save_forecast, get_current_forecast
from app.schemas.forecast import ForecastSnapshotResponse

router = APIRouter()


@router.get("/current", response_model=ForecastSnapshotResponse)
def get_current_forecast_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the most recent saved forecast snapshot."""
    business = get_current_active_business(None, current_user, db)
    snapshot = get_current_forecast(db, business)
    if not snapshot:
        # Compute on demand if none exists
        snapshot = compute_and_save_forecast(db, business, horizon_weeks=13)
    return snapshot


@router.post("/compute", response_model=ForecastSnapshotResponse)
def compute_forecast(
    horizon_weeks: int = Query(default=13, ge=4, le=26),
    as_of_date: date | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Compute and save a new forecast snapshot."""
    business = get_current_active_business(None, current_user, db)
    snapshot = compute_and_save_forecast(
        db=db,
        business=business,
        horizon_weeks=horizon_weeks,
        as_of_date=as_of_date,
    )
    return snapshot


@router.get("/history", response_model=list[ForecastSnapshotResponse])
def forecast_history(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get historical forecast snapshots for variance tracking."""
    business = get_current_active_business(None, current_user, db)
    from app.models.forecast import ForecastSnapshot
    snapshots = (
        db.query(ForecastSnapshot)
        .filter(ForecastSnapshot.business_id == business.id)
        .order_by(ForecastSnapshot.computed_at.desc())
        .limit(limit)
        .all()
    )
    return snapshots
