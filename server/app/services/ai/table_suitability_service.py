"""
Table Suitability Service for analyzing which tables are suitable for field mapping.
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class TableSuitabilityService:
    """
    Service to analyze tables and determine which ones are most suitable for field mapping.
    """
    
    def __init__(self):
        """Initialize the table suitability service."""
        self.available = True
        logger.info("Table Suitability Service initialized")
    
    def is_available(self) -> bool:
        """Check if the service is available."""
        return self.available
    
    async def analyze_tables_for_mapping(
        self, 
        tables: List[Dict[str, Any]], 
        document_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze multiple tables to determine which is most suitable for field mapping.
        
        Args:
            tables: List of table dictionaries to analyze
            document_context: Optional context about the document (carrier, date, etc.)
            
        Returns:
            Dictionary with analysis results including recommended table index
        """
        try:
            if not tables:
                return {
                    'success': False,
                    'error': 'No tables provided for analysis'
                }
            
            # Simple heuristic-based analysis
            # Prefer tables with more rows and reasonable column count
            best_table_index = 0
            best_score = 0
            
            for idx, table in enumerate(tables):
                score = self._calculate_table_score(table)
                
                if score > best_score:
                    best_score = score
                    best_table_index = idx
            
            logger.info(f"Table suitability analysis: Selected table {best_table_index} (score: {best_score})")
            
            return {
                'success': True,
                'recommended_table_index': best_table_index,
                'total_tables_analyzed': len(tables),
                'confidence': min(best_score / 100, 1.0),  # Normalize to 0-1
                'analysis': {
                    'table_scores': [
                        {
                            'index': idx,
                            'score': self._calculate_table_score(table),
                            'rows': len(table.get('rows', [])),
                            'columns': len(table.get('header', []))
                        }
                        for idx, table in enumerate(tables)
                    ]
                }
            }
            
        except Exception as e:
            logger.error(f"Error analyzing tables for mapping: {e}")
            return {
                'success': False,
                'error': str(e),
                'recommended_table_index': 0  # Default to first table on error
            }
    
    def _calculate_table_score(self, table: Dict[str, Any]) -> float:
        """
        Calculate a suitability score for a table based on various factors.
        
        Args:
            table: Table dictionary to score
            
        Returns:
            Float score (higher is better)
        """
        score = 0.0
        
        # Get table dimensions
        rows = table.get('rows', [])
        headers = table.get('header', [])
        num_rows = len(rows)
        num_cols = len(headers)
        
        # Prefer tables with data (not empty)
        if num_rows == 0:
            return 0.0
        
        # Score based on row count (more rows = better, but not too many)
        if 5 <= num_rows <= 100:
            score += 30
        elif num_rows > 100:
            score += 20  # Too many rows might be multiple tables merged
        elif num_rows > 0:
            score += 10  # Few rows is still okay
        
        # Score based on column count (reasonable number of columns)
        if 4 <= num_cols <= 20:
            score += 30
        elif 2 <= num_cols < 4:
            score += 15
        elif num_cols > 20:
            score += 10  # Too many columns might be formatting issues
        
        # Prefer tables with headers
        if headers and any(h.strip() for h in headers):
            score += 20
        
        # Check for common commission statement keywords in headers
        common_keywords = [
            'commission', 'policy', 'premium', 'name', 'date', 
            'amount', 'number', 'carrier', 'insured', 'agent'
        ]
        
        header_text = ' '.join(headers).lower()
        keyword_matches = sum(1 for keyword in common_keywords if keyword in header_text)
        score += keyword_matches * 5
        
        # Prefer tables with good data density (not too many empty cells)
        if rows:
            total_cells = num_rows * num_cols
            empty_cells = sum(
                1 for row in rows 
                for cell in row 
                if not str(cell).strip()
            )
            if total_cells > 0:
                data_density = 1 - (empty_cells / total_cells)
                score += data_density * 20
        
        return score

