from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import uuid

from app.db.session import get_db
from app.core.deps import get_current_user, get_current_active_business
from app.models.user import User
from app.models.weekly_review import WeeklyReviewSession, WeeklyReviewItem
from app.schemas.weekly_review import (
    WeeklyReviewSessionResponse,
    WeeklyReviewItemResponse,
    WeeklyReviewActionRequest,
)
from app.services.weekly_review import create_weekly_review, action_review_item

router = APIRouter()


@router.post("/start", response_model=WeeklyReviewSessionResponse)
def start_weekly_review(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Start (or resume) the weekly review session."""
    business = get_current_active_business(None, current_user, db)
    session = create_weekly_review(db, business)
    
    if session.status == "pending":
        session.status = "in_progress"
        session.started_at = datetime.now(timezone.utc)
        db.add(session)
        db.commit()
        db.refresh(session)
    
    return session


@router.get("/current", response_model=WeeklyReviewSessionResponse | None)
def get_current_review(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = get_current_active_business(None, current_user, db)
    session = (
        db.query(WeeklyReviewSession)
        .filter(
            WeeklyReviewSession.business_id == business.id,
            WeeklyReviewSession.status != "completed",
        )
        .order_by(WeeklyReviewSession.created_at.desc())
        .first()
    )
    return session


@router.get("/{session_id}", response_model=WeeklyReviewSessionResponse)
def get_review_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = get_current_active_business(None, current_user, db)
    session = db.query(WeeklyReviewSession).filter(
        WeeklyReviewSession.id == uuid.UUID(session_id),
        WeeklyReviewSession.business_id == business.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Review session not found")
    return session


@router.post("/{session_id}/items/{item_id}/action", response_model=WeeklyReviewItemResponse)
def action_item(
    session_id: str,
    item_id: str,
    action_request: WeeklyReviewActionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = get_current_active_business(None, current_user, db)
    session = db.query(WeeklyReviewSession).filter(
        WeeklyReviewSession.id == uuid.UUID(session_id),
        WeeklyReviewSession.business_id == business.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Review session not found")

    item = db.query(WeeklyReviewItem).filter(
        WeeklyReviewItem.id == uuid.UUID(item_id),
        WeeklyReviewItem.session_id == session.id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Review item not found")

    updated_item = action_review_item(
        db=db,
        item=item,
        action=action_request.action,
        confirmed_amount=action_request.confirmed_amount,
        confirmed_date=action_request.confirmed_date,
        match_transaction_id=action_request.match_transaction_id,
        user_id=current_user.id,
    )
    return updated_item


@router.post("/{session_id}/complete", response_model=WeeklyReviewSessionResponse)
def complete_review(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = get_current_active_business(None, current_user, db)
    session = db.query(WeeklyReviewSession).filter(
        WeeklyReviewSession.id == uuid.UUID(session_id),
        WeeklyReviewSession.business_id == business.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Review session not found")
    
    session.status = "completed"
    session.completed_at = datetime.now(timezone.utc)
    session.completed_by_user_id = current_user.id
    db.add(session)
    db.commit()
    db.refresh(session)
    return session
