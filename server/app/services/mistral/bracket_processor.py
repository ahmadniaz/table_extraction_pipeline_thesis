"""
Professional Bracket Processor for Accounting Notation

Converts accounting bracket notation (amount) to negative values -amount
following professional accounting standards.
"""

import re
import logging
from typing import Any, Dict, List, Union, Optional
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)

class AccountingBracketProcessor:
    """
    Professional bracket processor for accounting notation.
    Converts (amount) format to -amount format following accounting standards.
    """
    
    def __init__(self):
        # Comprehensive regex patterns for monetary values
        self.patterns = {
            # Bracketed amounts with currency symbol: ($123.45) or (\\$123.45)
            'bracketed_currency': re.compile(r'\(\s*\\?\$\s*([0-9,]+\.?\d*)\s*\)'),
            
            # Bracketed plain numbers: (123.45)
            'bracketed_plain': re.compile(r'\(\s*([0-9,]+\.?\d*)\s*\)'),
            
            # Regular currency amounts: $123.45 or \\$123.45
            'regular_currency': re.compile(r'\\?\$\s*([0-9,]+\.?\d*)'),
            
            # Bracketed currency with additional symbols: ($-1$) 
            'bracketed_mixed': re.compile(r'\(\s*\\?\$?\s*-?\s*([0-9,]+\.?\d*)\s*\$?\s*\)'),
            
            # Edge case: escaped brackets
            'escaped_brackets': re.compile(r'\\?\(\s*\\?\$\s*([0-9,]+\.?\d*)\s*\\?\)')
        }
        
        # Validation patterns
        self.currency_symbols = ['$', '€', '£', '¥', '₹']
        
        # Statistics for validation
        self.processing_stats = {
            'total_processed': 0,
            'brackets_converted': 0,
            'errors': 0,
            'validation_failures': 0
        }

    def process_table_data(self, table_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process all monetary values in table data.
        
        Args:
            table_data: Dict with 'headers' and 'rows' keys
            
        Returns:
            Table data with properly processed monetary values
        """
        try:
            headers = table_data.get('headers', [])
            rows = table_data.get('rows', [])
            
            if not rows:
                return table_data
            
            # Process each row
            processed_rows = []
            for row_idx, row in enumerate(rows):
                processed_row = self._process_row(row, row_idx)
                processed_rows.append(processed_row)
            
            # Create result with processing metadata
            result = {
                **table_data,
                'rows': processed_rows,
                'bracket_processing': {
                    'enabled': True,
                    'total_cells_processed': self.processing_stats['total_processed'],
                    'brackets_converted': self.processing_stats['brackets_converted'],
                    'errors': self.processing_stats['errors'],
                    'processing_method': 'professional_accounting_standard'
                }
            }
            
            # Validate processing
            validation_result = self._validate_processing(table_data, result)
            result['bracket_processing']['validation'] = validation_result
            
            return result
            
        except Exception as e:
            logger.error(f"Bracket processing failed: {e}")
            return table_data

    def _process_row(self, row: List[Any], row_idx: int) -> List[Any]:
        """Process all cells in a row for bracket notation"""
        processed_row = []
        
        for cell_idx, cell in enumerate(row):
            try:
                processed_cell = self._process_cell_value(cell, row_idx, cell_idx)
                processed_row.append(processed_cell)
                self.processing_stats['total_processed'] += 1
            except Exception as e:
                logger.warning(f"Failed to process cell [{row_idx}][{cell_idx}]: {e}")
                processed_row.append(cell)  # Keep original on error
                self.processing_stats['errors'] += 1
                
        return processed_row

    def _process_cell_value(self, cell_value: Any, row_idx: int, cell_idx: int) -> Any:
        """
        Process a single cell value for bracket notation.
        
        Returns the processed value or original if no processing needed.
        """
        if not cell_value or not isinstance(cell_value, (str, int, float)):
            return cell_value
        
        cell_str = str(cell_value).strip()
        
        if not cell_str:
            return cell_value
        
        # Try each pattern in order of specificity
        processed_value = self._apply_bracket_patterns(cell_str)
        
        if processed_value != cell_str:
            self.processing_stats['brackets_converted'] += 1
            logger.debug(f"Converted [{row_idx}][{cell_idx}]: '{cell_str}' -> '{processed_value}'")
        
        return processed_value

    def _apply_bracket_patterns(self, value_str: str) -> str:
        """Apply bracket processing patterns in order of specificity"""
        
        # Pattern 1: Bracketed currency amounts - highest priority
        match = self.patterns['bracketed_currency'].match(value_str)
        if match:
            amount = self._clean_numeric_value(match.group(1))
            return f"-${amount}"
        
        # Pattern 2: Bracketed mixed format (e.g., ($-1$))
        match = self.patterns['bracketed_mixed'].match(value_str)
        if match:
            amount = self._clean_numeric_value(match.group(1))
            return f"-${amount}"
        
        # Pattern 3: Escaped brackets
        match = self.patterns['escaped_brackets'].match(value_str)
        if match:
            amount = self._clean_numeric_value(match.group(1))
            return f"-${amount}"
        
        # Pattern 4: Bracketed plain numbers
        match = self.patterns['bracketed_plain'].match(value_str)
        if match:
            amount = self._clean_numeric_value(match.group(1))
            # Check if this seems like a monetary value based on context
            if self._seems_monetary(value_str):
                return f"-${amount}"
            else:
                return f"-{amount}"
        
        # Pattern 5: Regular currency amounts (positive)
        match = self.patterns['regular_currency'].match(value_str)
        if match:
            amount = self._clean_numeric_value(match.group(1))
            return f"${amount}"
        
        # No bracket pattern matched
        return value_str

    def _clean_numeric_value(self, numeric_str: str) -> str:
        """Clean and validate numeric portion"""
        # Remove commas and extra spaces
        cleaned = numeric_str.replace(',', '').strip()
        
        try:
            # Validate it's a proper number
            float(cleaned)
            return cleaned
        except ValueError:
            logger.warning(f"Invalid numeric value: '{numeric_str}'")
            return numeric_str  # Return original if not valid

    def _seems_monetary(self, value_str: str) -> bool:
        """Heuristic to determine if a bracketed number is monetary"""
        # Check for decimal places (common in monetary values)
        if '.' in value_str and len(value_str.split('.')[-1]) <= 2:
            return True
        
        # Check for comma thousands separators
        if ',' in value_str:
            return True
        
        # Check if value is in typical monetary range (somewhat arbitrary)
        try:
            num_value = float(value_str.replace(',', '').replace('(', '').replace(')', ''))
            return 0.01 <= num_value <= 1000000000  # 1 cent to 1 billion
        except:
            return False

    def _validate_processing(self, original_data: Dict[str, Any], processed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that bracket processing didn't corrupt data"""
        
        validation = {
            'total_cells_checked': 0,
            'negative_indicators_before': 0,
            'negative_values_after': 0,
            'data_integrity_preserved': True,
            'validation_errors': []
        }
        
        try:
            original_rows = original_data.get('rows', [])
            processed_rows = processed_data.get('rows', [])
            
            if len(original_rows) != len(processed_rows):
                validation['data_integrity_preserved'] = False
                validation['validation_errors'].append('Row count mismatch')
                return validation
            
            # Count negative indicators and validate cell by cell
            for row_idx, (orig_row, proc_row) in enumerate(zip(original_rows, processed_rows)):
                if len(orig_row) != len(proc_row):
                    validation['data_integrity_preserved'] = False
                    validation['validation_errors'].append(f'Column count mismatch in row {row_idx}')
                    continue
                
                for cell_idx, (orig_cell, proc_cell) in enumerate(zip(orig_row, proc_row)):
                    validation['total_cells_checked'] += 1
                    
                    # Count bracket indicators in original
                    if str(orig_cell).strip().startswith('(') and str(orig_cell).strip().endswith(')'):
                        validation['negative_indicators_before'] += 1
                    
                    # Count negative values in processed
                    if str(proc_cell).strip().startswith('-'):
                        validation['negative_values_after'] += 1
            
            # Additional validation: Check for data loss
            if validation['total_cells_checked'] == 0:
                validation['validation_errors'].append('No cells found to validate')
            
            return validation
            
        except Exception as e:
            validation['data_integrity_preserved'] = False
            validation['validation_errors'].append(f'Validation failed: {str(e)}')
            return validation

    def get_processing_summary(self) -> Dict[str, Any]:
        """Get summary of processing statistics"""
        return {
            'total_processed': self.processing_stats['total_processed'],
            'brackets_converted': self.processing_stats['brackets_converted'],
            'conversion_rate': (
                self.processing_stats['brackets_converted'] / 
                max(self.processing_stats['total_processed'], 1)
            ) * 100,
            'errors': self.processing_stats['errors'],
            'error_rate': (
                self.processing_stats['errors'] / 
                max(self.processing_stats['total_processed'], 1)
            ) * 100
        }

# Utility function for testing
def test_bracket_processor():
    """Test function for bracket processor"""
    processor = AccountingBracketProcessor()
    
    test_cases = [
        # (input, expected_output)
        ("($123.45)", "-$123.45"),
        ("(\\$123.45)", "-$123.45"),
        ("$123.45", "$123.45"),
        ("\\$123.45", "$123.45"),
        ("(123.45)", "-$123.45"),  # Assuming monetary context
        ("($1,234.56)", "-$1,234.56"),
        ("regular text", "regular text"),
        ("", ""),
        (None, None)
    ]
    
    print("Testing Bracket Processor:")
    for test_input, expected in test_cases:
        if test_input is None:
            result = processor._process_cell_value(test_input, 0, 0)
        else:
            result = processor._apply_bracket_patterns(test_input)
        
        status = "✓" if result == expected else "✗"
        print(f"{status} '{test_input}' -> '{result}' (expected: '{expected}')")

if __name__ == "__main__":
    test_bracket_processor()

