"""Evaluation metrics for table extraction pipeline."""

from typing import Dict, List, Any, Tuple, Optional
import numpy as np
from dataclasses import dataclass


@dataclass
class BoundingBox:
    """Bounding box representation."""
    x1: float
    y1: float
    x2: float
    y2: float
    
    @property
    def area(self) -> float:
        """Calculate area of bounding box."""
        return max(0, self.x2 - self.x1) * max(0, self.y2 - self.y1)
    
    def intersection(self, other: 'BoundingBox') -> 'BoundingBox':
        """Calculate intersection with another bounding box."""
        return BoundingBox(
            max(self.x1, other.x1),
            max(self.y1, other.y1),
            min(self.x2, other.x2),
            min(self.y2, other.y2)
        )
    
    def union(self, other: 'BoundingBox') -> 'BoundingBox':
        """Calculate union with another bounding box."""
        return BoundingBox(
            min(self.x1, other.x1),
            min(self.y1, other.y1),
            max(self.x2, other.x2),
            max(self.y2, other.y2)
        )
    
    def iou(self, other: 'BoundingBox') -> float:
        """Calculate Intersection over Union (IoU) with another bounding box."""
        intersection = self.intersection(other)
        intersection_area = intersection.area
        
        if intersection_area == 0:
            return 0.0
        
        union_area = self.area + other.area - intersection_area
        return intersection_area / union_area if union_area > 0 else 0.0


