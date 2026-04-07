"""
Post-processing and text cleaning utilities for Google Document AI extraction.
"""

import re
from typing import List, Tuple


class TextCleaner:
    """Text cleaning and OCR error correction."""
    
    @staticmethod
    def fix_ocr_errors(text: str) -> str:
        """Fix common OCR errors, particularly O to 0 in numeric contexts."""
        if not text:
            return text
        
        original_text = text
        
        # Fix O to 0 in numeric contexts
        # Pattern 1: O between digits (e.g., 2O25 -> 2025)
        text = re.sub(r'(\d)O(\d)', r'\g<1>0\g<2>', text)
        
        # Pattern 2: O after currency symbol (e.g., $O -> $0)
        text = re.sub(r'(\$)O(\d)', r'\g<1>0\g<2>', text)
        
        # Pattern 3: Years like 2O25 -> 2025
        text = re.sub(r'2O2[0-9]', lambda m: m.group().replace('O', '0'), text)
        
        # Pattern 4: O in decimal contexts (e.g., 1O9.O1 -> 109.01)
        text = re.sub(r'(\d)O(\d)\.O(\d)', r'\g<1>0\g<2>.0\g<3>', text)
        
        # Pattern 4b: O in decimal contexts without leading digit (e.g., O1 -> 01)
        text = re.sub(r'\.O(\d)', r'.0\g<1>', text)
        
        # Pattern 5: O in percentage contexts (e.g., 2O.O% -> 20.0%)
        text = re.sub(r'(\d)O\.O%', r'\g<1>0.0%', text)
        
        # Pattern 6: O in state codes (e.g., MNOO867 -> MN00867)
        text = re.sub(r'([A-Z]{2})O+(\d+)', r'\g<1>00\g<2>', text)
        
        # Pattern 6b: Fix remaining O's in state codes (e.g., MD005OO -> MD00500)
        text = re.sub(r'([A-Z]{2}\d+)O+', r'\g<1>0', text)
        
        # Pattern 7: O in standalone numeric contexts
        text = re.sub(r' O(\d) ', r' 0\g<1> ', text)
        
        # Debug logging for OCR corrections
        if original_text != text:
            print(f"🔧 OCR correction: '{original_text}' -> '{text}'")
        
        return text

    @staticmethod
    def clean_text(text: str) -> str:
        """Clean and normalize text."""
        if not text:
            return ""
        
        original_text = text
        
        # Remove excessive underscores (common in form fields and OCR artifacts)
        cleaned = re.sub(r'_+', ' ', text)
        
        # Remove excessive dashes (common in form fields)
        cleaned = re.sub(r'-+', ' ', cleaned)
        
        # Remove excessive dots/periods
        cleaned = re.sub(r'\.+', '.', cleaned)
        
        # Remove excessive spaces
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Remove common OCR artifacts
        cleaned = cleaned.replace("|", "I")  # Common OCR mistake
        
        # Fix OCR errors - O to 0 in numeric contexts (CRITICAL FIX)
        cleaned = TextCleaner.fix_ocr_errors(cleaned)
        
        # Remove leading/trailing whitespace
        cleaned = cleaned.strip()
        
        # If the result is just whitespace or empty, return empty string
        if not cleaned or cleaned.isspace():
            return ""
        
        # Debug logging for header cleaning
        if original_text != cleaned:
            print(f"🔧 Text cleaned: '{original_text}' -> '{cleaned}'")
        
        return cleaned
    
    @staticmethod
    def remove_empty_cells(headers: List[str], rows: List[List[str]]) -> Tuple[List[str], List[List[str]]]:
        """
        Data-preserving empty cell removal with enhanced logic.
        
        Args:
            headers: Table headers
            rows: Table data rows
            
        Returns:
            Tuple of (cleaned_headers, cleaned_rows) with preserved data
        """
        try:
            print(f"📊 Data preservation: Starting with {len(headers)} headers and {len(rows)} rows")
            
            # Only remove columns that are completely empty across ALL rows AND headers
            non_empty_cols = []
            max_cols = max(len(headers), max(len(row) for row in rows) if rows else 0)
            
            for col_idx in range(max_cols):
                # Check header
                header_value = headers[col_idx] if col_idx < len(headers) else ""
                
                # Check all rows in this column
                col_values = [header_value]
                for row in rows:
                    cell_value = row[col_idx] if col_idx < len(row) else ""
                    col_values.append(cell_value)
                
                # Debug logging for column analysis
                print(f"🔍 Column {col_idx}: header='{header_value}', has_content={any(value.strip() for value in col_values)}")
                
                # Only remove column if ALL values are empty (including header)
                if any(value.strip() for value in col_values):
                    non_empty_cols.append(col_idx)
                    print(f"✅ Keeping column {col_idx} with header '{header_value}'")
                else:
                    print(f"🗑️ Removing completely empty column {col_idx}")
            
            # Rebuild headers and rows with only non-empty columns
            new_headers = []
            for col_idx in non_empty_cols:
                if col_idx < len(headers):
                    new_headers.append(headers[col_idx])
                else:
                    new_headers.append(f"Column_{col_idx+1}")
            
            print(f"🔍 Rebuilt headers: {new_headers}")
            
            new_rows = []
            for row_idx, row in enumerate(rows):
                new_row = []
                for col_idx in non_empty_cols:
                    if col_idx < len(row):
                        new_row.append(row[col_idx])
                    else:
                        new_row.append("")  # Pad with empty string
                new_rows.append(new_row)
            
            # Only remove rows that are completely empty (all cells empty)
            filtered_rows = []
            for row_idx, row in enumerate(new_rows):
                if any(cell.strip() for cell in row):
                    filtered_rows.append(row)
                else:
                    print(f"🗑️ Removing completely empty row {row_idx}")
            
            print(f"📊 Data preservation: Final result - {len(new_headers)} headers and {len(filtered_rows)} rows")
            if len(rows) > 0:
                print(f"📊 Data preservation: Kept {len(filtered_rows)}/{len(rows)} rows ({len(filtered_rows)/len(rows)*100:.1f}% preserved)")
            
            return new_headers, filtered_rows
            
        except Exception as e:
            print(f"Error in data-preserving empty cell removal: {e}")
            return headers, rows


