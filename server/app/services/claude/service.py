"""
Claude Document AI Service - Superior PDF Table Extraction

This service provides intelligent document extraction capabilities using Claude 3.5 Sonnet
or Claude 4 for commission statement processing with excellent accuracy.

Key Features:
- Multi-model support (Claude 3.5 Sonnet, Claude 4)
- Large file handling (up to 100 pages / 32MB)
- Vision-powered table extraction
- Structured output with quality assessment
- WebSocket progress tracking integration
- Comprehensive error handling and fallbacks
"""

import os
import logging
import time
import asyncio
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path

# Load environment variables BEFORE anything else
from dotenv import load_dotenv
load_dotenv()

try:
    from anthropic import Anthropic, AsyncAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logging.warning("Anthropic SDK not available. Install with: pip install anthropic")

from .models import (
    ClaudeExtractionResponse,
    ClaudeDocumentMetadata,
    ClaudeTableData,
    ClaudeQualityMetrics,
    ClaudeChunkMetadata
)
from .prompts import ClaudePrompts
from .utils import (
    ClaudePDFProcessor,
    ClaudeTokenEstimator,
    ClaudeResponseParser,
    ClaudeQualityAssessor,
    ClaudeErrorHandler
)

# Import existing utilities for compatibility
from app.services.extraction_utils import normalize_multi_line_headers, normalize_statement_date

logger = logging.getLogger(__name__)


