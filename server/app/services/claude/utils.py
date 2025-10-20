"""
Utility functions for Claude Document AI service.

This module provides helper functions for PDF processing, token estimation,
error handling, and quality assessment.
"""

import os
import base64
import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import json
import re

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    logging.warning("PyMuPDF not available. PDF processing will be limited.")

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    logging.warning("tiktoken not available. Token estimation will be approximate.")

logger = logging.getLogger(__name__)


class ClaudePDFProcessor:
    """Handles PDF processing for Claude API"""
    
    @staticmethod
    def get_pdf_info(file_path: str) -> Dict[str, Any]:
        """Get PDF file information"""
        try:
            file_size_bytes = os.path.getsize(file_path)
            file_size_mb = file_size_bytes / (1024 * 1024)
            
            if not PYMUPDF_AVAILABLE:
                return {
                    'file_size_bytes': file_size_bytes,
                    'file_size_mb': file_size_mb,
                    'page_count': 0,
                    'error': 'PyMuPDF not available'
                }
            
            doc = fitz.open(file_path)
            page_count = len(doc)
            doc.close()
            
            return {
                'file_size_bytes': file_size_bytes,
                'file_size_mb': file_size_mb,
                'page_count': page_count,
                'is_large_file': file_size_mb > 20 or page_count > 50
            }
        except Exception as e:
            logger.error(f"Error getting PDF info: {e}")
            return {
                'file_size_bytes': 0,
                'file_size_mb': 0,
                'page_count': 0,
                'error': str(e)
            }
    
    @staticmethod
    def encode_pdf_to_base64(file_path: str) -> str:
        """Encode PDF file to base64 for API transmission"""
        try:
            with open(file_path, 'rb') as f:
                pdf_data = f.read()
            return base64.b64encode(pdf_data).decode('utf-8')
        except Exception as e:
            logger.error(f"Error encoding PDF to base64: {e}")
            raise
    
    @staticmethod
    def validate_pdf_size(file_path: str, max_size_mb: int = 32) -> Tuple[bool, Optional[str]]:
        """Validate PDF size against Claude's limits"""
        try:
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            
            if file_size_mb > max_size_mb:
                return False, f"File size {file_size_mb:.2f}MB exceeds maximum {max_size_mb}MB"
            
            return True, None
        except Exception as e:
            return False, f"Error validating file size: {str(e)}"
    
    @staticmethod
    def validate_pdf_pages(file_path: str, max_pages: int = 100) -> Tuple[bool, Optional[str]]:
        """Validate PDF page count against Claude's limits"""
        try:
            if not PYMUPDF_AVAILABLE:
                return True, None  # Skip validation if PyMuPDF not available
            
            doc = fitz.open(file_path)
            page_count = len(doc)
            doc.close()
            
            if page_count > max_pages:
                return False, f"Document has {page_count} pages, exceeds maximum {max_pages}"
            
            return True, None
        except Exception as e:
            return False, f"Error validating page count: {str(e)}"
    
    @staticmethod
    def chunk_large_pdf(file_path: str, max_pages_per_chunk: int = 50) -> List[Dict[str, Any]]:
        """
        Split large PDF into smaller chunks while preserving context.
        Returns list of chunk information.
        """
        try:
            if not PYMUPDF_AVAILABLE:
                raise ValueError("PyMuPDF required for PDF chunking")
            
            doc = fitz.open(file_path)
            total_pages = len(doc)
            doc.close()
            
            chunks = []
            for i in range(0, total_pages, max_pages_per_chunk):
                chunk_start = i
                chunk_end = min(i + max_pages_per_chunk, total_pages)
                
                chunks.append({
                    'chunk_index': len(chunks),
                    'total_chunks': (total_pages + max_pages_per_chunk - 1) // max_pages_per_chunk,
                    'page_range': [chunk_start, chunk_end],
                    'page_count': chunk_end - chunk_start
                })
            
            return chunks
        except Exception as e:
            logger.error(f"Error chunking PDF: {e}")
            raise