class PatternAnalyzer:
    """Analyze data patterns for header generation and validation."""
    
    @staticmethod
    def looks_like_date(value: str) -> bool:
        """Check if a value looks like a date."""
        date_patterns = [
            r'\d{1,2}/\d{1,2}/\d{2,4}',
            r'\d{1,2}-\d{1,2}-\d{2,4}',
            r'\d{4}-\d{2}-\d{2}'
        ]
        return any(re.match(pattern, value) for pattern in date_patterns)

    @staticmethod
    def looks_like_number(value: str) -> bool:
        """Check if a value looks like a number."""
        # Remove common currency symbols and commas
        cleaned = re.sub(r'[$,£€¥₹]', '', value)
        return bool(re.match(r'^[\d,]+\.?\d*$', cleaned))

    @staticmethod
    def looks_like_name(value: str) -> bool:
        """Check if a value looks like a name."""
        # Simple heuristic: contains letters and spaces, no numbers
        return bool(re.match(r'^[A-Za-z\s]+$', value))

    @staticmethod
    def generate_header_from_data(rows: List[List[str]], column_index: int) -> str:
        """
        Generate a header based on the data in a specific column.
        
        Args:
            rows: Table data rows
            column_index: Index of the column to analyze
            
        Returns:
            Generated header string
        """
        try:
            if not rows or column_index >= len(rows[0]):
                return f"Column_{column_index+1}"
            
            # Get all values in this column
            column_values = []
            for row in rows:
                if column_index < len(row):
                    value = row[column_index].strip()
                    if value:
                        column_values.append(value)
            
            if not column_values:
                return f"Column_{column_index+1}"
            
            # Analyze the data to generate a meaningful header
            sample_values = column_values[:5]  # Look at first 5 values
            
            # Check if it looks like dates
            if any(PatternAnalyzer.looks_like_date(val) for val in sample_values):
                return "Date"
            
            # Check if it looks like numbers
            if any(PatternAnalyzer.looks_like_number(val) for val in sample_values):
                return "Amount"
            
            # Check if it looks like names
            if any(PatternAnalyzer.looks_like_name(val) for val in sample_values):
                return "Name"
            
            # Default to a generic header
            return f"Column_{column_index+1}"
            
        except Exception as e:
            print(f"Error generating header from data: {e}")
            return f"Column_{column_index+1}"

