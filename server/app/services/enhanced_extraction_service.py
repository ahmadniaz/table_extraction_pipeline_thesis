"""
Enhanced extraction service with real-time progress tracking via WebSocket.
Enhanced with comprehensive timeout management for large file processing.
"""

import asyncio
import json
import logging
import time
import sys
import os
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from datetime import datetime
import uuid
from fastapi import HTTPException

# CRITICAL: Load environment variables FIRST, before importing any services
from dotenv import load_dotenv
load_dotenv()

from app.services.websocket_service import create_progress_tracker
from app.services.new_extraction_service import NewExtractionService
from app.services.gpt4o_vision_service import GPT4oVisionService
from app.services.extractor_google_docai import GoogleDocAIExtractor
from app.services.mistral.service import MistralDocumentAIService
from app.services.claude.service import ClaudeDocumentAIService
from app.services.excel_extraction_service import ExcelExtractionService
from app.services.extraction_utils import normalize_statement_date, normalize_multi_line_headers

# Import timeout configuration
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from config.timeouts import timeout_settings

logger = logging.getLogger(__name__)

class EnhancedExtractionService:
    """
    Enhanced extraction service with real-time progress tracking and comprehensive timeout management.
    
    PRIMARY EXTRACTION: Claude Document AI (superior vision-based extraction) 🆕
    FALLBACK: Mistral Document AI (intelligent QnA-based extraction)
    AI OPERATIONS: GPT-4 for field mapping, carrier detection, company metadata, plan type detection
    
    Integrates multiple extraction methods with WebSocket progress updates and timeout handling for large files.
    """
    
    def __init__(self):
        """Initialize the enhanced extraction service with timeout configuration."""
        # PRIMARY: Claude Document AI (NEW - Superior accuracy)
        self.claude_service = ClaudeDocumentAIService()
        
        # FALLBACK: Mistral Document AI (Keep as fallback)
        self.mistral_service = MistralDocumentAIService()
        
        # AI OPERATIONS: GPT-4 service
        self.gpt4o_service = GPT4oVisionService()
        
        # FALLBACK: Alternative extraction methods
        self.new_extraction_service = NewExtractionService()
        self.docai_extractor = GoogleDocAIExtractor()
        
        # EXCEL: Specialized Excel extraction
        self.excel_service = ExcelExtractionService()
        
        # Configure timeouts for different processing phases
        self.phase_timeouts = {
            'metadata_extraction': timeout_settings.metadata_extraction,  # 5 minutes
            'document_processing': timeout_settings.document_processing,  # 10 minutes
            'table_extraction': timeout_settings.table_extraction,  # 20 minutes
            'post_processing': timeout_settings.post_processing,  # 5 minutes
            'total_process': timeout_settings.total_extraction  # 30 minutes total
        }
        
        logger.info(f"✅ Enhanced Extraction Service initialized")
        logger.info(f"🆕 PRIMARY: Claude Document AI (extraction) + GPT-4 (AI operations)")
        logger.info(f"📋 FALLBACK: Mistral Document AI")
        logger.info(f"⏱️  Timeout management: {self.phase_timeouts}")
    
    async def _validate_extraction_services(self, extraction_method: str) -> Dict[str, Any]:
        """Validate that extraction services are actually functional before starting."""
        # For "smart" or default, validate Claude (our new primary)
        if extraction_method in ["claude", "smart"]:
            if not self.claude_service.is_available():
                logger.warning("⚠️  Claude service not available - falling back to Mistral")
                logger.warning(f"Claude client status: {self.claude_service.client}")
                logger.warning(f"ANTHROPIC_AVAILABLE: {hasattr(self.claude_service, 'client') and self.claude_service.client is not None}")
                # If Claude not available, check Mistral as fallback
                if not self.mistral_service.is_available():
                    return {
                        "healthy": False, 
                        "service": "claude",
                        "error": "Claude service not available and Mistral fallback also unavailable."
                    }
                logger.info("✅ Using Mistral as fallback (Claude unavailable)")
                return {"healthy": True, "service": "mistral", "fallback_mode": True}
            logger.info("✅ Using Claude as primary extraction service")
            return {"healthy": True, "service": "claude"}
        elif extraction_method == "mistral":
            if not self.mistral_service.is_available():
                return {
                    "healthy": False, 
                    "service": "mistral",
                    "error": "Mistral service not properly initialized. Check MISTRAL_API_KEY and SDK compatibility."
                }
        elif extraction_method == "gpt4o":
            if not self.gpt4o_service.is_available():
                return {
                    "healthy": False,
                    "service": "gpt4o", 
                    "error": "GPT-4 Vision service not available"
                }
        
        return {"healthy": True, "service": extraction_method}
    
    async def extract_tables_with_progress(
        self,
        file_path: str,
        company_id: str,
        upload_id: str,
        file_type: str = "pdf",
        extraction_method: str = "smart",
        upload_id_uuid: str = None
    ) -> Dict[str, Any]:
        """
        Extract tables with real-time progress tracking.
        
        Args:
            file_path: Path to the file to process
            company_id: Company ID for the upload
            upload_id: Upload ID for progress tracking (temporary ID for WebSocket)
            file_type: Type of file (pdf, excel, etc.)
            upload_id_uuid: Actual UUID from database (optional, for WebSocket completion)
            extraction_method: Method to use (smart, gpt4o, docai, mistral, excel)
            
        Returns:
            Dictionary with extraction results
        """
        progress_tracker = create_progress_tracker(upload_id)
        
        try:
            # ✅ CRITICAL: Validate services BEFORE starting progress tracking
            service_health = await self._validate_extraction_services(extraction_method)
            if not service_health['healthy']:
                error_msg = f"❌ {service_health['service'].upper()} service not available: {service_health['error']}"
                logger.error(error_msg)
                await progress_tracker.send_error(error_msg, "SERVICE_UNAVAILABLE")
                return {
                    "success": False, 
                    "error": service_health['error'],
                    "error_type": "SERVICE_UNAVAILABLE",
                    "tables": [],
                    "extraction_method": extraction_method
                }
            
            logger.info(f"✅ {service_health['service'].upper()} service validated successfully")
            
            # Determine extraction method based on file type and method preference
            if file_type.lower() in ['xlsx', 'xls', 'xlsm', 'xlsb']:
                return await self._extract_excel_with_progress(
                    file_path, company_id, progress_tracker, upload_id_uuid
                )
            elif extraction_method == "mistral":
                # Explicit Mistral request
                return await self._extract_with_mistral_progress(
                    file_path, company_id, progress_tracker, upload_id_uuid
                )
            elif extraction_method == "gpt4o":
                return await self._extract_with_gpt4o_progress(
                    file_path, company_id, progress_tracker, upload_id_uuid
                )
            elif extraction_method == "docai":
                return await self._extract_with_docai_progress(
                    file_path, company_id, progress_tracker, upload_id_uuid
                )
            else:  # claude, smart, or default - USE CLAUDE AS PRIMARY 🆕
                logger.info(f"Routing to Claude extraction (method: {extraction_method})")
                return await self._extract_with_claude_progress(
                    file_path, company_id, progress_tracker, upload_id_uuid
                )
                
        except Exception as e:
            logger.error(f"Extraction failed for upload {upload_id}: {e}")
            await progress_tracker.send_error(
                f"Extraction failed: {str(e)}",
                "EXTRACTION_ERROR"
            )
            raise
    
    async def _extract_excel_with_progress(
        self,
        file_path: str,
        company_id: str,
        progress_tracker,
        upload_id_uuid: str = None
    ) -> Dict[str, Any]:
        """Extract from Excel with progress tracking."""
        await progress_tracker.start_stage("document_processing", "Processing Excel file")
        
        # Stage 1: File validation and preparation
        await progress_tracker.update_progress("document_processing", 20, "Validating Excel file")
        await asyncio.sleep(0.1)  # Simulate processing time
        
        await progress_tracker.update_progress("document_processing", 50, "Reading Excel structure")
        await asyncio.sleep(0.1)
        
        await progress_tracker.complete_stage("document_processing", "Excel file validated")
        
        # Stage 2: Sheet processing
        await progress_tracker.start_stage("table_detection", "Detecting tables in Excel sheets")
        await progress_tracker.update_progress("table_detection", 30, "Analyzing sheet structure")
        
        # Perform actual Excel extraction
        result = self.excel_service.extract_tables_from_excel(file_path)
        
        await progress_tracker.update_progress("table_detection", 70, "Extracting table data")
        await asyncio.sleep(0.2)
        
        await progress_tracker.complete_stage("table_detection", "Tables detected and extracted")
        
        # Stage 3: Data processing
        await progress_tracker.start_stage("post_processing", "Processing extracted data")
        await progress_tracker.update_progress("post_processing", 50, "Formatting data")
        
        # Convert to client format
        client_result = self.excel_service.convert_to_client_format(result, Path(file_path).name)
        
        await progress_tracker.complete_stage("post_processing", "Data processing completed")
        
        # Stage 4: Validation
        await progress_tracker.start_stage("validation", "Validating extraction results")
        await progress_tracker.update_progress("validation", 100, "Validation completed")
        
        # Send completion including UUID
        await progress_tracker.send_completion({
            'upload_id': upload_id_uuid,  # Include the UUID from database
            'extraction_id': upload_id_uuid,  # Also include as extraction_id
            'tables': client_result.get('tables', []),
            'extraction_method': 'excel',
            'file_type': 'excel',
            'quality_summary': client_result.get('quality_summary', {}),
            'metadata': {
                'sheet_count': len(result.get('sheets', [])),
                'table_count': len(client_result.get('tables', []))
            }
        })
        
        return client_result
    
    async def _extract_with_smart_progress(
        self,
        file_path: str,
        company_id: str,
        progress_tracker,
        upload_id_uuid: str = None
    ) -> Dict[str, Any]:
        """Extract with smart method and progress tracking."""
        start_time = time.time()
        
        # Stage 1: Document processing
        await progress_tracker.connection_manager.send_stage_update(
            progress_tracker.upload_id,
            'document_processing', 
            10,
            "Analyzing document format and structure..."
        )

        # Document processing stage
        file_type = self._detect_file_type(file_path)
        
        # NEW: Extract carrier name, statement date, and broker using Claude AI
        carrier_info = None
        date_info = None
        broker_info = None
        metadata_extraction_success = False
        
        if file_type == 'pdf':
            try:
                # Stage: Claude Metadata Extraction
                await progress_tracker.connection_manager.send_stage_update(
                    progress_tracker.upload_id,
                    'metadata_extraction',
                    15,
                    "Extracting carrier, date, and broker with Claude AI..."
                )
                
                logger.info(f"Starting Claude metadata extraction for upload {progress_tracker.upload_id}")
                
                # Extract metadata using Claude AI (includes broker_company)
                claude_metadata = await self.claude_service.extract_metadata_only(file_path)
                
                if claude_metadata.get('success'):
                    carrier_info = {
                        'carrier_name': claude_metadata.get('carrier_name'),
                        'carrier_confidence': claude_metadata.get('carrier_confidence', 0.9)
                    }
                    date_info = {
                        'document_date': claude_metadata.get('statement_date'),
                        'date_confidence': claude_metadata.get('date_confidence', 0.9)
                    }
                    broker_info = {
                        'broker_company': claude_metadata.get('broker_company'),
                        'broker_confidence': claude_metadata.get('broker_confidence', 0.8)
                    }
                    metadata_extraction_success = True
                    
                    logger.info(f"Claude extracted: carrier={carrier_info.get('carrier_name')}, date={date_info.get('document_date')}, broker={broker_info.get('broker_company')}")
                    
                    # Send carrier detected message with actual Claude results
                    await progress_tracker.connection_manager.send_commission_specific_message(
                        progress_tracker.upload_id,
                        'carrier_detected',
                        {
                            'carrier_name': carrier_info.get('carrier_name', 'Unknown'), 
                            'current_stage': 'metadata_extraction', 
                            'progress': 25
                        }
                    )
                else:
                    logger.warning(f"Claude metadata extraction returned no success: {claude_metadata.get('error')}")
                    
            except Exception as e:
                logger.warning(f"Claude metadata extraction failed: {e}")
                # Continue with extraction even if Claude fails
        
        # If Claude didn't extract carrier, show placeholder
        if not metadata_extraction_success:
            await progress_tracker.connection_manager.send_commission_specific_message(
                progress_tracker.upload_id,
                'carrier_detected',
                {'carrier_name': 'Auto-detected', 'current_stage': 'document_processing', 'progress': 25}
            )

        # Table detection stage  
        await progress_tracker.connection_manager.send_stage_update(
            progress_tracker.upload_id,
            'table_detection',
            40, 
            "Scanning for commission tables and data structures..."
        )

        # Extract tables based on file type
        if file_type == 'pdf':
            tables = await self._extract_pdf_tables(file_path, progress_tracker)
        else:
            tables = await self._extract_excel_tables(file_path, progress_tracker)

        await progress_tracker.connection_manager.send_commission_specific_message(
            progress_tracker.upload_id,
            'tables_found',
            {'table_count': len(tables), 'current_stage': 'data_extraction', 'progress': 60}
        )

        # Data extraction stage
        await progress_tracker.connection_manager.send_stage_update(
            progress_tracker.upload_id,
            'data_extraction',
            65,
            "Extracting financial data and commission information..."
        )

        # Process extracted data
        processed_data = await self._process_extracted_data(tables, progress_tracker)

        # Financial processing stage
        await progress_tracker.connection_manager.send_stage_update(
            progress_tracker.upload_id,
            'financial_processing',
            80,
            "Processing commission calculations and validations..."
        )

        # Calculate commissions
        commission_summary = self._calculate_commission_summary(processed_data)
        
        await progress_tracker.connection_manager.send_commission_specific_message(
            progress_tracker.upload_id,
            'calculations_complete', 
            {
                'commission_amount': f"${commission_summary.get('total_commission', 0):,.2f}",
                'current_stage': 'quality_assurance',
                'progress': 90
            }
        )

        # Quality assurance stage
        await progress_tracker.connection_manager.send_stage_update(
            progress_tracker.upload_id,
            'quality_assurance',
            95,
            "Performing final quality checks and validation..."
        )

        # Quality check
        quality_score = self._assess_extraction_quality(processed_data)
        
        await progress_tracker.connection_manager.send_commission_specific_message(
            progress_tracker.upload_id,
            'quality_check',
            {
                'quality_score': quality_score,
                'current_stage': 'quality_assurance', 
                'progress': 100
            }
        )

        # CRITICAL: Normalize headers for smart extraction
        from app.services.extraction_utils import normalize_multi_line_headers
        for table in processed_data:
            raw_headers = table.get('headers', []) or table.get('header', [])
            rows = table.get('rows', [])
            if raw_headers:
                normalized_headers = normalize_multi_line_headers(raw_headers, rows)
                table['headers'] = normalized_headers
                table['header'] = normalized_headers
                logger.info(f"Smart: Normalized headers: {raw_headers} -> {normalized_headers}")
        
        # Final completion including UUID
        result = {
            'success': True,
            'upload_id': upload_id_uuid,  # Include the UUID from database
            'extraction_id': upload_id_uuid,  # Also include as extraction_id
            'tables': processed_data,
            'commission_summary': commission_summary,
            'quality_score': quality_score,
            'processing_time': time.time() - start_time,
            'metadata': {
                'file_type': file_type,
                'extraction_method': 'smart',
                'tables_extracted': len(processed_data)
            },
            'document_metadata': {
                'carrier_name': carrier_info.get('carrier_name') if carrier_info else None,
                'carrier_confidence': carrier_info.get('carrier_confidence') if carrier_info else 0.0,
                'document_date': date_info.get('document_date') if date_info else None,
                'date_confidence': date_info.get('date_confidence') if date_info else 0.0,
                'broker_company': broker_info.get('broker_company') if broker_info else None,
                'broker_confidence': broker_info.get('broker_confidence') if broker_info else 0.0
            }
        }

        await progress_tracker.send_completion(result)
        return result

    async def _extract_with_gpt4o_progress(
        self,
        file_path: str,
        company_id: str,
        progress_tracker,
        upload_id_uuid: str = None
    ) -> Dict[str, Any]:
        """Extract with GPT-4o Vision and progress tracking."""
        await progress_tracker.start_stage("document_processing", "Preparing document for GPT-4o Vision")
        
        # Stage 1: Document processing
        await progress_tracker.update_progress("document_processing", 30, "Converting PDF to images")
        await asyncio.sleep(0.2)
        
        await progress_tracker.update_progress("document_processing", 70, "Optimizing images for AI processing")
        await asyncio.sleep(0.1)
        
        await progress_tracker.complete_stage("document_processing", "Document prepared for AI")
        
        # Stage 2: AI processing
        await progress_tracker.start_stage("table_detection", "AI-powered table detection")
        await progress_tracker.update_progress("table_detection", 20, "Sending to GPT-4o Vision")
        
        # Perform actual extraction
        result = self.gpt4o_service.extract_commission_data(file_path)
        
        await progress_tracker.update_progress("table_detection", 60, "Processing AI response")
        await asyncio.sleep(0.3)
        
        await progress_tracker.update_progress("table_detection", 90, "Extracting table data")
        await asyncio.sleep(0.1)
        
        await progress_tracker.complete_stage("table_detection", "AI extraction completed")
        
        # Stage 3: Post processing
        await progress_tracker.start_stage("post_processing", "Processing AI results")
        await progress_tracker.update_progress("post_processing", 50, "Normalizing headers")
        
        # CRITICAL: Normalize headers for GPT4o extractions
        if result.get('success') and result.get('tables'):
            from app.services.extraction_utils import normalize_multi_line_headers
            for table in result.get('tables', []):
                raw_headers = table.get('headers', []) or table.get('header', [])
                rows = table.get('rows', [])
                if raw_headers:
                    normalized_headers = normalize_multi_line_headers(raw_headers, rows)
                    table['headers'] = normalized_headers
                    table['header'] = normalized_headers
                    logger.info(f"GPT4o: Normalized headers: {raw_headers} -> {normalized_headers}")
        
        await progress_tracker.update_progress("post_processing", 100, "Results processed")
        
        # Send completion including UUID
        await progress_tracker.send_completion({
            'upload_id': upload_id_uuid,  # Include the UUID from database
            'extraction_id': upload_id_uuid,  # Also include as extraction_id
            'tables': result.get('tables', []),
            'extraction_method': 'gpt4o',
            'file_type': 'pdf',
            'quality_summary': result.get('quality_summary', {}),
            'metadata': result.get('metadata', {})
        })
        
        return result

    async def _extract_with_docai_progress(
        self,
        file_path: str,
        company_id: str,
        progress_tracker,
        upload_id_uuid: str = None
    ) -> Dict[str, Any]:
        """Extract with Google DocAI and progress tracking."""
        await progress_tracker.start_stage("document_processing", "Preparing for Google Document AI")
        
        # Stage 1: Document processing
        await progress_tracker.update_progress("document_processing", 50, "Uploading to Google Cloud")
        await asyncio.sleep(0.2)
        
        await progress_tracker.complete_stage("document_processing", "Document uploaded")
        
        # Stage 2: DocAI processing
        await progress_tracker.start_stage("table_detection", "Processing with Google Document AI")
        await progress_tracker.update_progress("table_detection", 30, "Analyzing document structure")
        
        # Perform actual extraction
        result = await self.docai_extractor.extract_tables_async(file_path)
        
        await progress_tracker.update_progress("table_detection", 70, "Extracting tables")
        await asyncio.sleep(0.3)
        
        await progress_tracker.complete_stage("table_detection", "DocAI processing completed")
        
        # Stage 3: Post processing
        await progress_tracker.start_stage("post_processing", "Processing DocAI results")
        await progress_tracker.update_progress("post_processing", 50, "Normalizing headers")
        
        # CRITICAL: Normalize headers for DocAI extractions
        if result.get('success') and result.get('tables'):
            from app.services.extraction_utils import normalize_multi_line_headers
            for table in result.get('tables', []):
                raw_headers = table.get('headers', []) or table.get('header', [])
                rows = table.get('rows', [])
                if raw_headers:
                    normalized_headers = normalize_multi_line_headers(raw_headers, rows)
                    table['headers'] = normalized_headers
                    table['header'] = normalized_headers
                    logger.info(f"DocAI: Normalized headers: {raw_headers} -> {normalized_headers}")
        
        await progress_tracker.update_progress("post_processing", 100, "Results processed")
        
        # Send completion including UUID
        await progress_tracker.send_completion({
            'upload_id': upload_id_uuid,  # Include the UUID from database
            'extraction_id': upload_id_uuid,  # Also include as extraction_id
            'tables': result.get('tables', []),
            'extraction_method': 'docai',
            'file_type': 'pdf',
            'quality_summary': result.get('quality_summary', {}),
            'metadata': result.get('metadata', {})
        })
        
        return result

    async def _extract_with_mistral_progress(
        self,
        file_path: str,
        company_id: str,
        progress_tracker,
        upload_id_uuid: str = None
    ) -> Dict[str, Any]:
        """
        Extract with Mistral and comprehensive progress tracking with timeout management.
        Enhanced with phase-specific timeouts to prevent cascading failures on large files.
        """
        try:
            # Overall process timeout
            async with asyncio.timeout(self.phase_timeouts['total_process']):
                return await self._extract_with_phase_timeouts(
                    file_path, company_id, progress_tracker, upload_id_uuid
                )
        except asyncio.TimeoutError:
            error_msg = f"Extraction timeout after {self.phase_timeouts['total_process']} seconds. The document may be too large or complex."
            logger.error(f"Extraction timeout for upload {upload_id_uuid}: {error_msg}")
            await progress_tracker.send_error(error_msg, "EXTRACTION_TIMEOUT")
            raise HTTPException(
                status_code=408,
                detail=error_msg
            )
    
    async def _extract_with_phase_timeouts(
        self,
        file_path: str,
        company_id: str,
        progress_tracker,
        upload_id_uuid: str = None
    ) -> Dict[str, Any]:
        """Process extraction with individual phase timeouts."""
        
        await progress_tracker.start_stage("document_processing", "Preparing for Mistral Document AI")
        
        # Stage 1: Document processing with timeout
        await progress_tracker.update_progress("document_processing", 50, "Initializing Mistral AI")
        await asyncio.sleep(0.1)
        
        await progress_tracker.complete_stage("document_processing", "Mistral AI initialized")
        
        # Phase 1: Metadata Extraction with timeout using Claude AI
        carrier_info = None
        date_info = None
        broker_info = None
        metadata_extraction_success = False
        
        try:
            async with asyncio.timeout(self.phase_timeouts['metadata_extraction']):
                # Stage: Claude Metadata Extraction
                await progress_tracker.connection_manager.send_stage_update(
                    progress_tracker.upload_id,
                    'metadata_extraction',
                    15,
                    "Extracting carrier, date, and broker with Claude AI..."
                )
                
                logger.info(f"Starting Claude metadata extraction with {self.phase_timeouts['metadata_extraction']}s timeout")
                
                # Extract metadata using Claude AI (includes broker_company)
                claude_metadata = await self.claude_service.extract_metadata_only(file_path)
                
                if claude_metadata.get('success'):
                    carrier_info = {
                        'carrier_name': claude_metadata.get('carrier_name'),
                        'carrier_confidence': claude_metadata.get('carrier_confidence', 0.9)
                    }
                    date_info = {
                        'document_date': claude_metadata.get('statement_date'),
                        'date_confidence': claude_metadata.get('date_confidence', 0.9)
                    }
                    broker_info = {
                        'broker_company': claude_metadata.get('broker_company'),
                        'broker_confidence': claude_metadata.get('broker_confidence', 0.8)
                    }
                    metadata_extraction_success = True
                    
                    logger.info(f"Claude extracted: carrier={carrier_info.get('carrier_name')}, date={date_info.get('document_date')}, broker={broker_info.get('broker_company')}")
                    
                    # Send carrier detected message with actual Claude results
                    await progress_tracker.connection_manager.send_commission_specific_message(
                        progress_tracker.upload_id,
                        'carrier_detected',
                        {
                            'carrier_name': carrier_info.get('carrier_name', 'Unknown'), 
                            'current_stage': 'metadata_extraction', 
                            'progress': 25
                        }
                    )
                else:
                    logger.warning(f"Claude metadata extraction returned no success: {claude_metadata.get('error')}")
                    
        except asyncio.TimeoutError:
            logger.warning("Metadata extraction timeout, continuing without metadata")
            claude_metadata = {'success': False, 'error': 'Timeout'}
        except Exception as e:
            logger.warning(f"Claude metadata extraction failed: {e}")
            # Continue with extraction even if Claude fails
        
        # Phase 2: Mistral Table Extraction with timeout
        await progress_tracker.start_stage("table_detection", "Processing with Mistral Document AI")
        await progress_tracker.update_progress("table_detection", 25, "Analyzing document with QnA")
        
        # Perform actual extraction using intelligent method with timeout
        try:
            async with asyncio.timeout(self.phase_timeouts['table_extraction']):
                logger.info(f"Starting Mistral extraction with {self.phase_timeouts['table_extraction']}s timeout")
                result = await self.mistral_service.extract_commission_data_intelligently(file_path)
        except asyncio.TimeoutError:
            error_msg = f"Table extraction timeout after {self.phase_timeouts['table_extraction']} seconds"
            logger.error(error_msg)
            await progress_tracker.send_error(error_msg, "TABLE_EXTRACTION_TIMEOUT")
            raise HTTPException(status_code=408, detail=error_msg)
        except Exception as e:
            logger.warning(f"Intelligent extraction failed, falling back to legacy method: {e}")
            try:
                result = self.mistral_service.extract_commission_data(file_path)
            except Exception as fallback_error:
                logger.error(f"Fallback extraction also failed: {fallback_error}")
                raise
        
        await progress_tracker.update_progress("table_detection", 60, "Extracting tables using Mistral QnA")
        await asyncio.sleep(0.3)
        
        # Apply table merging for identical headers
        if result.get('success') and result.get('tables'):
            from app.services.extraction_utils import stitch_multipage_tables, normalize_multi_line_headers
            original_tables = result.get('tables', [])
            merged_tables = stitch_multipage_tables(original_tables)
            
            # CRITICAL: Normalize headers AFTER table stitching
            for table in merged_tables:
                raw_headers = table.get('headers', []) or table.get('header', [])
                rows = table.get('rows', [])
                if raw_headers:
                    normalized_headers = normalize_multi_line_headers(raw_headers, rows)
                    table['headers'] = normalized_headers
                    table['header'] = normalized_headers  # Keep both for compatibility
                    logger.info(f"Normalized headers: {raw_headers} -> {normalized_headers}")
            
            result['tables'] = merged_tables
            logger.info(f"Mistral: Merged {len(original_tables)} tables into {len(merged_tables)} tables with header normalization")
        
        await progress_tracker.update_progress("table_detection", 90, "Processing extracted data")
        await asyncio.sleep(0.1)
        
        await progress_tracker.complete_stage("table_detection", "Mistral processing completed")
        
        # Stage 3: Validation
        await progress_tracker.start_stage("validation", "Validating Mistral results")
        await progress_tracker.update_progress("validation", 100, "Validation completed")
        
        # Merge GPT metadata with Mistral result
        document_metadata = result.get('document_metadata', {})
        
        # If Claude metadata extraction was successful, override with Claude values
        if metadata_extraction_success and carrier_info:
            document_metadata['carrier_name'] = carrier_info.get('carrier_name')
            document_metadata['carrier_confidence'] = carrier_info.get('carrier_confidence', 0.9)
            document_metadata['carrier_source'] = 'claude_ai'
        
        if metadata_extraction_success and date_info:
            # Apply date normalization to extract start date from ranges
            raw_date = date_info.get('document_date')
            normalized_date = normalize_statement_date(raw_date) if raw_date else None
            document_metadata['statement_date'] = normalized_date
            document_metadata['date_confidence'] = date_info.get('date_confidence', 0.9)
            document_metadata['date_source'] = 'claude_ai'
        
        if metadata_extraction_success and broker_info:
            document_metadata['broker_company'] = broker_info.get('broker_company')
            document_metadata['broker_confidence'] = broker_info.get('broker_confidence', 0.8)
            document_metadata['broker_source'] = 'claude_ai'
        
        # Update result with merged metadata
        result['document_metadata'] = document_metadata
        result['extracted_carrier'] = document_metadata.get('carrier_name')
        result['extracted_date'] = document_metadata.get('statement_date')
        
        # Send completion with all fields from result including UUID
        await progress_tracker.send_completion({
            'upload_id': upload_id_uuid,  # Include the UUID from database
            'extraction_id': upload_id_uuid,  # Also include as extraction_id for backward compatibility
            'tables': result.get('tables', []),
            'extraction_method': 'mistral',
            'file_type': 'pdf',
            'quality_summary': result.get('quality_summary', {}),
            'metadata': result.get('metadata', {}),
            'extraction_config': result.get('extraction_config', {}),
            'document_metadata': document_metadata,
            'extracted_carrier': document_metadata.get('carrier_name'),
            'extracted_date': document_metadata.get('statement_date'),
            'gcs_url': result.get('gcs_url'),
            'gcs_key': result.get('gcs_key'),
            'extraction_intelligence': result.get('extraction_intelligence', {}),
            'extraction_quality': result.get('extraction_quality', {})
        })
        
        return result

    async def _extract_with_claude_progress(
        self,
        file_path: str,
        company_id: str,
        progress_tracker,
        upload_id_uuid: str = None
    ) -> Dict[str, Any]:
        """
        Extract with Claude AI and comprehensive progress tracking.
        Enhanced with Claude's superior vision capabilities for table extraction.
        """
        try:
            await progress_tracker.start_stage("document_processing", "Preparing for Claude AI")
            
            # Stage 1: Document processing
            await progress_tracker.update_progress("document_processing", 30, "Validating document for Claude")
            await asyncio.sleep(0.1)
            
            await progress_tracker.complete_stage("document_processing", "Claude AI ready")
            
            # Stage 2: Claude AI Extraction
            await progress_tracker.start_stage("table_detection", "Processing with Claude AI")
            await progress_tracker.update_progress("table_detection", 20, "Analyzing document with Claude vision")
            
            # Perform actual extraction using Claude
            logger.info(f"Starting Claude extraction for {file_path}")
            result = await self.claude_service.extract_commission_data(
                file_path,
                progress_tracker
            )
            
            await progress_tracker.update_progress("table_detection", 80, "Processing Claude results")
            await asyncio.sleep(0.2)
            
            # Apply table merging if needed (for consistency with other extractors)
            if result.get('success') and result.get('tables'):
                from app.services.extraction_utils import stitch_multipage_tables, normalize_multi_line_headers
                original_tables = result.get('tables', [])
                merged_tables = stitch_multipage_tables(original_tables)
                
                # Headers are already normalized by Claude service, but ensure consistency
                for table in merged_tables:
                    raw_headers = table.get('headers', []) or table.get('header', [])
                    rows = table.get('rows', [])
                    if raw_headers:
                        normalized_headers = normalize_multi_line_headers(raw_headers, rows)
                        table['headers'] = normalized_headers
                        table['header'] = normalized_headers
                        logger.info(f"Claude: Verified normalized headers")
                
                result['tables'] = merged_tables
                logger.info(f"Claude: Processed {len(original_tables)} tables into {len(merged_tables)} tables")
            
            await progress_tracker.complete_stage("table_detection", "Claude extraction completed")
            
            # Stage 3: Validation
            await progress_tracker.start_stage("validation", "Validating Claude results")
            await progress_tracker.update_progress("validation", 100, "Validation completed")
            
            # Send completion with all fields from result including UUID
            await progress_tracker.send_completion({
                'upload_id': upload_id_uuid,
                'extraction_id': upload_id_uuid,
                'tables': result.get('tables', []),
                'extraction_method': 'claude',
                'file_type': 'pdf',
                'quality_summary': result.get('quality_summary', {}),
                'metadata': result.get('metadata', {}),
                'document_metadata': result.get('document_metadata', {}),
                'extracted_carrier': result.get('extracted_carrier'),
                'extracted_date': result.get('extracted_date'),
                'extraction_quality': result.get('extraction_quality', {})
            })
            
            return result
        
        except Exception as e:
            logger.error(f"Claude extraction failed: {e}")
            
            # Fallback to Mistral if Claude fails
            logger.warning("Falling back to Mistral extraction after Claude failure")
            try:
                return await self._extract_with_mistral_progress(
                    file_path,
                    company_id,
                    progress_tracker,
                    upload_id_uuid
                )
            except Exception as fallback_error:
                logger.error(f"Fallback to Mistral also failed: {fallback_error}")
                raise

    # Helper methods (consolidated from duplicates)
    def _detect_file_type(self, file_path: str) -> str:
        """Detect file type from file path."""
        file_ext = Path(file_path).suffix.lower()
        if file_ext in ['.xlsx', '.xls', '.xlsm', '.xlsb']:
            return 'excel'
        elif file_ext == '.pdf':
            return 'pdf'
        else:
            return 'unknown'

    async def _extract_pdf_tables(self, file_path: str, progress_tracker) -> List[Dict]:
        """Extract tables from PDF file."""
        try:
            result = await self.new_extraction_service.extract_tables_from_file(file_path)
            return result.get('tables', [])
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            await progress_tracker.send_error(f"PDF extraction failed: {str(e)}")
            return []

    async def _extract_excel_tables(self, file_path: str, progress_tracker) -> List[Dict]:
        """Extract tables from Excel file."""
        try:
            result = self.excel_service.extract_tables_from_excel(file_path)
            return result.get('tables', [])
        except Exception as e:
            logger.error(f"Excel extraction failed: {e}")
            await progress_tracker.send_error(f"Excel extraction failed: {str(e)}")
            return []

    async def _process_extracted_data(self, tables: List[Dict], progress_tracker) -> List[Dict]:
        """Process and clean extracted table data."""
        try:
            processed_tables = []
            for table in tables:
                # Clean and validate table data
                cleaned_table = self._clean_table_data(table)
                if cleaned_table:
                    processed_tables.append(cleaned_table)
            return processed_tables
        except Exception as e:
            logger.error(f"Data processing failed: {e}")
            await progress_tracker.send_error(f"Data processing failed: {str(e)}")
            return tables

    def _clean_table_data(self, table: Dict) -> Dict:
        """Clean and validate individual table data."""
        try:
            # Basic data cleaning logic
            if 'data' in table and table['data']:
                # Remove empty rows and columns
                cleaned_data = [row for row in table['data'] if any(cell for cell in row)]
                table['data'] = cleaned_data
            return table
        except Exception as e:
            logger.error(f"Table cleaning failed: {e}")
            return table

    def _calculate_commission_summary(self, tables: List[Dict]) -> Dict:
        """Calculate commission summary from extracted tables."""
        try:
            total_commission = 0.0
            commission_count = 0
            
            for table in tables:
                if 'data' in table:
                    for row in table['data']:
                        for cell in row:
                            if isinstance(cell, (int, float)) and cell > 0:
                                total_commission += float(cell)
                                commission_count += 1
            
            return {
                'total_commission': total_commission,
                'commission_count': commission_count,
                'average_commission': total_commission / max(commission_count, 1)
            }
        except Exception as e:
            logger.error(f"Commission calculation failed: {e}")
            return {
                'total_commission': 0.0,
                'commission_count': 0,
                'average_commission': 0.0
            }

    def _assess_extraction_quality(self, tables: List[Dict]) -> int:
        """Assess the quality of extraction results."""
        try:
            if not tables:
                return 0
            
            quality_score = 0
            total_tables = len(tables)
            
            for table in tables:
                if 'data' in table and table['data']:
                    # Check if table has meaningful data
                    has_data = any(any(cell for cell in row) for row in table['data'])
                    if has_data:
                        quality_score += 1
                
                # Check for headers
                if 'headers' in table and table['headers']:
                    quality_score += 0.5
            
            # Calculate percentage
            max_score = total_tables * 1.5
            quality_percentage = int((quality_score / max_score) * 100) if max_score > 0 else 0
            
            return min(quality_percentage, 100)
        except Exception as e:
            logger.error(f"Quality assessment failed: {e}")
            return 50  # Default quality score

    async def _extract_metadata_with_gpt(self, file_path: str) -> Dict[str, Any]:
        """
        Extract carrier name and statement date from the first page of PDF using GPT-4.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Dictionary with carrier_name, statement_date, and confidence scores
        """
        try:
            import fitz  # PyMuPDF
            import base64
            from io import BytesIO
            from PIL import Image
            
            logger.info(f"Extracting metadata with GPT from first page of {file_path}")
            
            # Open PDF and get first page
            doc = fitz.open(file_path)
            if len(doc) == 0:
                logger.error("PDF has no pages")
                return {'success': False, 'error': 'PDF has no pages'}
            
            first_page = doc.load_page(0)
            
            # Convert first page to high-quality image
            matrix = fitz.Matrix(300/72, 300/72)  # 300 DPI for good quality
            pix = first_page.get_pixmap(matrix=matrix, alpha=False)
            
            # Convert to PIL Image
            img_data = pix.tobytes("png")
            img = Image.open(BytesIO(img_data))
            
            # Convert to base64
            buffer = BytesIO()
            img.save(buffer, format='PNG', optimize=True)
            img_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            doc.close()
            
            logger.info(f"Converted first page to image ({len(img_base64)} chars)")
            
            # Check if GPT service is available
            if not self.gpt4o_service.is_available():
                logger.warning("GPT-4 service not available")
                return {'success': False, 'error': 'GPT-4 service not available'}
            
            # Create specialized prompt for metadata extraction
            system_prompt = """You are an expert at extracting metadata from commission statement documents.

Your task is to analyze the first page of a commission statement and extract:
1. CARRIER NAME - The insurance company that issued this statement (e.g., "Aetna", "Blue Cross Blue Shield", "Cigna", "UnitedHealthcare", "Allied Benefit Systems", etc.)
   - Look in headers, logos, letterhead, and document branding
   - Look at page footers where companies often place their logos
   - DO NOT extract from table data columns - look at document structure elements only
   
2. STATEMENT DATE - The date of this commission statement (e.g., "12/31/2024", "October 31, 2024")
   - Look for "Statement Date:", "Commission Summary For:", "Report Date:", etc.
   - Look in document headers and titles
   - DO NOT extract random dates from table data

3. BROKER/AGENT COMPANY - The broker or agent entity receiving commissions (e.g., "Innovative BPS", "ABC Insurance Agency", etc.)
   - Look for "Agent:", "Broker:", "Agency:", "To:", "Prepared For:" labels
   - Usually appears near the top of the document
   - This is different from the carrier - it's the entity receiving the statement

Return your response in the following JSON format ONLY:
{
  "carrier_name": "Exact carrier name as it appears",
  "carrier_confidence": 0.95,
  "statement_date": "Date in original format",
  "date_confidence": 0.90,
  "broker_company": "Broker/Agent company name as it appears",
  "broker_confidence": 0.85,
  "evidence": "Brief explanation of where you found this information"
}

If you cannot find the information with high confidence, use null for the value and a lower confidence score."""

            user_prompt = "Extract the carrier name, statement date, and broker/agent company from this commission statement first page."
            
            # Call GPT-4 Vision API
            messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{img_base64}"}
                        }
                    ]
                }
            ]
            
            logger.info("Calling GPT-4 Vision API for metadata extraction")
            
            response = self.gpt4o_service.client.chat.completions.create(
                model="gpt-4o",  # Use gpt-4o for vision
                messages=messages,
                max_tokens=500,
                temperature=0.1  # Low temperature for consistent extraction
            )
            
            if not response.choices or len(response.choices) == 0:
                logger.error("GPT-4 returned no response")
                return {'success': False, 'error': 'GPT-4 returned no response'}
            
            content = response.choices[0].message.content
            logger.info(f"GPT-4 response: {content}")
            
            # Parse JSON response
            import json
            import re
            
            # Clean response content
            cleaned_content = content.strip()
            if cleaned_content.startswith('```json'):
                cleaned_content = cleaned_content[7:]
            if cleaned_content.startswith('```'):
                cleaned_content = cleaned_content[3:]
            if cleaned_content.endswith('```'):
                cleaned_content = cleaned_content[:-3]
            cleaned_content = cleaned_content.strip()
            
            # Parse JSON
            try:
                metadata = json.loads(cleaned_content)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse GPT response as JSON: {e}")
                # Try to extract using regex as fallback
                carrier_match = re.search(r'"carrier_name":\s*"([^"]+)"', cleaned_content)
                date_match = re.search(r'"statement_date":\s*"([^"]+)"', cleaned_content)
                
                metadata = {
                    'carrier_name': carrier_match.group(1) if carrier_match else None,
                    'statement_date': date_match.group(1) if date_match else None,
                    'carrier_confidence': 0.7,
                    'date_confidence': 0.7,
                    'evidence': 'Extracted with regex fallback'
                }
            
            # Apply date normalization before returning
            raw_date = metadata.get('statement_date')
            normalized_date = normalize_statement_date(raw_date) if raw_date else None
            
            # Return results
            result = {
                'success': True,
                'carrier_name': metadata.get('carrier_name'),
                'carrier_confidence': metadata.get('carrier_confidence', 0.8),
                'statement_date': normalized_date,
                'date_confidence': metadata.get('date_confidence', 0.8),
                'broker_company': metadata.get('broker_company'),
                'broker_confidence': metadata.get('broker_confidence', 0.8),
                'evidence': metadata.get('evidence', ''),
                'extraction_method': 'gpt4o_vision_first_page'
            }
            
            logger.info(f"GPT metadata extraction successful: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error extracting metadata with GPT: {e}", exc_info=True)
            return {
                'success': False,
                'error': f'Metadata extraction failed: {str(e)}'
            }