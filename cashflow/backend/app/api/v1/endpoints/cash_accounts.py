from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
import uuid

from app.db.session import get_db
from app.core.deps import get_current_user, get_current_active_business
from app.models.user import User
from app.models.cash_account import CashAccount, CashAccountSnapshot
from app.schemas.cash_account import CashAccountCreate, CashAccountUpdate, CashAccountResponse

router = APIRouter()


@router.get("", response_model=list[CashAccountResponse])
def list_cash_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = get_current_active_business(None, current_user, db)
    return db.query(CashAccount).filter(
        CashAccount.business_id == business.id,
        CashAccount.is_active == True,
    ).order_by(CashAccount.created_at).all()


@router.post("", response_model=CashAccountResponse, status_code=201)
def create_cash_account(
    account_in: CashAccountCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = get_current_active_business(None, current_user, db)
    account = CashAccount(
        business_id=business.id,
        name=account_in.name,
        account_type=account_in.account_type,
        institution_name=account_in.institution_name,
        last_four=account_in.last_four,
        current_balance=account_in.current_balance,
        balance_as_of=account_in.balance_as_of or date.today(),
        include_in_cash_position=account_in.include_in_cash_position,
    )
    db.add(account)
    db.flush()

    # Record initial snapshot
    if account_in.current_balance:
        snapshot = CashAccountSnapshot(
            account_id=account.id,
            snapshot_date=account_in.balance_as_of or date.today(),
            balance=account_in.current_balance,
            source="manual",
        )
        db.add(snapshot)

    db.commit()
    db.refresh(account)
    return account


@router.patch("/{account_id}", response_model=CashAccountResponse)
def update_cash_account(
    account_id: str,
    account_in: CashAccountUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = get_current_active_business(None, current_user, db)
    account = db.query(CashAccount).filter(
        CashAccount.id == uuid.UUID(account_id),
        CashAccount.business_id == business.id,
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    update_data = account_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(account, field, value)

    # Record snapshot if balance changed
    if account_in.current_balance is not None:
        snap_date = account_in.balance_as_of or date.today()
        existing_snap = db.query(CashAccountSnapshot).filter(
            CashAccountSnapshot.account_id == account.id,
            CashAccountSnapshot.snapshot_date == snap_date,
        ).first()
        if not existing_snap:
            db.add(CashAccountSnapshot(
                account_id=account.id,
                snapshot_date=snap_date,
                balance=account_in.current_balance,
                source="manual",
            ))

    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.delete("/{account_id}", status_code=204)
def delete_cash_account(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = get_current_active_business(None, current_user, db)
    account = db.query(CashAccount).filter(
        CashAccount.id == uuid.UUID(account_id),
        CashAccount.business_id == business.id,
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    account.is_active = False
    db.add(account)
    db.commit()