class ClaudeTokenEstimator:
    """Estimates token usage for cost optimization"""
    
    def __init__(self):
        self.encoder = None
        if TIKTOKEN_AVAILABLE:
            try:
                # Use cl100k_base encoding (similar to Claude's tokenization)
                self.encoder = tiktoken.get_encoding("cl100k_base")
            except Exception as e:
                logger.warning(f"Could not initialize tiktoken encoder: {e}")
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text"""
        if self.encoder:
            return len(self.encoder.encode(text))
        else:
            # Rough approximation: ~4 characters per token
            return len(text) // 4
    
    def estimate_pdf_tokens(self, file_path: str) -> Dict[str, Any]:
        """Estimate token usage for PDF processing"""
        try:
            pdf_info = ClaudePDFProcessor.get_pdf_info(file_path)
            
            # Rough estimation: ~500-1000 tokens per page for typical documents
            estimated_input_tokens = pdf_info.get('page_count', 0) * 750
            # Assume output is ~30% of input for table extraction
            estimated_output_tokens = int(estimated_input_tokens * 0.3)
            
            return {
                'estimated_input_tokens': estimated_input_tokens,
                'estimated_output_tokens': estimated_output_tokens,
                'estimated_total_tokens': estimated_input_tokens + estimated_output_tokens,
                'page_count': pdf_info.get('page_count', 0)
            }
        except Exception as e:
            logger.error(f"Error estimating PDF tokens: {e}")
            return {
                'estimated_input_tokens': 0,
                'estimated_output_tokens': 0,
                'estimated_total_tokens': 0,
                'error': str(e)
            }


class ClaudeResponseParser:
    """Parses and validates Claude API responses"""
    
    @staticmethod
    def parse_json_response(response_text: str) -> Optional[Dict[str, Any]]:
        """Parse JSON response from Claude, handling various formats"""
        try:
            # Clean response text
            cleaned = response_text.strip()
            
            # Remove markdown code blocks if present
            if cleaned.startswith('```json'):
                cleaned = cleaned[7:]
            elif cleaned.startswith('```'):
                cleaned = cleaned[3:]
            
            if cleaned.endswith('```'):
                cleaned = cleaned[:-3]
            
            cleaned = cleaned.strip()
            
            # Parse JSON
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            logger.error(f"Response text: {response_text[:500]}")
            
            # Try to extract JSON using regex as fallback
            try:
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(0))
            except Exception as regex_error:
                logger.error(f"Regex extraction also failed: {regex_error}")
            
            return None
        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            return None
    
    @staticmethod
    def validate_table_structure(table_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate extracted table structure"""
        required_fields = ['headers', 'rows']
        
        for field in required_fields:
            if field not in table_data:
                return False, f"Missing required field: {field}"
        
        headers = table_data.get('headers', [])
        rows = table_data.get('rows', [])
        
        if not isinstance(headers, list):
            return False, "Headers must be a list"
        
        if not isinstance(rows, list):
            return False, "Rows must be a list"
        
        # Check that all rows have the same number of columns as headers
        header_count = len(headers)
        for i, row in enumerate(rows):
            if not isinstance(row, list):
                return False, f"Row {i} must be a list"
            
            if len(row) != header_count:
                logger.warning(f"Row {i} has {len(row)} columns, expected {header_count}")
                # Don't fail validation, just log warning
        
        return True, None


