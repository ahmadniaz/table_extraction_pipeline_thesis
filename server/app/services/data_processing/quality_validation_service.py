"""
Quality Validation Service for Enhanced Mistral Document AI
This service provides comprehensive quality metrics and validation for extracted data.
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class QualityLevel(Enum):
    """Quality assessment levels"""
    EXCELLENT = "excellent"  # 90-100%
    GOOD = "good"           # 80-89%
    FAIR = "fair"           # 70-79%
    POOR = "poor"           # 60-69%
    FAILED = "failed"       # <60%

@dataclass
class QualityMetrics:
    """Comprehensive quality metrics for extracted data"""
    extraction_completeness: float
    structure_accuracy: float
    data_fidelity: float
    hierarchical_detection: float
    confidence_score: float
    overall_quality: QualityLevel
    validation_passed: bool
    issues_found: List[str]
    recommendations: List[str]

@dataclass
class ValidationResult:
    """Result of quality validation"""
    is_valid: bool
    quality_score: float
    quality_level: QualityLevel
    metrics: QualityMetrics
    warnings: List[str]
    errors: List[str]

class QualityValidationService:
    """
    Service for validating and assessing the quality of extracted commission data.
    Implements comprehensive quality metrics based on September 2025 research.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Quality thresholds
        self.thresholds = {
            "excellent": 0.90,
            "good": 0.80,
            "fair": 0.70,
            "poor": 0.60
        }
        
        # Financial data patterns for validation
        self.financial_patterns = {
            "currency": r'\$[\d,]+\.?\d*',
            "percentage": r'\d+\.?\d*%',
            "decimal": r'\d+\.\d{2}',
            "integer": r'\d+',
            "commission_terms": ['commission', 'premium', 'billing', 'amount', 'due', 'total'],
            "company_terms": ['llc', 'inc', 'corp', 'company', 'group', 'organization'],
            "date_patterns": [r'\d{1,2}/\d{1,2}/\d{4}', r'\d{4}-\d{2}-\d{2}', r'[A-Za-z]{3}\s+\d{4}']
        }
    
    def validate_extraction_result(self, result: Dict[str, Any]) -> ValidationResult:
        """
        Validate a complete extraction result and return comprehensive quality assessment.
        
        Args:
            result: Complete extraction result from Mistral service
            
        Returns:
            ValidationResult with quality metrics and recommendations
        """
        try:
            self.logger.info("Starting comprehensive quality validation")
            
            # Extract basic information
            tables = result.get("tables", [])
            extraction_metadata = result.get("extraction_metadata", {})
            
            if not tables:
                return self._create_failed_result("No tables found in extraction result")
            
            # Calculate individual quality metrics
            completeness = self._calculate_extraction_completeness(tables)
            structure_accuracy = self._calculate_structure_accuracy(tables)
            data_fidelity = self._calculate_data_fidelity(tables)
            hierarchical_detection = self._calculate_hierarchical_detection(tables)
            confidence_score = self._calculate_confidence_score(extraction_metadata)
            
            # Calculate overall quality score
            overall_score = (
                completeness * 0.25 +
                structure_accuracy * 0.25 +
                data_fidelity * 0.25 +
                hierarchical_detection * 0.15 +
                confidence_score * 0.10
            )
            
            # Determine quality level
            quality_level = self._determine_quality_level(overall_score)
            
            # Identify issues and recommendations
            issues = self._identify_issues(tables, overall_score)
            recommendations = self._generate_recommendations(issues, overall_score)
            
            # Create quality metrics
            metrics = QualityMetrics(
                extraction_completeness=completeness,
                structure_accuracy=structure_accuracy,
                data_fidelity=data_fidelity,
                hierarchical_detection=hierarchical_detection,
                confidence_score=confidence_score,
                overall_quality=quality_level,
                validation_passed=overall_score >= self.thresholds["fair"],
                issues_found=issues,
                recommendations=recommendations
            )
            
            # Determine if validation passed
            validation_passed = overall_score >= self.thresholds["fair"]
            
            # Generate warnings and errors
            warnings = self._generate_warnings(issues, overall_score)
            errors = self._generate_errors(issues, overall_score)
            
            self.logger.info(f"Quality validation completed. Overall score: {overall_score:.3f} ({quality_level.value})")
            
            return ValidationResult(
                is_valid=validation_passed,
                quality_score=overall_score,
                quality_level=quality_level,
                metrics=metrics,
                warnings=warnings,
                errors=errors
            )
            
        except Exception as e:
            self.logger.error(f"Quality validation failed: {e}")
            return self._create_failed_result(f"Validation error: {str(e)}")
    
    def _calculate_extraction_completeness(self, tables: List[Dict[str, Any]]) -> float:
        """Calculate how completely the data was extracted (0.0-1.0)"""
        if not tables:
            return 0.0
        
        total_cells = 0
        non_empty_cells = 0
        
        for table in tables:
            headers = table.get("headers", [])
            rows = table.get("rows", [])
            
            # Count total cells
            table_cells = len(headers) * len(rows) if headers and rows else 0
            total_cells += table_cells
            
            # Count non-empty cells
            if rows:
                for row in rows:
                    non_empty_cells += sum(1 for cell in row if str(cell).strip())
        
        if total_cells == 0:
            return 0.0
        
        completeness = non_empty_cells / total_cells
        return min(1.0, completeness)
    
    def _calculate_structure_accuracy(self, tables: List[Dict[str, Any]]) -> float:
        """Calculate how accurately the table structure was preserved (0.0-1.0)"""
        if not tables:
            return 0.0
        
        structure_scores = []
        
        for table in tables:
            headers = table.get("headers", [])
            rows = table.get("rows", [])
            
            score = 0.0
            
            # Check for proper headers
            if headers:
                meaningful_headers = sum(1 for h in headers if len(str(h).strip()) > 2)
                score += (meaningful_headers / len(headers)) * 0.4
            
            # Check for consistent row structure
            if rows and headers:
                consistent_rows = sum(1 for row in rows if len(row) == len(headers))
                score += (consistent_rows / len(rows)) * 0.4
            
            # Check for reasonable table size
            if headers and rows:
                table_size = len(headers) * len(rows)
                if 6 <= table_size <= 500:  # Reasonable table size
                    score += 0.2
            
            structure_scores.append(score)
        
        return sum(structure_scores) / len(structure_scores) if structure_scores else 0.0
    
    def _calculate_data_fidelity(self, tables: List[Dict[str, Any]]) -> float:
        """Calculate how accurately the data matches expected patterns (0.0-1.0)"""
        if not tables:
            return 0.0
        
        fidelity_scores = []
        
        for table in tables:
            headers = table.get("headers", [])
            rows = table.get("rows", [])
            
            score = 0.0
            
            # Check for financial data patterns
            if rows:
                financial_matches = 0
                total_cells = 0
                
                for row in rows[:10]:  # Sample first 10 rows
                    for cell in row:
                        cell_str = str(cell).strip()
                        if cell_str:
                            total_cells += 1
                            
                            # Check for currency patterns
                            if re.search(self.financial_patterns["currency"], cell_str):
                                financial_matches += 1
                            # Check for percentage patterns
                            elif re.search(self.financial_patterns["percentage"], cell_str):
                                financial_matches += 1
                            # Check for decimal patterns
                            elif re.search(self.financial_patterns["decimal"], cell_str):
                                financial_matches += 1
                
                if total_cells > 0:
                    score += (financial_matches / total_cells) * 0.6
            
            # Check for company name patterns
            if headers:
                company_headers = sum(1 for h in headers 
                                    if any(term in str(h).lower() for term in self.financial_patterns["company_terms"]))
                score += (company_headers / len(headers)) * 0.4
            
            fidelity_scores.append(score)
        
        return sum(fidelity_scores) / len(fidelity_scores) if fidelity_scores else 0.0
    
    def _calculate_hierarchical_detection(self, tables: List[Dict[str, Any]]) -> float:
        """Calculate how well hierarchical structures were detected (0.0-1.0)"""
        if not tables:
            return 0.0
        
        hierarchical_scores = []
        
        for table in tables:
            headers = table.get("headers", [])
            rows = table.get("rows", [])
            metadata = table.get("metadata", {})
            
            score = 0.0
            
            # Check for hierarchical metadata
            hierarchical_metadata = metadata.get("hierarchical_metadata", {})
            if hierarchical_metadata.get("company_sections_detected"):
                score += 0.4
            
            if hierarchical_metadata.get("company_names"):
                score += 0.3
            
            if hierarchical_metadata.get("hierarchical_levels", 0) > 0:
                score += 0.3
            
            # Check for company patterns in data
            if rows:
                company_patterns = 0
                for row in rows[:5]:  # Sample first 5 rows
                    for cell in row:
                        cell_str = str(cell).strip()
                        if any(term in cell_str.lower() for term in ['llc', 'inc', 'corp', 'company']):
                            company_patterns += 1
                            break
                
                if company_patterns > 0:
                    score += 0.2
            
            hierarchical_scores.append(score)
        
        return sum(hierarchical_scores) / len(hierarchical_scores) if hierarchical_scores else 0.0
    
    def _calculate_confidence_score(self, extraction_metadata: Dict[str, Any]) -> float:
        """Calculate confidence score from extraction metadata (0.0-1.0)"""
        # Get confidence from metadata
        confidence = extraction_metadata.get("confidence", 0.0)
        
        # If it's a string, try to convert to float
        if isinstance(confidence, str):
            try:
                confidence = float(confidence)
            except ValueError:
                confidence = 0.0
        
        # Get quality metrics from metadata if available
        quality_metrics = extraction_metadata.get("quality_metrics", {})
        if quality_metrics:
            # Use the confidence from quality metrics if available
            metrics_confidence = quality_metrics.get("confidence_score", confidence)
            confidence = max(confidence, metrics_confidence)
        
        return min(1.0, max(0.0, confidence))
    
    def _determine_quality_level(self, score: float) -> QualityLevel:
        """Determine quality level based on score"""
        if score >= self.thresholds["excellent"]:
            return QualityLevel.EXCELLENT
        elif score >= self.thresholds["good"]:
            return QualityLevel.GOOD
        elif score >= self.thresholds["fair"]:
            return QualityLevel.FAIR
        elif score >= self.thresholds["poor"]:
            return QualityLevel.POOR
        else:
            return QualityLevel.FAILED
    
    def _identify_issues(self, tables: List[Dict[str, Any]], overall_score: float) -> List[str]:
        """Identify specific issues with the extraction"""
        issues = []
        
        if not tables:
            issues.append("No tables extracted")
            return issues
        
        # Check for empty tables
        empty_tables = sum(1 for table in tables 
                          if not table.get("rows") or len(table.get("rows", [])) == 0)
        if empty_tables > 0:
            issues.append(f"{empty_tables} empty tables found")
        
        # Check for tables without headers
        no_header_tables = sum(1 for table in tables 
                              if not table.get("headers") or len(table.get("headers", [])) == 0)
        if no_header_tables > 0:
            issues.append(f"{no_header_tables} tables without headers found")
        
        # Check for inconsistent column counts
        inconsistent_tables = 0
        for table in tables:
            headers = table.get("headers", [])
            rows = table.get("rows", [])
            if headers and rows:
                expected_cols = len(headers)
                inconsistent_rows = sum(1 for row in rows if len(row) != expected_cols)
                if inconsistent_rows > len(rows) * 0.2:  # More than 20% inconsistent
                    inconsistent_tables += 1
        
        if inconsistent_tables > 0:
            issues.append(f"{inconsistent_tables} tables with inconsistent column counts")
        
        # Check for low data quality
        if overall_score < self.thresholds["fair"]:
            issues.append("Overall data quality below acceptable threshold")
        
        return issues
    
    def _generate_recommendations(self, issues: List[str], overall_score: float) -> List[str]:
        """Generate recommendations for improving extraction quality"""
        recommendations = []
        
        if not issues:
            recommendations.append("Extraction quality is excellent - no improvements needed")
            return recommendations
        
        # Issue-specific recommendations
        for issue in issues:
            if "empty tables" in issue:
                recommendations.append("Consider adjusting confidence thresholds to capture more data")
            elif "without headers" in issue:
                recommendations.append("Review table detection settings to better identify headers")
            elif "inconsistent column counts" in issue:
                recommendations.append("Enable table structure validation to ensure consistent formatting")
            elif "data quality below" in issue:
                recommendations.append("Consider using enhanced extraction features or retry with different parameters")
        
        # General recommendations based on score
        if overall_score < self.thresholds["good"]:
            recommendations.append("Consider using the enhanced Mistral service with advanced features")
        
        if overall_score < self.thresholds["fair"]:
            recommendations.append("Review document quality and consider preprocessing before extraction")
        
        return recommendations
    
    def _generate_warnings(self, issues: List[str], overall_score: float) -> List[str]:
        """Generate warnings for quality issues"""
        warnings = []
        
        if overall_score < self.thresholds["good"]:
            warnings.append(f"Extraction quality is {self._determine_quality_level(overall_score).value} - review results carefully")
        
        for issue in issues:
            if "inconsistent" in issue or "empty" in issue:
                warnings.append(f"Data quality issue: {issue}")
        
        return warnings
    
    def _generate_errors(self, issues: List[str], overall_score: float) -> List[str]:
        """Generate errors for critical quality issues"""
        errors = []
        
        if overall_score < self.thresholds["poor"]:
            errors.append("Extraction quality is critically low - results may be unreliable")
        
        if not issues:  # No tables found
            errors.append("No data extracted - extraction may have failed")
        
        return errors
    
    def _create_failed_result(self, error_message: str) -> ValidationResult:
        """Create a failed validation result"""
        return ValidationResult(
            is_valid=False,
            quality_score=0.0,
            quality_level=QualityLevel.FAILED,
            metrics=QualityMetrics(
                extraction_completeness=0.0,
                structure_accuracy=0.0,
                data_fidelity=0.0,
                hierarchical_detection=0.0,
                confidence_score=0.0,
                overall_quality=QualityLevel.FAILED,
                validation_passed=False,
                issues_found=[error_message],
                recommendations=["Review extraction parameters and document quality"]
            ),
            warnings=[],
            errors=[error_message]
        )
    
    def benchmark_extraction_performance(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Benchmark extraction performance across multiple documents"""
        try:
            if not results:
                return {"error": "No results provided for benchmarking"}
            
            total_documents = len(results)
            successful_extractions = sum(1 for result in results if result.get("success", False))
            success_rate = successful_extractions / total_documents if total_documents > 0 else 0.0
            
            # Calculate average quality scores
            quality_scores = []
            processing_times = []
            
            for result in results:
                if result.get("success"):
                    # Validate each result
                    validation = self.validate_extraction_result(result)
                    quality_scores.append(validation.quality_score)
                    
                    # Get processing time
                    metadata = result.get("extraction_metadata", {})
                    processing_time = metadata.get("processing_time", 0)
                    if processing_time:
                        processing_times.append(processing_time)
            
            avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
            avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0.0
            
            return {
                "total_documents": total_documents,
                "successful_extractions": successful_extractions,
                "success_rate": success_rate,
                "average_quality_score": avg_quality,
                "average_processing_time": avg_processing_time,
                "quality_distribution": {
                    "excellent": sum(1 for score in quality_scores if score >= self.thresholds["excellent"]),
                    "good": sum(1 for score in quality_scores if self.thresholds["good"] <= score < self.thresholds["excellent"]),
                    "fair": sum(1 for score in quality_scores if self.thresholds["fair"] <= score < self.thresholds["good"]),
                    "poor": sum(1 for score in quality_scores if self.thresholds["poor"] <= score < self.thresholds["fair"]),
                    "failed": sum(1 for score in quality_scores if score < self.thresholds["poor"])
                }
            }
            
        except Exception as e:
            self.logger.error(f"Benchmarking failed: {e}")
            return {"error": f"Benchmarking failed: {str(e)}"}
