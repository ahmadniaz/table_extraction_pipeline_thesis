"""Main table extraction pipeline orchestrator."""

import asyncio
import time
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import json
import re

from ..core.document_processor import DocumentProcessor, ProcessedDocument
from ..core.multipage_handler import MultiPageTableHandler
from ..models.tableformer import TableFormerModel, OCREngine, TableStructure
from ..models.advanced_tableformer import ProductionTableFormer
from ..models.advanced_ocr_engine import AdvancedOCREngine
from ..processors.financial_processor import SmartFinancialDocumentProcessor
from ..evaluation.advanced_metrics import AdvancedEvaluationMetrics
from ..utils.config import Config
from ..utils.logging_utils import get_logger, LogExtractionOperation
from ..utils.validation import ExtractionResultValidator, ValidationResult


class ExtractionStage(Enum):
    """Extraction pipeline stages."""
    DOCUMENT_PROCESSING = "document_processing"
    TABLE_DETECTION = "table_detection"
    STRUCTURE_RECOGNITION = "structure_recognition"
    TEXT_EXTRACTION = "text_extraction"
    POST_PROCESSING = "post_processing"
    VALIDATION = "validation"


@dataclass
class TableExtractionResult:
    """Result container for table extraction."""
    tables: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    processing_time: float = 0.0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    document_path: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'tables': self.tables,
            'metadata': self.metadata,
            'confidence_scores': self.confidence_scores,
            'processing_time': self.processing_time,
            'warnings': self.warnings,
            'errors': self.errors,
            'document_path': self.document_path
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2, default=str)


@dataclass
class ExtractionOptions:
    """Options for table extraction."""
    enable_ocr: bool = True
    enable_multipage: bool = True
    confidence_threshold: float = 0.5
    max_tables_per_page: int = 10
    output_format: str = "json"
    include_raw_data: bool = False
    enable_quality_checks: bool = True
    enable_advanced_tableformer: bool = True
    enable_ensemble_ocr: bool = True
    enable_financial_processing: bool = True
    enable_advanced_metrics: bool = True


