"""Advanced multi-page table linking and reconstruction."""

from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import re
from dataclasses import dataclass
import asyncio
from ..utils.logging_utils import get_logger
from ..utils.config import Config

@dataclass
class PageTable:
    """Represents a table found on a specific page."""
    page_number: int
    table_data: Dict[str, Any]
    headers: List[str]
    bbox: List[float]
    confidence: float
    original_table: Optional[Any] = None  # Store reference to original table object
    
class MultiPageTableHandler:
    """Handler for linking and reconstructing tables across multiple pages using sequence-based approach."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = get_logger(__name__, config)
        
        # Similarity thresholds for header detection
        self.header_similarity_threshold = 0.85
        self.new_table_detection_threshold = 0.3  # Low threshold to detect new tables
    
    async def link_multipage_tables(
        self, 
        page_tables: List[List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """Link tables that span multiple pages using sequence-based approach."""
        
        try:
            self.logger.logger.info(f"🔗 Sequence-based multipage handler: Processing {len(page_tables)} pages")
            
            # Convert to PageTable objects and sort by page number
            all_page_tables = []
            for page_num, tables in enumerate(page_tables):
                for table in tables:
                    page_table = PageTable(
                        page_number=page_num,
                        table_data=table,
                        headers=table.get('headers', []),
                        bbox=table.get('bbox', [0, 0, 0, 0]),
                        confidence=table.get('confidence', 0.0)
                    )
                    # **NEW: Store reference to original table object for better data extraction**
                    if hasattr(table, 'original_table'):
                        page_table.original_table = table.original_table
                    elif 'original_table' in table:
                        page_table.original_table = table['original_table']
                    all_page_tables.append(page_table)
            
            # Sort by page number to maintain sequence
            all_page_tables.sort(key=lambda t: t.page_number)
            
            self.logger.logger.info(f"📋 Converted to {len(all_page_tables)} PageTable objects across {len(page_tables)} pages")
            
            # Group tables by sequence-based continuation
            table_groups = await self._group_tables_by_sequence(all_page_tables)
            
            self.logger.logger.info(f"🔍 Found {len(table_groups)} table groups")
            for i, group in enumerate(table_groups):
                self.logger.logger.info(f"   Group {i}: {len(group)} tables from pages {[pt.page_number for pt in group]}")
            
            # Merge each group into a single table
            merged_tables = []
            for group in table_groups:
                if group:
                    merged_table = await self._merge_table_group(group)
                    merged_tables.append(merged_table)
            
            # **NEW: Final consolidation step - merge tables with similar headers**
            if len(merged_tables) > 1:
                self.logger.logger.info(f"🔗 Final consolidation: checking {len(merged_tables)} tables for similar headers")
                consolidated_tables = await self._consolidate_similar_headers(merged_tables)
                self.logger.logger.info(f"🔗 Final consolidation: {len(merged_tables)} → {len(consolidated_tables)} tables")
                merged_tables = consolidated_tables
            
            self.logger.logger.info(f"🔗 Linked {len(page_tables)} pages into {len(merged_tables)} tables")
            return merged_tables
            
        except Exception as e:
            self.logger.logger.error(f"Sequence-based multi-page linking failed: {e}")
            # Return original tables if linking fails
            return [table for page in page_tables for table in page]
    
    async def _group_tables_by_sequence(
        self, 
        page_tables: List[PageTable]
    ) -> List[List[PageTable]]:
        """Group tables by sequence-based continuation logic."""
        
        if not page_tables:
            return []
        
        table_groups = []
        current_group = []
        current_headers = None
        
        self.logger.logger.info(f"🔍 Starting sequence-based grouping of {len(page_tables)} tables")
        
        for i, table in enumerate(page_tables):
            self.logger.logger.info(f"🔍 Processing table {i} from page {table.page_number}")
            self.logger.logger.info(f"   Headers: {table.headers[:3]}...")
            
            # Check if this table starts a new table group
            is_new_table = await self._is_new_table_start(table, current_headers)
            
            if is_new_table:
                # Save current group if it exists
                if current_group:
                    table_groups.append(current_group)
                    self.logger.logger.info(f"✅ Completed group with {len(current_group)} tables")
                
                # Start new group
                current_group = [table]
                current_headers = table.headers
                self.logger.logger.info(f"🆕 Started new table group with headers: {table.headers[:3]}...")
                
            else:
                # Continue current group
                current_group.append(table)
                self.logger.logger.info(f"✅ Added to current group (now {len(current_group)} tables)")
        
        # Add the last group
        if current_group:
            table_groups.append(current_group)
            self.logger.logger.info(f"✅ Completed final group with {len(current_group)} tables")
        
        return table_groups
    
    async def _is_new_table_start(
        self, 
        table: PageTable, 
        current_headers: Optional[List[str]]
    ) -> bool:
        """Enhanced table continuation detection with intelligent commission statement handling."""
        
        # If no current headers, this is definitely a new table
        if current_headers is None:
            self.logger.logger.info(f"🆕 First table - starting new group")
            return True
        
        # **IMPROVED: Better handling of empty or minimal headers**
        # If table has no headers or very few headers, it's likely a continuation
        if not table.headers or len([h for h in table.headers if h.strip()]) <= 1:
            self.logger.logger.info(f"📋 No/minimal headers - likely continuation")
            return False
        
        # **NEW: Check if this is clearly a different table with distinct headers**
        if self._is_clearly_different_table(table.headers, current_headers):
            self.logger.logger.info(f"🆕 Clearly different table detected - starting new group")
            return True
        
        # Check if headers look like data (strong continuation indicator)
        if self._headers_look_like_data(table.headers):
            self.logger.logger.info(f"📋 Headers look like data - likely continuation")
            return False
        
        # **IMPROVED: Better commission statement continuation detection**
        if await self._is_commission_statement_continuation(table, current_headers):
            self.logger.logger.info(f"📋 Commission statement continuation detected - merging tables")
            return False
        
        # **NEW: Check for continuation indicators in table data**
        if self._has_continuation_indicators(table):
            self.logger.logger.info(f"📋 Found continuation indicators in table data - likely continuation")
            return False
        
        # Enhanced similarity analysis
        similarity_score = await self._calculate_comprehensive_similarity(table, current_headers)
        
        self.logger.logger.info(f"🔍 Comprehensive similarity score: {similarity_score:.3f}")
        
        # More flexible threshold for table merging
        # If similarity is high enough, merge even with some header differences
        if similarity_score >= 0.4:  # **CHANGED: Lowered from 0.5 to 0.4**
            self.logger.logger.info(f"📋 High comprehensive similarity ({similarity_score:.3f}) - merging tables")
            return False
        elif similarity_score >= 0.25:  # **CHANGED: Lowered from 0.3 to 0.25**
            # Check additional structural criteria for moderate similarity
            if await self._has_similar_structure(table, current_headers):
                self.logger.logger.info(f"📋 Moderate similarity with similar structure - merging tables")
                return False
            else:
                self.logger.logger.info(f"🆕 Moderate similarity but different structure - new table")
                return True
        else:
            self.logger.logger.info(f"🆕 Low similarity ({similarity_score:.3f}) - new table")
            return True
    
    async def _calculate_comprehensive_similarity(
        self, 
        table: PageTable, 
        current_headers: List[str]
    ) -> float:
        """Calculate comprehensive similarity score considering multiple factors."""
        
        scores = []
        weights = []
        
        # 1. Header similarity (weight: 0.3)
        header_similarity = self._calculate_header_similarity(current_headers, table.headers)
        scores.append(header_similarity)
        weights.append(0.3)
        
        # 2. Column count similarity (weight: 0.2)
        col_count_similarity = self._calculate_column_count_similarity(current_headers, table.headers)
        scores.append(col_count_similarity)
        weights.append(0.2)
        
        # 3. Row format similarity (weight: 0.25)
        row_format_similarity = await self._calculate_row_format_similarity(table, current_headers)
        scores.append(row_format_similarity)
        weights.append(0.25)
        
        # 4. Data pattern similarity (weight: 0.15)
        data_pattern_similarity = await self._calculate_data_pattern_similarity(table, current_headers)
        scores.append(data_pattern_similarity)
        weights.append(0.15)
        
        # 5. Table positioning similarity (weight: 0.1)
        position_similarity = self._calculate_position_similarity(table)
        scores.append(position_similarity)
        weights.append(0.1)
        
        # Calculate weighted average
        weighted_sum = sum(score * weight for score, weight in zip(scores, weights))
        total_weight = sum(weights)
        
        final_score = weighted_sum / total_weight if total_weight > 0 else 0.0
        
        self.logger.logger.info(f"🔍 Similarity breakdown:")
        self.logger.logger.info(f"   Header: {header_similarity:.3f}")
        self.logger.logger.info(f"   Column count: {col_count_similarity:.3f}")
        self.logger.logger.info(f"   Row format: {row_format_similarity:.3f}")
        self.logger.logger.info(f"   Data pattern: {data_pattern_similarity:.3f}")
        self.logger.logger.info(f"   Position: {position_similarity:.3f}")
        self.logger.logger.info(f"   Final weighted score: {final_score:.3f}")
        
        return final_score
    
    def _calculate_column_count_similarity(self, headers1: List[str], headers2: List[str]) -> float:
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
    
    async def _calculate_row_format_similarity(
        self, 
        table: PageTable, 
        current_headers: List[str]
    ) -> float:
        """Calculate similarity based on row format patterns."""
        rows = table.table_data.get('rows', [])
        if not rows:
            return 0.0
        
        # Analyze row format characteristics
        row_lengths = [len(row) for row in rows if row]
        if not row_lengths:
            return 0.0
        
        # Check if row lengths are consistent with current headers
        expected_length = len(current_headers)
        length_matches = sum(1 for length in row_lengths if abs(length - expected_length) <= 1)
        length_similarity = length_matches / len(row_lengths) if row_lengths else 0.0
        
        # Analyze cell content patterns
        cell_pattern_similarity = self._analyze_cell_pattern_similarity(rows, current_headers)
        
        # Combine length and pattern similarity
        return (length_similarity * 0.6) + (cell_pattern_similarity * 0.4)
    
    def _analyze_cell_pattern_similarity(self, rows: List[List[str]], current_headers: List[str]) -> float:
        """Analyze similarity of cell content patterns."""
        if not rows or not current_headers:
            return 0.0
        
        # Sample first few rows for pattern analysis
        sample_rows = rows[:min(3, len(rows))]
        
        pattern_matches = 0
        total_checks = 0
        
        for row in sample_rows:
            if len(row) != len(current_headers):
                continue
            
            row_matches = 0
            for i, cell in enumerate(row):
                if i >= len(current_headers):
                    break
                
                # Check if cell content pattern matches expected pattern for this column
                if self._cell_matches_column_pattern(cell, i, current_headers):
                    row_matches += 1
            
            if len(current_headers) > 0:
                pattern_matches += row_matches / len(current_headers)
                total_checks += 1
        
        return pattern_matches / total_checks if total_checks > 0 else 0.0
    
    def _cell_matches_column_pattern(self, cell: str, column_index: int, headers: List[str]) -> bool:
        """Check if a cell matches the expected pattern for its column."""
        if not cell or column_index >= len(headers):
            return False
        
        # Simple pattern matching based on column position and content
        cell_lower = cell.lower().strip()
        
        # Check for common patterns based on column position
        if column_index == 0:  # Usually company/name column
            return len(cell_lower) > 2 and any(c.isalpha() for c in cell_lower)
        elif column_index == len(headers) - 1:  # Usually total/amount column
            return any(c.isdigit() for c in cell_lower) or '$' in cell_lower
        
        # For middle columns, check for mixed content
        return len(cell_lower) > 0
    
    async def _calculate_data_pattern_similarity(
        self, 
        table: PageTable, 
        current_headers: List[str]
    ) -> float:
        """Calculate similarity based on data value patterns."""
        rows = table.table_data.get('rows', [])
        if not rows:
            return 0.0
        
        # Analyze data types in each column
        column_patterns = self._analyze_column_data_patterns(rows)
        
        # Compare with expected patterns based on current headers
        expected_patterns = self._get_expected_column_patterns(current_headers)
        
        # Calculate pattern similarity
        pattern_matches = 0
        total_columns = min(len(column_patterns), len(expected_patterns))
        
        for i in range(total_columns):
            if self._patterns_are_similar(column_patterns[i], expected_patterns[i]):
                pattern_matches += 1
        
        return pattern_matches / total_columns if total_columns > 0 else 0.0
    
    def _analyze_column_data_patterns(self, rows: List[List[str]]) -> List[Dict[str, Any]]:
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
                'has_numbers': any(self._is_numeric(val) for val in column_data),
                'has_currency': any('$' in val for val in column_data),
                'has_dates': any(self._is_date(val) for val in column_data),
                'avg_length': sum(len(val) for val in column_data) / len(column_data) if column_data else 0,
                'has_alpha': any(any(c.isalpha() for c in val) for val in column_data)
            }
            patterns.append(pattern)
        
        return patterns
    
    def _get_expected_column_patterns(self, headers: List[str]) -> List[Dict[str, Any]]:
        """Get expected patterns based on header names."""
        patterns = []
        
        for header in headers:
            header_lower = header.lower()
            pattern = {
                'has_numbers': any(word in header_lower for word in ['amount', 'total', 'count', 'number', 'rate', 'premium']),
                'has_currency': any(word in header_lower for word in ['amount', 'total', 'premium', 'commission', 'due']),
                'has_dates': any(word in header_lower for word in ['date', 'period', 'month', 'year']),
                'avg_length': 10,  # Default expected length
                'has_alpha': True  # Most headers contain text
            }
            patterns.append(pattern)
        
        return patterns
    
    def _patterns_are_similar(self, pattern1: Dict[str, Any], pattern2: Dict[str, Any]) -> bool:
        """Check if two column patterns are similar."""
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
    
    def _calculate_position_similarity(self, table: PageTable) -> float:
        """Calculate similarity based on table positioning."""
        if not table.bbox or len(table.bbox) < 4:
            return 0.5  # Neutral score if no position data
        
        # Tables that continue often start near the top of the page
        y_position = table.bbox[1]
        
        # Higher score for tables near the top (likely continuations)
        if y_position < 100:
            return 0.9
        elif y_position < 200:
            return 0.7
        elif y_position < 300:
            return 0.5
        else:
            return 0.3
    
    async def _has_similar_structure(self, table: PageTable, current_headers: List[str]) -> bool:
        """Check if table has similar structure to current headers."""
        rows = table.table_data.get('rows', [])
        if not rows:
            return False
        
        # Check if row structure matches
        expected_cols = len(current_headers)
        structure_matches = 0
        
        for row in rows[:5]:  # Check first 5 rows
            if len(row) == expected_cols:
                structure_matches += 1
        
        structure_similarity = structure_matches / min(5, len(rows)) if rows else 0.0
        
        # Also check if the table appears to be a continuation
        continuation_indicators = 0
        
        # Check if first row looks like data (not headers)
        if rows and not self._headers_look_like_data(rows[0]):
            continuation_indicators += 1
        
        # Check if table position suggests continuation
        if table.bbox and len(table.bbox) >= 4:
            if table.bbox[1] < 150:  # Near top of page
                continuation_indicators += 1
        
        return structure_similarity >= 0.6 or continuation_indicators >= 2
    
    def _is_numeric(self, value: str) -> bool:
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
    
    def _is_date(self, value: str) -> bool:
        """Check if a value looks like a date."""
        if not value:
            return False
        
        # Simple date pattern detection
        date_patterns = [
            r'\d{1,2}/\d{1,2}/\d{2,4}',  # MM/DD/YYYY
            r'\d{1,2}-\d{1,2}-\d{2,4}',  # MM-DD-YYYY
            r'\d{4}-\d{1,2}-\d{1,2}',    # YYYY-MM-DD
        ]
        
        import re
        for pattern in date_patterns:
            if re.search(pattern, value):
                return True
        
        return False
    
    async def _looks_like_continuation(
        self, 
        table: PageTable, 
        current_headers: List[str]
    ) -> bool:
        """Check if table looks like a continuation despite moderate header similarity."""
        
        # Check if table structure matches current headers
        if self._matches_table_structure(table.headers, {'headers': current_headers}):
            return True
        
        # Check if table position is consistent with continuation
        if table.bbox and len(table.bbox) >= 4:
            # Tables that continue often start near the top of the page
            if table.bbox[1] < 100:  # Near top of page
                return True
        
        # Check if the "headers" actually contain data patterns
        if self._has_similar_content_pattern(table.headers, {'headers': current_headers}):
            return True
        
        return False
    
    def _calculate_header_similarity(self, headers1: List[str], headers2: List[str]) -> float:
        """Calculate similarity between header lists with enhanced column splitting detection."""
        
        if not headers1 or not headers2:
            return 0.0
        
        # Normalize headers
        h1_norm = [h.lower().strip() for h in headers1]
        h2_norm = [h.lower().strip() for h in headers2]
        
        # Check for column splitting scenarios
        if self._detect_column_splitting(h1_norm, h2_norm):
            self.logger.logger.info(f"🔍 Detected column splitting - adjusting similarity calculation")
            return self._calculate_similarity_with_column_splitting(h1_norm, h2_norm)
        
        # Calculate Jaccard similarity
        set1 = set(h1_norm)
        set2 = set(h2_norm)
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0
    
    def _detect_column_splitting(self, headers1: List[str], headers2: List[str]) -> bool:
        """Detect if headers show signs of column splitting or confusion using smart techniques."""
        
        if not headers1 or not headers2:
            return False
        
        # Normalize headers
        h1_norm = [h.lower().strip() for h in headers1 if h.strip()]
        h2_norm = [h.lower().strip() for h in headers2 if h.strip()]
        
        # Technique 1: Word-level analysis
        if self._detect_word_level_splitting(h1_norm, h2_norm):
            return True
        
        # Technique 2: Phrase similarity analysis
        if self._detect_phrase_similarity_splitting(h1_norm, h2_norm):
            return True
        
        # Technique 3: Column count analysis with content similarity
        if self._detect_column_count_splitting(h1_norm, h2_norm):
            return True
        
        return False
    
    def _detect_word_level_splitting(self, headers1: List[str], headers2: List[str]) -> bool:
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
    
    def _detect_phrase_similarity_splitting(self, headers1: List[str], headers2: List[str]) -> bool:
        """Detect splitting by analyzing phrase similarity patterns."""
        
        # Join headers into phrases
        phrase1 = " ".join(headers1)
        phrase2 = " ".join(headers2)
        
        # Calculate phrase similarity
        phrase_similarity = self._calculate_phrase_similarity(phrase1, phrase2)
        
        # If phrases are very similar but have different word counts, likely splitting
        if phrase_similarity >= 0.7:
            words1 = phrase1.split()
            words2 = phrase2.split()
            
            # Check if one has significantly more words than the other
            if abs(len(words1) - len(words2)) >= 2:
                return True
        
        return False
    
    def _detect_column_count_splitting(self, headers1: List[str], headers2: List[str]) -> bool:
        """Detect splitting by analyzing column count differences with content similarity."""
        
        # If column counts are very different, check for content similarity
        if abs(len(headers1) - len(headers2)) >= 1:
            # Calculate content similarity
            content_similarity = self._calculate_content_similarity(headers1, headers2)
            
            # If content is very similar but column counts differ, likely splitting
            if content_similarity >= 0.6:
                return True
        
        return False
    
    def _calculate_content_similarity(self, headers1: List[str], headers2: List[str]) -> float:
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
        char_similarity = self._calculate_character_similarity(headers1, headers2)
        
        # Combine word and character similarity
        return (word_similarity * 0.7) + (char_similarity * 0.3)
    
    def _calculate_character_similarity(self, headers1: List[str], headers2: List[str]) -> float:
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
    
    def _calculate_similarity_with_column_splitting(self, headers1: List[str], headers2: List[str]) -> float:
        """Calculate similarity when column splitting is detected."""
        
        # Join headers to compare as phrases
        h1_joined = " ".join(headers1)
        h2_joined = " ".join(headers2)
        
        # Calculate phrase similarity
        phrase_similarity = self._calculate_phrase_similarity(h1_joined, h2_joined)
        
        # Also consider individual word matches
        words1 = set(h1_joined.split())
        words2 = set(h2_joined.split())
        
        word_intersection = len(words1.intersection(words2))
        word_union = len(words1.union(words2))
        word_similarity = word_intersection / word_union if word_union > 0 else 0.0
        
        # Combine phrase and word similarity
        combined_similarity = (phrase_similarity * 0.7) + (word_similarity * 0.3)
        
        self.logger.logger.info(f"🔍 Column splitting similarity: phrase={phrase_similarity:.3f}, word={word_similarity:.3f}, combined={combined_similarity:.3f}")
        
        return combined_similarity
    
    def _calculate_phrase_similarity(self, phrase1: str, phrase2: str) -> float:
        """Calculate similarity between phrases."""
        if not phrase1 or not phrase2:
            return 0.0
        
        if phrase1 == phrase2:
            return 1.0
        
        # Simple character-based similarity for phrases
        common_chars = sum(1 for c in phrase1 if c in phrase2)
        total_chars = max(len(phrase1), len(phrase2))
        
        return common_chars / total_chars if total_chars > 0 else 0.0
    
    def _has_continuation_indicators(self, table: PageTable) -> bool:
        """Check if table contains continuation indicators in its data."""
        if not table.table_data or not table.table_data.get('rows'):
            return False
        
        # Check first few rows for continuation indicators
        rows = table.table_data.get('rows', [])
        for row in rows[:3]:  # Check first 3 rows
            if not row:
                continue
            
            row_text = ' '.join(str(cell).lower() for cell in row if cell)
            
            # Look for continuation indicators
            continuation_indicators = [
                'continued', 'continued next page', 'anat goldstein continued',
                'total commissions', 'total medical premium', 'total dental premium',
                'total vision premium', 'total paid commissions'
            ]
            
            for indicator in continuation_indicators:
                if indicator in row_text:
                    self.logger.logger.info(f"🔍 Found continuation indicator: '{indicator}' in row: {row_text[:100]}...")
                    return True
        
        return False
    
    def _headers_look_like_data(self, headers: List[str]) -> bool:
        """Check if headers actually look like data rows instead of headers."""
        if not headers:
            return False
        
        # **IMPROVED: Better detection of actual headers vs data rows**
        # First check if this looks like a proper header row
        if self._looks_like_proper_header_row(headers):
            self.logger.logger.info(f"🔍 Headers look like proper headers - not data")
            return False
        
        # Use statistical analysis to determine if headers look like data
        data_indicators = 0
        total_headers = len(headers)
        
        for header in headers:
            header_str = str(header).strip()
            
            # Check for data-like characteristics
            if self._is_data_like_content(header_str):
                data_indicators += 1
        
        # If more than 40% of headers look like data, they probably are data
        threshold = 0.4 if total_headers >= 5 else 0.5
        
        result = data_indicators >= total_headers * threshold
        
        if result:
            self.logger.logger.info(f"🔍 Headers look like data: {data_indicators}/{total_headers} indicators")
        
        return result
    
    def _looks_like_proper_header_row(self, headers: List[str]) -> bool:
        """Check if headers look like a proper header row (not data)."""
        if not headers:
            return False
        
        # Check for common header patterns
        header_indicators = 0
        total_headers = len(headers)
        
        for header in headers:
            header_str = str(header).strip().lower()
            
            # Check for header-like characteristics
            if self._is_header_like_content(header_str):
                header_indicators += 1
        
        # If more than 60% of headers look like proper headers, they probably are headers
        threshold = 0.6 if total_headers >= 5 else 0.5
        
        result = header_indicators >= total_headers * threshold
        
        if result:
            self.logger.logger.info(f"🔍 Headers look like proper headers: {header_indicators}/{total_headers} indicators")
        
        return result
    
    def _is_header_like_content(self, content: str) -> bool:
        """Determine if content looks like a header using enhanced analysis."""
        if not content:
            return False
        
        indicators = 0
        
        # Header-like characteristics
        header_words = [
            'company', 'name', 'policy', 'current', 'comm', 'rate', 'invoicing', 'period', 
            'premium', 'amount', 'action', 'adjustment', 'group', 'comm.period',
            'billing', 'subscriber', 'total', 'due', 'prior', 'month', 'year', 'date'
        ]
        
        # Check for header words
        if any(word in content for word in header_words):
            indicators += 2
        
        # Check for proper case patterns (headers often have proper case or title case)
        if content.istitle() or content.islower():
            indicators += 1
        
        # Check for reasonable length (headers are usually not too long or too short)
        if 3 <= len(content) <= 25:
            indicators += 1
        
        # Check for common header patterns
        if any(pattern in content for pattern in ['comm.', 'period', 'amount', 'rate']):
            indicators += 1
        
        # Check for multiple words (headers often have multiple words)
        if len(content.split()) >= 2:
            indicators += 1
        
        # Check for no numbers at the start (headers rarely start with numbers)
        if not content[0].isdigit():
            indicators += 1
        
        # Check for no currency symbols (headers rarely have currency symbols)
        if '$' not in content:
            indicators += 1
        
        # Check for no percentage symbols (headers rarely have percentage symbols)
        if '%' not in content:
            indicators += 1
        
        # Check for no dates (headers rarely contain dates)
        if not re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', content):
            indicators += 1
        
        # Check for no company suffixes in the middle (data often has LLC, Inc, etc.)
        if not any(suffix in content for suffix in ['llc', 'inc', 'corp', 'company']):
            indicators += 1
        
        return indicators >= 4  # Need at least 4 indicators to be considered header-like
    
    def _is_data_like_content(self, content: str) -> bool:
        """Determine if content looks like data using statistical analysis."""
        if not content:
            return False
        
        indicators = 0
        
        # Length analysis
        if 3 <= len(content) <= 50:
            indicators += 1
        
        # Character type distribution
        alpha_count = sum(1 for c in content if c.isalpha())
        digit_count = sum(1 for c in content if c.isdigit())
        
        # Data often has mixed character types
        if alpha_count > 0 and digit_count > 0:
            indicators += 1
        
        # Case pattern analysis
        if content != content.upper() and content != content.lower():
            indicators += 1
        
        # Numeric content detection
        if any(c.isdigit() for c in content):
            if digit_count > alpha_count:
                indicators += 1
        
        # Word count analysis
        word_count = len(content.split())
        if 1 <= word_count <= 3:
            indicators += 1
        
        # Special character analysis
        if any(c in content for c in [',', '.', '-', '/', '(', ')']):
            indicators += 1
        
        # Financial document specific patterns
        if any(suffix in content.upper() for suffix in ['LLC', 'INC', 'CORP', 'CO', 'COMPANY']):
            indicators += 2
        
        if len(content) == 2 and content.isupper() and content.isalpha():
            indicators += 2
        
        if len(content) >= 6 and any(c.isdigit() for c in content) and any(c.isalpha() for c in content):
            indicators += 1
        
        if '$' in content and any(c.isdigit() for c in content):
            indicators += 2
        
        if content.isdigit() and 1 <= int(content) <= 100:
            indicators += 1
        
        if '/subscriber' in content.lower() or '/month' in content.lower():
            indicators += 2
        
        # Header-like content detection (negative indicators)
        header_indicators = 0
        
        if len(content) <= 15 and alpha_count > digit_count:
            header_indicators += 1
        
        if content.islower() or content.istitle():
            header_indicators += 1
        
        if len(content) <= 10 and content.islower():
            header_indicators += 1
        
        # Strong header indicators
        header_words = ['billing', 'group', 'premium', 'commission', 'rate', 'subscriber', 'total', 'due', 'current', 'prior', 'adjustment']
        if any(word in content.lower() for word in header_words):
            header_indicators += 2
        
        final_score = indicators - header_indicators
        return final_score >= 2
    
    def _is_clearly_different_table(self, headers1: List[str], headers2: List[str]) -> bool:
        """Check if headers represent clearly different tables."""
        
        if not headers1 or not headers2:
            return False
        
        # Normalize headers for comparison
        norm1 = [str(h).lower().strip() for h in headers1 if h.strip()]
        norm2 = [str(h).lower().strip() for h in headers2 if h.strip()]
        
        # Check for completely different header sets (no overlap)
        set1 = set(norm1)
        set2 = set(norm2)
        intersection = set1.intersection(set2)
        
        # If there's no overlap at all, it's clearly a different table
        if len(intersection) == 0:
            self.logger.logger.info(f"🔍 No header overlap - clearly different table")
            return True
        
        # Check for different column counts with minimal overlap
        if abs(len(norm1) - len(norm2)) >= 2 and len(intersection) <= 1:
            self.logger.logger.info(f"🔍 Different column count ({len(norm1)} vs {len(norm2)}) with minimal overlap - different table")
            return True
        
        # Check for specific patterns that indicate different table types
        # Commission adjustments vs Group business patterns
        adjustment_indicators = ['action', 'adjustment', 'comm.rate', 'overpayment', 'comm.period']
        group_business_indicators = ['company name', 'current comm.rate', 'invoicing period', 'premium', 'comm. amt', 'companyname']
        
        has_adjustment_indicators = any(indicator in ' '.join(norm1) for indicator in adjustment_indicators)
        has_group_business_indicators = any(indicator in ' '.join(norm1) for indicator in group_business_indicators)
        
        prev_has_adjustment = any(indicator in ' '.join(norm2) for indicator in adjustment_indicators)
        prev_has_group_business = any(indicator in ' '.join(norm2) for indicator in group_business_indicators)
        
        # If one is adjustment table and other is group business table, they're different
        if (has_adjustment_indicators and prev_has_group_business) or (has_group_business_indicators and prev_has_adjustment):
            self.logger.logger.info(f"🔍 Different table types detected (adjustment vs group business) - different table")
            return True
        
        # **NEW: Check for specific header patterns that indicate different table purposes**
        # Check if headers have completely different semantic meaning
        if self._has_different_table_purpose(norm1, norm2):
            self.logger.logger.info(f"🔍 Different table purposes detected - different table")
            return True
        
        # Check for header patterns that suggest different table purposes
        # If headers have completely different semantic meaning
        semantic_similarity = self._calculate_semantic_similarity(norm1, norm2)
        if semantic_similarity < 0.2:  # Very low semantic similarity
            self.logger.logger.info(f"🔍 Very low semantic similarity ({semantic_similarity:.3f}) - different table")
            return True
        
        return False
    
    def _calculate_semantic_similarity(self, headers1: List[str], headers2: List[str]) -> float:
        """Calculate semantic similarity between header sets."""
        
        if not headers1 or not headers2:
            return 0.0
        
        # Define semantic categories for headers
        categories = {
            'financial': ['amount', 'premium', 'commission', 'total', 'due', 'paid'],
            'identification': ['company', 'name', 'group', 'policy', 'number', 'id'],
            'temporal': ['date', 'period', 'month', 'year', 'invoicing'],
            'action': ['action', 'adjustment', 'increase', 'decrease', 'overpayment'],
            'rate': ['rate', 'percent', '%', 'commission rate', 'current comm']
        }
        
        # Categorize headers
        def categorize_headers(headers):
            categories_found = set()
            for header in headers:
                header_lower = header.lower()
                for category, keywords in categories.items():
                    if any(keyword in header_lower for keyword in keywords):
                        categories_found.add(category)
            return categories_found
        
        cat1 = categorize_headers(headers1)
        cat2 = categorize_headers(headers2)
        
        # Calculate Jaccard similarity for categories
        intersection = len(cat1.intersection(cat2))
        union = len(cat1.union(cat2))
        
        return intersection / union if union > 0 else 0.0
    
    def _has_different_table_purpose(self, headers1: List[str], headers2: List[str]) -> bool:
        """Check if headers represent tables with different purposes."""
        
        if not headers1 or not headers2:
            return False
        
        # Define table purpose categories
        purposes = {
            'adjustment': ['action', 'adjustment', 'comm.rate', 'overpayment', 'comm.period'],
            'group_business': ['company name', 'current comm.rate', 'invoicing period', 'premium', 'comm. amt', 'companyname'],
            'summary': ['total', 'summary', 'grand total', 'subtotal'],
            'billing': ['billing', 'invoice', 'due', 'paid', 'outstanding']
        }
        
        # Determine purpose of each header set
        def get_table_purpose(headers):
            header_text = ' '.join(headers).lower()
            purpose_scores = {}
            
            for purpose, keywords in purposes.items():
                score = sum(1 for keyword in keywords if keyword in header_text)
                purpose_scores[purpose] = score
            
            # Return the purpose with the highest score
            if purpose_scores:
                return max(purpose_scores, key=purpose_scores.get)
            return None
        
        purpose1 = get_table_purpose(headers1)
        purpose2 = get_table_purpose(headers2)
        
        # If purposes are different and both are clearly defined, they're different tables
        if purpose1 and purpose2 and purpose1 != purpose2:
            self.logger.logger.info(f"🔍 Different table purposes: {purpose1} vs {purpose2}")
            return True
        
        # Check for specific patterns that indicate different table types
        # Commission adjustments vs Group business patterns
        adjustment_indicators = ['action', 'adjustment', 'comm.rate', 'overpayment', 'comm.period']
        group_business_indicators = ['company name', 'current comm.rate', 'invoicing period', 'premium', 'comm. amt', 'companyname']
        
        has_adjustment_indicators = any(indicator in ' '.join(headers1) for indicator in adjustment_indicators)
        has_group_business_indicators = any(indicator in ' '.join(headers1) for indicator in group_business_indicators)
        
        prev_has_adjustment = any(indicator in ' '.join(headers2) for indicator in adjustment_indicators)
        prev_has_group_business = any(indicator in ' '.join(headers2) for indicator in group_business_indicators)
        
        # If one is adjustment table and other is group business table, they're different
        if (has_adjustment_indicators and prev_has_group_business) or (has_group_business_indicators and prev_has_adjustment):
            self.logger.logger.info(f"🔍 Different table types detected (adjustment vs group business) - different table")
            return True
        
        return False
    
    def _matches_table_structure(self, potential_data_row: List[str], table_data: Dict[str, Any]) -> bool:
        """Check if a potential data row matches the structure of the table."""
        if not potential_data_row or not table_data:
            return False
        
        # Get the number of columns in the original table
        original_headers = table_data.get('headers', [])
        original_columns = len(original_headers)
        
        # Check if the potential data row has the same number of columns
        if len(potential_data_row) == original_columns:
            return True
        
        # Check if it's close (within 1 column difference)
        if abs(len(potential_data_row) - original_columns) <= 1:
            return True
        
        return False
    
    def _has_similar_content_pattern(self, potential_data_row: List[str], table_data: Dict[str, Any]) -> bool:
        """Check if the potential data row has similar content patterns to the table."""
        if not potential_data_row or not table_data:
            return False
        
        # Get sample rows from the table to compare patterns
        rows = table_data.get('rows', [])
        if not rows:
            return False
        
        # Learn patterns from existing table data
        column_patterns = self._learn_column_patterns(rows)
        
        # Check if the potential data row matches learned patterns
        pattern_matches = 0
        total_checks = 0
        
        for i, cell in enumerate(potential_data_row):
            if i >= len(column_patterns):
                break
            
            cell_str = str(cell).strip()
            column_pattern = column_patterns[i]
            
            # Check if cell matches the learned pattern for this column
            if self._matches_column_pattern(cell_str, column_pattern):
                pattern_matches += 1
            
            total_checks += 1
        
        # Require at least 60% pattern match for continuation
        return total_checks > 0 and (pattern_matches / total_checks) >= 0.6
    
    def _learn_column_patterns(self, rows: List[List[str]]) -> List[Dict[str, Any]]:
        """Learn patterns from table data for each column."""
        if not rows:
            return []
        
        num_columns = max(len(row) for row in rows) if rows else 0
        column_patterns = []
        
        for col_idx in range(num_columns):
            column_data = []
            for row in rows:
                if col_idx < len(row):
                    column_data.append(str(row[col_idx]).strip())
            
            if column_data:
                pattern = self._analyze_column_pattern(column_data)
                column_patterns.append(pattern)
            else:
                column_patterns.append({})
        
        return column_patterns
    
    def _analyze_column_pattern(self, column_data: List[str]) -> Dict[str, Any]:
        """Analyze the pattern of a single column."""
        if not column_data:
            return {}
        
        pattern = {
            'length_stats': self._calculate_length_stats(column_data),
            'char_type_distribution': self._calculate_char_type_distribution(column_data),
            'case_patterns': self._analyze_case_patterns(column_data),
            'numeric_patterns': self._analyze_numeric_patterns(column_data),
            'special_char_patterns': self._analyze_special_char_patterns(column_data),
            'word_patterns': self._analyze_word_patterns(column_data)
        }
        
        return pattern
    
    def _calculate_length_stats(self, data: List[str]) -> Dict[str, float]:
        """Calculate length statistics for a column."""
        lengths = [len(item) for item in data if item]
        if not lengths:
            return {'mean': 0, 'std': 0, 'min': 0, 'max': 0}
        
        mean_length = sum(lengths) / len(lengths)
        variance = sum((x - mean_length) ** 2 for x in lengths) / len(lengths)
        std_length = variance ** 0.5
        
        return {
            'mean': mean_length,
            'std': std_length,
            'min': min(lengths),
            'max': max(lengths)
        }
    
    def _calculate_char_type_distribution(self, data: List[str]) -> Dict[str, float]:
        """Calculate character type distribution for a column."""
        total_chars = 0
        alpha_chars = 0
        digit_chars = 0
        special_chars = 0
        
        for item in data:
            for char in item:
                total_chars += 1
                if char.isalpha():
                    alpha_chars += 1
                elif char.isdigit():
                    digit_chars += 1
                else:
                    special_chars += 1
        
        if total_chars == 0:
            return {'alpha_ratio': 0, 'digit_ratio': 0, 'special_ratio': 0}
        
        return {
            'alpha_ratio': alpha_chars / total_chars,
            'digit_ratio': digit_chars / total_chars,
            'special_ratio': special_chars / total_chars
        }
    
    def _analyze_case_patterns(self, data: List[str]) -> Dict[str, Any]:
        """Analyze case patterns in a column."""
        all_upper = sum(1 for item in data if item.isupper())
        all_lower = sum(1 for item in data if item.islower())
        mixed_case = sum(1 for item in data if not item.isupper() and not item.islower() and item)
        title_case = sum(1 for item in data if item.istitle())
        
        total = len(data)
        if total == 0:
            return {'all_upper_ratio': 0, 'all_lower_ratio': 0, 'mixed_case_ratio': 0, 'title_case_ratio': 0}
        
        return {
            'all_upper_ratio': all_upper / total,
            'all_lower_ratio': all_lower / total,
            'mixed_case_ratio': mixed_case / total,
            'title_case_ratio': title_case / total
        }
    
    def _analyze_numeric_patterns(self, data: List[str]) -> Dict[str, Any]:
        """Analyze numeric patterns in a column."""
        numeric_count = 0
        decimal_count = 0
        currency_count = 0
        
        for item in data:
            clean_item = item.replace(',', '').replace('$', '').replace('%', '').strip()
            
            if clean_item.replace('.', '').isdigit():
                numeric_count += 1
                if '.' in clean_item:
                    decimal_count += 1
            
            if '$' in item or '%' in item:
                currency_count += 1
        
        total = len(data)
        if total == 0:
            return {'numeric_ratio': 0, 'decimal_ratio': 0, 'currency_ratio': 0}
        
        return {
            'numeric_ratio': numeric_count / total,
            'decimal_ratio': decimal_count / total,
            'currency_ratio': currency_count / total
        }
    
    def _analyze_special_char_patterns(self, data: List[str]) -> Dict[str, float]:
        """Analyze special character patterns in a column."""
        special_chars = set()
        for item in data:
            for char in item:
                if not char.isalnum() and char != ' ':
                    special_chars.add(char)
        
        char_freq = {}
        total_chars = sum(len(item) for item in data)
        
        if total_chars > 0:
            for char in special_chars:
                freq = sum(item.count(char) for item in data) / total_chars
                char_freq[char] = freq
        
        return char_freq
    
    def _analyze_word_patterns(self, data: List[str]) -> Dict[str, Any]:
        """Analyze word patterns in a column."""
        word_counts = [len(item.split()) for item in data]
        
        if not word_counts:
            return {'mean_words': 0, 'std_words': 0, 'max_words': 0}
        
        mean_words = sum(word_counts) / len(word_counts)
        variance = sum((x - mean_words) ** 2 for x in word_counts) / len(word_counts)
        std_words = variance ** 0.5
        
        return {
            'mean_words': mean_words,
            'std_words': std_words,
            'max_words': max(word_counts)
        }
    
    def _matches_column_pattern(self, cell: str, pattern: Dict[str, Any]) -> bool:
        """Check if a cell matches the learned pattern for a column."""
        if not pattern or not cell:
            return False
        
        matches = 0
        total_checks = 0
        
        # Check length pattern
        if 'length_stats' in pattern:
            length_stats = pattern['length_stats']
            cell_length = len(cell)
            mean_length = length_stats['mean']
            std_length = length_stats['std']
            
            if abs(cell_length - mean_length) <= 2 * std_length:
                matches += 1
            total_checks += 1
        
        # Check character type distribution
        if 'char_type_distribution' in pattern:
            char_dist = pattern['char_type_distribution']
            alpha_count = sum(1 for c in cell if c.isalpha())
            digit_count = sum(1 for c in cell if c.isdigit())
            special_count = len(cell) - alpha_count - digit_count
            
            if len(cell) > 0:
                alpha_ratio = alpha_count / len(cell)
                digit_ratio = digit_count / len(cell)
                special_ratio = special_count / len(cell)
                
                if (abs(alpha_ratio - char_dist['alpha_ratio']) <= 0.3 and
                    abs(digit_ratio - char_dist['digit_ratio']) <= 0.3 and
                    abs(special_ratio - char_dist['special_ratio']) <= 0.3):
                    matches += 1
                total_checks += 1
        
        # Check case pattern
        if 'case_patterns' in pattern:
            case_patterns = pattern['case_patterns']
            if cell.isupper() and case_patterns['all_upper_ratio'] > 0.5:
                matches += 1
            elif cell.islower() and case_patterns['all_lower_ratio'] > 0.5:
                matches += 1
            elif not cell.isupper() and not cell.islower() and case_patterns['mixed_case_ratio'] > 0.3:
                matches += 1
            total_checks += 1
        
        # Check numeric pattern
        if 'numeric_patterns' in pattern:
            numeric_patterns = pattern['numeric_patterns']
            clean_cell = cell.replace(',', '').replace('$', '').replace('%', '').strip()
            
            if clean_cell.replace('.', '').isdigit():
                if numeric_patterns['numeric_ratio'] > 0.5:
                    matches += 1
                if '.' in clean_cell and numeric_patterns['decimal_ratio'] > 0.3:
                    matches += 1
            if ('$' in cell or '%' in cell) and numeric_patterns['currency_ratio'] > 0.3:
                matches += 1
            total_checks += 1
        
        # Check word count pattern
        if 'word_patterns' in pattern:
            word_patterns = pattern['word_patterns']
            word_count = len(cell.split())
            mean_words = word_patterns['mean_words']
            std_words = word_patterns['std_words']
            
            if abs(word_count - mean_words) <= 2 * std_words:
                matches += 1
            total_checks += 1
        
        return total_checks > 0 and (matches / total_checks) >= 0.6
    
    async def _merge_table_group(self, table_group: List[PageTable]) -> Dict[str, Any]:
        """Merge a group of continued tables into a single table."""
        
        if not table_group:
            return {}
        
        if len(table_group) == 1:
            # For single tables, still add multipage_info
            base_table = table_group[0].table_data.copy()
            base_table['multipage_info'] = {
                'is_multipage': False,
                'page_count': 1,
                'page_numbers': [table_group[0].page_number],
                'merge_confidence': table_group[0].confidence
            }
            base_table['page_number'] = table_group[0].page_number
            base_table['page_sequence'] = [table_group[0].page_number]
            return base_table
        
        # Use first table as base
        base_table = table_group[0].table_data.copy()
        
        # Merge rows from subsequent tables
        all_rows = list(base_table.get('rows', []))
        all_cells = list(base_table.get('cells', []))
        
        current_row_offset = len(all_rows)
        
        for i, page_table in enumerate(table_group[1:], 1):
            table_data = page_table.table_data
            
            # Add rows (skip headers if they exist)
            rows = table_data.get('rows', [])
            
            # **IMPROVED: Better handling of continuation tables**
            # Check if the "headers" of this table are actually data
            if self._headers_look_like_data(table_data.get('headers', [])):
                # The "headers" are actually data, so include them as the first row
                if table_data.get('headers'):
                    rows = [table_data.get('headers')] + rows
            elif rows and table_data.get('headers') and i > 0:
                # Skip first row if it looks like headers
                if self._is_header_row(rows[0], base_table.get('headers', [])):
                    rows = rows[1:]
            
            # **NEW: Handle continuation tables with proper data extraction**
            # If this is a continuation table, ensure we extract all the data properly
            if i > 0 and self._is_continuation_table(page_table, base_table):
                # For continuation tables, we need to be more careful about data extraction
                rows = self._extract_continuation_data(table_data, base_table.get('headers', []))
            elif i > 0 and not rows:
                # If no rows found, try to extract from table_cells
                rows = self._extract_continuation_data(table_data, base_table.get('headers', []))
            elif i > 0 and rows and len(rows) < 3:
                # If very few rows found, try to extract from table_cells
                rows = self._extract_continuation_data(table_data, base_table.get('headers', []))
            
            # **NEW: Always try to extract from the original table object if we have it**
            if i > 0 and (not rows or len(rows) < 3):
                # Try to access the original table object from the page_table
                original_table = getattr(page_table, 'original_table', None)
                if original_table and hasattr(original_table, 'table_cells'):
                    self.logger.logger.info(f"🔍 Found original table with {len(original_table.table_cells)} cells")
                    rows = self._extract_rows_from_docling_cells(original_table.table_cells, base_table.get('headers', []))
                    self.logger.logger.info(f"🔍 Extracted {len(rows)} rows from original table")
                    
                    # If we still don't have enough rows, try to extract directly from the table_cells
                    if not rows or len(rows) < 3:
                        self.logger.logger.info(f"🔍 Still not enough rows, trying direct extraction from table_cells")
                        # Try to extract all rows from the table_cells, including continuation indicators
                        all_rows_from_cells = self._extract_all_rows_from_docling_cells(original_table.table_cells, base_table.get('headers', []))
                        if all_rows_from_cells:
                            self.logger.logger.info(f"🔍 Direct extraction found {len(all_rows_from_cells)} rows")
                            rows = all_rows_from_cells
            
            all_rows.extend(rows)
            
            # Add cells with updated row indices
            cells = table_data.get('cells', [])
            for cell in cells:
                if cell.get('is_header', False) and i > 0:
                    continue  # Skip header cells from continuation pages
                
                # Update row index
                updated_cell = cell.copy()
                updated_cell['row'] = cell.get('row', 0) + current_row_offset
                all_cells.append(updated_cell)
            
            current_row_offset = len(all_rows)
        
        # Update merged table
        base_table['rows'] = all_rows
        base_table['cells'] = all_cells
        base_table['row_count'] = len(all_rows)
        
        # Add multipage metadata (always add, even for single tables)
        base_table['multipage_info'] = {
            'is_multipage': len(table_group) > 1,
            'page_count': len(table_group),
            'page_numbers': [pt.page_number for pt in table_group],
            'merge_confidence': np.mean([pt.confidence for pt in table_group])
        }
        
        # Preserve page order information
        base_table['page_number'] = table_group[0].page_number
        base_table['page_sequence'] = [pt.page_number for pt in table_group]
        
        return base_table
    
    def _is_header_row(self, row: List[str], expected_headers: List[str]) -> bool:
        """Check if a row looks like a header row."""
        
        if not row or not expected_headers:
            return False
        
        # Compare with expected headers
        similarity = sum(
            1 for r, h in zip(row, expected_headers) 
            if r.lower().strip() == h.lower().strip()
        ) / max(len(row), len(expected_headers))
        
        return similarity > 0.7

    async def _consolidate_similar_headers(self, tables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Final consolidation step: merge tables with similar headers."""
        if len(tables) <= 1:
            return tables
        
        try:
            self.logger.logger.info(f"🔗 Consolidating {len(tables)} tables with similar headers")
            
            # Group tables by header similarity
            header_groups = {}
            
            for table in tables:
                headers = table.get('headers', [])
                if not headers:
                    continue
                
                # **IMPROVED: More robust header normalization**
                # Handle cases like ['Adj.', 'Period'] vs ['Adj. Period']
                normalized_headers = []
                for header in headers:
                    if header:
                        # Split combined headers and normalize
                        parts = header.replace('.', ' ').split()
                        normalized_headers.extend([part.lower().strip() for part in parts if part.strip()])
                
                # Create a key for grouping
                if normalized_headers:
                    key = "|".join(sorted(normalized_headers))
                    if key not in header_groups:
                        header_groups[key] = []
                    header_groups[key].append(table)
            
            # Log grouping results
            self.logger.logger.info(f"🔗 Header grouping results:")
            for key, group in header_groups.items():
                self.logger.logger.info(f"   Group '{key[:50]}...': {len(group)} tables")
            
            # Merge groups with multiple tables (similar headers)
            consolidated = []
            for group in header_groups.values():
                if len(group) > 1:
                    self.logger.logger.info(f"🔗 Merging {len(group)} tables with similar headers")
                    # Merge the tables in this group
                    merged_table = await self._merge_table_group(group)
                    consolidated.append(merged_table)
                else:
                    consolidated.extend(group)
            
            self.logger.logger.info(f"🔗 Consolidation completed: {len(tables)} → {len(consolidated)} tables")
            return consolidated
            
        except Exception as e:
            self.logger.logger.error(f"Header consolidation failed: {e}")
            return tables
    
    async def _is_commission_statement_continuation(
        self, 
        table: PageTable, 
        current_headers: List[str]
    ) -> bool:
        """Intelligent detection of commission statement table continuations."""
        
        # Check if this looks like a commission statement table
        if not self._is_commission_statement_table(table, current_headers):
            return False
        
        # **IMPROVED: Enhanced continuation detection for commission statements**
        continuation_indicators = []
        
        # 1. Check for explicit continuation text in table data
        continuation_text_found = False
        table_text = ""
        for row in table.table_data.get('rows', []):
            for cell in row:
                cell_text = str(cell).lower().strip()
                table_text += cell_text + " "
                if any(indicator in cell_text for indicator in [
                    'continued', 'anat goldstein continued', 'continued next page',
                    'total commissions', 'total medical premium', 'total dental premium', 'total vision premium'
                ]):
                    continuation_text_found = True
                    self.logger.logger.info(f"🔍 Found continuation text: '{cell_text}'")
        
        continuation_indicators.append(continuation_text_found)
        
        # 2. Check if headers are similar but with variations (more lenient)
        header_similarity = self._has_commission_header_variations(table.headers, current_headers)
        continuation_indicators.append(header_similarity)
        
        # 3. Check if data patterns match (financial data, company names, etc.)
        data_patterns_match = self._has_commission_data_patterns(table.table_data)
        continuation_indicators.append(data_patterns_match)
        
        # 4. **NEW: Check for commission statement specific patterns**
        commission_patterns = self._has_commission_specific_patterns(table.table_data, table_text)
        continuation_indicators.append(commission_patterns)
        
        # 5. **NEW: Check if this is a summary/continuation section**
        is_summary_section = self._is_commission_summary_section(table.table_data, table_text)
        continuation_indicators.append(is_summary_section)
        
        # 6. Check if column count matches (more flexible)
        column_count_match = (
            len(table.headers) == len(current_headers) if table.headers and current_headers else
            len(table.headers) <= len(current_headers) + 1 if table.headers and current_headers else
            False
        )
        continuation_indicators.append(column_count_match)
        
        # Calculate continuation score
        continuation_score = sum(continuation_indicators) / len(continuation_indicators)
        
        self.logger.logger.info(f"🔍 Commission continuation indicators:")
        self.logger.logger.info(f"   Continuation text: {continuation_text_found}")
        self.logger.logger.info(f"   Header similarity: {header_similarity}")
        self.logger.logger.info(f"   Data patterns: {data_patterns_match}")
        self.logger.logger.info(f"   Commission patterns: {commission_patterns}")
        self.logger.logger.info(f"   Summary section: {is_summary_section}")
        self.logger.logger.info(f"   Column count match: {column_count_match}")
        self.logger.logger.info(f"   Final score: {continuation_score:.3f}")
        
        # **IMPROVED: More aggressive threshold for commission statements**
        return continuation_score >= 0.2  # Lowered from 0.25 to 0.2
    
    def _is_commission_statement_table(self, table: PageTable, current_headers: List[str]) -> bool:
        """Check if this table appears to be from a commission statement."""
        
        # Commission statement indicators
        commission_indicators = [
            'commission', 'premium', 'group number', 'company name', 'paid month',
            'product', 'medical', 'dental', 'vision', 'agent', 'broker'
        ]
        
        # Check headers for commission-related terms
        all_headers = (table.headers or []) + (current_headers or [])
        header_text = ' '.join(str(h).lower() for h in all_headers)
        
        commission_score = sum(1 for indicator in commission_indicators if indicator in header_text)
        
        # Check table data for commission patterns
        if table.table_data and table.table_data.get('rows'):
            data_text = ' '.join(str(cell).lower() for row in table.table_data['rows'] for cell in row)
            data_commission_score = sum(1 for indicator in commission_indicators if indicator in data_text)
            commission_score += data_commission_score * 0.5  # Weight data patterns less
        
        return commission_score >= 2  # At least 2 indicators
    
    def _has_commission_header_variations(self, headers1: List[str], headers2: List[str]) -> bool:
        """Check if headers are variations of commission statement headers."""
        
        if not headers1 or not headers2:
            return False
        
        # Normalize headers for comparison
        norm1 = [str(h).lower().strip() for h in headers1]
        norm2 = [str(h).lower().strip() for h in headers2]
        
        # Check for partial matches (common in commission statements)
        matches = 0
        for h1 in norm1:
            for h2 in norm2:
                # Exact match
                if h1 == h2:
                    matches += 1
                # Partial match (one contains the other)
                elif h1 in h2 or h2 in h1:
                    matches += 0.5
                # Word overlap
                elif any(word in h2 for word in h1.split() if len(word) > 2):
                    matches += 0.3
        
        # Calculate similarity ratio
        max_headers = max(len(norm1), len(norm2))
        similarity = matches / max_headers if max_headers > 0 else 0
        
        return similarity >= 0.3  # At least 30% similarity
    
    def _has_commission_data_patterns(self, table_data: Dict[str, Any]) -> bool:
        """Check if table data contains commission statement patterns."""
        
        if not table_data or not table_data.get('rows'):
            return False
        
        patterns_found = 0
        
        for row in table_data['rows'][:5]:  # Check first 5 rows
            row_text = ' '.join(str(cell).lower() for cell in row)
            
            # Check for commission statement patterns
            if any(pattern in row_text for pattern in ['medical', 'dental', 'vision']):
                patterns_found += 1
            if re.search(r'\$\s*\d+[,.]?\d*', row_text):  # Dollar amounts
                patterns_found += 1
            if re.search(r'\d{5,}', row_text):  # Group numbers
                patterns_found += 1
            if re.search(r'\d{2}-\d{2}', row_text):  # Date patterns like 11-24
                patterns_found += 1
        
        return patterns_found >= 2  # At least 2 patterns found
    
    def _has_commission_specific_patterns(self, table_data: Dict[str, Any], table_text: str) -> bool:
        """Check for commission statement specific patterns."""
        
        if not table_data or not table_data.get('rows'):
            return False
        
        patterns_found = 0
        
        # Check for commission-specific patterns in the text
        commission_patterns = [
            'group number', 'company name', 'paid month', 'product', 'paid premium',
            'comm %', 'comm amount', 'medical', 'dental', 'vision', 'agent no',
            'broker', 'commission statement', 'californiachoice'
        ]
        
        for pattern in commission_patterns:
            if pattern in table_text.lower():
                patterns_found += 1
        
        # Check for financial data patterns in rows
        for row in table_data['rows'][:5]:  # Check first 5 rows
            row_text = ' '.join(str(cell).lower() for cell in row)
            
            # Check for group number patterns (5-digit numbers)
            if re.search(r'\b\d{5}\b', row_text):
                patterns_found += 1
            
            # Check for company name patterns (LLC, Inc, Corp)
            if any(suffix in row_text for suffix in ['llc', 'inc', 'corp', 'company']):
                patterns_found += 1
            
            # Check for date patterns (MM-YY)
            if re.search(r'\b\d{2}-\d{2}\b', row_text):
                patterns_found += 1
        
        return patterns_found >= 3  # At least 3 commission-specific patterns
    
    def _is_commission_summary_section(self, table_data: Dict[str, Any], table_text: str) -> bool:
        """Check if this is a commission summary/continuation section."""
        
        if not table_data or not table_data.get('rows'):
            return False
        
        # Check for summary indicators
        summary_indicators = [
            'total commissions', 'total medical premium', 'total dental premium',
            'total vision premium', 'total paid commissions', 'anat goldstein continued'
        ]
        
        for indicator in summary_indicators:
            if indicator in table_text.lower():
                return True
        
        # Check if this looks like a summary table (fewer rows, totals)
        rows = table_data.get('rows', [])
        if len(rows) <= 5:  # Summary sections typically have fewer rows
            # Check if rows contain totals or summary data
            for row in rows:
                row_text = ' '.join(str(cell).lower() for cell in row)
                if any(word in row_text for word in ['total', 'premium', 'commission', 'medical', 'dental', 'vision']):
                    return True
        
        return False
    
    def _is_continuation_table(self, page_table: PageTable, base_table: Dict[str, Any]) -> bool:
        """Check if a table is a continuation of the base table."""
        
        # Check for continuation indicators in headers
        headers = page_table.headers or []
        if any('continued' in str(h).lower() for h in headers):
            return True
        
        # Check if headers look like data (strong continuation indicator)
        if self._headers_look_like_data(headers):
            return True
        
        # Check if table has similar structure but different headers
        base_headers = base_table.get('headers', [])
        if len(headers) != len(base_headers) and len(headers) <= 1:
            return True
        
        return False
    
    def _extract_continuation_data(self, table_data: Dict[str, Any], expected_headers: List[str]) -> List[List[str]]:
        """Extract data from a continuation table, ensuring proper structure."""
        
        rows = table_data.get('rows', [])
        headers = table_data.get('headers', [])
        
        self.logger.logger.info(f"🔍 Extracting continuation data: {len(rows)} rows, {len(headers)} headers")
        self.logger.logger.info(f"🔍 Expected headers: {expected_headers}")
        
        # **IMPROVED: Better data extraction from continuation tables**
        # If headers look like data, they should be included as the first row
        if self._headers_look_like_data(headers):
            # The headers are actually data, so include them
            if headers:
                self.logger.logger.info(f"🔍 Headers look like data, including as first row: {headers}")
                rows = [headers] + rows
        
        # **NEW: Try to extract data from table_cells if rows are empty or incomplete**
        if not rows or all(not row or len(row) < len(expected_headers) for row in rows):
            self.logger.logger.info(f"🔍 Rows are empty/incomplete, trying to extract from cells")
            # Try to extract from table_cells
            cells = table_data.get('cells', [])
            if cells:
                self.logger.logger.info(f"🔍 Found {len(cells)} cells, extracting rows")
                rows = self._extract_rows_from_cells(cells, expected_headers)
                self.logger.logger.info(f"🔍 Extracted {len(rows)} rows from cells")
            else:
                # **NEW: Try to extract from table_cells in the original table structure**
                # Sometimes the cells are stored differently in the table data
                self.logger.logger.info(f"🔍 No cells found in 'cells' key, checking other structures")
                if hasattr(table_data, 'table_cells') and table_data.table_cells:
                    self.logger.logger.info(f"🔍 Found table_cells attribute with {len(table_data.table_cells)} cells")
                    rows = self._extract_rows_from_docling_cells(table_data.table_cells, expected_headers)
                    self.logger.logger.info(f"🔍 Extracted {len(rows)} rows from table_cells attribute")
        
        # **NEW: Try alternative extraction methods if still no data**
        if not rows or len(rows) == 0:
            self.logger.logger.info(f"🔍 Still no rows, trying alternative extraction methods")
            # Try to extract from other table data structures
            alternative_rows = self._extract_alternative_data(table_data, expected_headers)
            if alternative_rows:
                rows = alternative_rows
                self.logger.logger.info(f"🔍 Alternative extraction found {len(rows)} rows")
        
        # **IMPROVED: Better row filtering and validation**
        filtered_rows = []
        for i, row in enumerate(rows):
            if not row:
                continue
            
            # Skip completely empty rows
            if all(not str(cell).strip() for cell in row):
                continue
            
            # **NEW: Check if this row contains continuation indicators**
            row_text = ' '.join(str(cell).lower() for cell in row if cell)
            if any(indicator in row_text for indicator in [
                'continued', 'anat goldstein continued', 'total commissions',
                'total medical premium', 'total dental premium', 'total vision premium'
            ]):
                self.logger.logger.info(f"🔍 Found continuation indicator in row {i}: {row_text[:100]}...")
                # Include this row as it's part of the continuation data
            
            # **IMPROVED: Be more lenient with row filtering for continuation tables**
            # Don't filter out rows that might contain important data
            filtered_rows.append(row)
        
        rows = filtered_rows
        self.logger.logger.info(f"🔍 After filtering: {len(rows)} rows")
        
        # Ensure all rows have the correct number of columns
        expected_cols = len(expected_headers)
        normalized_rows = []
        
        for i, row in enumerate(rows):
            if not row:
                continue
            
            # Pad or truncate row to match expected column count
            if len(row) < expected_cols:
                # Pad with empty strings
                normalized_row = row + [''] * (expected_cols - len(row))
                self.logger.logger.info(f"🔍 Padded row {i} from {len(row)} to {expected_cols} columns")
            elif len(row) > expected_cols:
                # Truncate to expected length
                normalized_row = row[:expected_cols]
                self.logger.logger.info(f"🔍 Truncated row {i} from {len(row)} to {expected_cols} columns")
            else:
                normalized_row = row
            
            normalized_rows.append(normalized_row)
        
        self.logger.logger.info(f"🔍 Final normalized rows: {len(normalized_rows)}")
        return normalized_rows
    
    def _extract_rows_from_cells(self, cells: List[Dict[str, Any]], expected_headers: List[str]) -> List[List[str]]:
        """Extract rows from table cells when regular row extraction fails."""
        
        if not cells:
            return []
        
        self.logger.logger.info(f"🔍 Extracting rows from {len(cells)} cells")
        
        # Group cells by row
        rows_dict = {}
        for cell in cells:
            row_idx = cell.get('row', 0)
            col_idx = cell.get('col', 0)
            content = cell.get('content', '')
            
            if row_idx not in rows_dict:
                rows_dict[row_idx] = {}
            
            rows_dict[row_idx][col_idx] = content
        
        self.logger.logger.info(f"🔍 Grouped cells into {len(rows_dict)} rows")
        
        # Convert to list of rows
        rows = []
        for row_idx in sorted(rows_dict.keys()):
            row_data = rows_dict[row_idx]
            # Create row with proper column order
            row = []
            max_col = max(row_data.keys()) if row_data else 0
            for col_idx in range(max_col + 1):
                row.append(row_data.get(col_idx, ''))
            
            # Only add non-empty rows
            if any(cell.strip() for cell in row):
                rows.append(row)
                self.logger.logger.info(f"🔍 Row {row_idx}: {row}")
        
        self.logger.logger.info(f"🔍 Extracted {len(rows)} non-empty rows from cells")
        return rows
    
    def _extract_rows_from_docling_cells(self, table_cells, expected_headers: List[str]) -> List[List[str]]:
        """Extract rows from Docling table_cells when regular extraction fails."""
        
        if not table_cells:
            return []
        
        self.logger.logger.info(f"🔍 Extracting rows from {len(table_cells)} Docling cells")
        
        # Group cells by row
        rows_dict = {}
        for cell in table_cells:
            # Docling cells have different structure
            row_idx = getattr(cell, 'row', 0)
            col_idx = getattr(cell, 'col', 0)
            content = getattr(cell, 'content', '') or getattr(cell, 'text', '')
            
            if row_idx not in rows_dict:
                rows_dict[row_idx] = {}
            
            rows_dict[row_idx][col_idx] = content
        
        self.logger.logger.info(f"🔍 Grouped Docling cells into {len(rows_dict)} rows")
        
        # Convert to list of rows
        rows = []
        for row_idx in sorted(rows_dict.keys()):
            row_data = rows_dict[row_idx]
            # Create row with proper column order
            row = []
            max_col = max(row_data.keys()) if row_data else 0
            for col_idx in range(max_col + 1):
                row.append(row_data.get(col_idx, ''))
            
            # Only add non-empty rows and skip continuation indicators
            if any(cell.strip() for cell in row):
                row_text = ' '.join(str(cell).lower() for cell in row if cell)
                if not any(indicator in row_text for indicator in [
                    'continued', 'anat goldstein continued', 'total commissions',
                    'total medical premium', 'total dental premium', 'total vision premium'
                ]):
                    rows.append(row)
                    self.logger.logger.info(f"🔍 Docling Row {row_idx}: {row}")
        
        self.logger.logger.info(f"🔍 Extracted {len(rows)} non-empty rows from Docling cells")
        return rows
    
    def _extract_all_rows_from_docling_cells(self, table_cells, expected_headers: List[str]) -> List[List[str]]:
        """Extract all rows from Docling table_cells without filtering continuation indicators."""
        
        if not table_cells:
            return []
        
        self.logger.logger.info(f"🔍 Extracting ALL rows from {len(table_cells)} Docling cells")
        
        # Group cells by row
        rows_dict = {}
        for cell in table_cells:
            # Docling cells have different structure
            row_idx = getattr(cell, 'row', 0)
            col_idx = getattr(cell, 'col', 0)
            content = getattr(cell, 'content', '') or getattr(cell, 'text', '')
            
            if row_idx not in rows_dict:
                rows_dict[row_idx] = {}
            
            rows_dict[row_idx][col_idx] = content
        
        self.logger.logger.info(f"🔍 Grouped Docling cells into {len(rows_dict)} rows")
        
        # Convert to list of rows
        rows = []
        for row_idx in sorted(rows_dict.keys()):
            row_data = rows_dict[row_idx]
            # Create row with proper column order
            row = []
            max_col = max(row_data.keys()) if row_data else 0
            for col_idx in range(max_col + 1):
                row.append(row_data.get(col_idx, ''))
            
            # Only add non-empty rows (but don't filter continuation indicators)
            if any(cell.strip() for cell in row):
                rows.append(row)
                self.logger.logger.info(f"🔍 Docling Row {row_idx}: {row}")
        
        self.logger.logger.info(f"🔍 Extracted {len(rows)} non-empty rows from Docling cells (all rows)")
        return rows
    
    def _extract_alternative_data(self, table_data: Dict[str, Any], expected_headers: List[str]) -> List[List[str]]:
        """Try alternative methods to extract data from continuation tables."""
        
        rows = []
        
        # Method 1: Try to extract from any available data structures
        if 'data' in table_data:
            data = table_data['data']
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, list):
                        rows.append(item)
                    elif isinstance(item, dict) and 'text' in item:
                        rows.append([item['text']])
        
        # Method 2: Try to extract from text content
        if 'text' in table_data:
            text = table_data['text']
            if text:
                # Try to parse text into rows (simple approach)
                lines = text.split('\n')
                for line in lines:
                    if line.strip():
                        # Try to split by common delimiters
                        cells = []
                        for delimiter in ['\t', '|', '  ']:  # Tab, pipe, double space
                            if delimiter in line:
                                cells = [cell.strip() for cell in line.split(delimiter)]
                                break
                        
                        if not cells:
                            cells = [line.strip()]
                        
                        if cells:
                            rows.append(cells)
        
        # Method 3: Try to extract from any nested structures
        for key, value in table_data.items():
            if key not in ['rows', 'headers', 'cells', 'data', 'text'] and isinstance(value, list):
                for item in value:
                    if isinstance(item, list):
                        rows.append(item)
                    elif isinstance(item, dict):
                        # Try to extract text from dict values
                        row = []
                        for v in item.values():
                            if isinstance(v, str) and v.strip():
                                row.append(v.strip())
                        if row:
                            rows.append(row)
        
        self.logger.logger.info(f"🔍 Alternative extraction found {len(rows)} rows")
        return rows
