"""Advanced evaluation metrics for table extraction (TEDS, GriTS, etc.)"""

import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
import editdistance
from collections import defaultdict
import itertools

@dataclass
class TEDSResult:
    """Tree Edit Distance-based Similarity result."""
    score: float
    tree_edit_distance: int
    max_tree_size: int
    precision: float
    recall: float

class AdvancedEvaluationMetrics:
    """Implementation of TEDS, GriTS and other advanced table evaluation metrics."""
    
    def __init__(self):
        pass
    
    def calculate_teds_score(
        self, 
        pred_table: Dict[str, Any], 
        gt_table: Dict[str, Any]
    ) -> TEDSResult:
        """Calculate Tree Edit Distance-based Similarity (TEDS) score."""
        
        try:
            # Convert tables to tree representations
            pred_tree = self._table_to_tree(pred_table)
            gt_tree = self._table_to_tree(gt_table)
            
            # Calculate tree edit distance
            edit_distance = self._calculate_tree_edit_distance(pred_tree, gt_tree)
            
            # Calculate max tree size for normalization
            max_tree_size = max(len(pred_tree), len(gt_tree))
            
            # Calculate TEDS score
            teds_score = 1 - (edit_distance / max_tree_size) if max_tree_size > 0 else 0.0
            
            # Calculate precision and recall
            precision, recall = self._calculate_tree_precision_recall(pred_tree, gt_tree)
            
            return TEDSResult(
                score=teds_score,
                tree_edit_distance=edit_distance,
                max_tree_size=max_tree_size,
                precision=precision,
                recall=recall
            )
            
        except Exception as e:
            return TEDSResult(0.0, 0, 0, 0.0, 0.0)
    
    def calculate_grits_score(
        self, 
        pred_table: Dict[str, Any], 
        gt_table: Dict[str, Any]
    ) -> float:
        """Calculate Grid Table Similarity (GriTS) score."""
        
        try:
            # Convert tables to 2D grids
            pred_grid = self._table_to_2d_grid(pred_table)
            gt_grid = self._table_to_2d_grid(gt_table)
            
            if not pred_grid or not gt_grid:
                return 0.0
            
            # Align grids to same dimensions
            aligned_pred, aligned_gt = self._align_grids(pred_grid, gt_grid)
            
            # Calculate cell-wise similarity
            total_cells = len(aligned_gt) * len(aligned_gt[0]) if aligned_gt else 0
            if total_cells == 0:
                return 0.0
            
            matching_cells = 0
            for i in range(len(aligned_gt)):
                for j in range(len(aligned_gt[0])):
                    pred_cell = aligned_pred[i][j] if i < len(aligned_pred) and j < len(aligned_pred[i]) else ""
                    gt_cell = aligned_gt[i][j]
                    
                    if self._cells_match(pred_cell, gt_cell):
                        matching_cells += 1
            
            return matching_cells / total_cells
            
        except Exception as e:
            return 0.0
    
    def _table_to_tree(self, table: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert table to tree representation for TEDS calculation."""
        
        tree = []
        
        # Add table root
        tree.append({
            'type': 'table',
            'children': [],
            'attributes': {
                'rows': table.get('row_count', 0),
                'columns': table.get('column_count', 0)
            }
        })
        
        # Process cells and build hierarchical structure
        cells = table.get('cells', [])
        rows_dict = defaultdict(list)
        
        # Group cells by row
        for cell in cells:
            row_idx = cell.get('row', 0)
            rows_dict[row_idx].append(cell)
        
        # Build tree structure
        for row_idx in sorted(rows_dict.keys()):
            row_cells = sorted(rows_dict[row_idx], key=lambda c: c.get('column', 0))
            
            row_node = {
                'type': 'row',
                'children': [],
                'attributes': {'index': row_idx}
            }
            
            for cell in row_cells:
                cell_node = {
                    'type': 'cell',
                    'children': [],
                    'attributes': {
                        'row': cell.get('row', 0),
                        'column': cell.get('column', 0),
                        'text': cell.get('text', '').strip(),
                        'rowspan': cell.get('row_span', 1),
                        'colspan': cell.get('column_span', 1)
                    }
                }
                row_node['children'].append(cell_node)
            
            tree[0]['children'].append(row_node)
        
        return tree
    
    def _calculate_tree_edit_distance(self, tree1: List[Dict], tree2: List[Dict]) -> int:
        """Calculate edit distance between two tree structures."""
        
        if not tree1 or not tree2:
            return max(len(tree1), len(tree2))
        
        # Flatten trees to sequences for edit distance calculation
        seq1 = self._flatten_tree(tree1[0])
        seq2 = self._flatten_tree(tree2[0])
        
        # Use string edit distance on flattened sequences
        str1 = '|'.join(seq1)
        str2 = '|'.join(seq2)
        
        return editdistance.eval(str1, str2)
    
    def _flatten_tree(self, node: Dict[str, Any]) -> List[str]:
        """Flatten tree to sequence for edit distance calculation."""
        
        sequence = []
        
        # Add current node
        node_repr = f"{node['type']}"
        if 'attributes' in node:
            attrs = node['attributes']
            if 'text' in attrs:
                node_repr += f":{attrs['text']}"
            if 'row' in attrs and 'column' in attrs:
                node_repr += f"@{attrs['row']},{attrs['column']}"
        
        sequence.append(node_repr)
        
        # Add children
        for child in node.get('children', []):
            sequence.extend(self._flatten_tree(child))
        
        return sequence
    
    def _calculate_tree_precision_recall(
        self, 
        pred_tree: List[Dict], 
        gt_tree: List[Dict]
    ) -> Tuple[float, float]:
        """Calculate precision and recall for tree structures."""
        
        pred_elements = set(self._flatten_tree(pred_tree[0])) if pred_tree else set()
        gt_elements = set(self._flatten_tree(gt_tree[0])) if gt_tree else set()
        
        if not pred_elements and not gt_elements:
            return 1.0, 1.0
        
        if not pred_elements:
            return 0.0, 0.0
        
        if not gt_elements:
            return 0.0, 1.0
        
        intersection = pred_elements.intersection(gt_elements)
        
        precision = len(intersection) / len(pred_elements)
        recall = len(intersection) / len(gt_elements)
        
        return precision, recall
    
    def _table_to_2d_grid(self, table: Dict[str, Any]) -> List[List[str]]:
        """Convert table to 2D grid representation."""
        
        cells = table.get('cells', [])
        if not cells:
            return []
        
        # Find dimensions
        max_row = max(cell.get('row', 0) for cell in cells) + 1
        max_col = max(cell.get('column', 0) for cell in cells) + 1
        
        # Initialize grid
        grid = [["" for _ in range(max_col)] for _ in range(max_row)]
        
        # Fill grid
        for cell in cells:
            row = cell.get('row', 0)
            col = cell.get('column', 0)
            text = cell.get('text', '').strip()
            
            if row < max_row and col < max_col:
                grid[row][col] = text
                
                # Handle merged cells
                row_span = cell.get('row_span', 1)
                col_span = cell.get('column_span', 1)
                
                for r in range(row, min(row + row_span, max_row)):
                    for c in range(col, min(col + col_span, max_col)):
                        if r != row or c != col:  # Skip original cell
                            grid[r][c] = f"[MERGED:{text}]"
        
        return grid
    
    def _align_grids(
        self, 
        grid1: List[List[str]], 
        grid2: List[List[str]]
    ) -> Tuple[List[List[str]], List[List[str]]]:
        """Align two grids to have the same dimensions."""
        
        max_rows = max(len(grid1), len(grid2))
        max_cols = max(
            max(len(row) for row in grid1) if grid1 else 0,
            max(len(row) for row in grid2) if grid2 else 0
        )
        
        # Pad grid1
        aligned_grid1 = []
        for i in range(max_rows):
            row = grid1[i] if i < len(grid1) else []
            padded_row = row + [""] * (max_cols - len(row))
            aligned_grid1.append(padded_row[:max_cols])
        
        # Pad grid2
        aligned_grid2 = []
        for i in range(max_rows):
            row = grid2[i] if i < len(grid2) else []
            padded_row = row + [""] * (max_cols - len(row))
            aligned_grid2.append(padded_row[:max_cols])
        
        return aligned_grid1, aligned_grid2
    
    def _cells_match(self, cell1: str, cell2: str) -> bool:
        """Check if two cells match (with some tolerance)."""
        
        if cell1 == cell2:
            return True
        
        # Normalize for comparison
        norm1 = self._normalize_cell_text(cell1)
        norm2 = self._normalize_cell_text(cell2)
        
        return norm1 == norm2
    
    def _normalize_cell_text(self, text: str) -> str:
        """Normalize cell text for comparison."""
        
        if not text:
            return ""
        
        # Handle merged cell markers
        if text.startswith("[MERGED:") and text.endswith("]"):
            text = text[8:-1]
        
        # Normalize whitespace and case
        return text.strip().lower()
