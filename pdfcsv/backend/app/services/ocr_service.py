"""
Tesseract OCR Service (Free, Local)
Extracts text from PDF documents using Tesseract
"""
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image
import io
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class OCRService:
    """Service for OCR processing using Tesseract (free)"""
    
    def __init__(self):
        """Initialize Tesseract OCR service"""
        logger.info("Using Tesseract for OCR (free, local)")
    
    def extract_text_from_pdf(self, pdf_bytes: bytes) -> dict:
        """
        Extract text from PDF using Tesseract OCR
        
        Args:
            pdf_bytes: PDF file content as bytes
            
        Returns:
            dict with extracted_text, confidence, and page_count
        """
        try:
            # Convert PDF to images
            logger.info("Converting PDF to images...")
            images = convert_from_bytes(pdf_bytes, dpi=300)  # Higher DPI = better quality
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
    
    def extract_text_multipage(self, pdf_bytes: bytes) -> dict:
        """
        Extract text from multi-page PDF
        (Same as extract_text_from_pdf for Tesseract)
        """
        return self.extract_text_from_pdf(pdf_bytes)


# Global instance
ocr_service = OCRService()