class ClaudeQualityAssessor:
    """Assesses quality of Claude extractions"""
    
    @staticmethod
    def assess_extraction_quality(
        tables: List[Dict[str, Any]],
        document_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess overall extraction quality"""
        try:
            # Calculate various quality metrics
            table_count = len(tables)
            
            if table_count == 0:
                return {
                    'overall_confidence': 0.0,
                    'table_structure_score': 0.0,
                    'data_completeness': 0.0,
                    'extraction_accuracy': 0.0,
                    'issues_detected': ['No tables extracted'],
                    'quality_grade': 'F'
                }
            
            # Assess table structure
            structure_scores = []
            completeness_scores = []
            
            for table in tables:
                # Structure score based on headers and row consistency
                headers = table.get('headers', [])
                rows = table.get('rows', [])
                
                if headers and rows:
                    structure_scores.append(1.0)
                    
                    # Completeness: percentage of non-empty cells
                    total_cells = len(headers) * len(rows)
                    non_empty_cells = sum(
                        1 for row in rows for cell in row if cell and str(cell).strip()
                    )
                    completeness = non_empty_cells / total_cells if total_cells > 0 else 0
                    completeness_scores.append(completeness)
                else:
                    structure_scores.append(0.5)
                    completeness_scores.append(0.5)
            
            avg_structure = sum(structure_scores) / len(structure_scores) if structure_scores else 0
            avg_completeness = sum(completeness_scores) / len(completeness_scores) if completeness_scores else 0
            
            # Calculate overall confidence
            metadata_confidence = document_metadata.get('carrier_confidence', 0.5)
            overall_confidence = (avg_structure + avg_completeness + metadata_confidence) / 3
            
            # Determine quality grade
            if overall_confidence >= 0.95:
                quality_grade = 'A'
            elif overall_confidence >= 0.85:
                quality_grade = 'B'
            elif overall_confidence >= 0.75:
                quality_grade = 'C'
            elif overall_confidence >= 0.65:
                quality_grade = 'D'
            else:
                quality_grade = 'F'
            
            # Detect issues
            issues = []
            if avg_completeness < 0.7:
                issues.append('Low data completeness detected')
            if avg_structure < 0.8:
                issues.append('Inconsistent table structures')
            if metadata_confidence < 0.7:
                issues.append('Low confidence in metadata extraction')
            
            return {
                'overall_confidence': round(overall_confidence, 2),
                'table_structure_score': round(avg_structure, 2),
                'data_completeness': round(avg_completeness, 2),
                'extraction_accuracy': round(overall_confidence, 2),
                'issues_detected': issues,
                'quality_grade': quality_grade,
                'table_count': table_count
            }
        except Exception as e:
            logger.error(f"Error assessing quality: {e}")
            return {
                'overall_confidence': 0.5,
                'table_structure_score': 0.5,
                'data_completeness': 0.5,
                'extraction_accuracy': 0.5,
                'issues_detected': [f'Error during assessment: {str(e)}'],
                'quality_grade': 'C'
            }


class ClaudeErrorHandler:
    """Handles errors and retries for Claude API calls"""
    
    @staticmethod
    def is_retriable_error(error: Exception) -> bool:
        """Determine if an error is retriable"""
        error_str = str(error).lower()
        
        retriable_patterns = [
            'rate limit',
            'timeout',
            'connection',
            'network',
            'overloaded',
            'unavailable'
        ]
        
        return any(pattern in error_str for pattern in retriable_patterns)
    
    @staticmethod
    def get_retry_delay(attempt: int) -> int:
        """Calculate retry delay with exponential backoff"""
        # Exponential backoff: 2^attempt seconds, max 60 seconds
        return min(2 ** attempt, 60)
    
    @staticmethod
    def format_error_message(error: Exception) -> str:
        """Format error message for user display"""
        error_str = str(error)
        
        # Map common errors to user-friendly messages
        if 'rate limit' in error_str.lower():
            return "API rate limit reached. Please try again in a few moments."
        elif 'timeout' in error_str.lower():
            return "Request timed out. The document may be too large or complex."
        elif 'invalid' in error_str.lower() and 'api' in error_str.lower():
            return "Invalid API configuration. Please check your Claude API key."
        else:
            return f"Extraction error: {error_str}"

