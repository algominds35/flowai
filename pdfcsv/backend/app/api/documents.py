from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session, joinedload
from typing import List
import os
import uuid
import logging

from ..core.database import get_db
from ..models.user import User
from ..models.document import Document, DocumentStatus
from ..schemas.document import DocumentResponse, DocumentListResponse
from .auth import get_current_user
from ..services.processing_service import processing_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a PDF document for processing"""
    
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported"
        )
    
    # Read file content
    content = await file.read()
    file_size = len(content)
    
    # Check file size (max 10MB for now)
    if file_size > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size must be less than 10MB"
        )
    
    # Generate unique filename
    file_ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    
    # TODO: Upload to S3/R2
    # For now, we'll store locally in a temp directory
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, unique_filename)
    
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Create document record
    document = Document(
        user_id=current_user.id,
        filename=file.filename,
        file_path=file_path,
        file_size=file_size,
        status=DocumentStatus.UPLOADED
    )
    
    db.add(document)
    db.commit()
    db.refresh(document)
    
    # Process document in background
    logger.info(f"Queuing document {document.id} for processing")
    background_tasks.add_task(
        _process_document_task,
        document_id=document.id,
        pdf_bytes=content,
        db=db
    )
    
    return document


async def _process_document_task(document_id: int, pdf_bytes: bytes, db: Session):
    """Background task to process document"""
    try:
        result = await processing_service.process_document(document_id, pdf_bytes, db)
        if result['success']:
            logger.info(f"Document {document_id} processed successfully")
        else:
            logger.error(f"Document {document_id} processing failed: {result.get('error')}")
    except Exception as e:
        logger.error(f"Error in background processing for document {document_id}: {str(e)}")


@router.get("/", response_model=DocumentListResponse)
def list_documents(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all documents for current user"""
    
    total = db.query(Document).filter(Document.user_id == current_user.id).count()
    
    documents = (
        db.query(Document)
        .options(joinedload(Document.transactions))
        .filter(Document.user_id == current_user.id)
        .order_by(Document.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    # DEBUG: Log transaction counts
    for doc in documents:
        logger.info(f"🔍 Document {doc.id}: {len(doc.transactions)} transactions")
    
    return {"documents": documents, "total": total}


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific document with transactions"""
    
    document = db.query(Document).options(
        joinedload(Document.transactions)
    ).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # DEBUG: Log transaction count
    logger.info(f"🔍 Document {document_id}: {len(document.transactions)} transactions loaded")
    logger.info(f"🔍 Transaction IDs: {[t.id for t in document.transactions]}")
    
    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a document"""
    
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # TODO: Delete file from S3/R2
    if os.path.exists(document.file_path):
        os.remove(document.file_path)
    
    db.delete(document)
    db.commit()
    
    return None


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
def delete_all_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete all documents for current user (for debugging)"""
    
    documents = db.query(Document).filter(Document.user_id == current_user.id).all()
    
    for document in documents:
        # Delete file if exists
        if os.path.exists(document.file_path):
            try:
                os.remove(document.file_path)
            except:
                pass
        db.delete(document)
    
    db.commit()
    logger.info(f"Deleted {len(documents)} documents for user {current_user.id}")
    
    return None
