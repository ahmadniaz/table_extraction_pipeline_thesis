"""
Configuration and Monitoring for Mistral Extraction Enhancements

Provides configuration management and performance monitoring for the enhanced
summary detection and bracket processing systems.
"""

from dataclasses import dataclass
from typing import Dict, Any
import os
import logging

logger = logging.getLogger(__name__)

@dataclass
class EnhancementConfig:
    """Configuration for Mistral extraction enhancements"""
    
    # Summary Detection Settings
    summary_detection_enabled: bool = True
    summary_confidence_threshold: float = 0.85
    summary_minimum_strategies: int = 3
    summary_max_removal_percentage: float = 0.20
    
    # Bracket Processing Settings
    bracket_processing_enabled: bool = True
    bracket_validation_enabled: bool = True
    bracket_assume_monetary: bool = True
    
    # Monitoring Settings
    enable_detailed_logging: bool = False
    enable_performance_monitoring: bool = True
    enable_quality_metrics: bool = True
    
    # Safety Settings
    enable_safety_checks: bool = True
    preserve_original_data: bool = True
    
    @classmethod
    def from_env(cls) -> 'EnhancementConfig':
        """Create config from environment variables"""
        return cls(
            summary_detection_enabled=os.getenv('MISTRAL_SUMMARY_DETECTION_ENABLED', 'true').lower() == 'true',
            summary_confidence_threshold=float(os.getenv('MISTRAL_SUMMARY_CONFIDENCE_THRESHOLD', '0.85')),
            summary_minimum_strategies=int(os.getenv('MISTRAL_SUMMARY_MIN_STRATEGIES', '3')),
            summary_max_removal_percentage=float(os.getenv('MISTRAL_SUMMARY_MAX_REMOVAL_PCT', '0.20')),
            bracket_processing_enabled=os.getenv('MISTRAL_BRACKET_PROCESSING_ENABLED', 'true').lower() == 'true',
            bracket_validation_enabled=os.getenv('MISTRAL_BRACKET_VALIDATION_ENABLED', 'true').lower() == 'true',
            bracket_assume_monetary=os.getenv('MISTRAL_BRACKET_ASSUME_MONETARY', 'true').lower() == 'true',
            enable_detailed_logging=os.getenv('MISTRAL_DETAILED_LOGGING', 'false').lower() == 'true',
            enable_performance_monitoring=os.getenv('MISTRAL_PERFORMANCE_MONITORING', 'true').lower() == 'true',
            enable_quality_metrics=os.getenv('MISTRAL_QUALITY_METRICS', 'true').lower() == 'true',
            enable_safety_checks=os.getenv('MISTRAL_SAFETY_CHECKS', 'true').lower() == 'true',
            preserve_original_data=os.getenv('MISTRAL_PRESERVE_ORIGINAL', 'true').lower() == 'true'
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'summary_detection': {
                'enabled': self.summary_detection_enabled,
                'confidence_threshold': self.summary_confidence_threshold,
                'minimum_strategies': self.summary_minimum_strategies,
                'max_removal_percentage': self.summary_max_removal_percentage
            },
            'bracket_processing': {
                'enabled': self.bracket_processing_enabled,
                'validation_enabled': self.bracket_validation_enabled,
                'assume_monetary': self.bracket_assume_monetary
            },
            'monitoring': {
                'detailed_logging': self.enable_detailed_logging,
                'performance_monitoring': self.enable_performance_monitoring,
                'quality_metrics': self.enable_quality_metrics
            },
            'safety': {
                'safety_checks': self.enable_safety_checks,
                'preserve_original': self.preserve_original_data
            }
        }