class ClaudeDocumentAIService:
    """
    Claude Document AI Service for PDF Table Extraction
    
    This service uses Claude's superior vision and reasoning capabilities to extract
    tables and metadata from commission statements with high accuracy.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize Claude Document AI service
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        
        # Model configuration
        self.primary_model = os.getenv(
            'CLAUDE_MODEL_PRIMARY',
            'claude-sonnet-4-20250514'  # Latest Claude Sonnet 4 (May 2025)
        )
        self.fallback_model = os.getenv(
            'CLAUDE_MODEL_FALLBACK',
            'claude-sonnet-4-20250514'  # Use same as primary since old fallback is deprecated
        )
        
        # File limits
        self.max_file_size_mb = int(os.getenv('CLAUDE_MAX_FILE_SIZE', '32'))
        self.max_pages = int(os.getenv('CLAUDE_MAX_PAGES', '100'))
        
        # Timeout configuration
        self.timeout_seconds = int(os.getenv('CLAUDE_TIMEOUT_SECONDS', '300'))
        
        # Initialize API client
        self.client = None
        self.async_client = None
        self._initialize_client()
        
        # Initialize utility classes
        self.pdf_processor = ClaudePDFProcessor()
        self.token_estimator = ClaudeTokenEstimator()
        self.response_parser = ClaudeResponseParser()
        self.quality_assessor = ClaudeQualityAssessor()
        self.error_handler = ClaudeErrorHandler()
        self.prompts = ClaudePrompts()
        
        # Processing statistics
        self.stats = {
            'total_extractions': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'total_tokens_used': 0,
            'total_processing_time': 0.0
        }
        
        logger.info(f"✅ Claude Document AI Service initialized")
        logger.info(f"📋 Primary model: {self.primary_model}")
        logger.info(f"📋 Fallback model: {self.fallback_model}")
        logger.info(f"📏 Limits: {self.max_file_size_mb}MB, {self.max_pages} pages")
    
    def _initialize_client(self):
        """Initialize Claude API client"""
        try:
            if not ANTHROPIC_AVAILABLE:
                logger.error("❌ Anthropic SDK not available. Install with: pip install anthropic>=0.28.0")
                self.client = None
                self.async_client = None
                return
            
            api_key = os.getenv('CLAUDE_API_KEY')
            if not api_key:
                logger.error("❌ CLAUDE_API_KEY not set in environment variables")
                logger.error("Please set CLAUDE_API_KEY in your .env file")
                self.client = None
                self.async_client = None
                return
            
            # Log initialization attempt
            logger.info(f"🔄 Initializing Claude API client (SDK version: {ANTHROPIC_AVAILABLE})")
            logger.info(f"🔑 API Key found: {api_key[:15]}...")
            
            self.client = Anthropic(api_key=api_key)
            self.async_client = AsyncAnthropic(api_key=api_key)
            
            logger.info("✅ Claude API client initialized successfully")
            logger.info(f"📋 Client object: {type(self.client)}")
        except Exception as e:
            logger.error(f"❌ Error initializing Claude client: {e}")
            logger.exception("Full exception details:")
            self.client = None
            self.async_client = None
    
    def is_available(self) -> bool:
        """Check if Claude service is available"""
        return ANTHROPIC_AVAILABLE and self.client is not None
    
    async def extract_metadata_only(
        self,
        file_path: str
    ) -> Dict[str, Any]:
        """
        Extract only document metadata (carrier, date, broker) from PDF.
        Lightweight alternative to full extraction for metadata-only needs.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Dictionary with metadata extraction results
        """
        try:
            logger.info(f"🔍 Extracting metadata with Claude from: {file_path}")
            
            # Validate file
            validation = self._validate_file(file_path)
            if not validation['valid']:
                return {
                    'success': False,
                    'error': validation['error']
                }
            
            pdf_info = validation['pdf_info']
            
            # Encode PDF for metadata extraction
            pdf_base64 = self.pdf_processor.encode_pdf_to_base64(file_path)
            
            # Get metadata extraction prompt
            metadata_prompt = self.prompts.get_metadata_extraction_prompt()
            
            # Call Claude API
            extraction_result = await self._call_claude_api(
                pdf_base64,
                metadata_prompt,
                model=self.primary_model
            )
            
            # Parse response
            parsed_data = self.response_parser.parse_json_response(extraction_result['content'])
            
            if not parsed_data:
                return {
                    'success': False,
                    'error': 'Failed to parse Claude metadata response'
                }
            
            # Normalize statement date
            statement_date = parsed_data.get('statement_date')
            if statement_date:
                normalized_date = normalize_statement_date(statement_date)
                parsed_data['statement_date'] = normalized_date
            
            # Return metadata in standard format
            return {
                'success': True,
                'carrier_name': parsed_data.get('carrier_name'),
                'carrier_confidence': parsed_data.get('carrier_confidence', 0.9),
                'statement_date': parsed_data.get('statement_date'),
                'date_confidence': parsed_data.get('date_confidence', 0.9),
                'broker_company': parsed_data.get('broker_company'),
                'broker_confidence': parsed_data.get('broker_confidence', 0.8),
                'document_type': parsed_data.get('document_type', 'commission_statement'),
                'total_pages': pdf_info.get('page_count', 0),
                'extraction_method': 'claude_metadata',
                'evidence': parsed_data.get('evidence', 'Metadata extracted from document')
            }
            
        except Exception as e:
            logger.error(f"❌ Claude metadata extraction failed: {e}")
            return {
                'success': False,
                'error': f'Metadata extraction failed: {str(e)}'
            }
    
    async def extract_commission_data(
        self,
        file_path: str,
        progress_tracker = None
    ) -> Dict[str, Any]:
        """
        Main entry point for commission data extraction
        
        Args:
            file_path: Path to PDF file
            progress_tracker: Optional WebSocket progress tracker
            
        Returns:
            Dictionary with extraction results
        """
        start_time = time.time()
        self.stats['total_extractions'] += 1
        
        try:
            # Validate service availability
            if not self.is_available():
                raise ValueError("Claude service not available. Check API key and SDK installation.")
            
            # Validate file
            if progress_tracker:
                await progress_tracker.update_progress(
                    "document_processing",
                    10,
                    "Validating PDF file for Claude processing"
                )
            
            validation_result = self._validate_file(file_path)
            if not validation_result['valid']:
                raise ValueError(validation_result['error'])
            
            pdf_info = validation_result['pdf_info']
            
            # Determine processing strategy based on file size
            if pdf_info['is_large_file']:
                logger.info(f"Large file detected ({pdf_info['page_count']} pages, {pdf_info['file_size_mb']:.2f}MB)")
                result = await self._extract_large_file(file_path, pdf_info, progress_tracker)
            else:
                logger.info(f"Standard file ({pdf_info['page_count']} pages, {pdf_info['file_size_mb']:.2f}MB)")
                result = await self._extract_standard_file(file_path, pdf_info, progress_tracker)
            
            # Update statistics
            processing_time = time.time() - start_time
            self.stats['successful_extractions'] += 1
            self.stats['total_processing_time'] += processing_time
            
            logger.info(f"✅ Claude extraction completed in {processing_time:.2f}s")
            
            return result
        
        except Exception as e:
            self.stats['failed_extractions'] += 1
            processing_time = time.time() - start_time
            
            logger.error(f"❌ Claude extraction failed after {processing_time:.2f}s: {e}")
            
            return {
                'success': False,
                'error': str(e),
                'error_message': self.error_handler.format_error_message(e),
                'tables': [],
                'extraction_method': 'claude',
                'processing_time': processing_time
            }
    
    def _validate_file(self, file_path: str) -> Dict[str, Any]:
        """Validate file meets Claude's requirements"""
        try:
            # Check file exists
            if not os.path.exists(file_path):
                return {'valid': False, 'error': f'File not found: {file_path}'}
            
            # Get PDF info
            pdf_info = self.pdf_processor.get_pdf_info(file_path)
            
            if 'error' in pdf_info:
                return {'valid': False, 'error': pdf_info['error']}
            
            # Validate file size
            is_valid_size, size_error = self.pdf_processor.validate_pdf_size(
                file_path,
                self.max_file_size_mb
            )
            if not is_valid_size:
                return {'valid': False, 'error': size_error}
            
            # Validate page count
            is_valid_pages, pages_error = self.pdf_processor.validate_pdf_pages(
                file_path,
                self.max_pages
            )
            if not is_valid_pages:
                return {'valid': False, 'error': pages_error}
            
            return {'valid': True, 'pdf_info': pdf_info}
        
        except Exception as e:
            return {'valid': False, 'error': f'Validation error: {str(e)}'}
    
    async def _extract_standard_file(
        self,
        file_path: str,
        pdf_info: Dict[str, Any],
        progress_tracker = None
    ) -> Dict[str, Any]:
        """Extract data from standard-sized files (< 50 pages, < 20MB)"""
        try:
            # Stage 1: Prepare document
            if progress_tracker:
                await progress_tracker.update_progress(
                    "document_processing",
                    30,
                    "Encoding PDF for Claude AI"
                )
            
            pdf_base64 = self.pdf_processor.encode_pdf_to_base64(file_path)
            
            if progress_tracker:
                await progress_tracker.complete_stage(
                    "document_processing",
                    "Document prepared for Claude AI"
                )
            
            # Stage 2: Extract metadata and tables
            if progress_tracker:
                await progress_tracker.start_stage(
                    "table_detection",
                    "Analyzing document with Claude AI"
                )
                await progress_tracker.update_progress(
                    "table_detection",
                    20,
                    "Sending to Claude for analysis"
                )
            
            # Single API call for both metadata and tables (more efficient)
            extraction_result = await self._call_claude_api(
                pdf_base64,
                self.prompts.get_table_extraction_prompt(),
                model=self.primary_model
            )
            
            if progress_tracker:
                await progress_tracker.update_progress(
                    "table_detection",
                    70,
                    "Processing Claude response"
                )
            
            # Parse response
            parsed_data = self.response_parser.parse_json_response(extraction_result['content'])
            
            if not parsed_data:
                raise ValueError("Failed to parse Claude response as JSON")
            
            # Extract tables and metadata
            tables = parsed_data.get('tables', [])
            doc_metadata = parsed_data.get('document_metadata', {})
            
            # Normalize headers
            for table in tables:
                if 'headers' in table and 'rows' in table:
                    normalized_headers = normalize_multi_line_headers(
                        table['headers'],
                        table['rows']
                    )
                    table['headers'] = normalized_headers
            
            if progress_tracker:
                await progress_tracker.complete_stage(
                    "table_detection",
                    f"Extracted {len(tables)} tables with Claude AI"
                )
            
            # Stage 3: Quality assessment
            if progress_tracker:
                await progress_tracker.start_stage(
                    "validation",
                    "Assessing extraction quality"
                )
            
            quality_metrics = self.quality_assessor.assess_extraction_quality(
                tables,
                doc_metadata
            )
            
            if progress_tracker:
                await progress_tracker.complete_stage(
                    "validation",
                    f"Quality score: {quality_metrics.get('quality_grade', 'N/A')}"
                )
            
            # Format response
            result = self._format_response(
                tables=tables,
                doc_metadata=doc_metadata,
                pdf_info=pdf_info,
                token_usage=extraction_result.get('usage', {}),
                quality_metrics=quality_metrics
            )
            
            return result
        
        except Exception as e:
            logger.error(f"Error in standard file extraction: {e}")
            
            # Try fallback model if primary fails
            if hasattr(e, '__str__') and 'model' not in str(e).lower():
                logger.info("Attempting extraction with fallback model...")
                try:
                    return await self._extract_with_fallback(
                        file_path,
                        pdf_info,
                        progress_tracker
                    )
                except Exception as fallback_error:
                    logger.error(f"Fallback extraction also failed: {fallback_error}")
            
            raise
    
    async def _extract_large_file(
        self,
        file_path: str,
        pdf_info: Dict[str, Any],
        progress_tracker = None
    ) -> Dict[str, Any]:
        """Extract data from large files by chunking"""
        try:
            if progress_tracker:
                await progress_tracker.update_progress(
                    "document_processing",
                    20,
                    "Processing large document - preparing chunks"
                )
            
            # Split into manageable chunks
            chunks = self.pdf_processor.chunk_large_pdf(file_path, max_pages_per_chunk=40)
            
            logger.info(f"Split document into {len(chunks)} chunks")
            
            all_tables = []
            doc_metadata = {}
            
            # Process each chunk
            for chunk_idx, chunk_info in enumerate(chunks):
                if progress_tracker:
                    progress = 20 + (chunk_idx / len(chunks)) * 60
                    await progress_tracker.update_progress(
                        "table_detection",
                        int(progress),
                        f"Processing chunk {chunk_idx + 1}/{len(chunks)}"
                    )
                
                # Extract this chunk
                chunk_result = await self._extract_chunk(
                    file_path,
                    chunk_info,
                    progress_tracker
                )
                
                # Accumulate results
                if chunk_result.get('tables'):
                    all_tables.extend(chunk_result['tables'])
                
                # Use metadata from first chunk
                if chunk_idx == 0 and chunk_result.get('document_metadata'):
                    doc_metadata = chunk_result['document_metadata']
            
            # Merge tables that span across chunks
            merged_tables = self._merge_split_tables(all_tables)
            
            # Quality assessment
            quality_metrics = self.quality_assessor.assess_extraction_quality(
                merged_tables,
                doc_metadata
            )
            
            # Format response
            result = self._format_response(
                tables=merged_tables,
                doc_metadata=doc_metadata,
                pdf_info=pdf_info,
                token_usage={'note': 'Chunked processing - multiple API calls'},
                quality_metrics=quality_metrics
            )
            
            return result
        
        except Exception as e:
            logger.error(f"Error in large file extraction: {e}")
            raise
    
    async def _extract_chunk(
        self,
        file_path: str,
        chunk_info: Dict[str, Any],
        progress_tracker = None
    ) -> Dict[str, Any]:
        """Extract data from a specific chunk of the document"""
        try:
            # For now, encode entire PDF (Claude handles page ranges internally)
            # In production, you might want to extract specific pages to temp file
            pdf_base64 = self.pdf_processor.encode_pdf_to_base64(file_path)
            
            # Create chunk-specific prompt
            chunk_prompt = self.prompts.get_chunk_extraction_prompt(
                f"{chunk_info['chunk_index'] + 1}/{chunk_info['total_chunks']}"
            )
            
            # Call Claude API
            extraction_result = await self._call_claude_api(
                pdf_base64,
                chunk_prompt,
                model=self.primary_model
            )
            
            # Parse response
            parsed_data = self.response_parser.parse_json_response(
                extraction_result['content']
            )
            
            return parsed_data or {'tables': [], 'document_metadata': {}}
        
        except Exception as e:
            logger.error(f"Error extracting chunk: {e}")
            return {'tables': [], 'document_metadata': {}}
    
    async def _extract_with_fallback(
        self,
        file_path: str,
        pdf_info: Dict[str, Any],
        progress_tracker = None
    ) -> Dict[str, Any]:
        """Attempt extraction with fallback model"""
        logger.info(f"Attempting extraction with fallback model: {self.fallback_model}")
        
        if progress_tracker:
            await progress_tracker.update_progress(
                "table_detection",
                10,
                "Retrying with alternative Claude model"
            )
        
        # Similar to standard extraction but with fallback model
        pdf_base64 = self.pdf_processor.encode_pdf_to_base64(file_path)
        
        extraction_result = await self._call_claude_api(
            pdf_base64,
            self.prompts.get_table_extraction_prompt(),
            model=self.fallback_model
        )
        
        parsed_data = self.response_parser.parse_json_response(
            extraction_result['content']
        )
        
        if not parsed_data:
            raise ValueError("Fallback extraction also failed to parse response")
        
        tables = parsed_data.get('tables', [])
        doc_metadata = parsed_data.get('document_metadata', {})
        
        # Normalize headers
        for table in tables:
            if 'headers' in table and 'rows' in table:
                normalized_headers = normalize_multi_line_headers(
                    table['headers'],
                    table['rows']
                )
                table['headers'] = normalized_headers
        
        quality_metrics = self.quality_assessor.assess_extraction_quality(
            tables,
            doc_metadata
        )
        
        return self._format_response(
            tables=tables,
            doc_metadata=doc_metadata,
            pdf_info=pdf_info,
            token_usage=extraction_result.get('usage', {}),
            quality_metrics=quality_metrics
        )
    
    async def _call_claude_api(
        self,
        pdf_base64: str,
        prompt: str,
        model: str,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Call Claude API with retry logic
        
        Args:
            pdf_base64: Base64-encoded PDF
            prompt: Extraction prompt
            model: Claude model to use
            max_retries: Maximum retry attempts
            
        Returns:
            API response with content and usage
        """
        for attempt in range(max_retries):
            try:
                # Prepare messages
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "document",
                                "source": {
                                    "type": "base64",
                                    "media_type": "application/pdf",
                                    "data": pdf_base64
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
                
                # Call API
                logger.info(f"Calling Claude API with model: {model} (attempt {attempt + 1}/{max_retries})")
                
                response = await asyncio.wait_for(
                    self.async_client.messages.create(
                        model=model,
                        max_tokens=16000,  # Large enough for comprehensive extraction
                        temperature=0.1,  # Low temperature for consistency
                        system=self.prompts.get_system_prompt(),
                        messages=messages
                    ),
                    timeout=self.timeout_seconds
                )
                
                # Extract content
                content_blocks = response.content
                content_text = ""
                
                for block in content_blocks:
                    if hasattr(block, 'text'):
                        content_text += block.text
                    elif isinstance(block, dict) and 'text' in block:
                        content_text += block['text']
                
                # Extract usage
                usage = {}
                if hasattr(response, 'usage'):
                    usage = {
                        'input_tokens': getattr(response.usage, 'input_tokens', 0),
                        'output_tokens': getattr(response.usage, 'output_tokens', 0)
                    }
                    self.stats['total_tokens_used'] += usage.get('input_tokens', 0) + usage.get('output_tokens', 0)
                
                logger.info(f"✅ Claude API call successful. Tokens: {usage}")
                
                return {
                    'content': content_text,
                    'usage': usage,
                    'model': model
                }
            
            except asyncio.TimeoutError:
                logger.warning(f"Claude API timeout (attempt {attempt + 1}/{max_retries})")
                if attempt == max_retries - 1:
                    raise ValueError(f"Claude API timeout after {max_retries} attempts")
                await asyncio.sleep(self.error_handler.get_retry_delay(attempt))
            
            except Exception as e:
                logger.error(f"Claude API error (attempt {attempt + 1}/{max_retries}): {e}")
                
                if not self.error_handler.is_retriable_error(e) or attempt == max_retries - 1:
                    raise
                
                await asyncio.sleep(self.error_handler.get_retry_delay(attempt))
        
        raise ValueError(f"Claude API failed after {max_retries} attempts")
    
    def _merge_split_tables(self, tables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge tables that were split across chunks"""
        if len(tables) <= 1:
            return tables
        
        # Simple merge logic: combine tables with identical headers
        merged = []
        current_table = None
        
        for table in tables:
            if current_table is None:
                current_table = table
            elif current_table.get('headers') == table.get('headers'):
                # Same headers - merge rows
                current_table['rows'].extend(table.get('rows', []))
            else:
                # Different headers - start new table
                merged.append(current_table)
                current_table = table
        
        if current_table:
            merged.append(current_table)
        
        logger.info(f"Merged {len(tables)} table chunks into {len(merged)} tables")
        
        return merged
    
    def _format_response(
        self,
        tables: List[Dict[str, Any]],
        doc_metadata: Dict[str, Any],
        pdf_info: Dict[str, Any],
        token_usage: Dict[str, Any],
        quality_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format extraction response in standard format"""
        
        # Normalize statement date if present
        statement_date = doc_metadata.get('statement_date')
        if statement_date:
            normalized_date = normalize_statement_date(statement_date)
            doc_metadata['statement_date'] = normalized_date
        
        # Build response matching existing format
        response = {
            'success': True,
            'tables': tables,
            'extraction_method': 'claude',
            'file_type': 'pdf',
            'document_metadata': {
                'carrier_name': doc_metadata.get('carrier_name'),
                'carrier_confidence': doc_metadata.get('carrier_confidence', doc_metadata.get('confidence', 0.9)),
                'statement_date': doc_metadata.get('statement_date'),
                'date_confidence': doc_metadata.get('date_confidence', doc_metadata.get('confidence', 0.9)),
                'broker_company': doc_metadata.get('broker_company') or doc_metadata.get('broker_entity'),
                'broker_confidence': doc_metadata.get('broker_confidence', 0.8),
                'total_pages': pdf_info.get('page_count', 0),
                'file_size_mb': pdf_info.get('file_size_mb', 0),
                'extraction_method': 'claude',
                'claude_model': self.primary_model
            },
            'extracted_carrier': doc_metadata.get('carrier_name'),
            'extracted_date': doc_metadata.get('statement_date'),
            'quality_summary': quality_metrics,
            'metadata': {
                'table_count': len(tables),
                'quality_grade': quality_metrics.get('quality_grade', 'N/A'),
                'confidence_score': quality_metrics.get('overall_confidence', 0.0),
                'token_usage': token_usage
            },
            'extraction_quality': quality_metrics
        }
        
        return response
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return {
            **self.stats,
            'success_rate': (
                self.stats['successful_extractions'] / self.stats['total_extractions']
                if self.stats['total_extractions'] > 0
                else 0
            ),
            'avg_processing_time': (
                self.stats['total_processing_time'] / self.stats['successful_extractions']
                if self.stats['successful_extractions'] > 0
                else 0
            )
        }
    
    async def extract_summarize_data_via_claude(self, file_path: str) -> Dict[str, Any]:
        """
        Extract summarize data using Claude with OCR agent configuration.
        Returns only markdown result as specified.
        """
        start_time = time.time()
        self.stats['total_extractions'] += 1
        
        try:
            logger.info(f"Starting Claude-based summarize extraction for: {file_path}")
            
            # Validate service availability (same as extract_commission_data)
            if not self.is_available():
                raise ValueError("Claude service not available. Check API key and SDK installation.")
            
            # Validate file (same as extract_commission_data)
            validation_result = self._validate_file(file_path)
            if not validation_result['valid']:
                raise ValueError(validation_result['error'])
            
            pdf_info = validation_result['pdf_info']
            
            # Use the same PDF processor as other methods
            pdf_base64 = self.pdf_processor.encode_pdf_to_base64(file_path)
            
            # Use the specific prompt for summarize extraction
            prompt = self.prompts.get_summarize_extraction_prompt()
            
            # Use the same API call method as _extract_standard_file
            logger.info("Calling Claude API for summarize extraction")
            extraction_result = await self._call_claude_api(
                pdf_base64,
                prompt,
                model=self.primary_model
            )
            
            # Extract content from the result
            content = extraction_result.get('content', '')
            logger.info(f"Extracted content length: {len(content) if content else 0}")
            
            # Update statistics (same as extract_commission_data)
            processing_time = time.time() - start_time
            self.stats['successful_extractions'] += 1
            self.stats['total_processing_time'] += processing_time
            
            logger.info(f"✅ Claude summarize extraction completed in {processing_time:.2f}s")
            
            # Return result in same format as extract_commission_data
            result = {
                'success': True,
                'result': content,  # Only return the markdown result
                'processing_time': processing_time,
                'extraction_method': 'claude',
                'file_info': pdf_info
            }
            logger.info(f"Returning result with keys: {list(result.keys())}")
            return result
                
        except Exception as e:
            self.stats['failed_extractions'] += 1
            processing_time = time.time() - start_time
            
            logger.error(f"❌ Claude summarize extraction failed after {processing_time:.2f}s: {e}")
            
            return {
                'success': False,
                'error': str(e),
                'error_message': self.error_handler.format_error_message(e),
                'result': '',
                'extraction_method': 'claude',
                'processing_time': processing_time
            }

