"""
OCR Service with AWS Textract and Tesseract fallback
Extracts text from PDF documents using AWS Textract (if configured) or Tesseract
"""
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image
import io
import logging
from typing import Optional
from ..core.config import settings

logger = logging.getLogger(__name__)


class OCRService:
    """Service for OCR processing using AWS Textract or Tesseract"""
    
    def __init__(self):
        """Initialize OCR service"""
        self.use_aws = (
            settings.AWS_ACCESS_KEY_ID != "fake-aws-key" and 
            settings.AWS_SECRET_ACCESS_KEY != "fake-aws-secret"
        )
        
        if self.use_aws:
            try:
                import boto3
                self.textract_client = boto3.client(
                    'textract',
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_REGION
                )
                logger.info("✅ Using AWS Textract for OCR")
            except Exception as e:
                logger.warning(f"Failed to initialize AWS Textract: {e}. Falling back to Tesseract.")
                self.use_aws = False
        else:
            logger.info("Using Tesseract for OCR (AWS credentials not configured)")
    
    def extract_text_from_pdf(self, pdf_bytes: bytes) -> dict:
        """
        Extract text from PDF using AWS Textract or Tesseract
        
        Args:
            pdf_bytes: PDF file content as bytes
            
        Returns:
            dict with extracted_text, confidence, and page_count
        """
        if self.use_aws:
            return self._extract_with_textract(pdf_bytes)
        else:
            return self._extract_with_tesseract(pdf_bytes)
    
    def _extract_with_tesseract(self, pdf_bytes: bytes) -> dict:
        """Extract text using Tesseract OCR"""
        try:
            # Convert PDF to images
            logger.info("Converting PDF to images...")
            images = convert_from_bytes(pdf_bytes, dpi=300)
            logger.info(f"Converted {len(images)} pages")
            
            extracted_text = []
            confidence_scores = []
            
            for i, image in enumerate(images):
                logger.info(f"Processing page {i+1}/{len(images)}")
                
                # Extract text with confidence
                data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
                
                # Get text and confidence
                page_text = []
                for j, text in enumerate(data['text']):
                    if text.strip():  # Only non-empty text
                        page_text.append(text)
                        conf = int(data['conf'][j])
                        if conf > 0:  # Only valid confidence scores
                            confidence_scores.append(conf)
                
                if page_text:
                    extracted_text.append(' '.join(page_text))
            
            # Calculate average confidence
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 85
            
            # Join all text
            full_text = '\n\n'.join(extracted_text)
            
            logger.info(f"OCR complete. Extracted {len(full_text)} characters with {avg_confidence:.1f}% confidence")
            
            return {
                'extracted_text': full_text,
                'confidence': int(avg_confidence),
                'page_count': len(images),
                'success': True,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"Tesseract OCR failed: {str(e)}")
            return {
                'extracted_text': '',
                'confidence': 0,
                'page_count': 0,
                'success': False,
                'error': str(e)
            }
    
    def _extract_with_textract(self, pdf_bytes: bytes) -> dict:
        """Extract text using AWS Textract"""
        try:
            logger.info("🚀 Using AWS Textract for OCR...")
            
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
            
            logger.info(f"✅ AWS Textract complete. Extracted {len(full_text)} characters with {avg_confidence:.1f}% confidence")
            
            return {
                'extracted_text': full_text,
                'confidence': int(avg_confidence),
                'page_count': 1,  # Detect document text processes one page
                'success': True,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"❌ AWS Textract failed: {str(e)}")
            # Fallback to Tesseract
            logger.info("Falling back to Tesseract...")
            return self._extract_with_tesseract(pdf_bytes)
    
    def extract_text_multipage(self, pdf_bytes: bytes) -> dict:
        """
        Extract text from multi-page PDF
        """
        return self.extract_text_from_pdf(pdf_bytes)


# Global instance
ocr_service = OCRService()
