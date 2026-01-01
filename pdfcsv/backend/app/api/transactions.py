from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..core.database import get_db
from ..models.user import User
from ..models.transaction import Transaction
from ..models.document import Document
from ..schemas.transaction import TransactionUpdate, TransactionBulkUpdate
from ..schemas.document import TransactionResponse
from .auth import get_current_user

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific transaction"""
    
    transaction = (
        db.query(Transaction)
        .join(Document)
        .filter(
            Transaction.id == transaction_id,
            Document.user_id == current_user.id
        )
        .first()
    )
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    return transaction


@router.patch("/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: int,
    update_data: TransactionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a transaction"""
    
    transaction = (
        db.query(Transaction)
        .join(Document)
        .filter(
            Transaction.id == transaction_id,
            Document.user_id == current_user.id
        )
        .first()
    )
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    # Update fields
    update_dict = update_data.dict(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(transaction, field, value)
    
    db.commit()
    db.refresh(transaction)
    
    return transaction


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a transaction"""
    
    transaction = (
        db.query(Transaction)
        .join(Document)
        .filter(
            Transaction.id == transaction_id,
            Document.user_id == current_user.id
        )
        .first()
    )
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    db.delete(transaction)
    db.commit()
    
    return None


@router.post("/bulk-update", response_model=List[TransactionResponse])
def bulk_update_transactions(
    bulk_data: TransactionBulkUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Bulk update multiple transactions"""
    
    transactions = (
        db.query(Transaction)
        .join(Document)
        .filter(
            Transaction.id.in_(bulk_data.transaction_ids),
            Document.user_id == current_user.id
        )
        .all()
    )
    
    if not transactions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No transactions found"
        )
    
    # Update all transactions
    for transaction in transactions:
        if bulk_data.category is not None:
            transaction.category = bulk_data.category
        if bulk_data.is_verified is not None:
            transaction.is_verified = bulk_data.is_verified
    
    db.commit()
    
    # Refresh all
    for transaction in transactions:
        db.refresh(transaction)
    
    return transactions
