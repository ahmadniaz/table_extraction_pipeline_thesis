"""Real Microsoft Table Transformer implementation for production use."""

import torch
from transformers import AutoImageProcessor, TableTransformerForObjectDetection
from transformers import AutoTokenizer, AutoModel
import torchvision.transforms as transforms
from PIL import Image
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import asyncio
import time
import statistics
import re

from ..utils.config import Config
from ..utils.logging_utils import get_logger


class ProductionTableFormer:
    """Production-grade TableFormer implementation using Microsoft models."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = get_logger(__name__, config)
        self.device = torch.device(config.models.device)
        
        # Load actual Microsoft Table Transformer models
        self._load_detection_model()
        self._load_structure_model()
        
    def _load_detection_model(self):
        """Load Microsoft Table Transformer Detection model."""
        try:
            # Try with configured cache directory first
            self.detection_processor = AutoImageProcessor.from_pretrained(
                "microsoft/table-transformer-detection",
                cache_dir=self.config.models.cache_dir
            )
            self.detection_model = TableTransformerForObjectDetection.from_pretrained(
                "microsoft/table-transformer-detection",
                cache_dir=self.config.models.cache_dir
            ).to(self.device)
            self.detection_model.eval()
            self.logger.logger.info("Table detection model loaded successfully")
        except (OSError, PermissionError) as e:
            # Fallback: try without cache directory (uses default location)
            self.logger.logger.warning(f"Failed to load detection model with cache dir {self.config.models.cache_dir}: {e}")
            self.logger.logger.info("Attempting to load detection model without cache directory...")
            try:
                self.detection_processor = AutoImageProcessor.from_pretrained(
                    "microsoft/table-transformer-detection"
                )
                self.detection_model = TableTransformerForObjectDetection.from_pretrained(
                    "microsoft/table-transformer-detection"
                ).to(self.device)
                self.detection_model.eval()
                self.logger.logger.info("Table detection model loaded successfully (fallback)")
            except Exception as fallback_e:
                raise RuntimeError(f"Failed to load detection model (both cache and fallback): {fallback_e}")
        except Exception as e:
            raise RuntimeError(f"Failed to load detection model: {e}")
            
    def _load_structure_model(self):
        """Load Microsoft Table Transformer Structure Recognition model."""
        try:
            # Try with configured cache directory first
            self.structure_processor = AutoImageProcessor.from_pretrained(
                "microsoft/table-transformer-structure-recognition-v1.1-all",
                cache_dir=self.config.models.cache_dir
            )
            self.structure_model = TableTransformerForObjectDetection.from_pretrained(
                "microsoft/table-transformer-structure-recognition-v1.1-all",
                cache_dir=self.config.models.cache_dir
            ).to(self.device)
            self.structure_model.eval()
            self.logger.logger.info("Table structure model loaded successfully")
        except (OSError, PermissionError) as e:
            # Fallback: try without cache directory (uses default location)
            self.logger.logger.warning(f"Failed to load structure model with cache dir {self.config.models.cache_dir}: {e}")
            self.logger.logger.info("Attempting to load structure model without cache directory...")
            try:
                self.structure_processor = AutoImageProcessor.from_pretrained(
                    "microsoft/table-transformer-structure-recognition-v1.1-all"
                )
                self.structure_model = TableTransformerForObjectDetection.from_pretrained(
                    "microsoft/table-transformer-structure-recognition-v1.1-all"
                ).to(self.device)
                self.structure_model.eval()
                self.logger.logger.info("Table structure model loaded successfully (fallback)")
            except Exception as fallback_e:
                raise RuntimeError(f"Failed to load structure model (both cache and fallback): {fallback_e}")
        except Exception as e:
            raise RuntimeError(f"Failed to load structure model: {e}")
    
    async def detect_tables_advanced(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """Advanced table detection using Microsoft Table Transformer."""
        try:
            # Convert numpy array to PIL Image
            if isinstance(image, np.ndarray):
                image_pil = Image.fromarray(image)
            else:
                image_pil = image
            
            # Preprocess image
            inputs = self.detection_processor(image_pil, return_tensors="pt").to(self.device)
            
            # Run inference
            with torch.no_grad():
                outputs = self.detection_model(**inputs)
            
            # Process outputs
            target_sizes = torch.tensor([image_pil.size[::-1]]).to(self.device)
            results = self.detection_processor.post_process_object_detection(
                outputs, threshold=self.config.processing.table_detection_threshold, 
                target_sizes=target_sizes
            )[0]
            
            # Convert results to standard format
            detected_tables = []
            for i, (score, label, box) in enumerate(zip(
                results["scores"], results["labels"], results["boxes"]
            )):
                if score >= self.config.processing.table_detection_threshold:
                    detected_tables.append({
                        'bbox': box.cpu().numpy().tolist(),  # [x1, y1, x2, y2]
                        'confidence': float(score),
                        'label': int(label),
                        'table_id': i
                    })
            
            return detected_tables
            
        except Exception as e:
            self.logger.logger.error(f"Advanced table detection failed: {e}")
            raise
    
    async def recognize_structure_advanced(
        self, 
        image: np.ndarray, 
        table_bbox: List[float]
    ) -> Dict[str, Any]:
        """Advanced structure recognition with merged cell detection."""
        try:
            # Extract table region
            table_image = self._extract_table_region_precise(image, table_bbox)
            
            # Convert to PIL Image
            if isinstance(table_image, np.ndarray):
                table_pil = Image.fromarray(table_image)
            else:
                table_pil = table_image
            
            # Preprocess for structure recognition
            inputs = self.structure_processor(table_pil, return_tensors="pt").to(self.device)
            
            # Run structure recognition
            with torch.no_grad():
                outputs = self.structure_model(**inputs)
            
            # Process structure outputs
            target_sizes = torch.tensor([table_pil.size[::-1]]).to(self.device)
            results = self.structure_processor.post_process_object_detection(
                outputs, threshold=self.config.processing.cell_detection_threshold,
                target_sizes=target_sizes
            )[0]
            
            # Advanced structure analysis
            structure_info = await self._analyze_advanced_structure(
                results, table_bbox, table_pil.size
            )
            
            return structure_info
            
        except Exception as e:
            self.logger.logger.error(f"Advanced structure recognition failed: {e}")
            raise
    
    async def _analyze_advanced_structure(
        self, 
        detection_results: Dict, 
        table_bbox: List[float], 
        image_size: Tuple[int, int]
    ) -> Dict[str, Any]:
        """Analyze table structure with advanced cell relationship detection."""
        
        # Extract detected cells, rows, columns
        cells = []
        rows = []
        columns = []
        
        for score, label, box in zip(
            detection_results["scores"], 
            detection_results["labels"], 
            detection_results["boxes"]
        ):
            element_type = self._get_element_type(int(label))
            
            if element_type == "table row":
                rows.append({
                    'bbox': box.cpu().numpy().tolist(),
                    'confidence': float(score)
                })
            elif element_type == "table column":
                columns.append({
                    'bbox': box.cpu().numpy().tolist(),
                    'confidence': float(score)
                })
            elif element_type == "table":
                # Table-level detection
                pass
            else:
                # Individual cells or other elements
                cells.append({
                    'bbox': box.cpu().numpy().tolist(),
                    'confidence': float(score),
                    'type': element_type
                })
        
        # Advanced cell relationship analysis
        grid_cells = await self._build_cell_grid(cells, rows, columns)
        
        # Detect merged cells
        merged_cells = await self._detect_merged_cells(grid_cells, rows, columns)
        
        # Detect hierarchical headers
        hierarchical_headers = await self._detect_hierarchical_headers(grid_cells, rows)
        
        # Generate final table structure from grid cells
        table_structure = await self._generate_table_structure(grid_cells, rows, columns)
        
        return {
            'cells': grid_cells,
            'merged_cells': merged_cells,
            'hierarchical_headers': hierarchical_headers,
            'table_structure': table_structure,
            'rows': len(rows),
            'columns': len(columns),
            'confidence': float(np.mean([cell['confidence'] for cell in cells])) if cells else 0.0,
            'bbox': table_bbox
        }
    
    def _get_element_type(self, label_id: int) -> str:
        """Map label ID to element type."""
        label_map = {
            0: "table",
            1: "table column",
            2: "table row", 
            3: "table column header",
            4: "table projected row header",
            5: "table spanning cell"
        }
        return label_map.get(label_id, "unknown")
    
    async def _build_cell_grid(
        self, 
        cells: List[Dict], 
        rows: List[Dict], 
        columns: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Build structured cell grid with improved alignment and gap detection."""
        
        # Sort rows and columns by position
        rows_sorted = sorted(rows, key=lambda r: r['bbox'][1])  # Sort by y-coordinate
        columns_sorted = sorted(columns, key=lambda c: c['bbox'][0])  # Sort by x-coordinate
        
        # Create a more robust grid assignment system
        grid_cells = []
        cell_grid_matrix = {}  # Track occupied positions
        
        for cell in cells:
            cell_bbox = cell['bbox']
            
            # Use overlap-based assignment instead of center-point
            row_idx = self._find_row_assignment_overlap(cell_bbox, rows_sorted)
            col_idx = self._find_column_assignment_overlap(cell_bbox, columns_sorted)
            
            # Handle cell spans based on bbox overlap
            row_span = self._calculate_row_span_overlap(cell_bbox, rows_sorted, row_idx)
            col_span = self._calculate_column_span_overlap(cell_bbox, columns_sorted, col_idx)
            
            grid_cell = {
                'row': row_idx,
                'column': col_idx,
                'bbox': cell_bbox,
                'confidence': cell['confidence'],
                'text': '',  # Will be filled by OCR
                'row_span': row_span,
                'column_span': col_span,
                'is_header': row_idx == 0  # Assume first row is header
            }
            
            # Mark occupied positions in the grid
            for r in range(row_idx, row_idx + row_span):
                for c in range(col_idx, col_idx + col_span):
                    cell_grid_matrix[(r, c)] = grid_cell
            
            grid_cells.append(grid_cell)
        
        # Post-process to handle missing cells and column alignment
        grid_cells = await self._fix_column_alignment(grid_cells, rows_sorted, columns_sorted)
        
        return grid_cells
    
    def _find_row_assignment_overlap(self, cell_bbox: List[float], rows_sorted: List[Dict]) -> int:
        """Find row assignment based on bbox overlap instead of center point."""
        if not rows_sorted:
            return 0
            
        best_overlap = 0
        best_row = 0
        
        for i, row in enumerate(rows_sorted):
            row_bbox = row['bbox']
            
            # Calculate vertical overlap
            overlap_top = max(cell_bbox[1], row_bbox[1])
            overlap_bottom = min(cell_bbox[3], row_bbox[3])
            overlap_height = max(0, overlap_bottom - overlap_top)
            
            cell_height = cell_bbox[3] - cell_bbox[1]
            overlap_ratio = overlap_height / max(cell_height, 1)
            
            if overlap_ratio > best_overlap:
                best_overlap = overlap_ratio
                best_row = i
        
        return best_row
    
    def _find_column_assignment_overlap(self, cell_bbox: List[float], columns_sorted: List[Dict]) -> int:
        """Find column assignment based on bbox overlap instead of center point."""
        if not columns_sorted:
            return 0
            
        best_overlap = 0
        best_col = 0
        
        for i, col in enumerate(columns_sorted):
            col_bbox = col['bbox']
            
            # Calculate horizontal overlap
            overlap_left = max(cell_bbox[0], col_bbox[0])
            overlap_right = min(cell_bbox[2], col_bbox[2])
            overlap_width = max(0, overlap_right - overlap_left)
            
            cell_width = cell_bbox[2] - cell_bbox[0]
            overlap_ratio = overlap_width / max(cell_width, 1)
            
            if overlap_ratio > best_overlap:
                best_overlap = overlap_ratio
                best_col = i
        
        return best_col
    
    def _calculate_row_span_overlap(self, cell_bbox: List[float], rows_sorted: List[Dict], start_row: int) -> int:
        """Calculate row span based on bbox overlap with multiple rows."""
        if not rows_sorted:
            return 1
            
        span = 1
        cell_bottom = cell_bbox[3]
        
        # Check if cell extends into subsequent rows
        for i in range(start_row + 1, len(rows_sorted)):
            row_bbox = rows_sorted[i]['bbox']
            
            # Check if cell overlaps with this row significantly
            overlap_top = max(cell_bbox[1], row_bbox[1])
            overlap_bottom = min(cell_bbox[3], row_bbox[3])
            overlap_height = max(0, overlap_bottom - overlap_top)
            
            row_height = row_bbox[3] - row_bbox[1]
            overlap_ratio = overlap_height / max(row_height, 1)
            
            if overlap_ratio > 0.3:  # Significant overlap threshold
                span += 1
            else:
                break
                
        return span
    
    def _calculate_column_span_overlap(self, cell_bbox: List[float], columns_sorted: List[Dict], start_col: int) -> int:
        """Calculate column span based on bbox overlap with multiple columns."""
        if not columns_sorted:
            return 1
            
        span = 1
        cell_right = cell_bbox[2]
        
        # Check if cell extends into subsequent columns
        for i in range(start_col + 1, len(columns_sorted)):
            col_bbox = columns_sorted[i]['bbox']
            
            # Check if cell overlaps with this column significantly
            overlap_left = max(cell_bbox[0], col_bbox[0])
            overlap_right = min(cell_bbox[2], col_bbox[2])
            overlap_width = max(0, overlap_right - overlap_left)
            
            col_width = col_bbox[2] - col_bbox[0]
            overlap_ratio = overlap_width / max(col_width, 1)
            
            if overlap_ratio > 0.3:  # Significant overlap threshold
                span += 1
            else:
                break
                
        return span
    
    async def _fix_column_alignment(self, grid_cells: List[Dict], rows_sorted: List[Dict], columns_sorted: List[Dict]) -> List[Dict]:
        """Post-process grid cells to fix column alignment issues and detect missing cells."""
        if not grid_cells:
            return grid_cells
        
        # Create a matrix representation
        max_row = max(cell['row'] + cell['row_span'] - 1 for cell in grid_cells)
        max_col = max(cell['column'] + cell['column_span'] - 1 for cell in grid_cells)
        
        # Build cell matrix
        cell_matrix = {}
        for cell in grid_cells:
            for r in range(cell['row'], cell['row'] + cell['row_span']):
                for c in range(cell['column'], cell['column'] + cell['column_span']):
                    cell_matrix[(r, c)] = cell
        
        # Detect and fix column shifts caused by missing cells
        fixed_cells = []
        for cell in grid_cells:
            fixed_cell = cell.copy()
            
            # Check for patterns that suggest missing cells in previous columns
            if self._detect_missing_cell_pattern(cell, cell_matrix, max_col):
                # Attempt to adjust column assignment
                adjusted_col = self._adjust_for_missing_cells(cell, cell_matrix, columns_sorted)
                if adjusted_col != cell['column']:
                    self.logger.logger.info(f"Adjusted cell column from {cell['column']} to {adjusted_col}")
                    fixed_cell['column'] = adjusted_col
            
            fixed_cells.append(fixed_cell)
        
        return fixed_cells
    
    def _detect_missing_cell_pattern(self, cell: Dict, cell_matrix: Dict, max_col: int) -> bool:
        """Detect if there are likely missing cells causing column misalignment."""
        row = cell['row']
        col = cell['column']
        
        # Look for gaps in the row that suggest missing cells
        if row == 0:  # Header row
            return False
            
        # Check if there are empty positions before this cell in the same row
        empty_before = 0
        for c in range(col):
            if (row, c) not in cell_matrix:
                empty_before += 1
        
        # If there are many empty positions, it might indicate missing cells
        return empty_before > 0 and col < max_col - 1
    
    def _adjust_for_missing_cells(self, cell: Dict, cell_matrix: Dict, columns_sorted: List[Dict]) -> int:
        """Attempt to adjust cell column based on context and typical table patterns."""
        # This is a heuristic approach - could be improved with ML
        row = cell['row']
        original_col = cell['column']
        
        # Look at the pattern in the header row to understand expected structure
        header_cells = [(c, cell_matrix[(0, c)]) for c in range(len(columns_sorted)) if (0, c) in cell_matrix]
        
        # For now, return original column (can be enhanced with more sophisticated logic)
        return original_col
    
    def _find_row_assignment(self, y_center: float, rows_sorted: List[Dict]) -> int:
        """Find the row assignment for a cell center."""
        for i, row in enumerate(rows_sorted):
            row_bbox = row['bbox']
            if row_bbox[1] <= y_center <= row_bbox[3]:
                return i
        # If not found in any row, assign to closest row
        if rows_sorted:
            distances = [abs(y_center - (row['bbox'][1] + row['bbox'][3]) / 2) for row in rows_sorted]
            return distances.index(min(distances))
        return 0
    
    def _find_column_assignment(self, x_center: float, columns_sorted: List[Dict]) -> int:
        """Find the column assignment for a cell center."""
        for i, col in enumerate(columns_sorted):
            col_bbox = col['bbox']
            if col_bbox[0] <= x_center <= col_bbox[2]:
                return i
        # If not found in any column, assign to closest column
        if columns_sorted:
            distances = [abs(x_center - (col['bbox'][0] + col['bbox'][2]) / 2) for col in columns_sorted]
            return distances.index(min(distances))
        return 0
    
    async def _detect_merged_cells(
        self, 
        cells: List[Dict], 
        rows: List[Dict], 
        columns: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Detect merged cells based on overlapping bounding boxes."""
        
        merged_cells = []
        
        # Group cells by position
        cell_grid = {}
        for cell in cells:
            key = (cell['row'], cell['column'])
            if key not in cell_grid:
                cell_grid[key] = []
            cell_grid[key].append(cell)
        
        # Detect spans
        for (row, col), cell_list in cell_grid.items():
            if len(cell_list) == 1:
                cell = cell_list[0]
                
                # Check for column span
                col_span = self._calculate_column_span(cell, columns)
                
                # Check for row span  
                row_span = self._calculate_row_span(cell, rows)
                
                if col_span > 1 or row_span > 1:
                    merged_cells.append({
                        'row': row,
                        'column': col,
                        'row_span': row_span,
                        'column_span': col_span,
                        'bbox': cell['bbox'],
                        'confidence': cell['confidence']
                    })
                    
                    # Update original cell
                    cell['row_span'] = row_span
                    cell['column_span'] = col_span
        
        return merged_cells
    
    def _calculate_column_span(self, cell: Dict, columns: List[Dict]) -> int:
        """Calculate column span for a cell."""
        cell_bbox = cell['bbox']
        cell_width = cell_bbox[2] - cell_bbox[0]
        
        # Find overlapping columns
        overlapping_cols = 0
        for col in columns:
            col_bbox = col['bbox']
            # Check if column overlaps with cell
            if not (cell_bbox[2] <= col_bbox[0] or cell_bbox[0] >= col_bbox[2]):
                overlapping_cols += 1
        
        return max(1, overlapping_cols)
    
    def _calculate_row_span(self, cell: Dict, rows: List[Dict]) -> int:
        """Calculate row span for a cell."""
        cell_bbox = cell['bbox']
        cell_height = cell_bbox[3] - cell_bbox[1]
        
        # Find overlapping rows
        overlapping_rows = 0
        for row in rows:
            row_bbox = row['bbox']
            # Check if row overlaps with cell
            if not (cell_bbox[3] <= row_bbox[1] or cell_bbox[1] >= row_bbox[3]):
                overlapping_rows += 1
        
        return max(1, overlapping_rows)
    
    async def _detect_hierarchical_headers(
        self, 
        cells: List[Dict], 
        rows: List[Dict]
    ) -> Dict[str, Any]:
        """Detect multi-level headers in tables."""
        
        if len(rows) < 2:
            return {'levels': 1, 'structure': []}
        
        # Analyze first few rows for header patterns
        header_rows = []
        for i in range(min(3, len(rows))):  # Check first 3 rows
            row_cells = [cell for cell in cells if cell['row'] == i]
            
            # Analyze cell characteristics
            avg_confidence = np.mean([cell['confidence'] for cell in row_cells]) if row_cells else 0
            has_merged_cells = any(cell['column_span'] > 1 for cell in row_cells)
            
            # Heuristics for header detection
            is_header = (
                i == 0 or  # First row is typically header
                has_merged_cells or  # Merged cells often in headers
                avg_confidence > 0.8  # High confidence cells
            )
            
            if is_header:
                header_rows.append({
                    'row_index': i,
                    'cells': row_cells,
                    'merged_cells': [cell for cell in row_cells if cell['column_span'] > 1],
                    'confidence': avg_confidence
                })
            else:
                break  # Stop when we hit non-header rows
        
        return {
            'levels': len(header_rows),
            'structure': header_rows
        }
    
    async def _generate_table_structure(self, grid_cells: List[Dict], rows: List[Dict], columns: List[Dict]) -> Dict[str, Any]:
        """Generate structured table representation from grid cells with gap detection."""
        if not grid_cells:
            return {'headers': [], 'rows': []}
        
        # Determine table dimensions
        max_row = max(cell['row'] + cell['row_span'] - 1 for cell in grid_cells)
        max_col = max(cell['column'] + cell['column_span'] - 1 for cell in grid_cells)
        
        # Create cell matrix for easier access
        cell_matrix = {}
        for cell in grid_cells:
            for r in range(cell['row'], cell['row'] + cell['row_span']):
                for c in range(cell['column'], cell['column'] + cell['column_span']):
                    cell_matrix[(r, c)] = cell
        
        # Extract headers (first row with content)
        headers = []
        header_row = 0
        
        # Find the best header row
        for r in range(min(3, max_row + 1)):  # Check first 3 rows
            row_cells = []
            for c in range(max_col + 1):
                if (r, c) in cell_matrix:
                    cell = cell_matrix[(r, c)]
                    # Only add if this is the primary position for the cell
                    if cell['row'] == r and cell['column'] == c:
                        row_cells.append(cell.get('text', ''))
                    else:
                        row_cells.append('')  # Merged cell continuation
                else:
                    row_cells.append('')  # Missing cell
                    
            # Score this row as potential header
            if self._is_likely_header_row(row_cells):
                headers = row_cells
                header_row = r
                break
        
        # Extract data rows
        data_rows = []
        for r in range(header_row + 1, max_row + 1):
            row_data = []
            for c in range(max_col + 1):
                if (r, c) in cell_matrix:
                    cell = cell_matrix[(r, c)]
                    # Only add if this is the primary position for the cell
                    if cell['row'] == r and cell['column'] == c:
                        text = cell.get('text', '')
                        row_data.append(text)
                    else:
                        row_data.append('')  # Merged cell continuation
                else:
                    row_data.append('')  # Missing cell - key improvement!
            
            # Only add non-empty rows
            if any(str(cell).strip() for cell in row_data):
                data_rows.append(row_data)
        
        # Clean up headers and ensure consistent width
        headers = [str(h).strip() for h in headers]
        target_width = len(headers)
        
        # Ensure all rows have same width as headers
        normalized_rows = []
        for row in data_rows:
            normalized_row = row[:target_width]  # Truncate if too long
            while len(normalized_row) < target_width:  # Pad if too short
                normalized_row.append('')
            normalized_rows.append(normalized_row)
        
        return {
            'headers': headers,
            'rows': normalized_rows,
            'header_row_index': header_row,
            'dimensions': {'rows': max_row + 1, 'columns': max_col + 1}
        }
    
    def _is_likely_header_row(self, row_cells: List[str]) -> bool:
        """Determine if a row is likely to be a header row."""
        if not row_cells or not any(str(cell).strip() for cell in row_cells):
            return False
        
        # Check for typical header characteristics
        non_empty_cells = [str(cell).strip() for cell in row_cells if str(cell).strip()]
        
        if len(non_empty_cells) < 3:  # Need at least 3 headers
            return False
        
        # Header heuristics
        header_indicators = 0
        total_indicators = 0
        
        for cell in non_empty_cells:
            cell_str = str(cell).lower()
            
            # Positive indicators for headers
            if any(keyword in cell_str for keyword in [
                'name', 'group', 'no', 'number', 'id', 'period', 'date', 
                'amount', 'total', 'method', 'type', 'status', 'paid',
                'invoice', 'commission', 'premium', 'census', 'calculation'
            ]):
                header_indicators += 1
            
            # Negative indicators (typical data patterns)
            if any([
                re.search(r'^\d+$', cell_str),  # Pure numbers
                re.search(r'^\$[\d,.-]+$', cell_str),  # Money amounts
                cell_str.startswith('(') and cell_str.endswith(')'),  # Parenthetical
                len(cell_str) > 50  # Very long text (likely data)
            ]):
                header_indicators -= 1
                
            total_indicators += 1
        
        # Must have more positive than negative indicators
        return header_indicators > 0 and header_indicators / max(total_indicators, 1) > 0.3
    
    def _extract_table_region_precise(self, image: np.ndarray, bbox: List[float]) -> np.ndarray:
        """Extract table region with precise coordinates and validation."""
        
        if not bbox or len(bbox) != 4:
            return image
        
        x1, y1, x2, y2 = [int(coord) for coord in bbox]
        
        # Validate coordinates
        h, w = image.shape[:2]
        x1 = max(0, min(x1, w))
        y1 = max(0, min(y1, h))
        x2 = max(x1, min(x2, w))
        y2 = max(y1, min(y2, h))
        
        # Add small padding for better extraction
        padding = 5
        x1 = max(0, x1 - padding)
        y1 = max(0, y1 - padding)
        x2 = min(w, x2 + padding)
        y2 = min(h, y2 + padding)
        
        # Extract region
        table_region = image[y1:y2, x1:x2]
        
        if table_region.size == 0:
            return image
        
        return table_region
