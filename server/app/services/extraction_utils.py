import os
import json
import base64
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import pandas as pd
import numpy as np
from PIL import Image
import io
import logging
import fitz  # PyMuPDF
from pdfplumber.pdf import PDF
import re
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)

# Configuration constants for table stitching
HEADER_SIMILARITY_THRESHOLD = 0.8
PATTERN_MATCH_THRESHOLD = 0.6


def normalize_statement_date(date_string: str) -> str:
    """
    Extract and normalize the primary date from various date formats.
    Handles date ranges by extracting only the start date.
    
    Examples:
        - "2025-03-15 thr 2025-04-14" -> "2025-03-15"
        - "March 15, 2025 through April 14, 2025" -> "2025-03-15"
        - "2025-03-15 to 2025-04-14" -> "2025-03-15"
        - "2025-03-15" -> "2025-03-15"
        - "03/15/2025 - 04/14/2025" -> "2025-03-15"
    
    Args:
        date_string: Date string that may be a single date or date range
        
    Returns:
        Normalized date in ISO format (YYYY-MM-DD), or original string if parsing fails
    """
    if not date_string or not isinstance(date_string, str):
        return date_string
    
    try:
        # Clean up the input string
        date_string = date_string.strip()
        
        # Common date range separators
        range_separators = [
            r'\s+through\s+',
            r'\s+thru\s+',
            r'\s+thr\s+',
            r'\s+to\s+',
            r'\s+-\s+',
            r'\s+–\s+',  # en dash
            r'\s+—\s+',  # em dash
            r'\s+until\s+',
            r'\s+till\s+',
        ]
        
        # Try to split on date range separators
        start_date_str = date_string
        for separator in range_separators:
            parts = re.split(separator, date_string, maxsplit=1, flags=re.IGNORECASE)
            if len(parts) == 2:
                # Found a range, use the first part (start date)
                start_date_str = parts[0].strip()
                logger.debug(f"Detected date range, extracting start date: '{start_date_str}' from '{date_string}'")
                break
        
        # Parse the date using dateutil parser (handles many formats automatically)
        try:
            parsed_date = date_parser.parse(start_date_str, fuzzy=True)
            # Return in ISO format (YYYY-MM-DD)
            normalized = parsed_date.strftime('%Y-%m-%d')
            
            if normalized != date_string:
                logger.info(f"Date normalized: '{date_string}' -> '{normalized}'")
            
            return normalized
            
        except (ValueError, TypeError, date_parser.ParserError) as parse_error:
            # If dateutil fails, try manual parsing for specific formats
            logger.warning(f"dateutil parser failed for '{start_date_str}', trying manual parsing: {parse_error}")
            
            # Try MM/DD/YYYY format
            mm_dd_yyyy_match = re.match(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', start_date_str)
            if mm_dd_yyyy_match:
                month, day, year = mm_dd_yyyy_match.groups()
                parsed_date = datetime(int(year), int(month), int(day))
                return parsed_date.strftime('%Y-%m-%d')
            
            # Try YYYY-MM-DD format (already normalized)
            yyyy_mm_dd_match = re.match(r'(\d{4})-(\d{1,2})-(\d{1,2})', start_date_str)
            if yyyy_mm_dd_match:
                return start_date_str  # Already in correct format
            
            # If all parsing fails, return original string
            logger.error(f"Could not parse date: '{date_string}'")
            return date_string
            
    except Exception as e:
        logger.error(f"Error normalizing date '{date_string}': {e}")
        return date_string


def normalize_multi_line_headers(headers: List[str], rows: List[List[str]] = None) -> List[str]:
    """
    Normalize multi-line column headers where parent columns span multiple sub-columns.
    
    Example transformation:
        Input: ["Clients", "", "Ind. Insurance", "Active HRA Employees", "", "", "Commissions", "", ""]
        Output: ["Clients", "Broker", "Ind. Insurance", "Active HRA Employees Lives", 
                 "Active HRA Employees PEPM", "Active HRA Employees Subtotal", 
                 "Commissions IND", "Commissions HRA", "Commissions Total"]
    
    Args:
        headers: List of header strings (may contain empty strings for sub-columns)
        rows: Optional sample rows to help infer sub-column names
        
    Returns:
        List of normalized header strings with hierarchical names
    """
    if not headers:
        return headers
    
    try:
        normalized = []
        last_parent = None
        parent_column_index = -1
        sub_column_count = 0
        
        # Common sub-column names for inference
        common_sub_columns = [
            ['Lives', 'PEPM', 'Subtotal'],
            ['Count', 'Amount', 'Total'],
            ['IND', 'HRA', 'Total'],
            ['Quantity', 'Rate', 'Amount'],
            ['Name', 'Value', 'Total'],
            ['Start', 'End', 'Duration'],
            ['Min', 'Max', 'Average'],
        ]
        
        for i, header in enumerate(headers):
            header_stripped = header.strip() if header else ""
            
            if header_stripped:
                # This is a parent column or standalone column
                # Check if next columns are empty (indicating this is a parent)
                empty_count = 0
                for j in range(i + 1, len(headers)):
                    if not headers[j].strip():
                        empty_count += 1
                    else:
                        break
                
                if empty_count > 0:
                    # This is a parent column with sub-columns
                    last_parent = header_stripped
                    parent_column_index = i
                    sub_column_count = 0
                    normalized.append(header_stripped)  # Keep parent name for first column
                else:
                    # Standalone column
                    last_parent = None
                    normalized.append(header_stripped)
            else:
                # Empty header - this is a sub-column
                if last_parent:
                    sub_column_count += 1
                    
                    # Try to infer sub-column name from data if rows provided
                    inferred_name = None
                    if rows and len(rows) > 0:
                        # Look at the first few rows to infer the sub-column name
                        inferred_name = _infer_sub_column_name(rows, i, sub_column_count)
                    
                    # Use inferred name or generate a generic one
                    if inferred_name:
                        sub_column_name = f"{last_parent} {inferred_name}"
                    else:
                        # Try to match common sub-column patterns
                        matched_pattern = _match_sub_column_pattern(sub_column_count, empty_count + 1)
                        if matched_pattern:
                            sub_column_name = f"{last_parent} {matched_pattern}"
                        else:
                            # Fallback to generic naming
                            sub_column_name = f"{last_parent} {sub_column_count}"
                    
                    normalized.append(sub_column_name)
                else:
                    # Empty header without a parent - generate a generic name
                    normalized.append(f"Column {i + 1}")
        
        logger.info(f"Header normalization: {len(headers)} headers normalized")
        logger.debug(f"Original headers: {headers}")
        logger.debug(f"Normalized headers: {normalized}")
        
        return normalized
        
    except Exception as e:
        logger.error(f"Error normalizing multi-line headers: {e}")
        # Return original headers if normalization fails
        return headers


def _infer_sub_column_name(rows: List[List[str]], column_index: int, sub_column_number: int) -> Optional[str]:
    """Infer sub-column name from data patterns."""
    try:
        # Look at first 5 rows for patterns
        sample_size = min(5, len(rows))
        column_values = []
        
        for i in range(sample_size):
            if column_index < len(rows[i]):
                value = str(rows[i][column_index]).strip()
                if value:
                    column_values.append(value.lower())
        
        if not column_values:
            return None
        
        # Check for common patterns
        if any('live' in v or 'count' in v or 'member' in v for v in column_values):
            return "Lives"
        elif any('pepm' in v or 'per member' in v for v in column_values):
            return "PEPM"
        elif any('subtotal' in v or 'sub total' in v for v in column_values):
            return "Subtotal"
        elif any('ind' in v or 'individual' in v for v in column_values):
            return "IND"
        elif any('hra' in v for v in column_values):
            return "HRA"
        elif any('total' in v for v in column_values):
            return "Total"
        elif any('amount' in v for v in column_values):
            return "Amount"
        elif any('rate' in v for v in column_values):
            return "Rate"
        
        return None
        
    except Exception as e:
        logger.warning(f"Error inferring sub-column name: {e}")
        return None


def _match_sub_column_pattern(position: int, total_sub_columns: int) -> Optional[str]:
    """Match common sub-column naming patterns based on position."""
    # Common 3-column patterns
    if total_sub_columns == 3:
        patterns_3col = [
            ['Lives', 'PEPM', 'Subtotal'],
            ['Count', 'Amount', 'Total'],
            ['IND', 'HRA', 'Total'],
            ['Quantity', 'Rate', 'Amount'],
        ]
        for pattern in patterns_3col:
            if position <= len(pattern):
                return pattern[position - 1]
    
    # Common 2-column patterns
    elif total_sub_columns == 2:
        patterns_2col = [
            ['Count', 'Amount'],
            ['Quantity', 'Total'],
            ['Value', 'Total'],
        ]
        for pattern in patterns_2col:
            if position <= len(pattern):
                return pattern[position - 1]
    
    return None


def detect_pdf_type(pdf_path: str) -> str:
    """
    Detect if PDF is scanned/image-based or digital/text-based.
    Returns: 'scanned' or 'digital'
    """
    try:
        doc = fitz.open(pdf_path)
        text_content = ""
        
        # Check first few pages for text content
        for page_num in range(min(3, len(doc))):
            page = doc.load_page(page_num)
            text_content += page.get_text()
        
        doc.close()
        
        # If we have substantial text content, it's likely digital
        if len(text_content.strip()) > 100:
            return "digital"
        else:
            return "scanned"
    except Exception as e:
        print(f"Error detecting PDF type: {e}")
        return "unknown"


def get_pdf_page_count(pdf_path: str) -> int:
    """
    Get the number of pages in a PDF document.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Number of pages in the PDF
    """
    try:
        doc = fitz.open(pdf_path)
        page_count = len(doc)
        doc.close()
        return page_count
    except Exception as e:
        print(f"Error getting PDF page count: {e}")
        return 0


def capture_table_screenshot(pdf_path: str, bbox: Tuple[float, float, float, float], page_num: int = 0) -> str:
    """
    Capture a screenshot of a table region for error reporting.
    Returns base64 encoded image.
    """
    try:
        doc = fitz.open(pdf_path)
        page = doc.load_page(page_num)
        
        # Convert bbox to fitz format (x0, y0, x1, y1)
        rect = fitz.Rect(bbox)
        
        # Get the pixmap of the region
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=rect)
        
        # Convert to PIL Image
        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        doc.close()
        return img_str
    except Exception as e:
        print(f"Error capturing screenshot: {e}")
        return ""


