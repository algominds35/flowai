from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid

from app.db.session import get_db
from app.core.deps import get_current_user, get_current_active_business
from app.models.user import User
from app.models.scenario import Scenario, ScenarioItem
from app.schemas.scenario import ScenarioCreate, ScenarioResponse
from app.services.scenarios import compute_scenario

router = APIRouter()


@router.get("", response_model=list[ScenarioResponse])
def list_scenarios(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = get_current_active_business(None, current_user, db)
    return (
        db.query(Scenario)
        .filter(Scenario.business_id == business.id)
        .order_by(Scenario.created_at.desc())
        .all()
    )


@router.post("", response_model=ScenarioResponse, status_code=201)
def create_scenario(
    scenario_in: ScenarioCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create and immediately compute a 'Can I Afford This?' scenario."""
    business = get_current_active_business(None, current_user, db)
    
    scenario = Scenario(
        business_id=business.id,
        name=scenario_in.name,
        description=scenario_in.description,
        scenario_type=scenario_in.scenario_type,
        amount=scenario_in.amount,
        start_date=scenario_in.start_date,
        end_date=scenario_in.end_date,
        frequency=scenario_in.frequency,
        additional_params=scenario_in.additional_params,
        status="draft",
    )
    db.add(scenario)
    db.flush()

    # Compute immediately
    result = compute_scenario(db, business, scenario)
    return result


@router.get("/{scenario_id}", response_model=ScenarioResponse)
def get_scenario(
    scenario_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = get_current_active_business(None, current_user, db)
    s = db.query(Scenario).filter(
        Scenario.id == uuid.UUID(scenario_id),
        Scenario.business_id == business.id,
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return s


@router.post("/{scenario_id}/recompute", response_model=ScenarioResponse)
def recompute_scenario(
    scenario_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Recompute an existing scenario with current financial data."""
    business = get_current_active_business(None, current_user, db)
    s = db.query(Scenario).filter(
        Scenario.id == uuid.UUID(scenario_id),
        Scenario.business_id == business.id,
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return compute_scenario(db, business, s)


@router.delete("/{scenario_id}", status_code=204)
def delete_scenario(
    scenario_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = get_current_active_business(None, current_user, db)
    s = db.query(Scenario).filter(
        Scenario.id == uuid.UUID(scenario_id),
        Scenario.business_id == business.id,
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail="Scenario not found")
    db.delete(s)
    db.commit()
