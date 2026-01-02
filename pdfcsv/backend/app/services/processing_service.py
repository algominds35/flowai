"""
Document Processing Pipeline
Orchestrates OCR and extraction services
"""
from sqlalchemy.orm import Session
from typing import Optional
from ..models.document import Document, DocumentStatus, DocumentType
from ..models.transaction import Transaction
from .ocr_service import ocr_service
from .extraction_service import extraction_service
import logging

logger = logging.getLogger(__name__)


class ProcessingService:
    """Main service for processing documents"""
    
    async def process_document(self, document_id: int, pdf_bytes: bytes, db: Session) -> dict:
        """
        Process a document through OCR and extraction pipeline
        
        Args:
            document_id: Document ID in database
            pdf_bytes: PDF file content
            db: Database session
            
        Returns:
            dict with processing results
        """
        try:
            # Get document
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                return {'success': False, 'error': 'Document not found'}
            
            # Update status to PROCESSING
            document.status = DocumentStatus.PROCESSING
            db.commit()
            
            # Step 1: OCR Extraction
            logger.info(f"Starting OCR for document {document_id}")
            ocr_result = ocr_service.extract_text_from_pdf(pdf_bytes)
            
            if not ocr_result['success']:
                document.status = DocumentStatus.ERROR
                document.error_message = f"OCR failed: {ocr_result['error']}"
                db.commit()
                return {'success': False, 'error': ocr_result['error']}
            
            # Update document with OCR results
            document.ocr_text = ocr_result['extracted_text']
            document.ocr_confidence = ocr_result['confidence']
            document.page_count = ocr_result['page_count']
            document.status = DocumentStatus.OCR_COMPLETE
            db.commit()
            
            # Step 2: Transaction Extraction with GPT-4
            logger.info(f"Starting extraction for document {document_id}")
            extraction_result = extraction_service.extract_transactions(ocr_result['extracted_text'])
            
            if not extraction_result['success']:
                document.status = DocumentStatus.ERROR
                document.error_message = f"Extraction failed: {extraction_result['error']}"
                db.commit()
                return {'success': False, 'error': extraction_result['error']}
            
            # Set document type
            if extraction_result['document_type'] == 'CREDIT_CARD':
                document.document_type = DocumentType.CREDIT_CARD
            elif extraction_result['document_type'] == 'BANK_STATEMENT':
                document.document_type = DocumentType.BANK_STATEMENT
            else:
                document.document_type = DocumentType.UNKNOWN
            
            # Step 3: Save transactions
            logger.info(f"Saving {len(extraction_result['transactions'])} transactions for document {document_id}")
            transaction_count = 0
            
            for txn_data in extraction_result['transactions']:
                transaction = Transaction(
                    document_id=document.id,
                    transaction_date=txn_data['transaction_date'],
                    description=txn_data['description'],
                    amount=txn_data['amount'],
                    balance=txn_data.get('balance'),
                    category=txn_data['category']
                )
                db.add(transaction)
                transaction_count += 1
            
            # Update document status
            document.status = DocumentStatus.READY
            db.commit()
            
            logger.info(f"Document {document_id} processed successfully. {transaction_count} transactions extracted.")
            
            return {
                'success': True,
                'document_id': document_id,
                'transaction_count': transaction_count,
                'ocr_confidence': ocr_result['confidence'],
                'document_type': extraction_result['document_type']
            }
            
        except Exception as e:
            logger.error(f"Error processing document {document_id}: {str(e)}")
            
            # Update document status to error
            document = db.query(Document).filter(Document.id == document_id).first()
            if document:
                document.status = DocumentStatus.ERROR
                document.error_message = str(e)
                db.commit()
            
            return {'success': False, 'error': str(e)}


# Global instance
processing_service = ProcessingService()