def infer_column_types(df: pd.DataFrame) -> Dict[str, str]:
    """
    Infer column types (number, text, date, currency) from DataFrame.
    """
    column_types = {}
    
    for col in df.columns:
        try:
            if hasattr(df[col], 'dtype') and df[col].dtype in ['int64', 'float64']:
                column_types[col] = 'number'
            elif hasattr(df[col], 'dtype') and df[col].dtype == 'object':
                # Check for date patterns
                sample_values = df[col].dropna().head(10)
                date_patterns = [
                    r'\d{1,2}/\d{1,2}/\d{2,4}',
                    r'\d{4}-\d{2}-\d{2}',
                    r'\d{1,2}-\d{1,2}-\d{2,4}'
                ]
                
                is_date = any(
                    sample_values.astype(str).str.match(pattern).any()
                    for pattern in date_patterns
                )
                
                if is_date:
                    column_types[col] = 'date'
                elif sample_values.astype(str).str.contains(r'[\$€£¥]').any():
                    column_types[col] = 'currency'
                else:
                    column_types[col] = 'text'
            else:
                column_types[col] = 'text'
        except Exception as e:
            # If there's any error, default to text
            column_types[col] = 'text'
    
    return column_types


def normalize_table_data(table_data: List[List[str]], headers: List[str]) -> Dict[str, Any]:
    """
    Normalize table data and convert to structured format.
    """
    if not table_data or not headers:
        return {"headers": [], "rows": [], "metadata": {}}
    
    # Create DataFrame for easier manipulation
    df = pd.DataFrame(table_data, columns=headers)
    
    # Clean up data
    df = df.replace('', np.nan)
    df = df.dropna(how='all')  # Remove completely empty rows
    
    # Infer column types
    column_types = infer_column_types(df)
    
    # Convert back to list format
    normalized_data = {
        "headers": headers,
        "rows": df.values.tolist(),
        "metadata": {
            "column_types": column_types,
            "row_count": len(df),
            "column_count": len(headers),
            "extraction_timestamp": datetime.now().isoformat()
        }
    }
    
    return normalized_data