class TableExtractionMetrics:
    """Metrics for evaluating table extraction performance."""
    
    def __init__(self, iou_threshold: float = 0.5):
        """Initialize metrics calculator."""
        self.iou_threshold = iou_threshold
    
    def calculate_detection_metrics(
        self,
        predicted_tables: List[Dict[str, Any]],
        ground_truth_tables: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Calculate table detection metrics."""
        if not ground_truth_tables:
            return {
                'precision': 1.0 if not predicted_tables else 0.0,
                'recall': 0.0,
                'f1_score': 0.0,
                'average_iou': 0.0
            }
        
        # Convert to bounding boxes
        pred_boxes = [
            BoundingBox(*table['bbox']) 
            for table in predicted_tables 
            if 'bbox' in table
        ]
        gt_boxes = [
            BoundingBox(*table['bbox']) 
            for table in ground_truth_tables 
            if 'bbox' in table
        ]
        
        if not pred_boxes:
            return {
                'precision': 0.0,
                'recall': 0.0,
                'f1_score': 0.0,
                'average_iou': 0.0
            }
        
        # Match predictions to ground truth
        matched_pairs = self._match_boxes(pred_boxes, gt_boxes)
        
        # Calculate metrics
        true_positives = len(matched_pairs)
        false_positives = len(pred_boxes) - true_positives
        false_negatives = len(gt_boxes) - true_positives
        
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
        f1_score = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        
        # Calculate average IoU for matched pairs
        avg_iou = np.mean([
            pred_boxes[pred_idx].iou(gt_boxes[gt_idx])
            for pred_idx, gt_idx in matched_pairs
        ]) if matched_pairs else 0.0
        
        return {
            'precision': precision,
            'recall': recall,
            'f1_score': f1_score,
            'average_iou': avg_iou,
            'true_positives': true_positives,
            'false_positives': false_positives,
            'false_negatives': false_negatives
        }
    
    def _match_boxes(
        self,
        pred_boxes: List[BoundingBox],
        gt_boxes: List[BoundingBox]
    ) -> List[Tuple[int, int]]:
        """Match predicted boxes to ground truth boxes using IoU threshold."""
        matched_pairs = []
        used_gt_indices = set()
        
        # Calculate IoU matrix
        iou_matrix = np.zeros((len(pred_boxes), len(gt_boxes)))
        for i, pred_box in enumerate(pred_boxes):
            for j, gt_box in enumerate(gt_boxes):
                iou_matrix[i, j] = pred_box.iou(gt_box)
        
        # Greedily match boxes with highest IoU
        for _ in range(min(len(pred_boxes), len(gt_boxes))):
            # Find maximum IoU
            max_iou_idx = np.unravel_index(np.argmax(iou_matrix), iou_matrix.shape)
            pred_idx, gt_idx = max_iou_idx
            max_iou = iou_matrix[pred_idx, gt_idx]
            
            # Check if IoU meets threshold
            if max_iou >= self.iou_threshold and gt_idx not in used_gt_indices:
                matched_pairs.append((pred_idx, gt_idx))
                used_gt_indices.add(gt_idx)
                
                # Remove matched boxes from consideration
                iou_matrix[pred_idx, :] = 0
                iou_matrix[:, gt_idx] = 0
            else:
                break
        
        return matched_pairs
    
    def calculate_structure_metrics(
        self,
        predicted_structure: Dict[str, Any],
        ground_truth_structure: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate table structure recognition metrics."""
        metrics = {}
        
        # Row and column accuracy
        pred_rows = predicted_structure.get('rows', 0)
        pred_cols = predicted_structure.get('columns', 0)
        gt_rows = ground_truth_structure.get('rows', 0)
        gt_cols = ground_truth_structure.get('columns', 0)
        
        metrics['row_accuracy'] = 1.0 if pred_rows == gt_rows else 0.0
        metrics['column_accuracy'] = 1.0 if pred_cols == gt_cols else 0.0
        metrics['structure_accuracy'] = 1.0 if (pred_rows == gt_rows and pred_cols == gt_cols) else 0.0
        
        # Cell-level metrics
        pred_cells = predicted_structure.get('cells', [])
        gt_cells = ground_truth_structure.get('cells', [])
        
        if gt_cells:
            cell_metrics = self._calculate_cell_metrics(pred_cells, gt_cells)
            metrics.update(cell_metrics)
        
        return metrics
    
    def _calculate_cell_metrics(
        self,
        pred_cells: List[Dict[str, Any]],
        gt_cells: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Calculate cell-level metrics."""
        # Create cell position maps
        pred_positions = {(cell.get('row', -1), cell.get('column', -1)): cell for cell in pred_cells}
        gt_positions = {(cell.get('row', -1), cell.get('column', -1)): cell for cell in gt_cells}
        
        # Calculate cell detection accuracy
        common_positions = set(pred_positions.keys()) & set(gt_positions.keys())
        cell_detection_accuracy = len(common_positions) / len(gt_positions) if gt_positions else 0.0
        
        # Calculate text accuracy for matched cells
        text_matches = 0
        for pos in common_positions:
            pred_text = pred_positions[pos].get('text', '').strip().lower()
            gt_text = gt_positions[pos].get('text', '').strip().lower()
            if pred_text == gt_text:
                text_matches += 1
        
        text_accuracy = text_matches / len(common_positions) if common_positions else 0.0
        
        return {
            'cell_detection_accuracy': cell_detection_accuracy,
            'text_accuracy': text_accuracy,
            'detected_cells': len(pred_cells),
            'ground_truth_cells': len(gt_cells),
            'matched_cells': len(common_positions)
        }
    
    def calculate_overall_metrics(
        self,
        predicted_result: Dict[str, Any],
        ground_truth_result: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate overall extraction metrics."""
        pred_tables = predicted_result.get('tables', [])
        gt_tables = ground_truth_result.get('tables', [])
        
        # Detection metrics
        detection_metrics = self.calculate_detection_metrics(pred_tables, gt_tables)
        
        # Structure metrics (average across all tables)
        structure_metrics_list = []
        
        # Match tables first
        pred_boxes = [BoundingBox(*table['bbox']) for table in pred_tables if 'bbox' in table]
        gt_boxes = [BoundingBox(*table['bbox']) for table in gt_tables if 'bbox' in table]
        matched_pairs = self._match_boxes(pred_boxes, gt_boxes)
        
        for pred_idx, gt_idx in matched_pairs:
            pred_structure = pred_tables[pred_idx].get('structure', {})
            gt_structure = gt_tables[gt_idx].get('structure', {})
            
            table_metrics = self.calculate_structure_metrics(pred_structure, gt_structure)
            structure_metrics_list.append(table_metrics)
        
        # Average structure metrics
        if structure_metrics_list:
            avg_structure_metrics = {}
            for key in structure_metrics_list[0].keys():
                avg_structure_metrics[f'avg_{key}'] = np.mean([
                    metrics[key] for metrics in structure_metrics_list
                ])
        else:
            avg_structure_metrics = {}
        
        # Combine all metrics
        overall_metrics = {
            **detection_metrics,
            **avg_structure_metrics,
            'num_predicted_tables': len(pred_tables),
            'num_ground_truth_tables': len(gt_tables),
            'processing_time': predicted_result.get('processing_time', 0.0)
        }
        
        return overall_metrics


def calculate_confidence_statistics(
    tables: List[Dict[str, Any]]
) -> Dict[str, float]:
    """Calculate confidence score statistics."""
    if not tables:
        return {
            'mean_confidence': 0.0,
            'std_confidence': 0.0,
            'min_confidence': 0.0,
            'max_confidence': 0.0
        }
    
    detection_confidences = [
        table.get('detection_confidence', 0.0) for table in tables
    ]
    structure_confidences = [
        table.get('structure_confidence', 0.0) for table in tables
    ]
    quality_scores = [
        table.get('quality_score', 0.0) for table in tables
    ]
    
    return {
        'mean_detection_confidence': np.mean(detection_confidences),
        'std_detection_confidence': np.std(detection_confidences),
        'min_detection_confidence': np.min(detection_confidences),
        'max_detection_confidence': np.max(detection_confidences),
        'mean_structure_confidence': np.mean(structure_confidences),
        'std_structure_confidence': np.std(structure_confidences),
        'mean_quality_score': np.mean(quality_scores),
        'std_quality_score': np.std(quality_scores)
    }


def benchmark_extraction_speed(
    processing_times: List[float],
    file_sizes: List[int]
) -> Dict[str, float]:
    """Benchmark extraction speed performance."""
    if not processing_times:
        return {}
    
    # Convert file sizes to MB
    file_sizes_mb = [size / (1024 * 1024) for size in file_sizes]
    
    # Calculate speed metrics
    avg_time = np.mean(processing_times)
    std_time = np.std(processing_times)
    
    # Calculate throughput (MB/second)
    throughput = [
        size_mb / time if time > 0 else 0
        for size_mb, time in zip(file_sizes_mb, processing_times)
    ]
    
    return {
        'average_processing_time': avg_time,
        'std_processing_time': std_time,
        'min_processing_time': np.min(processing_times),
        'max_processing_time': np.max(processing_times),
        'average_throughput_mb_per_sec': np.mean(throughput),
        'std_throughput_mb_per_sec': np.std(throughput),
        'total_files_processed': len(processing_times),
        'total_processing_time': np.sum(processing_times)
    }
