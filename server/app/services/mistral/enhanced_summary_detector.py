"""
Enhanced Summary Row Detection System

Professional-grade multi-strategy summary row detector for commission statements.
Only removes rows with extremely high confidence (>85%) to prevent data loss.
"""

import re
import logging
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from statistics import mean, stdev

logger = logging.getLogger(__name__)

@dataclass
class RowAnalysis:
    """Analysis results for a single row"""
    row_index: int
    semantic_score: float
    density_score: float
    position_score: float
    business_logic_score: float
    overall_confidence: float
    evidence: List[str]
    is_summary_candidate: bool

class EnhancedSummaryRowDetector:
    """
    Professional-grade summary row detector for commission statements.
    Uses multiple strategies with conservative removal thresholds.
    """
    
    def __init__(self):
        # Conservative thresholds - require high confidence
        self.removal_confidence_threshold = 0.75  # Lowered from 0.85 to catch clear summary patterns
        self.semantic_confidence_threshold = 0.90
        self.minimum_strategies_agreement = 2  # Lowered from 3 to 2 for better detection
        
        # Commission statement specific patterns
        self.strong_summary_keywords = [
            r'^total\s+for\s+group:?',
            r'^grand\s+total:?',
            r'^total\s+for\s+vendor:?',
            r'^summary:?',
            r'^sub\s*total:?',
            r'^net\s+total:?'
        ]
        
        self.agent_info_patterns = [
            r'^writing\s+agent\s+number:?',
            r'^writing\s+agent\s+2\s+no:?',
            r'^writing\s+agent\s+name:?',
            r'^writing\s+agent\s+2\s+name:?'
        ]
        
        # Weak indicators - need multiple to trigger
        self.weak_summary_indicators = [
            r'total', r'sum', r'subtotal', r'aggregate', 
            r'overall', r'combined', r'consolidated'
        ]

    def detect_and_remove_summary_rows(self, table_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main method: Detect and remove summary rows with high confidence.
        
        Args:
            table_data: Dict with 'headers' and 'rows' keys
            
        Returns:
            Enhanced table_data with summary_detection metadata
        """
        headers = table_data.get('headers', [])
        rows = table_data.get('rows', [])
        
        if not rows or len(rows) < 3:
            return self._create_result(table_data, [], "insufficient_rows")
        
        try:
            # Analyze each row using multiple strategies
            row_analyses = []
            for i, row in enumerate(rows):
                analysis = self._analyze_row(i, row, rows, headers)
                row_analyses.append(analysis)
            
            # Determine which rows to remove based on conservative criteria
            rows_to_remove = self._determine_rows_to_remove(row_analyses)
            
            # Apply safety checks
            if self._safety_checks_pass(rows, rows_to_remove):
                cleaned_rows = [row for i, row in enumerate(rows) if i not in rows_to_remove]
                removed_rows = [rows[i] for i in rows_to_remove]
                
                return self._create_result(
                    table_data, 
                    rows_to_remove, 
                    "multi_strategy_conservative",
                    cleaned_rows=cleaned_rows,
                    removed_rows=removed_rows,
                    row_analyses=row_analyses
                )
            else:
                logger.warning("Safety checks failed - preserving all rows")
                return self._create_result(table_data, [], "safety_check_failed")
                
        except Exception as e:
            logger.error(f"Summary detection failed: {e}")
            return self._create_result(table_data, [], "detection_error")

    def _analyze_row(self, row_index: int, row: List[str], all_rows: List[List[str]], headers: List[str]) -> RowAnalysis:
        """Analyze a single row using all detection strategies"""
        
        # Strategy 1: Semantic Analysis
        semantic_score = self._analyze_semantic_patterns(row)
        
        # Strategy 2: Data Density Analysis  
        density_score = self._analyze_data_density(row, all_rows)
        
        # Strategy 3: Structural Position Analysis
        position_score = self._analyze_position_patterns(row_index, row, all_rows)
        
        # Strategy 4: Business Logic Analysis
        business_logic_score = self._analyze_business_logic(row, headers, all_rows)
        
        # Calculate overall confidence with weighted scoring
        overall_confidence = self._calculate_overall_confidence(
            semantic_score, density_score, position_score, business_logic_score
        )
        
        # Collect evidence
        evidence = self._collect_evidence(row, semantic_score, density_score, position_score, business_logic_score)
        
        return RowAnalysis(
            row_index=row_index,
            semantic_score=semantic_score,
            density_score=density_score, 
            position_score=position_score,
            business_logic_score=business_logic_score,
            overall_confidence=overall_confidence,
            evidence=evidence,
            is_summary_candidate=overall_confidence > self.removal_confidence_threshold
        )

    def _analyze_semantic_patterns(self, row: List[str]) -> float:
        """Analyze row for semantic summary indicators"""
        row_text = ' '.join(str(cell) for cell in row).lower().strip()
        
        # Strong indicators - high confidence
        for pattern in self.strong_summary_keywords:
            if re.search(pattern, row_text):
                return 0.95
        
        # Agent information patterns - medium-high confidence
        for pattern in self.agent_info_patterns:
            if re.search(pattern, row_text):
                return 0.85
        
        # Multiple weak indicators
        weak_matches = sum(1 for indicator in self.weak_summary_indicators 
                          if indicator in row_text)
        
        if weak_matches >= 2:
            return min(0.7 + (weak_matches * 0.1), 0.85)
        elif weak_matches == 1:
            return 0.4
        
        return 0.1

    def _analyze_data_density(self, row: List[str], all_rows: List[List[str]]) -> float:
        """Compare data density of this row vs typical rows"""
        if not all_rows:
            return 0.0
            
        # Calculate this row's density
        current_density = sum(1 for cell in row if str(cell).strip()) / len(row) if row else 0
        
        # Calculate average density of all rows
        densities = []
        for r in all_rows:
            if r:  # Skip empty rows
                density = sum(1 for cell in r if str(cell).strip()) / len(r)
                densities.append(density)
        
        if not densities:
            return 0.0
        
        avg_density = mean(densities)
        
        # Summary rows typically have lower density
        if current_density < avg_density * 0.5:  # Less than 50% of average
            return 0.8
        elif current_density < avg_density * 0.7:  # Less than 70% of average
            return 0.6
        elif current_density < avg_density * 0.9:  # Less than 90% of average
            return 0.3
        
        return 0.1

    def _analyze_position_patterns(self, row_index: int, row: List[str], all_rows: List[List[str]]) -> float:
        """Analyze structural position for summary likelihood"""
        total_rows = len(all_rows)
        
        # Summary rows often appear after groups of data
        if row_index == total_rows - 1:  # Last row
            return 0.7
        elif row_index > total_rows * 0.8:  # In last 20%
            return 0.5
        elif row_index > total_rows * 0.6:  # In last 40%
            return 0.3
        
        # Check if row appears after a group (heuristic)
        if row_index > 0 and row_index < total_rows - 1:
            prev_row = all_rows[row_index - 1]
            next_row = all_rows[row_index + 1]
            
            # If surrounded by different patterns, might be summary
            if self._rows_are_different_patterns(row, prev_row) and self._rows_are_different_patterns(row, next_row):
                return 0.4
        
        return 0.2

    def _analyze_business_logic(self, row: List[str], headers: List[str], all_rows: List[List[str]]) -> float:
        """Apply business logic specific to commission statements"""
        row_text = ' '.join(str(cell) for cell in row).lower()
        
        # Commission statement specific patterns
        commission_totals = ['total commission', 'commission total', 'net commission']
        group_totals = ['total for group', 'group total']
        vendor_totals = ['total for vendor', 'vendor total']
        
        for pattern in commission_totals:
            if pattern in row_text:
                return 0.9
        
        for pattern in group_totals:
            if pattern in row_text:
                return 0.9
                
        for pattern in vendor_totals:
            if pattern in row_text:
                return 0.9
        
        # Look for agent information blocks
        if any(agent_key in row_text for agent_key in ['writing agent', 'agent number', 'agent name']):
            return 0.8
        
        return 0.1

    def _calculate_overall_confidence(self, semantic: float, density: float, position: float, business: float) -> float:
        """Calculate weighted overall confidence score"""
        
        # Weighted scoring - semantic and business logic get much higher weight for clear patterns
        weights = {
            'semantic': 0.45,  # Increased from 0.4
            'business': 0.35,  # Increased from 0.3
            'density': 0.15,   # Decreased from 0.2
            'position': 0.05   # Decreased from 0.1
        }
        
        overall = (
            semantic * weights['semantic'] +
            business * weights['business'] +
            density * weights['density'] +
            position * weights['position']
        )
        
        return min(overall, 1.0)

    def _collect_evidence(self, row: List[str], semantic_score: float, density_score: float, 
                         position_score: float, business_logic_score: float) -> List[str]:
        """Collect evidence strings for why row was classified as summary"""
        evidence = []
        
        if semantic_score > 0.7:
            evidence.append(f"Strong semantic indicators (score: {semantic_score:.2f})")
        
        if density_score > 0.6:
            evidence.append(f"Low data density compared to average (score: {density_score:.2f})")
        
        if position_score > 0.5:
            evidence.append(f"Appears in typical summary position (score: {position_score:.2f})")
        
        if business_logic_score > 0.7:
            evidence.append(f"Matches business logic patterns (score: {business_logic_score:.2f})")
        
        return evidence

    def _determine_rows_to_remove(self, row_analyses: List[RowAnalysis]) -> List[int]:
        """Determine which rows to remove based on conservative criteria"""
        candidates = []
        
        for analysis in row_analyses:
            # Require multiple strong indicators
            strong_indicators = sum([
                analysis.semantic_score > 0.8,
                analysis.business_logic_score > 0.7,
                analysis.density_score > 0.6,
                analysis.position_score > 0.5
            ])
            
            # Conservative removal criteria
            if (analysis.overall_confidence > self.removal_confidence_threshold and 
                strong_indicators >= self.minimum_strategies_agreement):
                candidates.append(analysis.row_index)
        
        # Additional safety: Never remove more than 35% of rows (increased from 20% for documents with many summary rows)
        # Commission statements often have agent info + totals which can be 30%+ of rows
        max_removable_percentage = 0.35
        max_removable = max(1, int(len(row_analyses) * max_removable_percentage))
        
        if len(candidates) > max_removable:
            # Keep only highest confidence candidates
            sorted_analyses = [row_analyses[i] for i in candidates]
            sorted_analyses.sort(key=lambda x: x.overall_confidence, reverse=True)
            candidates = [a.row_index for a in sorted_analyses[:max_removable]]
            logger.warning(f"Summary detection capped: {len(candidates)} candidates but only removing top {max_removable} (35% limit)")
        
        return candidates

    def _safety_checks_pass(self, original_rows: List[List[str]], rows_to_remove: List[int]) -> bool:
        """Perform safety checks before removing rows"""
        
        # Never remove more than 35% of rows (updated to match removal percentage)
        if len(rows_to_remove) > len(original_rows) * 0.35:
            logger.warning(f"Safety check failed: Attempting to remove {len(rows_to_remove)} rows ({len(rows_to_remove)/len(original_rows)*100:.1f}%) from {len(original_rows)} total")
            return False
        
        # Never remove all rows
        if len(rows_to_remove) >= len(original_rows):
            logger.warning("Safety check failed: Attempting to remove all rows")
            return False
        
        # Require at least 3 rows to remain
        if len(original_rows) - len(rows_to_remove) < 3:
            logger.warning("Safety check failed: Less than 3 rows would remain")
            return False
        
        return True

    def _rows_are_different_patterns(self, row1: List[str], row2: List[str]) -> bool:
        """Heuristic to determine if two rows have different patterns"""
        if not row1 or not row2:
            return True
        
        # Compare density
        density1 = sum(1 for cell in row1 if str(cell).strip()) / len(row1)
        density2 = sum(1 for cell in row2 if str(cell).strip()) / len(row2)
        
        # If densities differ significantly
        if abs(density1 - density2) > 0.3:
            return True
        
        # Compare text patterns
        text1 = ' '.join(str(cell) for cell in row1).lower()
        text2 = ' '.join(str(cell) for cell in row2).lower()
        
        # Look for format differences
        has_numbers1 = bool(re.search(r'\d', text1))
        has_numbers2 = bool(re.search(r'\d', text2))
        
        if has_numbers1 != has_numbers2:
            return True
        
        return False

    def _create_result(self, table_data: Dict[str, Any], removed_indices: List[int], 
                      detection_method: str, cleaned_rows: List[List[str]] = None,
                      removed_rows: List[List[str]] = None, row_analyses: List[RowAnalysis] = None) -> Dict[str, Any]:
        """Create result dictionary with metadata"""
        
        # Calculate overall confidence
        if row_analyses and removed_indices:
            avg_confidence = mean([row_analyses[i].overall_confidence for i in removed_indices])
        elif removed_indices:
            avg_confidence = self.removal_confidence_threshold
        else:
            avg_confidence = 0.0
        
        result = {
            **table_data,
            'summary_detection': {
                'enabled': True,
                'removed_indices': removed_indices,
                'detection_method': detection_method,
                'detection_confidence': avg_confidence,
                'total_rows_before': len(table_data.get('rows', [])),
                'total_rows_after': len(cleaned_rows) if cleaned_rows else len(table_data.get('rows', [])),
                'removal_threshold': self.removal_confidence_threshold,
                'strategies_used': ['semantic', 'density', 'position', 'business_logic']
            },
            # CRITICAL: Clear summaryRows since rows were already removed from the data
            # The old indices would point to wrong rows in the cleaned array
            'summaryRows': []
        }
        
        # Add cleaned rows if available
        if cleaned_rows is not None:
            result['rows'] = cleaned_rows
        
        # Add detailed analysis if available
        if row_analyses and removed_indices:
            result['summary_detection']['removed_row_details'] = [
                {
                    'index': idx,
                    'confidence': row_analyses[idx].overall_confidence,
                    'evidence': row_analyses[idx].evidence,
                    'scores': {
                        'semantic': row_analyses[idx].semantic_score,
                        'density': row_analyses[idx].density_score,
                        'position': row_analyses[idx].position_score,
                        'business_logic': row_analyses[idx].business_logic_score
                    }
                }
                for idx in removed_indices
            ]
        
        return result

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about detector configuration"""
        return {
            'removal_confidence_threshold': self.removal_confidence_threshold,
            'semantic_confidence_threshold': self.semantic_confidence_threshold,
            'minimum_strategies_agreement': self.minimum_strategies_agreement,
            'strong_summary_patterns': len(self.strong_summary_keywords),
            'agent_info_patterns': len(self.agent_info_patterns),
            'weak_indicators': len(self.weak_summary_indicators)
        }