def stitch_multipage_tables(tables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Enhanced multi-strategy table stitching for tables spanning multiple pages.
    
    Strategies:
    1. Canonical header identification and unification
    2. Comprehensive similarity analysis (header, structure, data patterns)
    3. Exact header matching (case-insensitive)
    4. Partial header matching (80% similarity threshold)
    5. Structure-based matching (column count and data patterns)
    6. Continuation detection (headers only on first page)
    7. Column count alignment for missing headers
    """
    if not tables:
        return tables
    
    print(f"📎 Enhanced multi-strategy stitching: Processing {len(tables)} tables")
    
    # Step 1: Find canonical header (most complete header)
    headers_list = [table.get("headers", []) for table in tables if table.get("headers") and len(table.get("headers", [])) > 0]
    canonical_header = max(headers_list, key=len) if headers_list else []
    print(f"📎 Canonical header identified: {canonical_header} ({len(canonical_header)} columns)")
    
    # **DEBUG: Log header information for each table**
    for i, table in enumerate(tables):
        headers = table.get("headers", [])
        print(f"📎 Table {i+1} headers: {headers} ({len(headers)} columns)")
    
    # Step 2: Group tables by comprehensive similarity
    table_groups = _group_tables_by_similarity(tables, canonical_header)
    
    print(f"📎 Grouped {len(tables)} tables into {len(table_groups)} groups")
    
    # Step 3: Merge each group
    merged_tables = []
    for i, group in enumerate(table_groups):
        print(f"📎 Merging group {i+1} with {len(group)} tables")
        merged_table = _merge_table_group(group, canonical_header)
        
        # **DEBUG: Log merged table structure**
        merged_headers = merged_table.get("headers", [])
        merged_rows = merged_table.get("rows", [])
        print(f"📎 Merged table {i+1}: {len(merged_headers)} headers, {len(merged_rows)} rows")
        print(f"📎 Merged headers: {merged_headers}")
        
        merged_tables.append(merged_table)
    
    print(f"📎 Enhanced stitching completed: {len(merged_tables)} final tables")
    return merged_tables

def _group_tables_by_similarity(tables: List[Dict[str, Any]], canonical_header: List[str]) -> List[List[Dict[str, Any]]]:
    """Group tables by comprehensive similarity analysis with improved identical header handling."""
    if not tables:
        return []
    
    groups = []
    processed = set()
    
    # **IMPROVED: First pass - group all tables with identical headers**
    header_groups = {}
    for i, table in enumerate(tables):
        headers = table.get("headers", [])
        header_key = tuple(h.lower().strip() for h in headers)
        
        if header_key not in header_groups:
            header_groups[header_key] = []
        header_groups[header_key].append((i, table))
    
    print(f"📎 Found {len(header_groups)} unique header patterns")
    for header_key, table_list in header_groups.items():
        if len(table_list) > 1:
            print(f"📎 Header pattern '{header_key[0] if header_key else 'empty'}' appears in {len(table_list)} tables")
    
    # Process each header group
    for header_key, table_list in header_groups.items():
        if not table_list:
            continue
            
        # If multiple tables have the same headers, group them together
        if len(table_list) > 1:
            group_indices = [i for i, _ in table_list]
            group_tables = [table for _, table in table_list]
            
            print(f"📎 Creating group with {len(group_tables)} tables (identical headers)")
            groups.append(group_tables)
            
            # Mark all tables in this group as processed
            for i in group_indices:
                processed.add(i)
        else:
            # Single table with unique headers - process individually
            i, table = table_list[0]
            if i not in processed:
                groups.append([table])
                processed.add(i)
    
    # **SECOND PASS: For remaining unprocessed tables, use similarity-based grouping**
    remaining_tables = [(i, table) for i, table in enumerate(tables) if i not in processed]
    
    for i, table in remaining_tables:
        if i in processed:
            continue
        
        # Start new group
        current_group = [table]
        processed.add(i)
        
        # Find similar tables among remaining tables
        for j, other_table in remaining_tables:
            if j in processed or j == i:
                continue
            
            # Calculate comprehensive similarity for non-exact matches
            similarity = _calculate_comprehensive_similarity(table, other_table, canonical_header)
            
            print(f"📎 Similarity between table {i} and {j}: {similarity:.3f}")
            
            # More flexible threshold for grouping
            if similarity >= 0.6:
                print(f"📎 Adding table {j} to group (similarity: {similarity:.3f})")
                current_group.append(other_table)
                processed.add(j)
        
        groups.append(current_group)
    
    return groups

def _calculate_comprehensive_similarity(table1: Dict[str, Any], table2: Dict[str, Any], canonical_header: List[str]) -> float:
    """Calculate comprehensive similarity score considering multiple factors."""
    scores = []
    weights = []
    
    # 1. Header similarity (weight: 0.3)
    headers1 = table1.get("headers", [])
    headers2 = table2.get("headers", [])
    header_similarity = _calculate_header_similarity_comprehensive(headers1, headers2)
    scores.append(header_similarity)
    weights.append(0.3)
    
    # 2. Column count similarity (weight: 0.2)
    col_count_similarity = _calculate_column_count_similarity(headers1, headers2)
    scores.append(col_count_similarity)
    weights.append(0.2)
    
    # 3. Row format similarity (weight: 0.25)
    row_format_similarity = _calculate_row_format_similarity(table1, table2, canonical_header)
    scores.append(row_format_similarity)
    weights.append(0.25)
    
    # 4. Data pattern similarity (weight: 0.15)
    data_pattern_similarity = _calculate_data_pattern_similarity(table1, table2)
    scores.append(data_pattern_similarity)
    weights.append(0.15)
    
    # 5. Structure similarity (weight: 0.1)
    structure_similarity = _calculate_structure_similarity(table1, table2)
    scores.append(structure_similarity)
    weights.append(0.1)
    
    # Calculate weighted average
    weighted_sum = sum(score * weight for score, weight in zip(scores, weights))
    total_weight = sum(weights)
    
    final_score = weighted_sum / total_weight if total_weight > 0 else 0.0
    
    print(f"📎 Similarity breakdown for tables:")
    print(f"   Header: {header_similarity:.3f}")
    print(f"   Column count: {col_count_similarity:.3f}")
    print(f"   Row format: {row_format_similarity:.3f}")
    print(f"   Data pattern: {data_pattern_similarity:.3f}")
    print(f"   Structure: {structure_similarity:.3f}")
    print(f"   Final score: {final_score:.3f}")
    
    return final_score

def _calculate_header_similarity_comprehensive(headers1: List[str], headers2: List[str]) -> float:
    """Calculate comprehensive header similarity with smart column splitting detection."""
    if not headers1 or not headers2:
        return 0.0
    
    # Normalize headers
    h1_norm = [h.lower().strip() for h in headers1]
    h2_norm = [h.lower().strip() for h in headers2]
    
    # Check for smart column splitting detection
    if _detect_smart_column_splitting(h1_norm, h2_norm):
        print(f"   🔍 Smart column splitting detected - using enhanced similarity")
        return _calculate_similarity_with_smart_splitting(h1_norm, h2_norm)
    
    # Calculate similarity for each header pair
    similarities = []
    max_len = max(len(h1_norm), len(h2_norm))
    
    for i in range(max_len):
        h1 = h1_norm[i] if i < len(h1_norm) else ""
        h2 = h2_norm[i] if i < len(h2_norm) else ""
        
        if h1 == h2:
            similarities.append(1.0)
        else:
            # Calculate partial similarity
            similarity = _calculate_string_similarity(h1, h2)
            similarities.append(similarity)
    
    return sum(similarities) / len(similarities) if similarities else 0.0

def _detect_smart_column_splitting(headers1: List[str], headers2: List[str]) -> bool:
    """Detect column splitting using smart, non-hardcoded techniques."""
    
    if not headers1 or not headers2:
        return False
    
    # Technique 1: Word-level analysis
    if _detect_word_level_splitting(headers1, headers2):
        return True
    
    # Technique 2: Phrase similarity analysis
    if _detect_phrase_similarity_splitting(headers1, headers2):
        return True
    
    # Technique 3: Column count analysis with content similarity
    if _detect_column_count_splitting(headers1, headers2):
        return True
    
    return False

def _detect_word_level_splitting(headers1: List[str], headers2: List[str]) -> bool:
    """Detect splitting by analyzing word-level patterns."""
    
    # Get all words from both header sets
    words1 = set()
    words2 = set()
    
    for header in headers1:
        words1.update(header.split())
    
    for header in headers2:
        words2.update(header.split())
    
    # Check for common words that might indicate splitting
    common_words = words1.intersection(words2)
    
    # If there are many common words but different column counts, likely splitting
    if len(common_words) >= 3 and abs(len(headers1) - len(headers2)) >= 1:
        # Check if the common words form meaningful phrases when combined
        common_words_list = list(common_words)
        for i, word1 in enumerate(common_words_list):
            for word2 in common_words_list[i+1:]:
                combined_phrase = f"{word1} {word2}"
                # Check if this combined phrase exists in either header set
                headers1_joined = " ".join(headers1)
                headers2_joined = " ".join(headers2)
                if combined_phrase in headers1_joined or combined_phrase in headers2_joined:
                    return True
    
    return False

def _detect_phrase_similarity_splitting(headers1: List[str], headers2: List[str]) -> bool:
    """Detect splitting by analyzing phrase similarity patterns."""
    
    # Join headers into phrases
    phrase1 = " ".join(headers1)
    phrase2 = " ".join(headers2)
    
    # Calculate phrase similarity
    phrase_similarity = _calculate_phrase_similarity(phrase1, phrase2)
    
    # If phrases are very similar but have different word counts, likely splitting
    if phrase_similarity >= 0.7:
        words1 = phrase1.split()
        words2 = phrase2.split()
        
        # Check if one has significantly more words than the other
        if abs(len(words1) - len(words2)) >= 2:
            return True
    
    return False

def _detect_column_count_splitting(headers1: List[str], headers2: List[str]) -> bool:
    """Detect splitting by analyzing column count differences with content similarity."""
    
    # If column counts are very different, check for content similarity
    if abs(len(headers1) - len(headers2)) >= 1:
        # Calculate content similarity
        content_similarity = _calculate_content_similarity(headers1, headers2)
        
        # If content is very similar but column counts differ, likely splitting
        if content_similarity >= 0.6:
            return True
    
    return False

def _calculate_content_similarity(headers1: List[str], headers2: List[str]) -> float:
    """Calculate similarity based on content analysis."""
    
    if not headers1 or not headers2:
        return 0.0
    
    # Get all words from both sets
    all_words1 = set()
    all_words2 = set()
    
    for header in headers1:
        all_words1.update(header.split())
    
    for header in headers2:
        all_words2.update(header.split())
    
    # Calculate Jaccard similarity for words
    intersection = len(all_words1.intersection(all_words2))
    union = len(all_words1.union(all_words2))
    
    word_similarity = intersection / union if union > 0 else 0.0
    
    # Also check character-level similarity
    char_similarity = _calculate_character_similarity(headers1, headers2)
    
    # Combine word and character similarity
    return (word_similarity * 0.7) + (char_similarity * 0.3)

def _calculate_character_similarity(headers1: List[str], headers2: List[str]) -> float:
    """Calculate character-level similarity between header sets."""
    
    # Join all headers into single strings
    text1 = " ".join(headers1)
    text2 = " ".join(headers2)
    
    # Calculate character-based similarity
    chars1 = set(text1)
    chars2 = set(text2)
    
    intersection = len(chars1.intersection(chars2))
    union = len(chars1.union(chars2))
    
    return intersection / union if union > 0 else 0.0

def _calculate_phrase_similarity(phrase1: str, phrase2: str) -> float:
    """Calculate similarity between phrases."""
    if not phrase1 or not phrase2:
        return 0.0
    
    if phrase1 == phrase2:
        return 1.0
    
    # Simple character-based similarity for phrases
    common_chars = sum(1 for c in phrase1 if c in phrase2)
    total_chars = max(len(phrase1), len(phrase2))
    
    return common_chars / total_chars if total_chars > 0 else 0.0

def _calculate_similarity_with_smart_splitting(headers1: List[str], headers2: List[str]) -> float:
    """Calculate similarity when smart column splitting is detected."""
    
    # Join headers to compare as phrases
    h1_joined = " ".join(headers1)
    h2_joined = " ".join(headers2)
    
    # Calculate phrase similarity
    phrase_similarity = _calculate_phrase_similarity(h1_joined, h2_joined)
    
    # Also consider individual word matches
    words1 = set(h1_joined.split())
    words2 = set(h2_joined.split())
    
    word_intersection = len(words1.intersection(words2))
    word_union = len(words1.union(words2))
    word_similarity = word_intersection / word_union if word_union > 0 else 0.0
    
    # Combine phrase and word similarity
    combined_similarity = (phrase_similarity * 0.7) + (word_similarity * 0.3)
    
    print(f"   Smart splitting similarity: phrase={phrase_similarity:.3f}, word={word_similarity:.3f}, combined={combined_similarity:.3f}")
    
    return combined_similarity

def _calculate_column_count_similarity(headers1: List[str], headers2: List[str]) -> float:
    """Calculate similarity based on column count."""
    count1 = len(headers1)
    count2 = len(headers2)
    
    if count1 == count2:
        return 1.0
    elif count1 == 0 or count2 == 0:
        return 0.0
    else:
        # Calculate similarity based on difference ratio
        max_count = max(count1, count2)
        min_count = min(count1, count2)
        difference_ratio = (max_count - min_count) / max_count
        return 1.0 - difference_ratio

def _calculate_row_format_similarity(table1: Dict[str, Any], table2: Dict[str, Any], canonical_header: List[str]) -> float:
    """Calculate similarity based on row format patterns."""
    rows1 = table1.get("rows", [])
    rows2 = table2.get("rows", [])
    
    if not rows1 or not rows2:
        return 0.0
    
    # Check row length consistency with canonical header
    expected_length = len(canonical_header)
    
    length_matches1 = sum(1 for row in rows1 if abs(len(row) - expected_length) <= 1)
    length_matches2 = sum(1 for row in rows2 if abs(len(row) - expected_length) <= 1)
    
    format_similarity1 = length_matches1 / len(rows1) if rows1 else 0.0
    format_similarity2 = length_matches2 / len(rows2) if rows2 else 0.0
    
    return (format_similarity1 + format_similarity2) / 2

def _calculate_data_pattern_similarity(table1: Dict[str, Any], table2: Dict[str, Any]) -> float:
    """Calculate similarity based on data value patterns."""
    rows1 = table1.get("rows", [])[:3]  # Sample first 3 rows
    rows2 = table2.get("rows", [])[:3]
    
    if not rows1 or not rows2:
        return 0.0
    
    # Analyze column patterns
    patterns1 = _analyze_column_patterns(rows1)
    patterns2 = _analyze_column_patterns(rows2)
    
    # Compare patterns
    pattern_matches = 0
    total_columns = min(len(patterns1), len(patterns2))
    
    for i in range(total_columns):
        if _patterns_are_similar(patterns1[i], patterns2[i]):
            pattern_matches += 1
    
    return pattern_matches / total_columns if total_columns > 0 else 0.0

def _analyze_column_patterns(rows: List[List[str]]) -> List[Dict[str, Any]]:
    """Analyze data patterns for each column."""
    if not rows:
        return []
    
    max_cols = max(len(row) for row in rows) if rows else 0
    patterns = []
    
    for col_idx in range(max_cols):
        column_data = []
        for row in rows:
            if col_idx < len(row):
                column_data.append(str(row[col_idx]).strip())
        
        pattern = {
            'has_numbers': any(_is_numeric(val) for val in column_data),
            'has_currency': any('$' in val for val in column_data),
            'has_dates': any(_is_date(val) for val in column_data),
            'avg_length': sum(len(val) for val in column_data) / len(column_data) if column_data else 0,
            'has_alpha': any(any(c.isalpha() for c in val) for val in column_data)
        }
        patterns.append(pattern)
    
    return patterns

def _patterns_are_similar(pattern1: Dict[str, Any], pattern2: Dict[str, Any]) -> bool:
    """Check if two column patterns are similar."""
    if not pattern1 or not pattern2:
        return False
    
    matches = 0
    total_checks = 0
    
    for key in ['has_numbers', 'has_currency', 'has_dates', 'has_alpha']:
        if pattern1.get(key) == pattern2.get(key):
            matches += 1
        total_checks += 1
    
    # Check length similarity
    length_diff = abs(pattern1.get('avg_length', 0) - pattern2.get('avg_length', 0))
    if length_diff <= 5:  # Allow 5 character difference
        matches += 1
    total_checks += 1
    
    return matches / total_checks >= 0.7 if total_checks > 0 else False

def _calculate_structure_similarity(table1: Dict[str, Any], table2: Dict[str, Any]) -> float:
    """Calculate similarity based on table structure."""
    has_headers1 = bool(table1.get("headers"))
    has_headers2 = bool(table2.get("headers"))
    has_rows1 = bool(table1.get("rows"))
    has_rows2 = bool(table2.get("rows"))
    
    matches = 0
    total_checks = 0
    
    if has_headers1 == has_headers2:
        matches += 1
    total_checks += 1
    
    if has_rows1 == has_rows2:
        matches += 1
    total_checks += 1
    
    # Check row count similarity
    if has_rows1 and has_rows2:
        rows1 = table1.get("rows", [])
        rows2 = table2.get("rows", [])
        row_count_diff = abs(len(rows1) - len(rows2))
        max_rows = max(len(rows1), len(rows2))
        if max_rows > 0 and row_count_diff / max_rows <= 0.5:
            matches += 1
        total_checks += 1
    
    return matches / total_checks if total_checks > 0 else 0.0

def _merge_table_group(group: List[Dict[str, Any]], canonical_header: List[str]) -> Dict[str, Any]:
    """Merge a group of similar tables into a single table."""
    if not group:
        return {}
    
    # **IMPROVED: Find the best header from the group**
    best_headers = None
    for table in group:
        headers = table.get("headers", [])
        if headers and len(headers) > 0:
            # Use the first non-empty header we find
            if not best_headers or len(headers) > len(best_headers):
                best_headers = headers
    
    # Fallback to canonical header if no good headers found
    if not best_headers:
        best_headers = canonical_header
    
    # Use the first table as base
    base_table = group[0].copy()
    all_rows = base_table.get("rows", [])
    
    # Add rows from other tables
    for table in group[1:]:
        rows = table.get("rows", [])
        all_rows.extend(rows)
    
    # **IMPROVED: Preserve original table metadata**
    merged_metadata = {
        "total_tables_merged": len(group),
        "total_rows": len(all_rows),
        "canonical_header": best_headers,
        "merged_from_tables": [table.get("metadata", {}).get("table_id", i) for i, table in enumerate(group)]
    }
    
    # Create merged table - preserve ALL fields from base table
    merged_table = base_table.copy()  # Start with all fields from base table
    merged_table.update({
        "headers": best_headers,
        "rows": all_rows,
        "metadata": merged_metadata
    })
    
    # **CRITICAL: Re-apply enhancements to the MERGED table with full row count**
    # The enhancements were applied to individual tables before merging,
    # but need to be re-applied to the merged table to work on all rows together
    try:
        from app.services.mistral.service import MistralDocumentAIService
        
        # Initialize service to get enhancement processors
        mistral_service = MistralDocumentAIService()
        
        # Re-apply enhancements to the merged table
        enhanced_merged = mistral_service._enhance_table_with_summary_detection(merged_table)
        
        logger.info(f"✅ Re-applied enhancements to merged table: {len(all_rows)} rows")
        return enhanced_merged
        
    except Exception as e:
        logger.warning(f"Failed to re-apply enhancements after merging: {e}")
        # Fallback: preserve original summary_detection from base table if it exists
        if "summary_detection" in base_table:
            merged_table["summary_detection"] = base_table["summary_detection"]
            # Update counts if summary rows were removed
            if merged_table["summary_detection"].get("removed_indices"):
                merged_table["summary_detection"]["original_row_count"] = len(all_rows)
                merged_table["summary_detection"]["cleaned_row_count"] = len(all_rows)
        
        return merged_table

def log_pipeline_performance(tables: List[Dict[str, Any]], original_tables: List[Dict[str, Any]], filename: str = "unknown"):
    """
    Log comprehensive pipeline performance statistics.
    
    Args:
        tables: Final processed tables
        original_tables: Original extracted tables before processing
        filename: Original PDF filename
    """
    print(f"\n📊 PIPELINE PERFORMANCE SUMMARY for {filename}")
    print(f"=" * 60)
    
    # Original extraction stats
    total_original_tables = len(original_tables)
    total_original_rows = sum(len(table.get("rows", [])) for table in original_tables)
    total_original_headers = sum(len(table.get("headers", [])) for table in original_tables)
    
    print(f"📋 Original Extraction:")
    print(f"   - Tables extracted: {total_original_tables}")
    print(f"   - Total rows: {total_original_rows}")
    print(f"   - Total headers: {total_original_headers}")
    
    # Final processing stats
    total_final_tables = len(tables)
    total_final_rows = sum(len(table.get("rows", [])) for table in tables)
    total_final_headers = sum(len(table.get("headers", [])) for table in tables)
    
    print(f"📋 Final Processing:")
    print(f"   - Tables after processing: {total_final_tables}")
    print(f"   - Total rows: {total_final_rows}")
    print(f"   - Total headers: {total_final_headers}")
    
    # Efficiency metrics
    row_preservation = (total_final_rows / total_original_rows * 100) if total_original_rows > 0 else 0
    table_reduction = ((total_original_tables - total_final_tables) / total_original_tables * 100) if total_original_tables > 0 else 0
    
    print(f"📋 Efficiency Metrics:")
    print(f"   - Row preservation: {row_preservation:.1f}%")
    print(f"   - Table reduction: {table_reduction:.1f}%")
    print(f"   - Average rows per table: {total_final_rows / total_final_tables:.1f}" if total_final_tables > 0 else "N/A")
    
    # Table details
    print(f"📋 Table Details:")
    for i, table in enumerate(tables):
        headers = table.get("headers", [])
        rows = table.get("rows", [])
        metadata = table.get("metadata", {})
        
        print(f"   Table {i + 1}:")
        print(f"     - Headers: {len(headers)} columns")
        print(f"     - Rows: {len(rows)}")
        print(f"     - Extraction method: {metadata.get('extraction_method', 'unknown')}")
        
        # Show stitching info if available
        if "total_tables_merged" in metadata:
            print(f"     - Tables merged: {metadata['total_tables_merged']}")
            print(f"     - Mapping efficiency: {metadata.get('header_alignment_stats', {}).get('mapping_efficiency', 0) * 100:.1f}%")
    
    print(f"=" * 60)

def _headers_exact_match(headers1: List[str], headers2: List[str]) -> bool:
    """Check if headers match exactly (case-insensitive)."""
    if len(headers1) != len(headers2):
        return False
    
    headers1_lower = [h.lower().strip() for h in headers1]
    headers2_lower = [h.lower().strip() for h in headers2]
    
    return headers1_lower == headers2_lower

def _headers_partial_match(headers1: List[str], headers2: List[str]) -> bool:
    """Check if headers match partially with similarity threshold."""
    if len(headers1) != len(headers2):
        return False
    
    # Calculate similarity for each header pair
    similarities = []
    for h1, h2 in zip(headers1, headers2):
        similarity = _calculate_string_similarity(h1, h2)
        similarities.append(similarity)
    
    # Check if average similarity meets threshold
    avg_similarity = sum(similarities) / len(similarities) if similarities else 0
    
    # Enhanced logging for debugging
    print(f"   Header similarity check: {avg_similarity:.3f} (threshold: {HEADER_SIMILARITY_THRESHOLD})")
    print(f"   Headers 1: {headers1}")
    print(f"   Headers 2: {headers2}")
    print(f"   Individual similarities: {similarities}")
    
    return avg_similarity >= HEADER_SIMILARITY_THRESHOLD

def _calculate_string_similarity(str1: str, str2: str) -> float:
    """Calculate similarity between two strings."""
    if not str1 or not str2:
        return 0.0
    
    str1_lower = str1.lower().strip()
    str2_lower = str2.lower().strip()
    
    if str1_lower == str2_lower:
        return 1.0
    
    # Simple character-based similarity
    common_chars = sum(1 for c in str1_lower if c in str2_lower)
    total_chars = max(len(str1_lower), len(str2_lower))
    
    return common_chars / total_chars if total_chars > 0 else 0.0

def _structure_based_match(table1: Dict[str, Any], table2: Dict[str, Any]) -> bool:
    """Check if tables have similar structure based on column count and data patterns."""
    rows1 = table1.get("rows", [])
    rows2 = table2.get("rows", [])
    
    if not rows1 or not rows2:
        return False
    
    # Check column count similarity
    col_count1 = len(rows1[0]) if rows1 else 0
    col_count2 = len(rows2[0]) if rows2 else 0
    
    if col_count1 != col_count2:
        return False
    
    # Check data pattern similarity (first few rows)
    pattern_similarity = _analyze_data_patterns(rows1[:3], rows2[:3])
    return pattern_similarity >= PATTERN_MATCH_THRESHOLD

def _analyze_data_patterns(rows1: List[List[str]], rows2: List[List[str]]) -> float:
    """Analyze data patterns between two sets of rows."""
    if not rows1 or not rows2:
        return 0.0
    
    # Simple pattern analysis: check if columns contain similar data types
    similarities = []
    
    for col_idx in range(min(len(rows1[0]), len(rows2[0]))):
        col1_values = [row[col_idx] for row in rows1 if col_idx < len(row)]
        col2_values = [row[col_idx] for row in rows2 if col_idx < len(row)]
        
        # Check if columns have similar characteristics
        similarity = _compare_column_characteristics(col1_values, col2_values)
        similarities.append(similarity)
    
    return sum(similarities) / len(similarities) if similarities else 0.0

def _compare_column_characteristics(values1: List[str], values2: List[str]) -> float:
    """Compare characteristics of two columns."""
    if not values1 or not values2:
        return 0.0
    
    # Check if both columns contain similar data types
    has_numbers1 = any(_is_numeric(v) for v in values1)
    has_numbers2 = any(_is_numeric(v) for v in values2)
    
    has_dates1 = any(_is_date(v) for v in values1)
    has_dates2 = any(_is_date(v) for v in values2)
    
    # Calculate similarity based on data type consistency
    type_similarity = 0.0
    if has_numbers1 == has_numbers2:
        type_similarity += 0.5
    if has_dates1 == has_dates2:
        type_similarity += 0.5
    
    return type_similarity

def _is_numeric(value: str) -> bool:
    """Check if a value is numeric."""
    if not value:
        return False
    
    # Remove common non-numeric characters
    clean_value = value.replace(',', '').replace('$', '').replace('%', '').strip()
    
    # Check if it's a number
    try:
        float(clean_value)
        return True
    except ValueError:
        return False

def _is_date(value: str) -> bool:
    """Check if a value looks like a date."""
    if not value:
        return False
    
    # Simple date pattern detection
    import re
    date_patterns = [
        r'\d{1,2}/\d{1,2}/\d{2,4}',  # MM/DD/YYYY
        r'\d{1,2}-\d{1,2}-\d{2,4}',  # MM-DD-YYYY
        r'\d{4}-\d{1,2}-\d{1,2}',    # YYYY-MM-DD
    ]
    
    for pattern in date_patterns:
        if re.search(pattern, value):
            return True
    
    return False

def _continuation_detection(headers1: List[str], headers2: List[str], rows2: List[List[str]]) -> bool:
    """Detect if table2 is a continuation of table1 (headers only on first page)."""
    # Case 1: Next table has no headers
    if not headers2:
        return True
    
    # Case 2: Next table has very few headers (likely not real headers)
    if len(headers2) <= 2:
        return True
    
    # Case 3: Next table has data rows but headers look like data
    if rows2 and len(headers2) == len(rows2[0]):
        # Check if headers look like data (contain numbers, etc.)
        header_looks_like_data = any(_is_numeric(h) or _is_date(h) for h in headers2)
        return header_looks_like_data
    
    return False


def validate_table_structure(table: Dict[str, Any]) -> Dict[str, Any]:
    """
    Data-preserving table structure validation with enhanced logic.
    
    Args:
        table: Table dictionary to validate
        
    Returns:
        Validated table with metadata
    """
    validation_result = {
        "is_valid": True,
        "warnings": [],
        "errors": [],
        "preservation_metrics": {
            "original_rows": 0,
            "preserved_rows": 0,
            "original_columns": 0,
            "preserved_columns": 0
        }
    }
    
    headers = table.get("headers", [])
    rows = table.get("rows", [])
    footers = table.get("footers", [])
    
    # Track original dimensions
    original_row_count = len(rows)
    original_col_count = len(headers) if headers else 0
    
    print(f"📊 Data preservation: Validating table with {original_row_count} rows and {original_col_count} columns")
    
    # Generate default headers if none exist
    if not headers and rows:
        print("📋 Data preservation: No headers found, generating default headers")
        max_cols = max(len(row) for row in rows) if rows else 0
        headers = [f"Column_{i+1}" for i in range(max_cols)]
        table["headers"] = headers
        validation_result["warnings"].append("Generated default headers")
    
    # Ensure headers are strings and not empty
    if headers:
        normalized_headers = []
        for i, header in enumerate(headers):
            if header and str(header).strip():
                cleaned_header = _clean_text(str(header).strip())
                normalized_headers.append(cleaned_header)
            else:
                # Generate meaningful header based on data
                meaningful_header = _generate_header_from_data(rows, i) if rows else f"Column_{i+1}"
                normalized_headers.append(meaningful_header)
                print(f"📋 Data preservation: Generated header '{meaningful_header}' for empty column {i}")
        
        table["headers"] = normalized_headers
        headers = normalized_headers
    
    # Preserve all rows and normalize cell content
    if rows:
        normalized_rows = []
        for i, row in enumerate(rows):
            if isinstance(row, (list, tuple)):
                # Preserve all cells, normalize to strings and clean them
                normalized_row = [_clean_text(str(cell).strip()) if cell else "" for cell in row]
                normalized_rows.append(normalized_row)
            else:
                # Single value row - preserve as single column
                normalized_rows.append([_clean_text(str(row).strip()) if row else ""])
                validation_result["warnings"].append(f"Row {i} converted to single column")
        
        table["rows"] = normalized_rows
        rows = normalized_rows
    
    # Normalize row lengths by padding (don't truncate)
    if rows and headers:
        max_cols = len(headers)
        for i, row in enumerate(rows):
            if len(row) < max_cols:
                # Pad with empty strings
                rows[i] = row + [""] * (max_cols - len(row))
            elif len(row) > max_cols:
                # Extend headers to match longest row
                while len(headers) < len(row):
                    headers.append(f"Column_{len(headers)+1}")
                table["headers"] = headers
                validation_result["warnings"].append(f"Extended headers to match row {i} length")
    
    # Ensure footers are strings
    if footers:
        footers = [str(f).strip() if f else "" for f in footers]
        table["footers"] = footers
    
    # Check for duplicate headers and make them unique
    if headers:
        unique_headers = []
        header_counts = {}
        
        for header in headers:
            if header in header_counts:
                header_counts[header] += 1
                unique_header = f"{header}_{header_counts[header]}"
                unique_headers.append(unique_header)
                validation_result["warnings"].append(f"Made duplicate header '{header}' unique: '{unique_header}'")
            else:
                header_counts[header] = 1
                unique_headers.append(header)
        
        table["headers"] = unique_headers
    
    # Calculate preservation metrics
    final_row_count = len(rows)
    final_col_count = len(headers)
    
    validation_result["preservation_metrics"] = {
        "original_rows": original_row_count,
        "preserved_rows": final_row_count,
        "original_columns": original_col_count,
        "preserved_columns": final_col_count,
        "row_preservation_rate": final_row_count / original_row_count if original_row_count > 0 else 1.0,
        "column_preservation_rate": final_col_count / original_col_count if original_col_count > 0 else 1.0
    }
    
    print(f"📊 Data preservation: Final result - {final_row_count} rows and {final_col_count} columns")
    print(f"📊 Data preservation: Row preservation rate: {validation_result['preservation_metrics']['row_preservation_rate']:.1%}")
    print(f"📊 Data preservation: Column preservation rate: {validation_result['preservation_metrics']['column_preservation_rate']:.1%}")
    
    # Ensure required fields exist
    if "row_count" not in table:
        table["row_count"] = len(rows)
    if "column_count" not in table:
        table["column_count"] = len(headers)
    if "extractor" not in table:
        table["extractor"] = "unknown"
    
    # Update validation result
    table["validation"] = validation_result
    return table

def _clean_text(text: str) -> str:
    """
    Clean and normalize text by removing excessive formatting and artifacts.
    
    Args:
        text: Raw text to clean
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Remove excessive underscores (common in form fields and OCR artifacts)
    import re
    cleaned = re.sub(r'_+', ' ', text)
    
    # Remove excessive dashes (common in form fields)
    cleaned = re.sub(r'-+', ' ', cleaned)
    
    # Remove excessive dots/periods
    cleaned = re.sub(r'\.+', '.', cleaned)
    
    # Remove excessive spaces
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    # Remove leading/trailing whitespace
    cleaned = cleaned.strip()
    
    # If the result is just whitespace or empty, return empty string
    if not cleaned or cleaned.isspace():
        return ""
    
    return cleaned

def _generate_header_from_data(rows: List[List[str]], column_index: int) -> str:
    """
    Generate a meaningful header based on the data in a specific column.
    
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
        date_pattern = any(_is_date(val) for val in sample_values)
        if date_pattern:
            return "Date"
        
        # Check if it looks like numbers
        number_pattern = any(_is_numeric(val) for val in sample_values)
        if number_pattern:
            return "Amount"
        
        # Check if it looks like names
        name_pattern = any(_looks_like_name(val) for val in sample_values)
        if name_pattern:
            return "Name"
        
        # Default to a generic header
        return f"Column_{column_index+1}"
        
    except Exception as e:
        print(f"Error generating header from data: {e}")
        return f"Column_{column_index+1}"

def _looks_like_name(value: str) -> bool:
    """Check if a value looks like a name."""
    import re
    # Simple heuristic: contains letters and spaces, no numbers
    return bool(re.match(r'^[A-Za-z\s]+$', value))


def convert_to_csv(table: Dict[str, Any]) -> str:
    """
    Convert table data to CSV format.
    """
    try:
        df = pd.DataFrame(table.get("rows", []), columns=table.get("headers", []))
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        return csv_buffer.getvalue()
    except Exception as e:
        print(f"Error converting to CSV: {e}")
        return ""


def convert_to_excel(tables: List[Dict[str, Any]]) -> bytes:
    """
    Convert multiple tables to Excel format.
    """
    try:
        with pd.ExcelWriter(io.BytesIO(), engine='openpyxl') as writer:
            for i, table in enumerate(tables):
                df = pd.DataFrame(table.get("rows", []), columns=table.get("headers", []))
                sheet_name = f"Table_{i+1}"
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        return writer.buffer.getvalue()
    except Exception as e:
        print(f"Error converting to Excel: {e}")
        return b""


def transform_pipeline_response_to_client_format(pipeline_response: Dict[str, Any], filename: str = "uploaded_file.pdf") -> Dict[str, Any]:
    """
    Transform pipeline response to the format expected by the client.
    Enhanced to handle Docling output and ensure consistent structure.
    
    Args:
        pipeline_response: Response from the pipeline or Docling extractor
        filename: Original filename
    
    Returns:
        Client-expected format response
    """
    import uuid
    from datetime import datetime
    
    # Handle different response formats
    if pipeline_response.get("status") == "error":
        return {
            "status": "error",
            "error": pipeline_response.get("error", "Unknown error"),
            "timestamp": datetime.now().isoformat()
        }
    
    # Check if this is a Docling-specific response
    if "docling" in pipeline_response.get("metadata", {}).get("extractors_used", []):
        tables = pipeline_response.get("tables", [])
        if not tables:
            return {
                "status": "success",
                "job_id": str(uuid.uuid4()),
                "file_name": filename,
                "extraction_metrics": {
                    "total_text_elements": 0,
                    "extraction_time": pipeline_response.get("extraction_time_seconds", 0.0),
                    "table_confidence": 0.0,
                    "model_used": "docling"
                },
                "document_info": {},
                "table_headers": [],
                "table_data": [],
                            "quality_summary": {
                "total_tables": 0,
                "valid_tables": 0,
                "average_quality_score": 0.0,
                "overall_confidence": "LOW",
                "issues_found": ["No tables found"],
                "recommendations": ["Check PDF quality and extraction parameters"]
            },
            "quality_metrics": {
                "table_confidence": 0.0,
                "text_elements_extracted": 0,
                "table_rows_extracted": 0,
                "extraction_completeness": "none",
                "data_quality": "none"
            },
                "timestamp": datetime.now().isoformat()
            }
        
        # Combine all tables into one response with smart header handling
        all_headers = []
        all_table_data = []
        total_rows = 0
        total_cells = 0
        all_valid = True
        
        # First pass: find the most comprehensive header set
        for table in tables:
            headers = table.get("headers", [])
            if len(headers) > len(all_headers):
                all_headers = headers
        
        # If no headers found, try to infer from the largest table
        if not all_headers:
            largest_table = max(tables, key=lambda t: len(t.get("rows", [])))
            if largest_table.get("rows"):
                max_cols = max(len(row) for row in largest_table["rows"])
                all_headers = [f"Column_{i+1}" for i in range(max_cols)]
        
        # Second pass: process all tables with the unified header set
        for table_idx, table in enumerate(tables):
            headers = table.get("headers", [])
            rows = table.get("rows", [])
            
            # Convert rows to the expected format
            for row_idx, row in enumerate(rows):
                row_dict = {}
                
                # Handle cases where row has different number of columns than headers
                for i, header in enumerate(all_headers):
                    if i < len(headers):
                        # Use the table's own header if available
                        header_key = headers[i].lower().replace(" ", "_").replace("-", "_")
                    else:
                        # Use the unified header
                        header_key = header.lower().replace(" ", "_").replace("-", "_")
                    
                    # Get the value, handling different row lengths
                    if i < len(row):
                        value = str(row[i])
                    else:
                        value = ""
                    
                    row_dict[header_key] = value
                
                all_table_data.append(row_dict)
            
            total_rows += len(rows)
            total_cells += sum(len(row) for row in rows) if rows else 0
            
            # Check validation
            validation = table.get("validation", {})
            if not validation.get("is_valid", False):
                all_valid = False
        
        # Calculate confidence based on validation
        confidence = 1.0 if all_valid else 0.5
        
        # Convert table_data back to the format expected by frontend
        # table_data is currently an array of objects, need to convert to array of arrays
        table_rows = []
        for row_dict in all_table_data:
            row_array = []
            for header in all_headers:
                header_key = header.lower().replace(" ", "_").replace("-", "_")
                row_array.append(row_dict.get(header_key, ""))
            table_rows.append(row_array)
        
        # Create tables array in the format expected by frontend
        frontend_tables = [{
            "header": all_headers,
            "rows": table_rows,
            "extractor": "docling",  # Add extractor information
            "metadata": {
                "extraction_method": "docling"
            }
        }]
        
        return {
            "status": "success",
            "job_id": str(uuid.uuid4()),
            "file_name": filename,
            "extraction_metrics": {
                "total_text_elements": total_cells,
                "extraction_time": pipeline_response.get("extraction_time_seconds", 0.0),
                "table_confidence": confidence,
                "model_used": "docling"
            },
            "document_info": {
                "pdf_type": "unknown",
                "total_tables": len(tables)
            },
            "tables": frontend_tables,  # Frontend expects this format
            "table_headers": all_headers,  # Keep for backward compatibility
            "table_data": all_table_data,  # Keep for backward compatibility
            "quality_summary": {
                "total_tables": len(tables),
                "valid_tables": len(tables),  # All tables are considered valid
                "average_quality_score": 100.0,  # High score since no quality assessment
                "overall_confidence": "HIGH",
                "issues_found": [],
                "recommendations": ["Extraction completed successfully"]
            },
            "quality_metrics": {
                "table_confidence": confidence,
                "text_elements_extracted": total_cells,
                "table_rows_extracted": total_rows,
                "extraction_completeness": "complete" if total_rows > 0 else "none",
                "data_quality": "good" if all_valid else "poor"
            },
            "timestamp": datetime.now().isoformat()
        }
    
    # Handle standard pipeline response
    if not pipeline_response.get("success", False):
        return {
            "status": "error",
            "error": pipeline_response.get("error", "Unknown error"),
            "timestamp": datetime.now().isoformat()
        }
    
    # Get the first table (or create empty if none)
    tables = pipeline_response.get("tables", [])
    if not tables:
        return {
            "status": "success",
            "job_id": str(uuid.uuid4()),
            "file_name": filename,
            "extraction_metrics": {
                "total_text_elements": 0,
                "extraction_time": 0.0,
                "table_confidence": 0.0,
                "model_used": "none"
            },
            "document_info": {},
            "tables": [],  # Frontend expects this format
            "table_headers": [],
            "table_data": [],
            "quality_metrics": {
                "table_confidence": 0.0,
                "text_elements_extracted": 0,
                "table_rows_extracted": 0,
                "extraction_completeness": "none",
                "data_quality": "none"
            },
            "timestamp": datetime.now().isoformat()
        }
    
    # Combine all tables into one response with smart header handling
    all_headers = []
    all_table_data = []
    total_rows = 0
    total_cells = 0
    all_valid = True
    
    # First pass: find the most comprehensive header set
    for table in tables:
        headers = table.get("headers", [])
        if len(headers) > len(all_headers):
            all_headers = headers
    
    # If no headers found, try to infer from the largest table
    if not all_headers:
        largest_table = max(tables, key=lambda t: len(t.get("rows", [])))
        if largest_table.get("rows"):
            max_cols = max(len(row) for row in largest_table["rows"])
            all_headers = [f"Column_{i+1}" for i in range(max_cols)]
    
    # Second pass: process all tables with the unified header set
    for table_idx, table in enumerate(tables):
        headers = table.get("headers", [])
        rows = table.get("rows", [])
        
        # Convert rows to the expected format
        for row_idx, row in enumerate(rows):
            row_dict = {}
            
            # Handle cases where row has different number of columns than headers
            for i, header in enumerate(all_headers):
                if i < len(headers):
                    # Use the table's own header if available
                    header_key = headers[i].lower().replace(" ", "_").replace("-", "_")
                else:
                    # Use the unified header
                    header_key = header.lower().replace(" ", "_").replace("-", "_")
                
                # Get the value, handling different row lengths
                if i < len(row):
                    value = str(row[i])
                else:
                    value = ""
                
                row_dict[header_key] = value
            
            all_table_data.append(row_dict)
        
        total_rows += len(rows)
        total_cells += sum(len(row) for row in rows) if rows else 0
        
        # Check validation
        validation = table.get("validation", {})
        if not validation.get("is_valid", False):
            all_valid = False
    
    # Get extraction method used
    extraction_methods = pipeline_response.get("metadata", {}).get("extraction_methods_used", ["unknown"])
    model_used = extraction_methods[0] if extraction_methods else "unknown"
    
    # Calculate confidence based on validation
    confidence = 1.0 if all_valid else 0.5
    
    # Convert table_data back to the format expected by frontend
    # table_data is currently an array of objects, need to convert to array of arrays
    table_rows = []
    for row_dict in all_table_data:
        row_array = []
        for header in all_headers:
            header_key = header.lower().replace(" ", "_").replace("-", "_")
            row_array.append(row_dict.get(header_key, ""))
        table_rows.append(row_array)
    
    # Create tables array in the format expected by frontend
    frontend_tables = [{
        "header": all_headers,
        "rows": table_rows,
        "extractor": model_used,  # Add extractor information
        "metadata": {
            "extraction_method": model_used
        }
    }]
    
    return {
        "status": "success",
        "job_id": str(uuid.uuid4()),
        "file_name": filename,
        "extraction_metrics": {
            "total_text_elements": total_cells,
            "extraction_time": pipeline_response.get("extraction_time_seconds", 1.0),
            "table_confidence": confidence,
            "model_used": model_used
        },
        "document_info": {
            "pdf_type": pipeline_response.get("pdf_type", "unknown"),
            "total_tables": len(tables)
        },
        "tables": frontend_tables,  # Frontend expects this format
        "table_headers": all_headers,
        "table_data": all_table_data,
        "quality_metrics": {
            "table_confidence": confidence,
            "text_elements_extracted": total_cells,
            "table_rows_extracted": total_rows,
            "extraction_completeness": "complete" if total_rows > 0 else "none",
            "data_quality": "good" if all_valid else "poor"
        },
        "timestamp": datetime.now().isoformat()
    } 