class ExtractionPipeline:
    """Main orchestrator for the table extraction pipeline."""
    
    def __init__(self, config: Config):
        """Initialize extraction pipeline."""
        self.config = config
        self.logger = get_logger(__name__, config)
        
        # Initialize components
        self._initialize_components()
        
        # Validator
        self.validator = ExtractionResultValidator()
        
        # Pipeline statistics
        self.stats = {
            'total_documents_processed': 0,
            'total_tables_extracted': 0,
            'average_processing_time': 0.0,
            'success_rate': 0.0
        }
    
    def _initialize_components(self):
        """Initialize all pipeline components."""
        try:
            self.logger.logger.info("Initializing pipeline components...")
            
            # Document processor
            self.document_processor = DocumentProcessor(self.config)
            
            # TableFormer models (both legacy and advanced)
            self.tableformer = TableFormerModel(self.config)
            
            # Advanced components
            try:
                self.advanced_tableformer = ProductionTableFormer(self.config)
                self.logger.logger.info("Advanced TableFormer initialized")
            except Exception as e:
                self.logger.logger.warning(f"Advanced TableFormer failed to initialize: {e}")
                self.advanced_tableformer = None
            
            # Multi-page handler
            self.multipage_handler = MultiPageTableHandler(self.config)
            
            # Smart Financial processor - INTELLIGENT, NO HARDCODED PATTERNS
            self.financial_processor = SmartFinancialDocumentProcessor(self.config)
            
            # Advanced metrics
            self.metrics_engine = AdvancedEvaluationMetrics()
            
            # OCR engines
            if self.config.processing.enable_ocr:
                self.ocr_engine = OCREngine(self.config)
                try:
                    self.advanced_ocr_engine = AdvancedOCREngine(self.config)
                    self.logger.logger.info("Advanced OCR engine initialized")
                except Exception as e:
                    self.logger.logger.warning(f"Advanced OCR failed to initialize: {e}")
                    self.advanced_ocr_engine = None
            else:
                self.ocr_engine = None
                self.advanced_ocr_engine = None
            
            self.logger.logger.info("Pipeline components initialized successfully")
            
        except Exception as e:
            self.logger.logger.error(f"Failed to initialize pipeline components: {e}")
            raise
    
    async def extract_tables(
        self, 
        document_path: Union[str, Path],
        options: Optional[ExtractionOptions] = None
    ) -> TableExtractionResult:
        """Main extraction method."""
        if options is None:
            options = ExtractionOptions()
        
        document_path = Path(document_path)
        start_time = time.time()
        
        result = TableExtractionResult(
            document_path=str(document_path)
        )
        
        with LogExtractionOperation(self.logger, str(document_path), "table_extraction"):
            try:
                # Stage 1: Document preprocessing
                self.logger.log_extraction_progress(
                    ExtractionStage.DOCUMENT_PROCESSING.value, 0.1
                )
                processed_doc = await self._process_document(document_path)
                
                # Stage 2: Table detection and extraction
                self.logger.log_extraction_progress(
                    ExtractionStage.TABLE_DETECTION.value, 0.3
                )
                tables = await self._extract_tables_from_document(
                    processed_doc, options
                )
                
                # Stage 3: Multi-page linking (if enabled)
                if options.enable_multipage and len(tables) > 0:
                    self.logger.log_extraction_progress("multipage_linking", 0.6)
                    tables = await self._link_multipage_tables(tables, processed_doc)
                
                # Stage 4: Financial processing (if enabled)
                if options.enable_financial_processing:
                    self.logger.log_extraction_progress("financial_processing", 0.7)
                    tables = await self._process_financial_tables(tables, options)
                
                # Stage 5: Merge tables with identical headers
                self.logger.log_extraction_progress("table_merging", 0.75)
                tables = await self._merge_sequential_tables(tables)
                
                # Stage 6: Post-processing and validation
                self.logger.log_extraction_progress(
                    ExtractionStage.POST_PROCESSING.value, 0.8
                )
                final_tables = await self._postprocess_tables(tables, options)
                
                # Stage 4: Validation
                self.logger.log_extraction_progress(
                    ExtractionStage.VALIDATION.value, 0.9
                )
                
                # Compile final results
                result.tables = final_tables
                result.metadata = self._generate_metadata(processed_doc, options)
                result.confidence_scores = self._calculate_confidence_scores(final_tables)
                result.processing_time = time.time() - start_time
                
                # Validate results
                validation_result = self.validator.validate_extraction_result(
                    result.to_dict()
                )
                
                if validation_result.warnings:
                    result.warnings.extend(validation_result.warnings)
                
                if not validation_result.is_valid:
                    result.errors.extend(validation_result.errors)
                
                # Update statistics
                self._update_statistics(result)
                
                self.logger.log_extraction_success(
                    str(document_path),
                    len(result.tables),
                    result.processing_time,
                    result.confidence_scores
                )
                
                return result
                
            except Exception as e:
                result.errors.append(str(e))
                result.processing_time = time.time() - start_time
                
                self.logger.log_extraction_error(
                    str(document_path),
                    e,
                    context={'options': options.__dict__}
                )
                
                return result
    
    async def _process_document(self, document_path: Path) -> ProcessedDocument:
        """Process the input document."""
        try:
            processed_doc = await self.document_processor.process_document(document_path)
            
            self.logger.logger.info(
                f"Document processed: {processed_doc.num_pages} pages, "
                f"format: {processed_doc.format.value}"
            )
            
            return processed_doc
            
        except Exception as e:
            self.logger.logger.error(f"Document processing failed: {e}")
            raise
    
    async def _extract_tables_from_document(
        self, 
        processed_doc: ProcessedDocument,
        options: ExtractionOptions
    ) -> List[Dict[str, Any]]:
        """Enhanced extraction with complex document support."""
        all_tables = []
        
        if hasattr(processed_doc, 'extracted_tables') and processed_doc.extracted_tables:
            self.logger.logger.info(f"Using pre-extracted tables: {len(processed_doc.extracted_tables)}")
            
            # ✅ ENHANCED: Multi-tier confidence strategy for complex docs
            tables_with_scores = []
            for table_data in processed_doc.extracted_tables:
                table_confidence = table_data.get('metadata', {}).get('confidence', 1.0)
                tables_with_scores.append((table_data, table_confidence))
            
            # ✅ NEW: Detect document complexity and adjust strategy
            document_complexity = self._assess_overall_document_complexity(tables_with_scores)
            self.logger.logger.info(f"📊 Document complexity assessed as: {document_complexity}")
            
            if document_complexity == 'complex':
                # Use aggressive extraction for complex documents
                all_tables = await self._extract_from_complex_document(tables_with_scores, options)
            else:
                # Use standard extraction for simple documents
                all_tables = await self._extract_from_standard_document(tables_with_scores, options)
        
        # Fallback: extract from pages if no pre-extracted tables
        if not all_tables:
            self.logger.logger.info("No pre-extracted tables found, falling back to page-based extraction")
            for page_num in range(processed_doc.num_pages):
                try:
                    page_tables = await self._extract_tables_from_page(
                        processed_doc, page_num, options
                    )
                    all_tables.extend(page_tables)
                    
                    self.logger.logger.info(
                        f"Page {page_num}: extracted {len(page_tables)} tables"
                    )
                    
                except Exception as e:
                    self.logger.logger.error(
                        f"Failed to extract tables from page {page_num}: {e}"
                    )
                    continue
        
        return all_tables

    def _assess_overall_document_complexity(self, tables_with_scores) -> str:
        """Assess overall document complexity."""
        if not tables_with_scores:
            return 'standard'
        
        complexity_indicators = 0
        
        # Check table count
        if len(tables_with_scores) > 5:
            complexity_indicators += 1
        
        # Check header diversity
        all_headers = []
        for table_data, _ in tables_with_scores:
            headers = table_data.get('headers', [])
            all_headers.extend(headers)
        
        if len(set(all_headers)) > 15:  # Many unique headers
            complexity_indicators += 1
        
        # Check row count variation
        row_counts = [len(table_data.get('rows', [])) for table_data, _ in tables_with_scores]
        if len(set(row_counts)) > 3:  # High variation in table sizes
            complexity_indicators += 1
        
        return 'complex' if complexity_indicators >= 2 else 'standard'

    async def _extract_from_complex_document(self, tables_with_scores, options) -> List[Dict[str, Any]]:
        """Aggressive extraction strategy for complex documents."""
        all_tables = []
        
        # ✅ PROGRESSIVE: Try multiple threshold strategies
        progressive_thresholds = [0.7, 0.5, 0.3, 0.1, 0.05]  # Very aggressive
        
        for threshold in progressive_thresholds:
            candidate_tables = []
            
            for table_data, confidence in tables_with_scores:
                if confidence >= threshold:
                    # ✅ ENHANCED: Additional validation for complex docs
                    if self._is_meaningful_complex_table(table_data):
                        formatted_table = self._format_table_for_pipeline(table_data, confidence, threshold)
                        candidate_tables.append(formatted_table)
            
            if candidate_tables:
                all_tables.extend(candidate_tables)
                self.logger.logger.info(f"✅ COMPLEX DOC: Found {len(candidate_tables)} tables with threshold {threshold}")
                break  # Use first successful threshold
        
        return all_tables

    def _is_meaningful_complex_table(self, table_data: Dict[str, Any]) -> bool:
        """Check if table is meaningful for complex documents."""
        headers = table_data.get('headers', [])
        rows = table_data.get('rows', [])
        
        # Very lenient criteria for complex documents
        has_content = len(headers) > 0 or len(rows) > 0
        has_meaningful_size = (len(headers) * len(rows)) >= 1  # At least 1 cell
        
        return has_content and has_meaningful_size

    def _format_table_for_pipeline(self, table_data: Dict[str, Any], confidence: float, threshold: float) -> Dict[str, Any]:
        """Format table data for pipeline output."""
        return {
            "table_id": table_data.get('table_index', 0),
            "headers": table_data.get('headers', []),
            "rows": table_data.get('rows', []),
            "cells": table_data.get('cells', []),
            "columns": table_data.get('columns', []),
            "metadata": table_data.get('metadata', {}),
            "confidence": confidence,
            "extraction_method": "docling_complex",
            "complex_threshold": threshold,
            "row_count": table_data.get('row_count', 0),
            "column_count": table_data.get('column_count', 0),
            "page_number": table_data.get('page_number', 0)
        }

    async def _extract_from_standard_document(self, tables_with_scores, options) -> List[Dict[str, Any]]:
        """Standard extraction strategy (existing logic)."""
        all_tables = []
        
        # Apply confidence filtering and format the extracted tables
        for table_data, table_confidence in tables_with_scores:
            if table_confidence >= options.confidence_threshold:
                # Format for pipeline output
                formatted_table = {
                    "table_id": table_data.get('table_index', 0),
                    "headers": table_data.get('headers', []),
                    "rows": table_data.get('rows', []),
                    "cells": table_data.get('cells', []),
                    "columns": table_data.get('columns', []),
                    "metadata": table_data.get('metadata', {}),
                    "confidence": table_confidence,
                    "extraction_method": "docling",
                    "row_count": table_data.get('row_count', 0),
                    "column_count": table_data.get('column_count', 0),
                    "page_number": table_data.get('page_number', 0)
                }
                all_tables.append(formatted_table)
                
                self.logger.logger.info(
                    f"Added table {table_data.get('table_index', 0)}: {len(table_data.get('rows', []))} rows, confidence: {table_confidence:.2f}"
                )
        
        # If no tables passed the threshold, try progressively lower thresholds
        if not all_tables and tables_with_scores:
            self.logger.logger.warning(f"No tables found with confidence threshold {options.confidence_threshold}")
            self.logger.logger.info("🔍 Trying adaptive threshold strategy...")
            
            # Try progressively lower thresholds
            adaptive_thresholds = [0.5, 0.3, 0.2, 0.1]
            
            for threshold in adaptive_thresholds:
                candidate_tables = []
                for table_data, table_confidence in tables_with_scores:
                    if table_confidence >= threshold:
                        formatted_table = {
                            "table_id": table_data.get('table_index', 0),
                            "headers": table_data.get('headers', []),
                            "rows": table_data.get('rows', []),
                            "cells": table_data.get('cells', []),
                            "columns": table_data.get('columns', []),
                            "metadata": table_data.get('metadata', {}),
                            "confidence": table_confidence,
                            "extraction_method": "docling_adaptive",
                            "adaptive_threshold": threshold,
                            "row_count": table_data.get('row_count', 0),
                            "column_count": table_data.get('column_count', 0),
                            "page_number": table_data.get('page_number', 0)
                        }
                        candidate_tables.append(formatted_table)
                
                if candidate_tables:
                    all_tables.extend(candidate_tables)
                    self.logger.logger.info(f"✅ Found {len(candidate_tables)} tables with adaptive threshold {threshold}")
                    break
        
        return all_tables
    
    async def _extract_tables_from_page(
        self,
        processed_doc: ProcessedDocument,
        page_num: int,
        options: ExtractionOptions
    ) -> List[Dict[str, Any]]:
        """Extract tables from a specific page."""
        page_tables = []
        
        try:
            # Get page images
            if processed_doc.raw_images and page_num < len(processed_doc.raw_images):
                page_image = processed_doc.raw_images[page_num]
            else:
                # Extract page image from document
                page_images = await self.document_processor.extract_images_from_pages(
                    processed_doc
                )
                if page_num < len(page_images):
                    page_image = page_images[page_num]
                else:
                    self.logger.logger.warning(f"No image available for page {page_num}")
                    return page_tables
            
            # Use TableFormer for end-to-end processing
            detected_tables = await self.tableformer.process_table_end_to_end(page_image)
            
            for i, table_info in enumerate(detected_tables):
                # Skip tables with low confidence
                if (table_info.get('detection_confidence', 0) < 
                    options.confidence_threshold):
                    continue
                
                # Extract text from cells if OCR is enabled
                if options.enable_ocr and self.ocr_engine:
                    table_info = await self._extract_text_from_table(
                        page_image, table_info
                    )
                
                # Add page and document metadata
                table_info.update({
                    'page_number': page_num,
                    'table_index': i,
                    'document_path': processed_doc.document_path,
                    'extraction_timestamp': time.time()
                })
                
                page_tables.append(table_info)
                
                # Limit number of tables per page
                if len(page_tables) >= options.max_tables_per_page:
                    break
            
        except Exception as e:
            self.logger.logger.error(f"Table extraction from page {page_num} failed: {e}")
            raise
        
        return page_tables
    
    async def _link_multipage_tables(
        self, 
        tables: List[Dict[str, Any]], 
        processed_doc: ProcessedDocument
    ) -> List[Dict[str, Any]]:
        """Link tables that span multiple pages."""
        try:
            self.logger.logger.info(f"🔗 Starting multipage linking with {len(tables)} tables")
            
            # **IMPROVED: Don't skip multipage processing for single page documents**
            # Even single page documents can have multiple tables that should be merged
            # The multipage handler can handle both multipage and single-page table merging
            
            # Group tables by page
            page_tables = {}
            for table in tables:
                page_num = table.get('page_number', 0)
                if page_num not in page_tables:
                    page_tables[page_num] = []
                page_tables[page_num].append(table)
            
            self.logger.logger.info(f"📄 Tables grouped by page: {list(page_tables.keys())}")
            for page_num, page_table_list in page_tables.items():
                self.logger.logger.info(f"   Page {page_num}: {len(page_table_list)} tables")
            
            # **IMPROVED: Always use multipage handler for table merging**
            # Even if all tables are on the same page, the multipage handler can merge them
            # based on header similarity and data patterns
            
            # Convert to list format expected by multipage handler
            max_page = max(page_tables.keys()) if page_tables else 0
            page_tables_list = [page_tables.get(i, []) for i in range(max_page + 1)]
            
            self.logger.logger.info(f"📋 Page tables list: {len(page_tables_list)} pages")
            
            # Link multipage tables using the multipage handler
            linked_tables = await self.multipage_handler.link_multipage_tables(page_tables_list)
            
            self.logger.logger.info(f"🔗 Multipage linking: {len(tables)} → {len(linked_tables)} tables")
            return linked_tables
            
        except Exception as e:
            self.logger.logger.error(f"Multipage linking failed: {e}")
            return tables
    
    async def _process_financial_tables(
        self, 
        tables: List[Dict[str, Any]], 
        options: ExtractionOptions
    ) -> List[Dict[str, Any]]:
        """Process tables with financial document specialization."""
        try:
            processed_tables = []
            
            for table in tables:
                # Apply financial processing
                financial_table = await self.financial_processor.process_financial_table(table)
                processed_tables.append(financial_table)
            
            self.logger.logger.info(f"Financial processing completed for {len(processed_tables)} tables")
            return processed_tables
            
        except Exception as e:
            self.logger.logger.error(f"Financial processing failed: {e}")
            return tables
    
    async def _merge_sequential_tables(self, tables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge tables that are sequential continuations of each other, respecting page order."""
        if len(tables) <= 1:
            return tables
        
        try:
            self.logger.logger.info(f"🔗 Starting sequential table merging: {len(tables)} tables")
            
            # Sort tables by page number and position within page
            sorted_tables = sorted(tables, key=lambda t: (
                t.get('page_number', 0),
                t.get('metadata', {}).get('table_index', 0)
            ))
            
            self.logger.logger.info(f"📋 Tables sorted by page order:")
            for i, table in enumerate(sorted_tables):
                page_num = table.get('page_number', 0)
                table_idx = table.get('metadata', {}).get('table_index', 0)
                headers = table.get('headers', [])
                row_count = len(table.get('rows', []))
                self.logger.logger.info(f"   {i}: Page {page_num}, Table {table_idx}, Headers: {headers[:3]}..., Rows: {row_count}")
            
            merged_tables = []
            current_table_group = []
            
            for i, table in enumerate(sorted_tables):
                if not current_table_group:
                    # Start a new group
                    current_table_group = [table]
                    self.logger.logger.info(f"🔍 Starting new table group with table from page {table.get('page_number', 0)}")
                    continue
                
                # Check if this table is a sequential continuation of the current group
                is_continuation = await self._is_sequential_continuation(current_table_group, table)
                
                self.logger.logger.info(f"🔍 Table from page {table.get('page_number', 0)}: continuation = {is_continuation}")
                
                if is_continuation:
                    # Add to current group
                    current_table_group.append(table)
                    self.logger.logger.info(f"✅ Added table from page {table.get('page_number', 0)} to current group (now {len(current_table_group)} tables)")
                else:
                    # Finalize current group and start new one
                    if len(current_table_group) > 1:
                        merged_table = await self._merge_table_group(current_table_group)
                        merged_tables.append(merged_table)
                        self.logger.logger.info(f"🔗 MERGED: {len(current_table_group)} sequential tables into 1")
                    else:
                        merged_tables.append(current_table_group[0])
                        self.logger.logger.info(f"📋 Added single table from page {current_table_group[0].get('page_number', 0)}")
                    
                    # Start new group with current table
                    current_table_group = [table]
                    self.logger.logger.info(f"🔍 Starting new table group with table from page {table.get('page_number', 0)}")
            
            # Handle the last group
            if current_table_group:
                if len(current_table_group) > 1:
                    merged_table = await self._merge_table_group(current_table_group)
                    merged_tables.append(merged_table)
                    self.logger.logger.info(f"🔗 MERGED: {len(current_table_group)} sequential tables into 1 (final group)")
                else:
                    merged_tables.append(current_table_group[0])
                    self.logger.logger.info(f"📋 Added single table from page {current_table_group[0].get('page_number', 0)} (final)")
            
            # **NEW: Final consolidation step - merge tables with identical headers**
            self.logger.logger.info(f"🔗 Starting final consolidation of {len(merged_tables)} tables")
            final_tables = await self._consolidate_identical_headers(merged_tables)
            
            # **HOTFIX: Force merge tables with identical headers regardless of metadata issues**
            if len(final_tables) > 1:
                self.logger.logger.info(f"🔗 HOTFIX: Checking for tables with identical headers (metadata-agnostic)")
                header_groups = {}
                for table in final_tables:
                    headers = table.get('headers', [])
                    if headers:
                        key = "|".join(sorted([h.lower().strip() for h in headers if h.strip()]))
                        if key not in header_groups:
                            header_groups[key] = []
                        header_groups[key].append(table)
                
                # Merge groups with multiple tables (identical headers)
                truly_final = []
                for group in header_groups.values():
                    if len(group) > 1:
                        self.logger.logger.info(f"🔗 HOTFIX: Merging {len(group)} tables with identical headers")
                        merged = await self._merge_table_group(group)
                        merged['name'] = f"HOTFIX Merged Table ({len(group)} sources)"
                        truly_final.append(merged)
                    else:
                        truly_final.extend(group)
                
                final_tables = truly_final
                self.logger.logger.info(f"🔗 HOTFIX: Final consolidation completed: {len(merged_tables)} → {len(final_tables)} tables")
            
            self.logger.logger.info(f"📊 SEQUENTIAL MERGING + CONSOLIDATION: {len(tables)} → {len(final_tables)} tables")
            return final_tables
            
        except Exception as e:
            self.logger.logger.error(f"Error in sequential table merging: {e}")
            return tables
    
    async def _consolidate_identical_headers(self, tables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Final consolidation step: merge tables with identical headers."""
        if len(tables) <= 1:
            return tables
        
        try:
            self.logger.logger.info(f"🔗 Consolidating {len(tables)} tables with identical headers")
            
            # Group tables by header similarity - more robust approach
            header_groups = {}
            
            for table in tables:
                headers = table.get('headers', [])
                if not headers:
                    continue
                
                # **IMPROVED: More robust header key creation**
                # Normalize headers: lowercase, strip whitespace, remove empty strings, sort
                normalized_headers = [h.lower().strip() for h in headers if h.strip()]
                if not normalized_headers:
                    continue
                
                # Create a normalized header key that's metadata-agnostic
                header_key = "|".join(sorted(normalized_headers))
                
                if header_key not in header_groups:
                    header_groups[header_key] = []
                header_groups[header_key].append(table)
            
            # Log header grouping results
            self.logger.logger.info(f"🔗 Header grouping results:")
            for header_key, group in header_groups.items():
                header_sample = header_key.split("|")[:3]  # Show first 3 headers
                self.logger.logger.info(f"   Group '{'|'.join(header_sample)}...': {len(group)} tables")
            
            # Merge tables within each header group
            consolidated_tables = []
            
            for header_key, table_group in header_groups.items():
                if len(table_group) == 1:
                    # Single table, no merging needed
                    consolidated_tables.append(table_group[0])
                    header_sample = header_key.split("|")[:3]
                    self.logger.logger.info(f"📋 Single table with headers: {'|'.join(header_sample)}... ({len(table_group[0].get('headers', []))} columns)")
                else:
                    # Multiple tables with identical headers, merge them
                    header_sample = header_key.split("|")[:3]
                    self.logger.logger.info(f"🔗 Consolidating {len(table_group)} tables with identical headers: {'|'.join(header_sample)}...")
                    merged_table = await self._merge_table_group(table_group)
                    merged_table['name'] = f"Consolidated Table ({len(table_group)} sources)"
                    consolidated_tables.append(merged_table)
            
            self.logger.logger.info(f"🔗 Consolidation completed: {len(tables)} → {len(consolidated_tables)} tables")
            return consolidated_tables
            
        except Exception as e:
            self.logger.logger.error(f"Error in header consolidation: {e}")
            return tables
    
    def _normalize_header_key(self, headers: List[str]) -> str:
        """Create a normalized key for header comparison."""
        if not headers:
            return ""
        
        # Normalize headers: lowercase, strip whitespace, remove empty strings
        normalized = [str(h).lower().strip() for h in headers if str(h).strip()]
        
        # Sort to ensure consistent ordering regardless of original order
        normalized.sort()
        
        # Join with a separator to create a unique key
        return "|".join(normalized)
    
    async def _is_sequential_continuation(
        self, 
        current_group: List[Dict[str, Any]], 
        candidate_table: Dict[str, Any]
    ) -> bool:
        """Check if candidate table is a sequential continuation of the current group."""
        
        if not current_group:
            return False
        
        # Get the last table in the current group
        last_table = current_group[-1]
        
        # **IMPROVED: Handle missing/invalid metadata gracefully**
        last_page = last_table.get('page_number', 0)
        candidate_page = candidate_table.get('page_number', 0)
        
        # Check header similarity first (most important indicator)
        last_headers = last_table.get('headers', [])
        candidate_headers = candidate_table.get('headers', [])
        
        # **NEW: Check for identical headers first (strongest continuation indicator)**
        if self._headers_are_identical(last_headers, candidate_headers):
            self.logger.logger.info(f"✅ Identical headers detected - strong continuation indicator")
            # For identical headers, be very permissive with page gaps
            if last_page == 0 and candidate_page == 0:
                # Both tables have invalid metadata, but identical headers - likely continuation
                self.logger.logger.info(f"✅ Both tables have invalid metadata but identical headers - treating as continuation")
                return True
            elif last_page == 0 or candidate_page == 0:
                # One table has invalid metadata, but identical headers - likely continuation
                self.logger.logger.info(f"✅ One table has invalid metadata but identical headers - treating as continuation")
                return True
            else:
                # Both have valid metadata, allow larger page gaps for identical headers
                page_gap = candidate_page - last_page
                if page_gap <= 3:  # Allow up to 3 page gap for identical headers
                    return True
                else:
                    self.logger.logger.info(f"⚠️ Page gap too large even for identical headers: {page_gap} pages")
                    return False
        
        # **FALLBACK: If metadata is invalid, rely heavily on header similarity**
        if last_page == 0 or candidate_page == 0:
            self.logger.logger.info(f"⚠️ Invalid metadata detected - relying on header similarity")
            similarity = self._calculate_header_similarity(last_headers, candidate_headers)
            if similarity >= 0.9:  # Very high similarity threshold for invalid metadata
                self.logger.logger.info(f"✅ High header similarity ({similarity:.3f}) with invalid metadata - treating as continuation")
                return True
        
        # **STANDARD: Check page sequence for valid metadata**
        page_gap = candidate_page - last_page
        if page_gap < 0:
            self.logger.logger.info(f"❌ Page regression: {last_page} → {candidate_page}")
            return False
        
        # **IMPROVED: Check if candidate headers look like data (strong continuation indicator)**
        if self._headers_look_like_data(candidate_headers, last_headers):
            self.logger.logger.info(f"✅ Candidate headers look like data - likely continuation")
            # For data-like headers, be more restrictive with page gaps
            if page_gap <= 1:
                return True
            else:
                self.logger.logger.info(f"⚠️ Page gap too large for data-like headers: {page_gap} pages")
                return False
        
        # Check header similarity for non-identical headers
        similarity = self._calculate_header_similarity(last_headers, candidate_headers)
        
        if similarity >= 0.8:  # High similarity
            self.logger.logger.info(f"✅ High header similarity ({similarity:.3f}) - likely continuation")
            # For high similarity, allow moderate page gaps
            if page_gap <= 2:
                return True
            else:
                self.logger.logger.info(f"⚠️ Page gap too large for high similarity: {page_gap} pages")
                return False
        elif similarity >= 0.6:  # Medium similarity
            # Additional checks for medium similarity
            if self._has_similar_structure(last_table, candidate_table):
                self.logger.logger.info(f"✅ Medium similarity with similar structure - likely continuation")
                # For medium similarity, be more restrictive
                if page_gap <= 1:
                    return True
                else:
                    self.logger.logger.info(f"⚠️ Page gap too large for medium similarity: {page_gap} pages")
                    return False
        
        self.logger.logger.info(f"❌ Not a continuation (similarity: {similarity:.3f}, page gap: {page_gap})")
        return False
    
    def _headers_are_identical(self, headers1: List[str], headers2: List[str]) -> bool:
        """Check if two header lists are identical (case-insensitive, ignoring whitespace)."""
        if not headers1 or not headers2:
            return False
        
        if len(headers1) != len(headers2):
            return False
        
        # Normalize headers for comparison
        normalized1 = [str(h).lower().strip() for h in headers1 if str(h).strip()]
        normalized2 = [str(h).lower().strip() for h in headers2 if str(h).strip()]
        
        # Check if all headers match exactly
        return normalized1 == normalized2
    
    def _has_similar_structure(self, table1: Dict[str, Any], table2: Dict[str, Any]) -> bool:
        """Check if two tables have similar structure."""
        
        # Compare column counts
        cols1 = table1.get('column_count', len(table1.get('headers', [])))
        cols2 = table2.get('column_count', len(table2.get('headers', [])))
        
        if abs(cols1 - cols2) > 1:
            return False
        
        # Compare row patterns
        rows1 = table1.get('rows', [])
        rows2 = table2.get('rows', [])
        
        if not rows1 or not rows2:
            return True  # If one has no rows, assume similar structure
        
        # Check if the data patterns are similar
        return self._has_similar_content_pattern(rows2, table1)
    
    def _has_similar_content_pattern(self, candidate_rows: List[List[str]], reference_table: Dict[str, Any]) -> bool:
        """Check if candidate rows have similar content patterns to the reference table."""
        
        if not candidate_rows or not reference_table:
            return False
        
        reference_rows = reference_table.get('rows', [])
        if not reference_rows:
            return False
        
        # Learn patterns from reference table
        column_patterns = self._learn_column_patterns(reference_rows)
        
        # Check if candidate rows match learned patterns
        pattern_matches = 0
        total_checks = 0
        
        for row in candidate_rows[:3]:  # Check first 3 rows
            row_matches = 0
            row_checks = 0
            
            for i, cell in enumerate(row):
                if i >= len(column_patterns):
                    break
                
                cell_str = str(cell).strip()
                column_pattern = column_patterns[i]
                
                if self._matches_column_pattern(cell_str, column_pattern):
                    row_matches += 1
                row_checks += 1
            
            if row_checks > 0:
                pattern_matches += row_matches / row_checks
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
            # Remove common non-numeric characters for analysis
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
        
        # Calculate frequency of each special character
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
            
            # Check if length is within 2 standard deviations
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
                
                # Check if ratios are similar (within 0.3 tolerance)
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
        
        # Return True if at least 60% of checks pass
        return total_checks > 0 and (matches / total_checks) >= 0.6
    
    def _calculate_header_similarity(self, headers1: List[str], headers2: List[str]) -> float:
        """Calculate similarity between two header sets."""
        if not headers1 or not headers2:
            return 0.0
        
        # **IMPROVED: Handle different column counts**
        # If column counts are very different, it's likely not the same table
        if abs(len(headers1) - len(headers2)) > 2:
            return 0.0
        
        # Use the shorter header list as reference to avoid index errors
        min_len = min(len(headers1), len(headers2))
        matches = 0
        
        for i in range(min_len):
            h1_clean = str(headers1[i]).lower().strip()
            h2_clean = str(headers2[i]).lower().strip()
            
            # Exact match
            if h1_clean == h2_clean:
                matches += 1
            # Partial match for similar terms
            elif h1_clean in h2_clean or h2_clean in h1_clean:
                matches += 0.8
            # **NEW: Check for common financial header variations**
            elif self._are_headers_semantically_similar(h1_clean, h2_clean):
                matches += 0.7
        
        # Calculate similarity based on the shorter header list
        similarity = matches / min_len
        
        # **NEW: Bonus for same column count**
        if len(headers1) == len(headers2):
            similarity += 0.1
        
        return min(similarity, 1.0)
    
    def _are_headers_semantically_similar(self, header1: str, header2: str) -> bool:
        """Check if two headers are semantically similar (same meaning, different wording)."""
        # Common financial header variations
        header_variations = {
            'billing group': ['billing', 'group', 'company', 'organization'],
            'group id': ['id', 'group id', 'company id', 'account id'],
            'group state': ['state', 'group state', 'location', 'region'],
            'premium': ['premium', 'amount', 'billing amount', 'total premium'],
            'current month subscribers': ['subscribers', 'current subscribers', 'monthly subscribers'],
            'prior month': ['prior', 'previous', 'prior month', 'previous month'],
            'subscriber adjustments': ['adjustments', 'subscriber adjustments', 'changes'],
            'total subscribers': ['total', 'total subscribers', 'subscriber total'],
            'rate': ['rate', 'commission rate', 'rate per subscriber'],
            'commission due': ['commission', 'due', 'commission due', 'amount due']
        }
        
        # Check if headers are in the same variation group
        for key, variations in header_variations.items():
            if header1 in variations and header2 in variations:
                return True
            if header1 == key and header2 in variations:
                return True
            if header2 == key and header1 in variations:
                return True
        
        return False
    
    async def _merge_table_group(self, table_group: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge a group of tables with similar headers into one table."""
        if not table_group:
            return {}
        
        if len(table_group) == 1:
            return table_group[0]
        
        # Find the table with the best/most complete headers
        best_table = self._find_best_header_table(table_group)
        merged_table = best_table.copy()
        base_headers = merged_table.get('headers', [])
        all_rows = list(merged_table.get('rows', []))
        
        # Merge rows from all other tables  
        for table in table_group:
            if table == best_table:
                continue  # Skip the base table
                
            table_headers = table.get('headers', [])
            table_rows = table.get('rows', [])
            
            # **IMPROVED: Better handling of continuation tables**
            # If this table has headers as first row, treat first row as data
            if self._headers_look_like_data(table_headers, base_headers):
                # The "headers" are actually data, so include them as first row
                data_rows = [table_headers] + table_rows
            else:
                # Filter out header-like rows and metadata rows, but be more permissive for continuation data
                data_rows = []
                for row in table_rows:
                    # **IMPROVED: Don't filter out rows that might be continuation data**
                    if not self._is_header_like_row(row, base_headers) or self._is_continuation_data_row(row):
                        data_rows.append(row)
            
            # Align columns to match base headers
            aligned_rows = self._align_rows_to_headers(data_rows, base_headers)
            all_rows.extend(aligned_rows)
        
        # Update the merged table
        merged_table['headers'] = base_headers  # Ensure consistent headers
        merged_table['rows'] = all_rows
        merged_table['row_count'] = len(all_rows)
        if 'metadata' in merged_table:
            merged_table['metadata']['merged_from'] = len(table_group)
        merged_table['name'] = f"Merged Table ({len(table_group)} sources)"
        
        return merged_table
    
    def _find_best_header_table(self, table_group: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Find the table with the best headers (most columns and proper header structure)."""
        best_table = table_group[0]
        best_score = 0
        
        for table in table_group:
            headers = table.get('headers', [])
            score = 0
            
            # Score based on number of columns
            score += len(headers)
            
            # Score based on header quality (financial terms, proper structure)
            for header in headers:
                header_lower = str(header).lower()
                if any(term in header_lower for term in ['group', 'billing', 'premium', 'commission', 'rate', 'subscriber']):
                    score += 2
                if 'due' in header_lower or 'amount' in header_lower:
                    score += 3
            
            # Penalty for headers that look like data
            if self._headers_look_like_data(headers, None):
                score -= 10
                
            if score > best_score:
                best_score = score
                best_table = table
        
        return best_table
    
    def _headers_look_like_data(self, headers: List[str], reference_headers: List[str] = None) -> bool:
        """Check if headers actually look like data rows."""
        if not headers:
            return False
        
        # Check for patterns that suggest these are data, not headers
        data_indicators = 0
        header_indicators = 0  # Counter for header-like patterns
        
        for header in headers:
            header_str = str(header).strip()
            
            # **IMPROVED: More comprehensive data pattern detection**
            
            # Company names, IDs, state codes, dollar amounts indicate data
            if any(pattern in header_str for pattern in ['LLC', 'Inc', 'Corp', 'UT', '$']):
                data_indicators += 1
            
            # State codes (2 letters)  
            if len(header_str) == 2 and header_str.isupper():
                data_indicators += 1
                
            # Numbers that look like subscriber counts
            if header_str.isdigit() and 1 <= int(header_str) <= 100:
                data_indicators += 1
            
            # **NEW: Additional financial data patterns**
            # Currency amounts ($X,XXX.XX pattern)
            if '$' in header_str and any(c.isdigit() for c in header_str):
                data_indicators += 1
            
            # Rate patterns (X.XX/subscriber)
            if '/subscriber' in header_str.lower() or '/month' in header_str.lower():
                data_indicators += 1
            
            # Company name patterns (multiple words, mixed case)
            if len(header_str.split()) >= 2 and not header_str.isupper() and not header_str.islower():
                data_indicators += 1
            
            # ID patterns (alphanumeric codes like UT123456)
            if len(header_str) >= 6 and any(c.isdigit() for c in header_str) and any(c.isalpha() for c in header_str):
                data_indicators += 1
            
            # **NEW: Header-like pattern detection (negative indicators)**
            # Common financial header words
            header_words = ['billing', 'group', 'premium', 'commission', 'rate', 'subscriber', 'total', 'due', 'current', 'prior', 'adjustment', 'month', 'amount']
            if any(word in header_str.lower() for word in header_words):
                header_indicators += 1
            
            # Headers are often shorter and more generic
            if len(header_str) <= 25 and header_str.islower():
                header_indicators += 1
            
            # Headers often have consistent case patterns
            if header_str.islower() or header_str.istitle():
                header_indicators += 1
        
        # **IMPROVED: More sophisticated scoring**
        # If we have strong header indicators, reduce the data score
        if header_indicators > 0:
            data_indicators = max(0, data_indicators - header_indicators)
        
        # **IMPROVED: More lenient threshold for financial documents**
        # If more than 40% of headers look like data, they probably are data
        threshold = 0.4 if len(headers) >= 5 else 0.5
        
        result = data_indicators >= len(headers) * threshold
        
        if result:
            self.logger.logger.info(f"🔍 Headers look like data: {data_indicators}/{len(headers)} indicators (threshold: {threshold:.1f})")
            self.logger.logger.info(f"   Sample headers: {headers[:3]}...")
        
        return result
    
    def _align_rows_to_headers(self, rows: List[List[str]], target_headers: List[str]) -> List[List[str]]:
        """Align rows to match the target header structure."""
        aligned_rows = []
        target_col_count = len(target_headers)
        
        for row in rows:
            # Ensure row has the right number of columns
            aligned_row = row[:target_col_count] if len(row) > target_col_count else row
            
            # Pad with empty strings if row is too short
            while len(aligned_row) < target_col_count:
                aligned_row.append('')
            
            aligned_rows.append(aligned_row)
        
        return aligned_rows
    
    def _is_continuation_data_row(self, row: List[str]) -> bool:
        """Check if a row contains continuation data that should be preserved."""
        if not row:
            return False
        
        row_text = ' '.join(str(cell).lower().strip() for cell in row if cell)
        
        # Look for continuation indicators
        continuation_indicators = [
            'continued', 'continued next page', 'anat goldstein continued',
            'total commissions', 'total medical premium', 'total dental premium',
            'total vision premium', 'total paid commissions'
        ]
        
        for indicator in continuation_indicators:
            if indicator in row_text:
                return True
        
        # Look for data patterns that suggest this is continuation data
        # Check if row contains financial data (numbers, currency symbols)
        has_financial_data = any(
            re.search(r'\$[\d,]+\.?\d*', str(cell)) or 
            re.search(r'\d+\.?\d*%', str(cell)) or
            re.search(r'\d{4,}', str(cell))  # Long numbers (like group numbers)
            for cell in row if cell
        )
        
        if has_financial_data:
            return True
        
        return False
    
    def _is_header_like_row(self, row: List[str], headers: List[str]) -> bool:
        """Check if a row looks like headers (to avoid duplicating headers in merged table)."""
        if not row or not headers:
            return False
        
        row_text = ' '.join(str(cell).lower().strip() for cell in row)
        header_text = ' '.join(str(header).lower().strip() for header in headers)
        
        # Check for high similarity with headers
        if len(row_text) > 0 and len(header_text) > 0:
            # Simple similarity check
            common_words = set(row_text.split()) & set(header_text.split())
            total_words = set(row_text.split()) | set(header_text.split())
            
            if total_words and len(common_words) / len(total_words) > 0.6:
                return True
        
        return False
    
    async def _extract_text_from_table(
        self,
        image,
        table_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract text from table cells using OCR."""
        if not self.ocr_engine and not self.advanced_ocr_engine:
            return table_info
        
        try:
            cells = table_info.get('cells', [])
            
            for cell in cells:
                bbox = cell.get('bbox')
                if bbox:
                    # Use advanced OCR if available
                    if self.advanced_ocr_engine:
                        ocr_result = await self.advanced_ocr_engine.extract_text_ensemble(image, bbox)
                        cell['text'] = ocr_result.text
                        cell['ocr_confidence'] = ocr_result.confidence
                        cell['ocr_engine'] = ocr_result.engine
                    else:
                        # Fallback to basic OCR
                        text = await self.ocr_engine.extract_text_from_cell(image, bbox)
                        cell['text'] = text
            
            table_info['cells'] = cells
            
        except Exception as e:
            self.logger.logger.error(f"OCR text extraction failed: {e}")
        
        return table_info
    
    async def _postprocess_tables(
        self,
        tables: List[Dict[str, Any]],
        options: ExtractionOptions
    ) -> List[Dict[str, Any]]:
        """Post-process extracted tables."""
        processed_tables = []
        
        for table in tables:
            try:
                # Clean and validate table data
                cleaned_table = self._clean_table_data(table)
                
                # Apply quality checks
                if options.enable_quality_checks:
                    quality_score = self._assess_table_quality(cleaned_table)
                    cleaned_table['quality_score'] = quality_score
                    
                    # Skip low-quality tables
                    if quality_score < 0.3:
                        self.logger.logger.warning(
                            f"Skipping low-quality table (score: {quality_score:.2f})"
                        )
                        continue
                
                processed_tables.append(cleaned_table)
                
            except Exception as e:
                self.logger.logger.error(f"Table post-processing failed: {e}")
                continue
        
        return processed_tables
    
    def _clean_table_data(self, table: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and normalize table data."""
        cleaned_table = table.copy()
        
        # Clean cell text
        cells = cleaned_table.get('cells', [])
        for cell in cells:
            if 'text' in cell:
                # Remove extra whitespace and normalize
                cell['text'] = ' '.join(cell['text'].split())
                
                # Remove special characters if needed
                # cell['text'] = re.sub(r'[^\w\s.-]', '', cell['text'])
        
        # Ensure required fields exist
        if 'structure' not in cleaned_table:
            cleaned_table['structure'] = {
                'rows': 0,
                'columns': 0,
                'confidence': 0.0
            }
        
        return cleaned_table
    
    def _assess_table_quality(self, table: Dict[str, Any]) -> float:
        """Intelligently assess table quality using adaptive algorithms."""
        
        # Use intelligent metadata if available
        intelligent_metadata = table.get('intelligent_metadata', {})
        if intelligent_metadata:
            # Use the intelligent confidence score
            confidence_score = intelligent_metadata.get('confidence_score', 0.0)
            processing_insights = intelligent_metadata.get('processing_insights', {})
            
            # Combine intelligent factors
            processing_quality = processing_insights.get('processing_quality', 0.5)
            data_consistency = processing_insights.get('data_consistency', 0.5)
            structure_coherence = processing_insights.get('structure_coherence', 0.5)
            
            # Weighted intelligent quality score
            intelligent_quality = (
                confidence_score * 0.4 +
                processing_quality * 0.3 +
                data_consistency * 0.2 +
                structure_coherence * 0.1
            )
            
            return min(1.0, intelligent_quality)
        
        # Fallback: intelligent assessment without metadata
        return self._assess_table_quality_fallback(table)

    def _assess_table_quality_fallback(self, table: Dict[str, Any]) -> float:
        """Fallback intelligent quality assessment"""
        quality_factors = []
        
        # Assess content richness
        content_richness = self._assess_content_richness(table)
        quality_factors.append(content_richness * 0.3)
        
        # Assess structural integrity
        structural_integrity = self._assess_structural_integrity(table)
        quality_factors.append(structural_integrity * 0.3)
        
        # Assess data coherence
        data_coherence = self._assess_data_coherence(table)
        quality_factors.append(data_coherence * 0.2)
        
        # Assess semantic completeness
        semantic_completeness = self._assess_semantic_completeness(table)
        quality_factors.append(semantic_completeness * 0.2)
        
        return sum(quality_factors)

    def _assess_content_richness(self, table: Dict[str, Any]) -> float:
        """Assess richness of table content"""
        cells = table.get('cells', [])
        if not cells:
            return 0.0
        
        non_empty_cells = sum(1 for cell in cells if cell.get('text', '').strip())
        content_ratio = non_empty_cells / len(cells)
        
        # Bonus for diverse content types
        content_types = set()
        for cell in cells:
            text = cell.get('text', '').strip()
            if re.search(r'[\d.,]', text):
                content_types.add('numeric')
            if re.search(r'[\$€£¥%]', text):
                content_types.add('financial')
            if re.match(r'^[a-zA-Z\s]+$', text):
                content_types.add('text')
        
        diversity_bonus = len(content_types) * 0.1
        return min(1.0, content_ratio + diversity_bonus)

    def _assess_structural_integrity(self, table: Dict[str, Any]) -> float:
        """Assess structural integrity of table"""
        headers = table.get('headers', [])
        rows = table.get('rows', [])
        
        integrity_score = 0.0
        
        # Check header quality
        if headers:
            non_empty_headers = sum(1 for h in headers if str(h).strip())
            header_ratio = non_empty_headers / len(headers)
            integrity_score += header_ratio * 0.4
        
        # Check row consistency
        if rows and headers:
            consistent_rows = sum(1 for row in rows if len(row) == len(headers))
            consistency_ratio = consistent_rows / len(rows)
            integrity_score += consistency_ratio * 0.4
        
        # Check size appropriateness
        table_size = len(headers) * len(rows) if headers and rows else 0
        if 6 <= table_size <= 500:  # Reasonable table size
            integrity_score += 0.2
        
        return min(1.0, integrity_score)

    def _assess_data_coherence(self, table: Dict[str, Any]) -> float:
        """Assess coherence of data within table"""
        cells = table.get('cells', [])
        if not cells:
            return 0.0
        
        # Group cells by column
        columns = {}
        for cell in cells:
            col = cell.get('column', 0)
            if col not in columns:
                columns[col] = []
            columns[col].append(cell.get('text', ''))
        
        # Assess column coherence
        coherence_scores = []
        for col_data in columns.values():
            if col_data:
                coherence = self._assess_column_coherence(col_data)
                coherence_scores.append(coherence)
        
        return sum(coherence_scores) / len(coherence_scores) if coherence_scores else 0.0

    def _assess_column_coherence(self, column_data: List[str]) -> float:
        """Assess coherence within a single column"""
        if not column_data:
            return 0.0
        
        # Check for consistent data patterns
        numeric_count = sum(1 for data in column_data if re.search(r'\d', data))
        text_count = sum(1 for data in column_data if re.match(r'^[a-zA-Z\s]+$', data))
        
        total_items = len(column_data)
        
        # High coherence if most items follow same pattern
        if numeric_count > total_items * 0.8:
            return 0.9  # Mostly numeric
        elif text_count > total_items * 0.8:
            return 0.8  # Mostly text
        elif numeric_count + text_count > total_items * 0.8:
            return 0.7  # Mixed but consistent
        else:
            return 0.5  # Mixed patterns

    def _assess_semantic_completeness(self, table: Dict[str, Any]) -> float:
        """Assess semantic completeness of table"""
        headers = table.get('headers', [])
        if not headers:
            return 0.0
        
        # Look for semantic indicators in headers
        semantic_indicators = 0
        for header in headers:
            header_lower = str(header).lower().strip()
            if any(term in header_lower for term in ['name', 'id', 'date', 'amount', 'total', 'type']):
                semantic_indicators += 1
        
        semantic_ratio = semantic_indicators / len(headers)
        return min(1.0, semantic_ratio)
    
    def _generate_metadata(
        self,
        processed_doc: ProcessedDocument,
        options: ExtractionOptions
    ) -> Dict[str, Any]:
        """Generate metadata for extraction result."""
        return {
            'document_format': processed_doc.format.value,
            'num_pages': processed_doc.num_pages,
            'extraction_options': options.__dict__,
            'pipeline_version': '1.0.0',
            'models_used': {
                'document_processor': 'docling-1.20.0',
                'table_detection': 'tableformer-custom',
                'advanced_tableformer': 'microsoft-table-transformer' if self.advanced_tableformer else None,
                'ocr_engine': self.config.models.ocr_engine if options.enable_ocr else None,
                'advanced_ocr': 'ensemble-ocr' if self.advanced_ocr_engine else None,
                'multipage_handler': 'advanced-linking' if options.enable_multipage else None,
                'financial_processor': 'financial-specialized' if options.enable_financial_processing else None
            },
            'processing_config': {
                'confidence_threshold': options.confidence_threshold,
                'max_image_size': self.config.processing.max_image_size,
                'device': self.config.models.device
            }
        }
    
    def _calculate_confidence_scores(self, tables: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate overall confidence scores."""
        if not tables:
            return {'overall': 0.0}
        
        detection_scores = [
            table.get('detection_confidence', 0.0) for table in tables
        ]
        structure_scores = [
            table.get('structure_confidence', 0.0) for table in tables
        ]
        quality_scores = [
            table.get('quality_score', 0.0) for table in tables
        ]
        
        return {
            'overall': sum(detection_scores) / len(detection_scores),
            'detection': sum(detection_scores) / len(detection_scores),
            'structure': sum(structure_scores) / len(structure_scores),
            'quality': sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        }
    
    def _update_statistics(self, result: TableExtractionResult):
        """Update pipeline statistics."""
        self.stats['total_documents_processed'] += 1
        self.stats['total_tables_extracted'] += len(result.tables)
        
        # Update average processing time
        current_avg = self.stats['average_processing_time']
        total_docs = self.stats['total_documents_processed']
        
        self.stats['average_processing_time'] = (
            (current_avg * (total_docs - 1) + result.processing_time) / total_docs
        )
        
        # Update success rate
        if not result.errors:
            success_count = self.stats.get('successful_extractions', 0) + 1
            self.stats['successful_extractions'] = success_count
            self.stats['success_rate'] = success_count / total_docs
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        return self.stats.copy()
    
    async def extract_tables_batch(
        self,
        document_paths: List[Union[str, Path]],
        options: Optional[ExtractionOptions] = None
    ) -> List[TableExtractionResult]:
        """Extract tables from multiple documents."""
        results = []
        
        for doc_path in document_paths:
            try:
                result = await self.extract_tables(doc_path, options)
                results.append(result)
                
            except Exception as e:
                self.logger.logger.error(f"Batch processing failed for {doc_path}: {e}")
                error_result = TableExtractionResult(
                    document_path=str(doc_path),
                    errors=[str(e)]
                )
                results.append(error_result)
        
        return results

    async def _extract_table_complex(self, table, table_index: int, document_path: str) -> Optional[Dict[str, Any]]:
        """Extract table using complex structure analysis."""
        try:
            # Use the complex extraction method
            from ..core.table_extractor import TableExtractor
            extractor = TableExtractor(self.logger)
            
            # Try the complex extraction method directly
            headers, rows = extractor._extract_complex_table_structure(table)
            
            if headers and rows:
                # Create table data structure
                table_data = {
                    "headers": headers,
                    "rows": rows,
                    "cells": extractor._create_cells_from_headers_and_rows(headers, rows),
                    "columns": [{"name": header, "index": i} for i, header in enumerate(headers)],
                    "footers": [],
                    "metadata": extractor._extract_table_metadata(table, table_index, document_path),
                    "row_count": len(rows),
                    "column_count": len(headers),
                    "table_index": table_index,
                    "extractor": "ComplexTableExtractor"
                }
                return table_data
            
            return None
            
        except Exception as e:
            self.logger.logger.error(f"Complex extraction failed: {e}")
            return None
    
    def _calculate_table_confidence(self, table_data: Dict[str, Any]) -> float:
        """Calculate confidence score for a table based on its structure and content."""
        try:
            confidence = 0.0
            
            # Base confidence from structure
            headers = table_data.get('headers', [])
            rows = table_data.get('rows', [])
            
            if headers and rows:
                # Good structure
                confidence += 0.4
                
                # Check header quality
                meaningful_headers = sum(1 for h in headers if len(str(h).strip()) > 2)
                if meaningful_headers >= len(headers) * 0.8:
                    confidence += 0.2
                
                # Check data quality
                if len(rows) >= 1:
                    confidence += 0.2
                    
                    # Check for data diversity
                    all_cells = []
                    for row in rows[:5]:  # Sample first 5 rows
                        all_cells.extend([str(cell).strip() for cell in row if cell])
                    
                    if all_cells:
                        unique_ratio = len(set(all_cells)) / len(all_cells)
                        if unique_ratio > 0.5:
                            confidence += 0.1
                
                # Check for financial table indicators
                header_text = ' '.join(str(h).lower() for h in headers)
                financial_terms = ['commission', 'premium', 'billed', 'group', 'client', 'total', 'amount']
                financial_matches = sum(1 for term in financial_terms if term in header_text)
                if financial_matches >= 2:
                    confidence += 0.1
            
            return min(1.0, confidence)
            
        except Exception as e:
            self.logger.logger.error(f"Error calculating table confidence: {e}")
            return 0.5  # Default confidence
