from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_user, get_current_active_business
from app.models.user import User
from app.models.business import Business, BusinessMember
from app.schemas.business import BusinessCreate, BusinessUpdate, BusinessResponse, OnboardingStep

router = APIRouter()


@router.post("", response_model=BusinessResponse, status_code=201)
def create_business(
    business_in: BusinessCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new business and make the current user the owner."""
    business = Business(
        name=business_in.name,
        industry=business_in.industry,
        currency=business_in.currency,
        minimum_cash_reserve=business_in.minimum_cash_reserve,
        fiscal_year_start_month=business_in.fiscal_year_start_month,
        onboarding_step=1,
    )
    db.add(business)
    db.flush()

    member = BusinessMember(
        business_id=business.id,
        user_id=current_user.id,
        role="owner",
        is_primary=True,
    )
    db.add(member)
    db.commit()
    db.refresh(business)
    return business


@router.get("/mine", response_model=list[BusinessResponse])
def list_my_businesses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all businesses the current user belongs to."""
    memberships = (
        db.query(BusinessMember)
        .filter(BusinessMember.user_id == current_user.id)
        .all()
    )
    return [m.business for m in memberships]


@router.get("/{business_id}", response_model=BusinessResponse)
def get_business(
    business_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = get_current_active_business(business_id, current_user, db)
    return business


@router.patch("/{business_id}", response_model=BusinessResponse)
def update_business(
    business_id: str,
    business_in: BusinessUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = get_current_active_business(business_id, current_user, db)
    
    update_data = business_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(business, field, value)
    
    db.add(business)
    db.commit()
    db.refresh(business)
    return business


@router.post("/{business_id}/onboarding", response_model=BusinessResponse)
def update_onboarding(
    business_id: str,
    step: OnboardingStep,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Advance the onboarding step."""
    business = get_current_active_business(business_id, current_user, db)
    business.onboarding_step = step.step
    
    if step.step >= 5:  # 5 steps in onboarding
        business.onboarding_completed = True
    
    db.add(business)
    db.commit()
    db.refresh(business)
    return business