class EnhancementMonitor:
    """Monitor enhancement performance and quality"""
    
    def __init__(self):
        self.metrics = {
            'summary_detection': {
                'total_tables_processed': 0,
                'tables_with_summary_rows': 0,
                'rows_removed': 0,
                'avg_confidence': 0.0,
                'safety_check_failures': 0
            },
            'bracket_processing': {
                'total_cells_processed': 0,
                'brackets_converted': 0,
                'conversion_errors': 0,
                'validation_failures': 0
            },
            'performance': {
                'avg_processing_time': 0.0,
                'total_extractions': 0,
                'total_processing_time': 0.0
            }
        }
    
    def record_summary_detection(self, detection_result: Dict[str, Any]):
        """Record summary detection metrics"""
        try:
            metrics = self.metrics['summary_detection']
            metrics['total_tables_processed'] += 1
            
            removed_indices = detection_result.get('removed_indices', [])
            if removed_indices:
                metrics['tables_with_summary_rows'] += 1
                metrics['rows_removed'] += len(removed_indices)
            
            confidence = detection_result.get('detection_confidence', 0.0)
            current_avg = metrics['avg_confidence']
            total_processed = metrics['total_tables_processed']
            metrics['avg_confidence'] = ((current_avg * (total_processed - 1)) + confidence) / total_processed
            
            # Check for safety failures
            if detection_result.get('detection_method') == 'safety_check_failed':
                metrics['safety_check_failures'] += 1
            
            logger.info(f"Summary detection recorded: {len(removed_indices)} rows removed, confidence: {confidence:.2f}")
        except Exception as e:
            logger.error(f"Failed to record summary detection metrics: {e}")
    
    def record_bracket_processing(self, processing_result: Dict[str, Any]):
        """Record bracket processing metrics"""
        try:
            metrics = self.metrics['bracket_processing']
            
            if 'bracket_processing' in processing_result:
                bp = processing_result['bracket_processing']
                metrics['total_cells_processed'] += bp.get('total_cells_processed', 0)
                metrics['brackets_converted'] += bp.get('brackets_converted', 0)
                metrics['conversion_errors'] += bp.get('errors', 0)
                
                validation = bp.get('validation', {})
                if not validation.get('data_integrity_preserved', True):
                    metrics['validation_failures'] += 1
                
                logger.info(f"Bracket processing recorded: {bp.get('brackets_converted', 0)} brackets converted")
        except Exception as e:
            logger.error(f"Failed to record bracket processing metrics: {e}")
    
    def record_performance(self, processing_time: float):
        """Record performance metrics"""
        try:
            metrics = self.metrics['performance']
            metrics['total_extractions'] += 1
            metrics['total_processing_time'] += processing_time
            metrics['avg_processing_time'] = metrics['total_processing_time'] / metrics['total_extractions']
            
            logger.info(f"Performance recorded: {processing_time:.2f}s (avg: {metrics['avg_processing_time']:.2f}s)")
        except Exception as e:
            logger.error(f"Failed to record performance metrics: {e}")
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics"""
        try:
            summary_det = self.metrics['summary_detection']
            bracket_proc = self.metrics['bracket_processing']
            performance = self.metrics['performance']
            
            return {
                'summary_detection': {
                    **summary_det,
                    'summary_detection_rate': (
                        summary_det['tables_with_summary_rows'] /
                        max(summary_det['total_tables_processed'], 1)
                    ) * 100,
                    'avg_rows_removed_per_table': (
                        summary_det['rows_removed'] /
                        max(summary_det['tables_with_summary_rows'], 1)
                    ) if summary_det['tables_with_summary_rows'] > 0 else 0
                },
                'bracket_processing': {
                    **bracket_proc,
                    'conversion_rate': (
                        bracket_proc['brackets_converted'] /
                        max(bracket_proc['total_cells_processed'], 1)
                    ) * 100,
                    'error_rate': (
                        bracket_proc['conversion_errors'] /
                        max(bracket_proc['total_cells_processed'], 1)
                    ) * 100
                },
                'performance': {
                    **performance,
                    'total_extractions': performance['total_extractions'],
                    'avg_processing_time_seconds': performance['avg_processing_time'],
                    'total_processing_time_seconds': performance['total_processing_time']
                }
            }
        except Exception as e:
            logger.error(f"Failed to get metrics summary: {e}")
            return {'error': str(e)}
    
    def reset_metrics(self):
        """Reset all metrics to initial state"""
        self.metrics = {
            'summary_detection': {
                'total_tables_processed': 0,
                'tables_with_summary_rows': 0,
                'rows_removed': 0,
                'avg_confidence': 0.0,
                'safety_check_failures': 0
            },
            'bracket_processing': {
                'total_cells_processed': 0,
                'brackets_converted': 0,
                'conversion_errors': 0,
                'validation_failures': 0
            },
            'performance': {
                'avg_processing_time': 0.0,
                'total_extractions': 0,
                'total_processing_time': 0.0
            }
        }
        logger.info("Metrics reset to initial state")
    
    def log_detailed_report(self):
        """Log detailed report of all metrics"""
        try:
            summary = self.get_metrics_summary()
            
            logger.info("=" * 80)
            logger.info("MISTRAL ENHANCEMENTS - DETAILED METRICS REPORT")
            logger.info("=" * 80)
            
            # Summary Detection
            logger.info("\nSUMMARY DETECTION:")
            sd = summary['summary_detection']
            logger.info(f"  Tables Processed: {sd['total_tables_processed']}")
            logger.info(f"  Tables with Summary Rows: {sd['tables_with_summary_rows']}")
            logger.info(f"  Total Rows Removed: {sd['rows_removed']}")
            logger.info(f"  Detection Rate: {sd['summary_detection_rate']:.2f}%")
            logger.info(f"  Avg Confidence: {sd['avg_confidence']:.2f}")
            logger.info(f"  Avg Rows Removed per Table: {sd['avg_rows_removed_per_table']:.2f}")
            logger.info(f"  Safety Check Failures: {sd['safety_check_failures']}")
            
            # Bracket Processing
            logger.info("\nBRACKET PROCESSING:")
            bp = summary['bracket_processing']
            logger.info(f"  Cells Processed: {bp['total_cells_processed']}")
            logger.info(f"  Brackets Converted: {bp['brackets_converted']}")
            logger.info(f"  Conversion Rate: {bp['conversion_rate']:.2f}%")
            logger.info(f"  Conversion Errors: {bp['conversion_errors']}")
            logger.info(f"  Error Rate: {bp['error_rate']:.4f}%")
            logger.info(f"  Validation Failures: {bp['validation_failures']}")
            
            # Performance
            logger.info("\nPERFORMANCE:")
            perf = summary['performance']
            logger.info(f"  Total Extractions: {perf['total_extractions']}")
            logger.info(f"  Avg Processing Time: {perf['avg_processing_time_seconds']:.2f}s")
            logger.info(f"  Total Processing Time: {perf['total_processing_time_seconds']:.2f}s")
            
            logger.info("=" * 80)
        except Exception as e:
            logger.error(f"Failed to log detailed report: {e}")


# Global monitor instance
_global_monitor = None

def get_global_monitor() -> EnhancementMonitor:
    """Get or create global monitor instance"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = EnhancementMonitor()
    return _global_monitor

def reset_global_monitor():
    """Reset global monitor metrics"""
    global _global_monitor
    if _global_monitor:
        _global_monitor.reset_metrics()

