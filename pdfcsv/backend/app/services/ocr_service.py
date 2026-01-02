"""
AWS Textract OCR Service
Extracts text from PDF documents using AWS Textract
"""
import boto3
import io
from typing import Optional
from ..core.config import settings


class OCRService:
    """Service for OCR processing using AWS Textract"""
    
    def __init__(self):
        """Initialize AWS Textract client"""
        self.textract_client = boto3.client(
            'textract',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
    
    def extract_text_from_pdf(self, pdf_bytes: bytes) -> dict:
        """
        Extract text from PDF using AWS Textract
        
        Args:
            pdf_bytes: PDF file content as bytes
            
        Returns:
            dict with extracted_text, confidence, and page_count
        """
        try:
            # Call Textract
            response = self.textract_client.detect_document_text(
                Document={'Bytes': pdf_bytes}
            )
            
            # Extract text and confidence
            extracted_text = []
            confidence_scores = []
            
            for block in response['Blocks']:
                if block['BlockType'] == 'LINE':
                    extracted_text.append(block['Text'])
                    if 'Confidence' in block:
                        confidence_scores.append(block['Confidence'])
            
            # Calculate average confidence
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
            
            # Join all text
            full_text = '\n'.join(extracted_text)
            
            return {
                'extracted_text': full_text,
                'confidence': int(avg_confidence),
                'page_count': 1,  # Detect document text processes one page
                'success': True,
                'error': None
            }
            
        except Exception as e:
            return {
                'extracted_text': '',
                'confidence': 0,
                'page_count': 0,
                'success': False,
                'error': str(e)
            }
    
    def extract_text_multipage(self, pdf_bytes: bytes) -> dict:
        """
        Extract text from multi-page PDF using AWS Textract (async)
        For documents with more than 1 page
        
        Args:
            pdf_bytes: PDF file content as bytes
            
        Returns:
            dict with extracted_text, confidence, and page_count
        """
        # For MVP, we'll use the simple detect_document_text
        # In production, you'd use start_document_text_detection for multi-page
        return self.extract_text_from_pdf(pdf_bytes)


# Global instance
ocr_service = OCRService()
