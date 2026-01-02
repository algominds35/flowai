"""
OpenAI GPT-4 Extraction Service
Extracts and categorizes transactions from OCR text
"""
from openai import OpenAI
from typing import List, Dict, Optional
import json
from ..core.config import settings


class ExtractionService:
    """Service for extracting transactions using OpenAI GPT-4"""
    
    def __init__(self):
        """Initialize OpenAI client"""
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    def extract_transactions(self, ocr_text: str) -> dict:
        """
        Extract transactions from OCR text using GPT-4
        
        Args:
            ocr_text: Raw text extracted from bank statement
            
        Returns:
            dict with transactions list and metadata
        """
        try:
            # Create prompt for GPT-4
            prompt = self._create_extraction_prompt(ocr_text)
            
            # Call GPT-4
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are an expert at extracting financial transactions from bank statements. Extract all transactions with date, description, amount, and balance. Return ONLY valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            # Parse response
            result = json.loads(response.choices[0].message.content)
            
            # Validate and categorize transactions
            transactions = self._validate_and_categorize(result.get('transactions', []))
            
            return {
                'transactions': transactions,
                'success': True,
                'error': None,
                'document_type': self._detect_document_type(ocr_text)
            }
            
        except Exception as e:
            return {
                'transactions': [],
                'success': False,
                'error': str(e),
                'document_type': 'UNKNOWN'
            }
    
    def _create_extraction_prompt(self, ocr_text: str) -> str:
        """Create extraction prompt for GPT-4"""
        return f"""Extract all transactions from this bank statement text.

For each transaction, extract:
- date (YYYY-MM-DD format)
- description (transaction description)
- amount (positive for credits, negative for debits)
- balance (account balance after transaction, if available)

Return JSON in this exact format:
{{
    "transactions": [
        {{
            "date": "2024-01-15",
            "description": "Amazon Purchase",
            "amount": -45.67,
            "balance": 1234.56
        }}
    ],
    "account_info": {{
        "account_number": "last 4 digits if visible",
        "statement_period": "date range if visible"
    }}
}}

Bank Statement Text:
{ocr_text[:8000]}
"""
    
    def _validate_and_categorize(self, transactions: List[Dict]) -> List[Dict]:
        """Validate and add categories to transactions"""
        categorized = []
        
        for txn in transactions:
            # Validate required fields
            if not all(key in txn for key in ['date', 'description', 'amount']):
                continue
            
            # Add category
            category = self._categorize_transaction(txn['description'])
            
            categorized.append({
                'transaction_date': txn['date'],
                'description': txn['description'],
                'amount': float(txn['amount']),
                'balance': float(txn.get('balance', 0)) if txn.get('balance') else None,
                'category': category,
                'confidence': 95  # GPT-4 is quite accurate
            })
        
        return categorized
    
    def _categorize_transaction(self, description: str) -> str:
        """Categorize transaction based on description"""
        description_lower = description.lower()
        
        # Simple rule-based categorization (can be enhanced with ML)
        if any(word in description_lower for word in ['amazon', 'walmart', 'target', 'store']):
            return 'Shopping'
        elif any(word in description_lower for word in ['restaurant', 'food', 'cafe', 'starbucks']):
            return 'Dining'
        elif any(word in description_lower for word in ['gas', 'fuel', 'shell', 'chevron']):
            return 'Transportation'
        elif any(word in description_lower for word in ['utility', 'electric', 'water', 'internet']):
            return 'Utilities'
        elif any(word in description_lower for word in ['payroll', 'salary', 'deposit']):
            return 'Income'
        elif any(word in description_lower for word in ['transfer', 'payment']):
            return 'Transfer'
        else:
            return 'Uncategorized'
    
    def _detect_document_type(self, ocr_text: str) -> str:
        """Detect if document is bank statement or credit card"""
        text_lower = ocr_text.lower()
        
        if 'credit card' in text_lower or 'visa' in text_lower or 'mastercard' in text_lower:
            return 'CREDIT_CARD'
        elif 'bank statement' in text_lower or 'checking' in text_lower or 'savings' in text_lower:
            return 'BANK_STATEMENT'
        else:
            return 'UNKNOWN'


# Global instance
extraction_service = ExtractionService()
