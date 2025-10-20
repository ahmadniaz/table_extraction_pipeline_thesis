import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)

class DataFormattingService:
    """
    Service for ensuring extracted data matches the LLM's specified format with ≥90% accuracy.
    
    This service processes extracted data based on GPT-5 Vision analysis to ensure:
    1. Data types match the LLM's specification (date, currency, percentage, number, text)
    2. Format patterns match the LLM's sample values
    3. Values are properly assigned to the correct columns
    4. At least 90% of data matches the expected format
    """
    
    def __init__(self):
        # Base patterns for fallback validation
        self.date_patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',  # MM/DD/YYYY or MM-DD-YYYY
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
            r'\d{1,2}/\d{1,2}/\d{2,4}'  # MM/DD/YYYY
        ]
        
        self.currency_patterns = [
            r'^\$[\d,]+\.?\d*$',  # $1,234.56
            r'^\(\$[\d,]+\.?\d*\)$',  # ($1,234.56)
            r'^\$[\d,]+\.?\d*$',  # $1,234.56
        ]
        
        self.percentage_patterns = [
            r'^\d+\.?\d*%$',  # 25% or 25.5%
        ]
        
        self.number_patterns = [
            r'^-?\d+\.?\d*$',  # -123 or 123.45
        ]
    
    def format_data_with_llm_analysis(self, 
                                    extracted_tables: List[Dict[str, Any]], 
                                    llm_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Format extracted data to match LLM's analysis with ≥90% accuracy.
        
        Args:
            extracted_tables: Current extracted table data
            llm_analysis: GPT-5 Vision analysis with column specifications
            
        Returns:
            Formatted tables with data matching LLM specifications
        """
        try:
            formatted_tables = []
            analysis = llm_analysis.get("analysis", {})
            pages = analysis.get("pages", [])
            
            # Process each page's analysis
            for page in pages:
                page_num = page.get("page_number", 1)
                headers = page.get("headers", [])
                columns = page.get("columns", [])
                
                # Create column mapping with dynamic patterns for this page
                column_mapping = self._create_column_mapping_with_patterns(headers, columns)
                
                # Find corresponding table data
                table_data = self._find_table_for_page(extracted_tables, page_num)
                if not table_data:
                    continue
                
                # Format the table data with strict LLM pattern enforcement
                formatted_table = self._format_table_data_with_llm_patterns(table_data, headers, column_mapping)
                formatted_tables.append(formatted_table)
            
            return formatted_tables
            
        except Exception as e:
            logger.error(f"Error formatting data with LLM analysis: {e}")
            return extracted_tables
    
    def _create_column_mapping_with_patterns(self, headers: List[str], columns: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Create a mapping of header names to column analysis with dynamic patterns."""
        column_mapping = {}
        
        for col_analysis in columns:
            header_text = col_analysis.get("header_text", "")
            if header_text in headers:
                # Build dynamic patterns from LLM analysis
                data_type = col_analysis.get("data_type", "text")
                sample_values = col_analysis.get("sample_values", [])
                value_patterns = col_analysis.get("value_patterns", [])
                
                # Generate dynamic regex patterns from sample values
                dynamic_patterns = self._generate_dynamic_patterns(data_type, sample_values, value_patterns)
                
                column_mapping[header_text] = {
                    "data_type": data_type,
                    "sample_values": sample_values,
                    "value_patterns": value_patterns,
                    "dynamic_patterns": dynamic_patterns,
                    "header_index": headers.index(header_text)
                }
        
        return column_mapping
    
    def _generate_dynamic_patterns(self, data_type: str, sample_values: List[str], value_patterns: List[str]) -> List[str]:
        """Generate dynamic regex patterns from LLM analysis."""
        patterns = []
        
        # Add provided value patterns
        patterns.extend(value_patterns)
        
        # Generate patterns from sample values based on data type
        for sample in sample_values:
            if not sample:
                continue
                
            if data_type == "date":
                # Generate date patterns from sample
                date_pattern = self._generate_date_pattern_from_sample(sample)
                if date_pattern:
                    patterns.append(date_pattern)
                    
            elif data_type == "currency":
                # Generate currency patterns from sample
                currency_pattern = self._generate_currency_pattern_from_sample(sample)
                if currency_pattern:
                    patterns.append(currency_pattern)
                    
            elif data_type == "percentage":
                # Generate percentage patterns from sample
                percentage_pattern = self._generate_percentage_pattern_from_sample(sample)
                if percentage_pattern:
                    patterns.append(percentage_pattern)
                    
            elif data_type == "number":
                # Generate number patterns from sample
                number_pattern = self._generate_number_pattern_from_sample(sample)
                if number_pattern:
                    patterns.append(number_pattern)
                    
            elif data_type == "text":
                # Generate text patterns from sample
                text_pattern = self._generate_text_pattern_from_sample(sample)
                if text_pattern:
                    patterns.append(text_pattern)
        
        # Add fallback patterns based on data type
        fallback_patterns = self._get_fallback_patterns(data_type)
        patterns.extend(fallback_patterns)
        
        return list(set(patterns))  # Remove duplicates
    
    def _generate_date_pattern_from_sample(self, sample: str) -> Optional[str]:
        """Generate date regex pattern from sample value."""
        # Common date formats
        if re.match(r'\d{1,2}/\d{1,2}/\d{4}', sample):
            return r'\d{1,2}/\d{1,2}/\d{4}'
        elif re.match(r'\d{1,2}-\d{1,2}-\d{4}', sample):
            return r'\d{1,2}-\d{1,2}-\d{4}'
        elif re.match(r'\d{4}-\d{2}-\d{2}', sample):
            return r'\d{4}-\d{2}-\d{2}'
        elif re.match(r'\d{1,2}/\d{1,2}/\d{2}', sample):
            return r'\d{1,2}/\d{1,2}/\d{2}'
        return None
    
    def _generate_currency_pattern_from_sample(self, sample: str) -> Optional[str]:
        """Generate currency regex pattern from sample value."""
        if sample.startswith('$') and '(' not in sample:
            return r'^\$[\d,]+\.?\d*$'
        elif sample.startswith('($') and sample.endswith(')'):
            return r'^\(\$[\d,]+\.?\d*\)$'
        elif sample.startswith('$'):
            return r'^\$[\d,]+\.?\d*$'
        return None
    
    def _generate_percentage_pattern_from_sample(self, sample: str) -> Optional[str]:
        """Generate percentage regex pattern from sample value."""
        if sample.endswith('%'):
            return r'^\d+\.?\d*%$'
        return None
    
    def _generate_number_pattern_from_sample(self, sample: str) -> Optional[str]:
        """Generate number regex pattern from sample value."""
        if re.match(r'^-?\d+\.?\d*$', sample):
            return r'^-?\d+\.?\d*$'
        return None
    
    def _generate_text_pattern_from_sample(self, sample: str) -> Optional[str]:
        """Generate text regex pattern from sample value."""
        if sample.isalpha():
            return r'^[A-Za-z]+$'
        elif re.match(r'^[A-Za-z0-9]+$', sample):
            return r'^[A-Za-z0-9]+$'
        elif ' ' in sample:
            return r'^[A-Za-z\s]+$'
        return None
    
    def _get_fallback_patterns(self, data_type: str) -> List[str]:
        """Get fallback patterns for data type."""
        if data_type == "date":
            return self.date_patterns
        elif data_type == "currency":
            return self.currency_patterns
        elif data_type == "percentage":
            return self.percentage_patterns
        elif data_type == "number":
            return self.number_patterns
        else:
            return [r'^.+$']  # Greedy text pattern
    
    def _find_table_for_page(self, tables: List[Dict[str, Any]], page_num: int) -> Optional[Dict[str, Any]]:
        """Find table data corresponding to a specific page."""
        # Try to find table by page number in metadata
        for table in tables:
            metadata = table.get("metadata", {})
            if metadata.get("page_number") == page_num:
                return table
        
        # If not found, return the first table (fallback)
        return tables[0] if tables else None
    
    def _format_table_data_with_llm_patterns(self, 
                                          table_data: Dict[str, Any], 
                                          llm_headers: List[str], 
                                          column_mapping: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Format table data to match LLM specifications with strict pattern enforcement."""
        original_rows = table_data.get("rows", [])
        formatted_rows = []
        
        for row in original_rows:
            if not row:
                continue
            
            # Format the row based on LLM analysis with strict pattern enforcement
            formatted_row = self._format_row_with_llm_patterns(row, llm_headers, column_mapping)
            if formatted_row:
                formatted_rows.append(formatted_row)
        
        return {
            "header": llm_headers,
            "rows": formatted_rows,
            "name": f"Page {table_data.get('metadata', {}).get('page_number', 1)} - LLM Pattern Formatted",
            "metadata": {
                **table_data.get("metadata", {}),
                "formatting_method": "llm_pattern_enforcement",
                "column_mapping": column_mapping,
                "formatting_timestamp": datetime.now().isoformat(),
                "format_accuracy_target": "≥90%"
            }
        }
    
    def _format_row_with_llm_patterns(self, 
                                    row: List[str], 
                                    llm_headers: List[str], 
                                    column_mapping: Dict[str, Dict[str, Any]]) -> Optional[List[str]]:
        """Format a single row to match LLM specifications with strict pattern enforcement."""
        try:
            # Initialize formatted row with empty strings
            formatted_row = [""] * len(llm_headers)
            
            # Filter out noise and irrelevant data first
            filtered_row = self._filter_noise_from_row(row)
            
            if not filtered_row:
                return [""] * len(llm_headers)
            
            # If row has combined data, parse it with LLM pattern enforcement
            if len(filtered_row) == 1 and isinstance(filtered_row[0], str):
                parsed_data = self._parse_combined_data_with_llm_patterns(filtered_row[0], llm_headers, column_mapping)
                if parsed_data:
                    formatted_row = parsed_data
            else:
                # Process multi-cell row with LLM pattern enforcement
                formatted_row = self._format_multi_cell_row_with_llm_patterns(filtered_row, llm_headers, column_mapping)
            
            # Post-process the formatted row to clean up any remaining issues
            formatted_row = self._post_process_formatted_row(formatted_row, column_mapping)
            
            # Validate the formatted row with strict 90% rule
            if self._validate_formatted_row_strict(formatted_row, column_mapping):
                return formatted_row
            else:
                logger.warning(f"Row validation failed (strict 90% rule): {formatted_row}")
                # Return empty row if validation fails
                return [""] * len(llm_headers)
                
        except Exception as e:
            logger.error(f"Error formatting row {row}: {e}")
            return [""] * len(llm_headers)
    
    def _filter_noise_from_row(self, row: List[str]) -> List[str]:
        """Filter out noise and irrelevant data from a row with improved logic."""
        if not row:
            return []
        
        # Define noise patterns that should be filtered out
        noise_patterns = [
            r'^Report Date$',
            r'^Writing Agent \d+ No:$',
            r'^Writing Agent Number:$',
            r'^Page \d+$',
            r'^Total$',
            r'^Subtotal$',
            r'^Grand Total$',
            r'^Summary$',
            r'^Details$',
            r'^\s*$',  # Empty or whitespace-only
        ]
        
        filtered_row = []
        has_valid_data = False
        
        for cell in row:
            if not cell or not isinstance(cell, str):
                continue
            
            cell = cell.strip()
            if not cell:
                continue
            
            # Check if cell matches any noise pattern
            is_noise = False
            for pattern in noise_patterns:
                if re.match(pattern, cell, re.IGNORECASE):
                    is_noise = True
                    break
            
            if not is_noise:
                # Check if this looks like valid data
                if self._looks_like_valid_data(cell):
                    has_valid_data = True
                filtered_row.append(cell)
        
        # Only return the row if it contains valid data
        return filtered_row if has_valid_data else []
    
    def _looks_like_valid_data(self, cell: str) -> bool:
        """Check if a cell looks like valid data rather than noise."""
        # Valid data patterns
        valid_patterns = [
            r'^L\d+$',  # Group numbers
            r'^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$',  # Dates
            r'^\d{4}-\d{2}-\d{2}$',  # ISO dates
            r'^\$[\d,]+\.?\d*$',  # Currency
            r'^\(\$[\d,]+\.?\d*\)$',  # Negative currency
            r'^\d+\.?\d*%$',  # Percentages
            r'^-?\d+\.?\d*$',  # Numbers
            r'^[A-Za-z\s]+$',  # Text (words with spaces)
        ]
        
        for pattern in valid_patterns:
            if re.match(pattern, cell):
                return True
        
        return False
    
    def _post_process_formatted_row(self, 
                                  formatted_row: List[str], 
                                  column_mapping: Dict[str, Dict[str, Any]]) -> List[str]:
        """Post-process formatted row to clean up any remaining issues."""
        processed_row = formatted_row.copy()
        
        # Clean up duplicate values in cells
        for i, cell in enumerate(processed_row):
            if cell and isinstance(cell, str):
                # Remove duplicate words/phrases
                words = cell.split()
                unique_words = []
                for word in words:
                    if word not in unique_words:
                        unique_words.append(word)
                processed_row[i] = " ".join(unique_words)
        
        # Fix common formatting issues
        for i, cell in enumerate(processed_row):
            if cell and isinstance(cell, str):
                # Fix common OCR issues
                cell = cell.replace('O', '0')  # Fix OCR 'O' to '0'
                cell = cell.replace('l', '1')  # Fix OCR 'l' to '1'
                cell = cell.replace('I', '1')  # Fix OCR 'I' to '1'
                processed_row[i] = cell
        
        return processed_row
    
    def _parse_combined_data_with_llm_patterns(self, 
                                             combined_data: str, 
                                             llm_headers: List[str], 
                                             column_mapping: Dict[str, Dict[str, Any]]) -> Optional[List[str]]:
        """Parse combined data string and assign values to correct columns based on LLM patterns."""
        try:
            formatted_row = [""] * len(llm_headers)
            
            # Extract all possible values from combined data using LLM patterns
            extracted_values = self._extract_values_with_llm_patterns(combined_data, column_mapping)
            
            # Sort extracted values by priority (pattern matches first, then sample matches, then type matches)
            sorted_values = self._sort_extracted_values_by_priority(extracted_values, column_mapping)
            
            # Assign each extracted value to the best matching column
            for value, value_type in sorted_values:
                best_column = self._find_best_column_for_value_with_patterns(value, value_type, column_mapping)
                if best_column is not None:
                    col_index = column_mapping[best_column]["header_index"]
                    formatted_value = self._format_value_for_column_with_patterns(value, column_mapping[best_column])
                    
                    # Only assign if column is empty (strict one-value-per-column rule)
                    if not formatted_row[col_index]:
                        formatted_row[col_index] = formatted_value
            
            return formatted_row
            
        except Exception as e:
            logger.error(f"Error parsing combined data with LLM patterns '{combined_data}': {e}")
            return None
    
    def _sort_extracted_values_by_priority(self, 
                                         extracted_values: List[Tuple[str, str]], 
                                         column_mapping: Dict[str, Dict[str, Any]]) -> List[Tuple[str, str]]:
        """Sort extracted values by priority for better assignment."""
        def get_priority(value, value_type):
            priority = 0
            
            # Check if value matches any pattern exactly
            for col_info in column_mapping.values():
                dynamic_patterns = col_info.get("dynamic_patterns", [])
                for pattern in dynamic_patterns:
                    try:
                        if re.match(pattern, value):
                            priority += 100  # Highest priority for pattern matches
                            break
                    except re.error:
                        continue
            
            # Check if value matches any sample exactly
            for col_info in column_mapping.values():
                sample_values = col_info.get("sample_values", [])
                for sample in sample_values:
                    if value.lower() == sample.lower():
                        priority += 80  # High priority for exact sample matches
                        break
            
            # Priority based on data type specificity
            if value_type == "date":
                priority += 30
            elif value_type == "currency":
                priority += 30
            elif value_type == "percentage":
                priority += 30
            elif value_type == "number":
                priority += 20
            else:
                priority += 10
            
            return priority
        
        # Sort by priority (highest first)
        return sorted(extracted_values, key=lambda x: get_priority(x[0], x[1]), reverse=True)
    
    def _extract_values_with_llm_patterns(self, 
                                        combined_data: str, 
                                        column_mapping: Dict[str, Dict[str, Any]]) -> List[Tuple[str, str]]:
        """Extract all possible values from combined data using LLM patterns."""
        extracted_values = []
        
        # First, try to extract values using LLM patterns for each column
        for header, col_info in column_mapping.items():
            data_type = col_info.get("data_type", "text")
            dynamic_patterns = col_info.get("dynamic_patterns", [])
            sample_values = col_info.get("sample_values", [])
            
            # Try each pattern for this column
            for pattern in dynamic_patterns:
                try:
                    matches = re.findall(pattern, combined_data)
                    for match in matches:
                        if match and match.strip():
                            extracted_values.append((match.strip(), data_type))
                except re.error:
                    # Skip invalid regex patterns
                    continue
            
            # Also try to match sample values directly
            for sample in sample_values:
                if sample and sample in combined_data:
                    extracted_values.append((sample, data_type))
        
        # If we didn't find enough values, try more aggressive extraction
        if len(extracted_values) < 3:  # Arbitrary threshold
            extracted_values.extend(self._extract_values_aggressive(combined_data, column_mapping))
        
        # Remove duplicates while preserving order
        unique_values = []
        seen = set()
        for value, value_type in extracted_values:
            try:
                # Ensure value is hashable (convert to string if it's a dict or other unhashable type)
                if isinstance(value, dict):
                    # Convert dict to a hashable string representation
                    hashable_value = str(sorted(value.items())) if value else "{}"
                elif isinstance(value, (list, set)):
                    # Convert list/set to a hashable string representation
                    hashable_value = str(sorted(value)) if value else "[]"
                elif not isinstance(value, (str, int, float, bool, tuple)):
                    # Convert any other unhashable type to string
                    hashable_value = str(value)
                else:
                    hashable_value = value
                
                if hashable_value not in seen:
                    unique_values.append((value, value_type))
                    seen.add(hashable_value)
            except Exception as e:
                # If there's any issue with hashing, skip this value
                logger.warning(f"Failed to hash value {value}: {e}")
                continue
        
        return unique_values
    
    def _extract_values_aggressive(self, 
                                 combined_data: str, 
                                 column_mapping: Dict[str, Dict[str, Any]]) -> List[Tuple[str, str]]:
        """Extract values using more aggressive pattern matching with improved logic."""
        extracted_values = []
        
        # Enhanced pattern matching for specific data types
        patterns_to_extract = [
            # Group numbers (L followed by digits)
            (r'L\d+', 'text'),
            # Dates (various formats)
            (r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', 'date'),
            (r'\d{4}-\d{2}-\d{2}', 'date'),
            # Currency (with or without parentheses)
            (r'\$[\d,]+\.?\d*', 'currency'),
            (r'\(\$[\d,]+\.?\d*\)', 'currency'),
            # Percentages
            (r'\d+\.?\d*%', 'percentage'),
            # Numbers (including negative)
            (r'-?\d+\.?\d*', 'number'),
            # Text (words with spaces)
            (r'[A-Za-z]+(?:\s+[A-Za-z]+)*', 'text'),
        ]
        
        # Extract using patterns
        for pattern, data_type in patterns_to_extract:
            try:
                matches = re.findall(pattern, combined_data)
                for match in matches:
                    if match and match.strip() and len(match.strip()) > 1:
                        # Clean up the match
                        clean_match = match.strip()
                        
                        # Skip if it's just noise
                        if self._is_noise_value(clean_match):
                            continue
                        
                        extracted_values.append((clean_match, data_type))
            except re.error:
                continue
        
        # Also split by spaces and analyze individual parts
        parts = combined_data.split()
        for part in parts:
            if not part or len(part.strip()) < 2:
                continue
            
            part = part.strip()
            
            # Skip noise
            if self._is_noise_value(part):
                continue
            
            # Determine data type
            data_type = self._determine_data_type(part)
            
            # Only add if it's not already extracted
            if not any(part == val[0] for val in extracted_values):
                extracted_values.append((part, data_type))
        
        return extracted_values
    
    def _is_noise_value(self, value: str) -> bool:
        """Check if a value is noise that should be filtered out."""
        noise_patterns = [
            r'^Report$',
            r'^Date$',
            r'^Writing$',
            r'^Agent$',
            r'^Number$',
            r'^No:$',
            r'^Page$',
            r'^Total$',
            r'^Subtotal$',
            r'^Summary$',
            r'^Details$',
            r'^Premium$',
            r'^Equivalent$',
            r'^Calculation$',
            r'^Method$',
        ]
        
        for pattern in noise_patterns:
            if re.match(pattern, value, re.IGNORECASE):
                return True
        
        return False
    
    def _determine_data_type(self, value: str) -> str:
        """Determine the data type of a value."""
        if self._is_date_format(value):
            return "date"
        elif self._is_currency_format(value):
            return "currency"
        elif self._is_percentage_format(value):
            return "percentage"
        elif self._is_number_format(value):
            return "number"
        else:
            return "text"
    
    def _find_best_column_for_value_with_patterns(self, 
                                                value: str, 
                                                value_type: str,
                                                column_mapping: Dict[str, Dict[str, Any]]) -> Optional[str]:
        """Find the best column for a value based on LLM patterns."""
        best_column = None
        best_score = 0
        
        for header, col_info in column_mapping.items():
            score = self._calculate_column_match_score_with_patterns(value, value_type, col_info)
            if score > best_score:
                best_score = score
                best_column = header
        
        # Only return if we have a strong match (higher threshold for strict enforcement)
        return best_column if best_score > 15 else None
    
    def _calculate_column_match_score_with_patterns(self, 
                                                  value: str, 
                                                  value_type: str,
                                                  col_info: Dict[str, Any]) -> int:
        """Calculate how well a value matches a column based on LLM patterns."""
        score = 0
        data_type = col_info.get("data_type", "text")
        sample_values = col_info.get("sample_values", [])
        dynamic_patterns = col_info.get("dynamic_patterns", [])
        
        # Score based on data type match
        if value_type == data_type:
            score += 30
        elif data_type == "text" and value_type != "text":
            # Text columns can accept other types as fallback
            score += 5
        
        # Score based on pattern matches (highest priority)
        for pattern in dynamic_patterns:
            try:
                if re.match(pattern, value):
                    score += 50  # Increased weight for pattern matches
                    break
            except re.error:
                continue
        
        # Score based on sample values
        for sample in sample_values:
            if self._values_are_similar_with_patterns(value, sample, data_type):
                score += 40  # Increased weight for sample matches
                break
        
        # Additional scoring for specific data types
        if data_type == "date" and self._is_date_format(value):
            score += 25
        elif data_type == "currency" and self._is_currency_format(value):
            score += 25
        elif data_type == "percentage" and self._is_percentage_format(value):
            score += 25
        elif data_type == "number" and self._is_number_format(value):
            score += 20
        
        return score
    
    def _values_are_similar_with_patterns(self, value1: str, value2: str, data_type: str) -> bool:
        """Check if two values are similar based on patterns and data type."""
        # Normalize values for comparison
        v1 = value1.lower().strip()
        v2 = value2.lower().strip()
        
        # Exact match
        if v1 == v2:
            return True
        
        # Check if one contains the other (for text)
        if data_type == "text" and (v1 in v2 or v2 in v1):
            return True
        
        # Check for similar patterns based on data type
        if data_type == "date":
            return self._is_date_format(v1) and self._is_date_format(v2)
        elif data_type == "currency":
            return self._is_currency_format(v1) and self._is_currency_format(v2)
        elif data_type == "percentage":
            return self._is_percentage_format(v1) and self._is_percentage_format(v2)
        elif data_type == "number":
            return self._is_number_format(v1) and self._is_number_format(v2)
        
        return False
    
    def _format_value_for_column_with_patterns(self, value: str, col_info: Dict[str, Any]) -> str:
        """Format a value to match the column's expected format using LLM patterns."""
        data_type = col_info.get("data_type", "text")
        sample_values = col_info.get("sample_values", [])
        
        # Try to format based on data type and sample values
        if data_type == "date":
            return self._format_as_date_with_samples(value, sample_values)
        elif data_type == "currency":
            return self._format_as_currency_with_samples(value, sample_values)
        elif data_type == "percentage":
            return self._format_as_percentage_with_samples(value, sample_values)
        elif data_type == "number":
            return self._format_as_number_with_samples(value, sample_values)
        else:
            return value  # Keep text as is
    
    def _format_as_date_with_samples(self, value: str, sample_values: List[str]) -> str:
        """Format value as date using sample values as reference."""
        if self._is_date_format(value):
            return value
        return value
    
    def _format_as_currency_with_samples(self, value: str, sample_values: List[str]) -> str:
        """Format value as currency using sample values as reference."""
        if self._is_currency_format(value):
            return value
        return value
    
    def _format_as_percentage_with_samples(self, value: str, sample_values: List[str]) -> str:
        """Format value as percentage using sample values as reference."""
        if self._is_percentage_format(value):
            return value
        elif value.replace('.', '').replace('-', '').isdigit():
            return f"{value}%"
        return value
    
    def _format_as_number_with_samples(self, value: str, sample_values: List[str]) -> str:
        """Format value as number using sample values as reference."""
        if self._is_number_format(value):
            return value
        return value
    
    def _format_multi_cell_row_with_llm_patterns(self, 
                                               row: List[str], 
                                               llm_headers: List[str], 
                                               column_mapping: Dict[str, Dict[str, Any]]) -> List[str]:
        """Format a multi-cell row to match LLM specifications with improved pattern enforcement."""
        formatted_row = [""] * len(llm_headers)
        
        # Create a mapping of header indices for quick lookup
        header_indices = {header: i for i, header in enumerate(llm_headers)}
        
        # Process each cell with enhanced pattern matching
        for cell_value in row:
            if not cell_value or cell_value.strip() == "":
                continue
            
            cell_value = cell_value.strip()
            
            # Skip noise values
            if self._is_noise_value(cell_value):
                continue
            
            # Try to match the cell value directly to a column based on data type and patterns
            best_column = None
            best_score = 0
            
            for header, col_info in column_mapping.items():
                if header not in header_indices:
                    continue
                
                data_type = col_info.get("data_type", "text")
                sample_values = col_info.get("sample_values", [])
                dynamic_patterns = col_info.get("dynamic_patterns", [])
                
                # Calculate match score
                score = 0
                
                # Check pattern matches
                for pattern in dynamic_patterns:
                    try:
                        if re.match(pattern, cell_value):
                            score += 50
                            break
                    except re.error:
                        continue
                
                # Check sample value matches
                for sample in sample_values:
                    if self._values_are_similar_with_patterns(cell_value, sample, data_type):
                        score += 40
                        break
                
                # Check data type match
                cell_data_type = self._determine_data_type(cell_value)
                if cell_data_type == data_type:
                    score += 30
                elif data_type == "text" and cell_data_type != "text":
                    score += 10
                
                # Additional scoring for specific patterns
                if data_type == "text" and re.match(r'^L\d+$', cell_value):
                    score += 25  # Group numbers
                elif data_type == "date" and self._is_date_format(cell_value):
                    score += 25
                elif data_type == "currency" and self._is_currency_format(cell_value):
                    score += 25
                elif data_type == "percentage" and self._is_percentage_format(cell_value):
                    score += 25
                elif data_type == "number" and self._is_number_format(cell_value):
                    score += 20
                
                if score > best_score:
                    best_score = score
                    best_column = header
            
            # Assign to best matching column if score is high enough
            if best_column and best_score > 20:
                col_index = header_indices[best_column]
                formatted_value = self._format_value_for_column_with_patterns(cell_value, column_mapping[best_column])
                
                # Only assign if column is empty
                if not formatted_row[col_index]:
                    formatted_row[col_index] = formatted_value
        
        return formatted_row
    
    def _validate_formatted_row_strict(self, 
                                     row: List[str], 
                                     column_mapping: Dict[str, Dict[str, Any]]) -> bool:
        """Validate that a formatted row matches LLM specifications with strict ≥90% accuracy."""
        if not row:
            return False
        
        valid_cells = 0
        total_cells = len(row)
        
        for i, value in enumerate(row):
            if not value or value.strip() == "":
                # Empty cells are considered valid
                valid_cells += 1
                continue
            
            # Check if value matches any column's expected format using LLM patterns
            for col_info in column_mapping.values():
                score = self._calculate_column_match_score_with_patterns(value, "unknown", col_info)
                if score > 20:  # Higher threshold for strict validation
                    valid_cells += 1
                    break
        
        # Return True if ≥90% of cells are valid
        accuracy = valid_cells / total_cells if total_cells > 0 else 0
        return accuracy >= 0.9

    # Helper methods for pattern matching
    def _is_date_format(self, value: str) -> bool:
        """Check if value matches date format."""
        return any(re.match(pattern, value) for pattern in self.date_patterns)
    
    def _is_currency_format(self, value: str) -> bool:
        """Check if value matches currency format."""
        return any(re.match(pattern, value) for pattern in self.currency_patterns)
    
    def _is_percentage_format(self, value: str) -> bool:
        """Check if value matches percentage format."""
        return any(re.match(pattern, value) for pattern in self.percentage_patterns)
    
    def _is_number_format(self, value: str) -> bool:
        """Check if value matches number format."""
        return any(re.match(pattern, value) for pattern in self.number_patterns)
    
    def _is_text_format(self, value: str) -> bool:
        """Check if value is text format."""
        # Text is anything that's not clearly another type
        return not (self._is_date_format(value) or 
                   self._is_currency_format(value) or 
                   self._is_percentage_format(value) or 
                   self._is_number_format(value))
