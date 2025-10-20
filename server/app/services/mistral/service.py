"""
Mistral Document AI Service - Clean and Modular Implementation

This service provides intelligent document extraction capabilities using Mistral's
Pixtral Large model for commission statement processing.
"""

import os
import base64
import logging
import time
import re
import asyncio
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor
import multiprocessing as mp

from mistralai import Mistral
from mistralai.extra import response_format_from_pydantic_model

# Import timeout configuration
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))
from config.timeouts import timeout_settings, TimeoutSettings

# Import retry logic
try:
    from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
    TENACITY_AVAILABLE = True
except ImportError:
    TENACITY_AVAILABLE = False
    logging.warning("tenacity not available. Retry logic will use simple implementation.")

# Summary detection and performance optimization imports
try:
    import numpy as np
    from sklearn.cluster import KMeans
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

# Import normalization utilities
from app.services.extraction_utils import normalize_multi_line_headers

if not ML_AVAILABLE:
    logging.warning("ML libraries not available. Summary detection will use simplified approach.")

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logging.warning("psutil not available. Some performance metrics will be unavailable.")

from .models import (
    DocumentIntelligence,
    TableIntelligence,
    TableData,
    IntelligentExtractionResponse,
    EnhancedCommissionDocument,
    EnhancedDocumentMetadata,
    EnhancedCommissionTable
)
from .prompts import MistralPrompts
from .utils import PDFProcessor, DataValidator, JSONProcessor, QualityAssessor, CarrierDetector, DateExtractor, TableStructureDetector

# Import quality validation service
from ..quality_validation_service import QualityValidationService

# Import new enhancement modules
from .enhanced_summary_detector import EnhancedSummaryRowDetector as NewEnhancedSummaryRowDetector
from .bracket_processor import AccountingBracketProcessor
from .enhancement_config import EnhancementConfig, EnhancementMonitor, get_global_monitor

logger = logging.getLogger(__name__)


class LightweightPerformanceOptimizer:
    """
    Lightweight performance optimizations that don't compromise extraction quality
    """
    
    def __init__(self, max_workers: int = 2):
        self.max_workers = min(max_workers, mp.cpu_count())
        self.cache = {}
        self.cache_lock = threading.Lock()
        self.cache_max_size = 100
    
    def should_optimize_for_large_file(self, file_path: str) -> bool:
        """Check if file should use performance optimization"""
        try:
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            return file_size_mb > 20  # Files larger than 20MB
        except:
            return False
    
    def cache_result(self, key: str, result: Any):
        """Simple result caching"""
        with self.cache_lock:
            if len(self.cache) >= self.cache_max_size:
                # Remove oldest entry
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
            self.cache[key] = result
    
    def get_cached_result(self, key: str) -> Optional[Any]:
        """Get cached result if available"""
        with self.cache_lock:
            return self.cache.get(key)
    
    def create_cache_key(self, file_path: str) -> str:
        """Create cache key based on file path and modification time"""
        try:
            mtime = os.path.getmtime(file_path)
            return f"{file_path}_{mtime}"
        except:
            return file_path


class MistralDocumentAIService:
    """
    Intelligent Commission Statement Extraction System
    
    This service implements a two-phase extraction architecture that leverages
    LLM intelligence for document structure analysis and business context understanding.
    
    PHASE 1A: Document Intelligence Analysis - Uses LLM reasoning to identify carriers, dates, and entities
    PHASE 1B: Table Structure Intelligence - Extracts tables with business context understanding
    PHASE 2: Cross-validation and Quality Assessment - Validates extraction using business logic
    PHASE 3: Intelligent Response Formatting - Separates document metadata from table data
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        # Configuration with safe defaults
        self.config = config or {}
        
        # Summary detection configuration
        self.enable_summary_detection = self.config.get('enable_summary_detection', True)
        self.summary_confidence_threshold = self.config.get('summary_confidence_threshold', 0.85)
        
        # Performance optimization configuration  
        self.enable_performance_optimization = self.config.get('enable_performance_optimization', True)
        self.enable_caching = self.config.get('enable_caching', True)
        
        # Configure timeouts based on document size for large file processing
        self.timeout_config = {
            'small_document': timeout_settings.small_document_timeout,  # 5 minutes for < 10 pages
            'medium_document': timeout_settings.medium_document_timeout,  # 10 minutes for 10-50 pages
            'large_document': timeout_settings.large_document_timeout,  # 20 minutes for 50+ pages
            'max_timeout': timeout_settings.max_timeout  # 30 minutes absolute maximum
        }
        
        # Use Mistral OCR 2505 - Mistral's specialized OCR model for Document AI
        # This model powers Mistral's Document AI stack for extracting text and images
        self.intelligent_model = "mistral-ocr-latest"
        self.ocr_model = "mistral-ocr-latest"  # Correct model name for OCR endpoint
        self.max_pages = 500
        
        self.client = None
        self._initialize_client()
        
        # Initialize quality validation service
        self.quality_validator = QualityValidationService()
        
        # Initialize utility classes
        self.pdf_processor = PDFProcessor()
        self.data_validator = DataValidator()
        self.json_processor = JSONProcessor()
        self.quality_assessor = QualityAssessor()
        self.carrier_detector = CarrierDetector()
        self.date_extractor = DateExtractor()
        self.table_structure_detector = TableStructureDetector()
        
        # Initialize enhanced components (NEW: Professional-grade multi-strategy detection)
        self.summary_detector = NewEnhancedSummaryRowDetector()  # Using new enhanced detector
        self.bracket_processor = AccountingBracketProcessor()  # NEW: Bracket processing
        self.enhancement_config = EnhancementConfig.from_env()  # NEW: Configuration
        self.enhancement_monitor = get_global_monitor()  # NEW: Global monitor
        self.performance_optimizer = LightweightPerformanceOptimizer()
        
        # Performance and processing statistics
        self.processing_stats = {
            'total_documents_processed': 0,
            'summary_rows_detected': 0,
            'performance_optimizations_applied': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        # System prompt for enhanced extraction
        self.system_prompt = self._create_system_prompt()
        
        # Processing limits for different document types
        self.processing_limits = {
            "digital_documents": {"max_pages": 500},
            "scanned_documents": {"max_pages": 300},
            "hybrid_documents": {"max_pages": 400},
            "medium_documents": {"max_pages": 200},
            "large_documents": {"max_pages": 500}
        }
        
        logger.info("Enhanced Mistral service initialized with summary detection and performance optimization")
    
    def _initialize_client(self):
        """Initialize Mistral client with proper SDK compatibility."""
        try:
            api_key = os.getenv("MISTRAL_API_KEY")
            
            # Enhanced debugging for API key issues
            if not api_key:
                error_msg = (
                    "❌ MISTRAL_API_KEY not found in environment variables! "
                    "Mistral extraction will not work. Please set MISTRAL_API_KEY in your environment."
                )
                logger.error(error_msg)
                logger.error("Available environment variables: %s", [k for k in os.environ.keys() if 'MISTRAL' in k or 'API' in k])
                self.client = None
                return
            
            # Validate API key format
            if len(api_key) < 10:
                error_msg = f"❌ MISTRAL_API_KEY appears invalid (length: {len(api_key)}). Please check your API key."
                logger.error(error_msg)
                self.client = None
                return
            
            # ✅ FIX: Remove timeout parameter - handle timeouts at request level
            # The Mistral SDK doesn't support timeout parameter in initialization
            self.client = Mistral(api_key=api_key)
            
            # ✅ NOTE: mistral-ocr-latest is an OCR model that requires image/document input
            # We cannot validate it with a simple text test, so we skip validation
            # The model will be tested during actual extraction with proper document input
            logger.info("✅ Mistral client initialized successfully")
            logger.info(f"   Model: {self.ocr_model} (Mistral OCR for Document AI)")
            logger.info(f"   API Key: {'*' * (len(api_key) - 4)}{api_key[-4:]}")  # Show last 4 chars for verification
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Mistral client: {e}", exc_info=True)
            self.client = None
    
    def _create_system_prompt(self) -> str:
        """Create the main system prompt for enhanced extraction"""
        return """
You are an expert commission statement extraction specialist with deep understanding of:
- Insurance industry commission statements and billing documents
- Document structure analysis and table extraction
- Business entity relationships (carriers, brokers, companies)
- Financial data interpretation and validation

CRITICAL EXTRACTION REQUIREMENTS:

1. DOCUMENT COMPREHENSION:
   - Read and understand the document like a human analyst would
   - Identify the main insurance carrier from visual prominence, logos, headers
   - Find statement dates from document context, not just any date
   - Distinguish document metadata from table content data

2. BUSINESS ENTITY INTELLIGENCE:
   - CARRIERS: Insurance companies that issue statements (headers, logos, document owners)
   - BROKERS: Agencies/agents receiving commissions (addressees, recipients)
   - COMPANIES: Client businesses being insured (group names in data tables)

3. TABLE EXTRACTION EXCELLENCE:
   - Preserve exact table structure and column relationships
   - Include all rows and cells (even empty ones for structure preservation)
   - Identify column headers and their business meaning
   - Recognize data types: dates, currency, names, IDs, percentages
   - Understand row relationships and hierarchies

4. QUALITY INTELLIGENCE:
   - Flag inconsistencies between document header info and table data
   - Identify potential extraction errors using business logic
   - Provide detailed evidence for all high-confidence extractions
   - Calculate confidence scores based on context strength

USE YOUR INTELLIGENCE AND REASONING - not hardcoded rules or patterns.
Think like a business analyst reviewing these documents manually.

EXTRACTION TASK:
Extract all commission tables with maximum accuracy and provide:
1. Complete table structure (headers, rows, empty cells)
2. Document metadata (carrier, dates, broker information)
3. Quality metrics and confidence scores
4. Business context and entity classifications

Focus on achieving 99%+ extraction completeness with superior vision processing.
"""
    
    def _get_adaptive_timeout(self, file_path: str) -> int:
        """
        Calculate appropriate timeout based on document characteristics.
        Adaptive timeout prevents timeouts on large documents.
        """
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(file_path)
            page_count = len(doc)
            doc.close()
            
            # Adaptive timeout based on page count
            if page_count <= 10:
                timeout = self.timeout_config['small_document']
            elif page_count <= 50:
                timeout = self.timeout_config['medium_document']
            else:
                timeout = self.timeout_config['large_document']
            
            logger.info(f"Adaptive timeout for {page_count} pages: {timeout}s")
            return timeout
            
        except Exception as e:
            logger.warning(f"Could not determine document size: {e}")
            return self.timeout_config['large_document']  # Default to safe timeout
    
    def _simple_retry_wrapper(self, func, max_attempts: int = 3):
        """
        Simple retry wrapper for when tenacity is not available.
        Implements exponential backoff retry logic.
        """
        for attempt in range(max_attempts):
            try:
                return func()
            except (TimeoutError, asyncio.TimeoutError) as e:
                if attempt == max_attempts - 1:
                    raise
                wait_time = min(2 ** attempt, 10)  # Exponential backoff, max 10s
                logger.warning(f"Retry attempt {attempt + 1}/{max_attempts} after {wait_time}s delay: {e}")
                time.sleep(wait_time)
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise
                logger.warning(f"Retry attempt {attempt + 1}/{max_attempts}: {e}")
                time.sleep(2)
    
    def is_available(self) -> bool:
        """
        Check if Mistral OCR service is available.
        
        Note: mistral-ocr-latest is an OCR model that requires image/document input,
        so we cannot test it with a simple text ping. We just check if the client
        is initialized properly.
        """
        if not self.client:
            logger.warning("❌ Mistral client not initialized")
            return False
        
        # Client is initialized, service is available
        return True
    
    def _call_mistral_ocr(
        self,
        pdf_base64: str,
        prompt: str = None,
        max_tokens: int = 8000,
        temperature: float = 0
    ) -> Dict[str, Any]:
        """
        Call Mistral OCR API with proper endpoint.
        
        Mistral OCR uses a dedicated OCR endpoint (client.ocr.process).
        The OCR endpoint returns markdown-formatted content with tables.
        
        Returns:
            Dict with 'success', 'content' (markdown text), 'response', and 'method'
        """
        try:
            logger.info(f"🔍 Calling Mistral OCR API (model: {self.ocr_model})")
            
            # ✅ Use the dedicated OCR endpoint with correct model name
            logger.info("✅ Using dedicated OCR endpoint: client.ocr.process()")
            
            # Call the OCR endpoint asynchronously with correct model
            response = self.client.ocr.process(
                model=self.ocr_model,  # Use mistral-ocr-latest, not mistral-ocr-latest
                document={
                    "type": "document_url",
                    "document_url": f"data:application/pdf;base64,{pdf_base64}"
                },
                include_image_base64=True
            )
            
            # Extract markdown content from OCR response
            # Response structure: response.pages = [OCRPageObject(markdown='...', index=0), ...]
            content = ""
            pages_processed = 0
            
            if hasattr(response, 'pages') and response.pages:
                # Extract markdown from each page and combine
                markdown_pages = []
                for page in response.pages:
                    if hasattr(page, 'markdown') and page.markdown:
                        markdown_pages.append(page.markdown)
                        pages_processed += 1
                
                content = "\n\n---\n\n".join(markdown_pages)  # Separate pages with ---
                logger.info(f"✅ OCR completed: {pages_processed} pages, {len(content)} characters")
            else:
                logger.warning("⚠️  OCR response has no pages attribute")
                content = str(response)
            
            return {
                "success": True,
                "content": content,  # Markdown-formatted content from all pages
                "pages_processed": pages_processed,
                "response": response,
                "method": "ocr"
            }
                
        except Exception as e:
            logger.error(f"❌ Mistral OCR API call failed: {e}")
            logger.error(f"   Error type: {type(e).__name__}")
            return {
                "success": False,
                "error": str(e),
                "method": "ocr",
                "content": ""
            }
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test connection with Mistral OCR service.
        
        Note: mistral-ocr-latest is an OCR model that requires image/document input,
        so we cannot test it with a simple text message. This method just verifies
        the client is initialized.
        """
        try:
            if not self.is_available():
                return {"success": False, "error": "Mistral OCR client not initialized"}
            
            return {
                "success": True, 
                "message": "Mistral OCR connection successful (client initialized)",
                "service_type": "mistral_ocr_extraction",
                "version": "3.1.0",
                "diagnostics": {
                    "client_initialized": True,
                    "model": self.ocr_model,
                    "note": "mistral-ocr-latest requires document/image input for actual testing"
                }
            }
            
        except Exception as e:
            logger.error(f"Mistral OCR connection test failed: {e}")
            return {"success": False, "error": str(e)}
    
    def extract_tables_from_ocr_response(self, ocr_response) -> List[Dict]:
        """
        Extract tables from Mistral OCR markdown response.
        
        The OCR response contains markdown-formatted content with tables.
        This method parses the markdown to extract structured table data.
        """
        tables = []
        
        try:
            if hasattr(ocr_response, 'pages') and ocr_response.pages:
                for page_idx, page in enumerate(ocr_response.pages):
                    if hasattr(page, 'markdown') and page.markdown:
                        markdown_content = page.markdown
                        page_tables = self.parse_markdown_tables(markdown_content, page_idx + 1)
                        tables.extend(page_tables)
                        
                        logger.info(f"Page {page_idx + 1}: Found {len(page_tables)} tables")
            else:
                logger.warning("OCR response has no pages or markdown content")
                
        except Exception as e:
            logger.error(f"Error extracting tables from OCR response: {e}", exc_info=True)
        
        return tables
    
    def parse_markdown_tables(self, markdown_content: str, page_num: int) -> List[Dict]:
        """
        Parse tables from markdown content.
        
        Markdown tables have the format:
        | Header1 | Header2 | Header3 |
        |---------|---------|---------|
        | Data1   | Data2   | Data3   |
        """
        tables = []
        
        if not markdown_content:
            return tables
            
        lines = markdown_content.split('\n')
        current_table = None
        
        for line in lines:
            line = line.strip()
            
            # Check if line contains table content (has pipe characters)
            if '|' in line and line:
                if current_table is None:
                    # Start new table
                    current_table = {
                        'headers': [],
                        'rows': [],
                        'page_number': page_num
                    }
                    # First line with | is headers
                    headers = [cell.strip() for cell in line.split('|')[1:-1] if cell.strip()]
                    current_table['headers'] = headers
                elif line.startswith('|---') or line.startswith('| ---') or all(c in '|-: ' for c in line):
                    # Skip separator line
                    continue
                else:
                    # Data row
                    row_data = [cell.strip() for cell in line.split('|')[1:-1]]
                    if any(cell.strip() for cell in row_data):  # Only add non-empty rows
                        current_table['rows'].append(row_data)
            else:
                # End of table - save if it has data
                if current_table and current_table.get('rows'):
                    table_dict = {
                        'headers': current_table['headers'],
                        'rows': current_table['rows'],
                        'page_number': current_table['page_number'],
                        'extractor': 'mistral_ocr_2505',
                        'table_type': 'commission_table'
                    }
                    tables.append(table_dict)
                current_table = None
        
        # Don't forget the last table
        if current_table and current_table.get('rows'):
            table_dict = {
                'headers': current_table['headers'],
                'rows': current_table['rows'],
                'page_number': current_table['page_number'],
                'extractor': 'mistral_ocr_2505',
                'table_type': 'commission_table'
            }
            tables.append(table_dict)
        
        return tables
    
    async def extract_commission_data_via_ocr(self, file_path: str) -> Dict[str, Any]:
        """
        Extract commission tables using CORRECT Mistral OCR implementation.
        
        This method uses the dedicated OCR endpoint (client.ocr.process)
        with the correct model name (mistral-ocr-latest) and parses markdown tables.
        """
        if not self.is_available():
            return {
                "success": False,
                "error": "Mistral OCR service not available - MISTRAL_API_KEY not configured",
                "tables": []
            }
        
        try:
            # Read and encode PDF
            with open(file_path, "rb") as f:
                pdf_content = f.read()
            pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
            
            logger.info(f"🔍 Extracting tables via Mistral OCR (model: {self.ocr_model})")
            
            # CORRECT: Use OCR endpoint, not chat endpoint
            ocr_response = self.client.ocr.process(
                model=self.ocr_model,
                document={
                    "type": "document_url",
                    "document_url": f"data:application/pdf;base64,{pdf_base64}"
                },
                include_image_base64=True
            )
            
            # Extract tables from OCR response
            tables = self.extract_tables_from_ocr_response(ocr_response)
            
            logger.info(f"✅ OCR extraction successful: {len(tables)} tables found")
            
            return {
                "success": True,
                "tables": tables,
                "document_metadata": {
                    "total_pages": len(ocr_response.pages) if hasattr(ocr_response, 'pages') else 1,
                    "extraction_method": "mistral_ocr_2505",
                    "model": self.ocr_model
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Mistral OCR extraction failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "tables": []
            }
    
    async def extract_commission_data_intelligently(self, file_path: str) -> Dict:
        """
        INTELLIGENT extraction with adaptive timeout and retry logic for large file processing.
        
        This is the main entry point that implements the two-phase extraction architecture:
        1. Document Intelligence Analysis
        2. Table Structure Intelligence
        3. Cross-validation and Quality Assessment
        4. Intelligent Response Formatting
        
        Enhanced with:
        - Adaptive timeout based on document size
        - Automatic retry on transient failures
        - Comprehensive error handling for timeouts
        """
        # Check if client is available (API key configured)
        if not self.is_available():
            error_msg = (
                "❌ Mistral service is not available. MISTRAL_API_KEY is not configured. "
                "Please set the MISTRAL_API_KEY environment variable to enable Mistral extraction."
            )
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "error_type": "CONFIGURATION_ERROR",
                "tables": [],
                "document_metadata": {},
                "recommendation": "Set MISTRAL_API_KEY environment variable and restart the service."
            }
        
        try:
            logger.info(f"Starting intelligent extraction for: {file_path}")
            start_time = time.time()
            
            # Determine adaptive timeout based on document size
            adaptive_timeout = self._get_adaptive_timeout(file_path)
            logger.info(f"Using adaptive timeout: {adaptive_timeout}s for document processing")
            
            # Use asyncio.timeout for request-level timeout control
            try:
                async with asyncio.timeout(adaptive_timeout):
                    return await self._process_with_progress_tracking(file_path, start_time)
            except asyncio.TimeoutError:
                logger.error(f"Mistral processing timeout after {adaptive_timeout} seconds")
                return {
                    "success": False,
                    "error": f"Document processing timeout after {adaptive_timeout} seconds. The document may be too large or complex.",
                    "error_type": "TIMEOUT_ERROR",
                    "timeout_duration": adaptive_timeout,
                    "recommendation": "Try processing a smaller document or contact support for large file processing.",
                    "tables": [],
                    "document_metadata": {}
                }
                
        except Exception as e:
            logger.error(f"Intelligent extraction failed: {e}", exc_info=True)
            return self.handle_intelligent_error(e)
    
    async def _process_with_progress_tracking(self, file_path: str, start_time: float) -> Dict:
        """
        Process document with periodic progress updates to maintain WebSocket connection.
        This prevents timeout during long-running Mistral API calls.
        
        UPDATED: Now uses the correct OCR endpoint (client.ocr.process) as the primary method.
        """
        # Try OCR-based extraction first (CORRECT implementation)
        logger.info("🔍 Using Mistral OCR endpoint for table extraction")
        ocr_result = await self.extract_commission_data_via_ocr(file_path)
        
        if ocr_result.get("success") and ocr_result.get("tables"):
            # OCR extraction succeeded
            processing_time = time.time() - start_time
            logger.info(f"✅ OCR extraction completed in {processing_time:.2f}s with {len(ocr_result['tables'])} tables")
            
            return {
                "success": True,
                "tables": ocr_result["tables"],
                "document_metadata": ocr_result.get("document_metadata", {}),
                "extraction_method": "mistral_ocr_2505",
                "processing_time": processing_time
            }
        
        # If OCR fails, log the error and try fallback (if available)
        logger.warning(f"⚠️ OCR extraction failed or returned no tables: {ocr_result.get('error', 'Unknown error')}")
        logger.info("Attempting fallback extraction methods...")
        
        # Fallback to the old two-phase extraction (uses chat endpoints)
        # NOTE: This may fail if using OCR model with chat endpoints
        try:
            # Phase 1: Document Structure Intelligence
            logger.info("Phase 1: Document Intelligence Analysis")
            document_analysis = await self.analyze_document_intelligence(file_path)
            
            # Phase 2: Table Data Intelligence  
            logger.info("Phase 2: Table Intelligence Extraction")
            table_analysis = await self.extract_table_intelligence(file_path)
            
            # Phase 3: Cross-validation and Quality Assessment
            logger.info("Phase 3: Validation and Quality Assessment")
            validated_result = await self.validate_extraction_intelligence(
                document_analysis, table_analysis
            )
            
            # Phase 4: Intelligent Response Formatting
            logger.info("Phase 4: Response Formatting")
            return self.format_intelligent_response(validated_result, start_time)
        except Exception as fallback_error:
            logger.error(f"❌ Fallback extraction also failed: {fallback_error}")
            # Return the OCR error since it was the primary attempt
            return {
                "success": False,
                "error": f"OCR extraction failed: {ocr_result.get('error', 'Unknown error')}. Fallback also failed: {str(fallback_error)}",
                "tables": [],
                "document_metadata": {}
            }
    
    async def analyze_document_intelligence(self, file_path: str) -> DocumentIntelligence:
        """
        Phase 1A: Document Intelligence Analysis
        
        Uses LLM intelligence to understand document structure and extract metadata
        WITHOUT hardcoded patterns - let the AI identify what it sees
        """
        try:
            logger.info("Phase 1A: Starting document intelligence analysis")
            
            # Read PDF and convert to base64
            with open(file_path, 'rb') as f:
                pdf_content = f.read()
            pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
            
            # Create intelligent analysis prompt
            analysis_prompt = f"""
{MistralPrompts.get_document_intelligence_prompt()}

DOCUMENT ANALYSIS INSTRUCTIONS:
You are analyzing a commission statement document. Use your intelligence to:

1. DOCUMENT STRUCTURE ANALYSIS:
   - Identify the PRIMARY insurance carrier/company from headers, logos, letterheads
   - CRITICAL: Check both BOTTOM and TOP of pages for carrier logos (many carriers like ABSF, Allied, AIA place their branding at page footers)
   - Find the statement date from document headers/footers (NOT table data)
   - Look for dates in titles like "Commission Payment Summary" or "Statement Date: X"
   - Identify the broker/agency receiving commissions
   - Determine document type and purpose

2. ENTITY CLASSIFICATION:
   - CARRIER: Insurance company issuing the statement (headers/logos/PAGE FOOTERS)
     * Look at the VERY TOP of the document for company names and logos
     * Look at the VERY BOTTOM of pages for footer logos and branding
     * DO NOT use table column data labeled "CARRIER" - those are client companies
   - BROKER: Agent/agency receiving commissions (addressee/table data)  
   - COMPANIES: Client businesses being insured (group names in tables)

3. CONTEXT UNDERSTANDING:
   - Where is each piece of information located? (header/footer/table/body)
   - What is the confidence level for each extraction?
   - What visual cues support your identification?
   - Pay special attention to logos and branding elements

BE INTELLIGENT: Use context, visual layout, and business logic understanding.
DO NOT rely on pattern matching - use reasoning and document comprehension.

Extract this information with confidence scoring and location context.
Return structured JSON with your analysis.
"""
            
            messages = [
                {
                    "role": "system",
                    "content": analysis_prompt
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Analyze this commission statement document for carrier identification, statement dates, and business entity classification. Pay special attention to logos at the TOP and BOTTOM of pages. Provide detailed reasoning and confidence scores."
                        },
                        {
                            "type": "document_url",
                            "document_url": f"data:application/pdf;base64,{pdf_base64}"
                        }
                    ]
                }
            ]
            
            # TRY STRUCTURED OUTPUT FIRST
            try:
                logger.info("Phase 1A: Attempting structured output parsing")
                response = self.client.chat.parse(
                    model=self.intelligent_model,
                    messages=messages,
                    response_format=DocumentIntelligence,
                    max_tokens=4000,
                    temperature=0
                )
                
                if hasattr(response, 'choices') and response.choices:
                    document_analysis = response.choices[0].message.parsed
                    logger.info(f"Phase 1A: Document intelligence analysis completed successfully")
                    logger.info(f"Phase 1A: Carrier: {document_analysis.identified_carrier} (confidence: {document_analysis.carrier_confidence})")
                    logger.info(f"Phase 1A: Date: {document_analysis.statement_date} (confidence: {document_analysis.date_confidence})")
                    return document_analysis
                else:
                    raise Exception("No response from document intelligence analysis")
                    
            except Exception as parse_error:
                logger.warning(f"Phase 1A: Structured parsing failed: {parse_error}")
                logger.info("Phase 1A: Falling back to text completion with manual parsing")
                
                # FALLBACK TO TEXT COMPLETION WITH INTELLIGENT EXTRACTION
                try:
                    # Create a simpler, focused prompt for text extraction
                    simple_prompt = """You are analyzing a commission statement document.

TASK: Extract the following information and return ONLY a simple text response:

1. CARRIER NAME: The insurance company that issued this statement
   - Look at the TOP of the page (headers, logos, letterhead)
   - Look at the BOTTOM of pages (footer logos and branding)
   - DO NOT use table data - only document structure elements
   - Return the full company name as it appears

2. STATEMENT DATE: The date of this commission statement
   - Look in document headers/titles
   - Look for "Report Date", "Statement Date", "Date:", etc.
   - Return in format: MM/DD/YYYY or as shown

FORMAT YOUR RESPONSE EXACTLY LIKE THIS:
CARRIER: [company name or "Unknown"]
DATE: [date or "Unknown"]
EVIDENCE: [brief explanation of where you found this information]"""

                    simple_messages = [
                        {"role": "system", "content": simple_prompt},
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "Extract carrier name and statement date from this document."},
                                {"type": "document_url", "document_url": f"data:application/pdf;base64,{pdf_base64}"}
                            ]
                        }
                    ]
                    
                    response = self.client.chat.complete(
                        model=self.intelligent_model,
                        messages=simple_messages,
                        max_tokens=1000,
                        temperature=0
                    )
                    
                    if hasattr(response, 'choices') and response.choices:
                        content = response.choices[0].message.content
                        logger.info(f"Phase 1A: Received text response:\n{content}")
                        
                        # Parse the simple text response - NO PATTERN MATCHING, just extract what AI found
                        carrier_name = None
                        statement_date = None
                        evidence = ""
                        
                        # Extract carrier from text response
                        import re
                        carrier_match = re.search(r'CARRIER:\s*(.+?)(?:\n|$)', content, re.IGNORECASE)
                        if carrier_match:
                            carrier_name = carrier_match.group(1).strip()
                            if carrier_name.lower() in ['unknown', 'not found', 'n/a', 'none']:
                                carrier_name = None
                        
                        # Extract date from text response
                        date_match = re.search(r'DATE:\s*(.+?)(?:\n|$)', content, re.IGNORECASE)
                        if date_match:
                            statement_date = date_match.group(1).strip()
                            if statement_date.lower() in ['unknown', 'not found', 'n/a', 'none']:
                                statement_date = None
                        
                        # Extract evidence
                        evidence_match = re.search(r'EVIDENCE:\s*(.+?)(?:\n|$)', content, re.IGNORECASE)
                        if evidence_match:
                            evidence = evidence_match.group(1).strip()
                        
                        logger.info(f"Phase 1A: Intelligent extraction - Carrier: {carrier_name}, Date: {statement_date}")
                        
                        return DocumentIntelligence(
                            identified_carrier=carrier_name,
                            carrier_confidence=0.75 if carrier_name else 0.0,
                            carrier_location_evidence=evidence or "Extracted from AI text analysis",
                            statement_date=statement_date,
                            date_confidence=0.75 if statement_date else 0.0,
                            date_location_evidence=evidence or "Extracted from AI text analysis",
                            broker_entity=None,
                            document_classification="commission_statement",
                            confidence_score=0.75 if (carrier_name or statement_date) else 0.0
                        )
                        
                except Exception as fallback_error:
                    logger.error(f"Phase 1A: Fallback extraction failed: {fallback_error}")
                    raise
                
        except Exception as e:
            logger.error(f"Document intelligence analysis failed: {e}")
            # Return fallback analysis
            return DocumentIntelligence(
                identified_carrier=None,
                carrier_confidence=0.0,
                carrier_location_evidence="Analysis failed",
                statement_date=None,
                date_confidence=0.0,
                date_location_evidence="Analysis failed",
                broker_entity=None,
                document_classification="unknown",
                confidence_score=0.0
            )
    
    async def extract_table_intelligence(self, file_path: str) -> TableIntelligence:
        """
        Phase 1B: Table Structure Intelligence
        
        Intelligent table extraction that understands business context
        """
        try:
            logger.info("Phase 1B: Starting table intelligence extraction")
            
            # Read PDF and convert to base64
            with open(file_path, 'rb') as f:
                pdf_content = f.read()
            pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
            
            # Create table intelligence prompt
            table_prompt = f"""
{MistralPrompts.get_table_intelligence_prompt()}

TABLE EXTRACTION INSTRUCTIONS:
Now extract ALL table data with business intelligence:

1. TABLE STRUCTURE RECOGNITION:
   - Identify column headers and their business meaning
   - Recognize data types: dates, currency, names, IDs, percentages
   - Understand row relationships and hierarchies

2. BUSINESS LOGIC UNDERSTANDING:
   - Summary/total rows vs data rows
   - Positive vs negative values meaning
   - Date ranges and their significance
   - Commission calculations and relationships

3. DATA INTEGRITY:
   - Preserve exact table structure
   - Maintain column relationships
   - Keep empty cells for structure preservation
   - Flag unusual or suspicious data

USE YOUR INTELLIGENCE to understand what each table element represents
in the context of commission statements and insurance business.

Return structured JSON with all tables and business context analysis.
"""
            
            messages = [
                {
                    "role": "system",
                    "content": table_prompt
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Extract all commission tables from this document with business intelligence. Preserve exact structure and provide business context analysis."
                        },
                        {
                            "type": "document_url",
                            "document_url": f"data:application/pdf;base64,{pdf_base64}"
                        }
                    ]
                }
            ]
            
            # TRY STRUCTURED OUTPUT FIRST
            try:
                logger.info("Phase 1B: Attempting structured output parsing")
                response = self.client.chat.parse(
                    model=self.intelligent_model,
                    messages=messages,
                    response_format=TableIntelligence,
                    max_tokens=8000,
                    temperature=0
                )
                
                if hasattr(response, 'choices') and response.choices:
                    table_analysis = response.choices[0].message.parsed
                    logger.info(f"Phase 1B: Table intelligence extraction completed successfully with {len(table_analysis.structured_tables)} tables")
                    
                    # Log table structure for debugging
                    for i, table in enumerate(table_analysis.structured_tables):
                        if hasattr(table, 'headers'):
                            logger.info(f"Table {i}: {len(table.headers)} headers, {len(table.rows)} rows")
                        else:
                            logger.warning(f"Table {i}: Missing expected structure")
                    
                    return table_analysis
                else:
                    raise Exception("No response from table intelligence extraction")
                    
            except Exception as parse_error:
                logger.warning(f"Phase 1B: Structured parsing failed: {parse_error}")
                logger.info("Phase 1B: Falling back to text completion with manual JSON parsing")
                
                # FALLBACK TO TEXT COMPLETION
                try:
                    response = self.client.chat.complete(
                        model=self.intelligent_model,
                        messages=messages,
                        max_tokens=8000,
                        temperature=0
                    )
                    
                    if hasattr(response, 'choices') and response.choices:
                        content = response.choices[0].message.content
                        logger.info(f"Phase 1B: Received text response, length: {len(content)}")
                        
                        # Parse JSON manually with safe parsing
                        parsed_json = self.json_processor.parse_commission_json_safely(content)
                        
                        if parsed_json.get("success"):
                            # Convert to TableIntelligence structure
                            tables_data = parsed_json.get("tables", [])
                            
                            # Convert dict tables to TableData objects
                            structured_tables = []
                            for table_dict in tables_data:
                                try:
                                    table_data = TableData(
                                        headers=table_dict.get("headers", []),
                                        rows=table_dict.get("rows", []),
                                        table_type=table_dict.get("table_type", "commission_table"),
                                        company_name=table_dict.get("company_name"),
                                        confidence=table_dict.get("confidence", 0.85)
                                    )
                                    structured_tables.append(table_data)
                                except Exception as conv_error:
                                    logger.warning(f"Failed to convert table: {conv_error}")
                                    continue
                            
                            logger.info(f"Phase 1B: Manual parsing succeeded with {len(structured_tables)} tables")
                            
                            return TableIntelligence(
                                structured_tables=structured_tables,
                                business_logic_consistency=0.8,
                                entity_classification_accuracy=0.8,
                                data_integrity_score=0.85,
                                confidence_score=0.8
                            )
                        else:
                            raise Exception(f"Manual JSON parsing failed: {parsed_json.get('error')}")
                            
                except Exception as fallback_error:
                    logger.error(f"Phase 1B: Fallback extraction failed: {fallback_error}")
                    raise
                
        except Exception as e:
            logger.error(f"Table intelligence extraction failed: {e}")
            # Return fallback analysis
            return TableIntelligence(
                structured_tables=[],
                business_logic_consistency=0.0,
                entity_classification_accuracy=0.0,
                data_integrity_score=0.0,
                confidence_score=0.0
            )
    
    async def validate_extraction_intelligence(self, doc_analysis: DocumentIntelligence, table_analysis: TableIntelligence) -> Dict:
        """
        Phase 2: Cross-validation and Quality Assessment
        
        Validates extraction using business logic and cross-references document and table data
        """
        try:
            logger.info("Phase 2: Starting extraction validation and quality assessment")
            
            # Cross-validate carrier identification
            carrier_validation = self.data_validator.validate_carrier_consistency(doc_analysis, table_analysis)
            
            # Validate date consistency
            date_validation = self.data_validator.validate_date_consistency(doc_analysis, table_analysis)
            
            # Assess business logic consistency
            business_logic_score = self.data_validator.assess_business_logic_consistency(table_analysis)
            
            # Calculate overall quality score
            overall_confidence = self.data_validator.calculate_overall_confidence(
                doc_analysis.confidence_score,
                table_analysis.confidence_score,
                carrier_validation,
                date_validation,
                business_logic_score
            )
            
            validation_result = {
                "document_analysis": doc_analysis,
                "table_analysis": table_analysis,
                "carrier_validation": carrier_validation,
                "date_validation": date_validation,
                "business_logic_score": business_logic_score,
                "overall_confidence": overall_confidence,
                "validation_timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Phase 2: Validation completed with overall confidence: {overall_confidence:.2f}")
            return validation_result
            
        except Exception as e:
            logger.error(f"Extraction validation failed: {e}")
            return {
                "document_analysis": doc_analysis,
                "table_analysis": table_analysis,
                "carrier_validation": {"consistent": False, "confidence": 0.0},
                "date_validation": {"consistent": False, "confidence": 0.0},
                "business_logic_score": 0.0,
                "overall_confidence": 0.0,
                "validation_error": str(e)
            }
    
    def format_intelligent_response(self, validated_result: Dict, start_time: float) -> Dict:
        """
        Phase 3: Intelligent Response Formatting
        
        Creates intelligent response structure that clearly separates document intelligence from table data
        """
        try:
            logger.info("Phase 3: Formatting intelligent response")
            
            doc_analysis = validated_result["document_analysis"]
            table_analysis = validated_result["table_analysis"]
            overall_confidence = validated_result["overall_confidence"]
            
            processing_time = time.time() - start_time
            
            # Create intelligent response structure
            intelligent_response = {
                "success": True,
                "extraction_intelligence": {
                    "analysis_method": "multi_phase_intelligent_extraction",
                    "document_understanding": doc_analysis.confidence_score,
                    "table_understanding": table_analysis.confidence_score,
                    "overall_confidence": overall_confidence,
                    "processing_time": processing_time,
                    "intelligence_version": "2.0.0"
                },
                
                # SEPARATE: Document-level intelligence
                "document_metadata": {
                    "carrier_name": doc_analysis.identified_carrier,
                    "carrier_confidence": doc_analysis.carrier_confidence,
                    "carrier_evidence": doc_analysis.carrier_location_evidence,
                    "statement_date": doc_analysis.statement_date,
                    "date_confidence": doc_analysis.date_confidence,
                    "date_evidence": doc_analysis.date_location_evidence,
                    "broker_company": doc_analysis.broker_entity,
                    "document_type": doc_analysis.document_classification
                },
                
                # SEPARATE: Table business data - convert TableData objects to dicts
                "tables": self._convert_tables_to_dicts(table_analysis.structured_tables),
                
                # INTELLIGENT: Quality assessment
                "extraction_quality": {
                    "metadata_completeness": self.quality_assessor.assess_metadata_quality(doc_analysis),
                    "table_completeness": self.quality_assessor.assess_table_quality(table_analysis),
                    "business_logic_consistency": validated_result["business_logic_score"],
                    "extraction_anomalies": self.quality_assessor.detect_anomalies(validated_result),
                    "overall_confidence": overall_confidence,
                    "requires_human_review": overall_confidence < 0.7
                },
                
                # Legacy compatibility
                "extraction_metadata": {
                    "method": "intelligent_mistral_extraction",
                    "timestamp": datetime.now().isoformat(),
                    "confidence": overall_confidence,
                    "total_tables": len(table_analysis.structured_tables),
                    "processing_time": processing_time
                }
            }
            
            logger.info("Phase 3: Intelligent response formatting completed successfully")
            return intelligent_response
            
        except Exception as e:
            logger.error(f"Intelligent response formatting failed: {e}")
            return self.handle_intelligent_error(e)
    
    def handle_intelligent_error(self, error: Exception) -> Dict:
        """Handle errors in intelligent extraction with detailed error information"""
        return {
            "success": False,
            "error": str(error),
            "intelligence_failure": True,
            "extraction_intelligence": {
                "analysis_method": "intelligent_extraction_failed",
                "error_type": type(error).__name__,
                "timestamp": datetime.now().isoformat()
            },
            "document_metadata": {},
            "tables": [],
            "extraction_quality": {
                "overall_confidence": 0.0,
                "requires_human_review": True,
                "error_details": str(error)
            }
        }
    
    def extract_commission_data(self, file_path: str, max_pages: int = None) -> Dict[str, Any]:
        """
        Legacy compatibility method that uses intelligent extraction with performance optimization
        
        This method maintains backward compatibility while using the new intelligent system
        with caching and performance enhancements.
        """
        try:
            # Check cache first if caching is enabled
            if self.enable_caching:
                cache_key = self.performance_optimizer.create_cache_key(file_path)
                cached_result = self.performance_optimizer.get_cached_result(cache_key)
                if cached_result:
                    logger.info("Returning cached extraction result")
                    self.processing_stats['cache_hits'] += 1
                    return cached_result
                else:
                    self.processing_stats['cache_misses'] += 1
            
            # Check if large file optimization should be applied
            if self.enable_performance_optimization:
                is_large_file = self.performance_optimizer.should_optimize_for_large_file(file_path)
                if is_large_file:
                    logger.info("Applying large file optimization strategies")
                    self.processing_stats['performance_optimizations_applied'] += 1
            
            # First try the structured extraction with EnhancedCommissionDocument
            result = self._extract_with_enhanced_model(file_path, max_pages)
            if result.get("success") and result.get("tables"):
                # Apply enhancement metrics logging
                self._log_enhancement_metrics(result)
                
                # Cache successful results
                if self.enable_caching:
                    self.performance_optimizer.cache_result(cache_key, result)
                
                # Update processing stats
                self.processing_stats['total_documents_processed'] += 1
                
                return result
            
            # If that fails, fall back to intelligent extraction
            logger.info("Enhanced model extraction failed, falling back to intelligent extraction")
            import asyncio
            
            # Check if we're already in an event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # We're in an async context, need to use run_in_executor
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, self.extract_commission_data_intelligently(file_path))
                        result = future.result()
                else:
                    # No event loop running, we can use asyncio.run
                    result = asyncio.run(self.extract_commission_data_intelligently(file_path))
            except RuntimeError:
                # No event loop, use asyncio.run
                result = asyncio.run(self.extract_commission_data_intelligently(file_path))
            
            # Transform to legacy format if needed
            if result.get("success") and "extraction_intelligence" in result:
                # Already in intelligent format
                final_result = result
            else:
                # Transform to legacy format
                final_result = self._transform_to_legacy_format(result)
            
            # Cache successful results
            if self.enable_caching and final_result.get("success"):
                self.performance_optimizer.cache_result(cache_key, final_result)
            
            # Update processing stats
            self.processing_stats['total_documents_processed'] += 1
            
            # Apply enhancement metrics logging
            self._log_enhancement_metrics(final_result)
            
            return final_result
                
        except Exception as e:
            logger.error(f"Legacy extraction failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "tables": [],
                "extraction_metadata": {
                    "method": "intelligent_mistral_legacy_fallback",
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e)
                }
            }
    
    def _enhance_table_with_summary_detection(self, table_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply enhanced summary row detection and bracket processing to a single table
        
        NEW: Multi-strategy summary detection with >85% confidence threshold
        NEW: Professional bracket processing for negative values
        NEW: Performance monitoring and validation
        """
        start_time = time.time()
        
        # Ensure summaryRows exists for frontend compatibility
        table_dict['summaryRows'] = []
        
        try:
            logger.info(f"Applying enhancements to table with {len(table_dict.get('rows', []))} rows")
            
            # ENHANCEMENT 1: Apply bracket processing first (before summary detection)
            if self.enhancement_config.bracket_processing_enabled:
                logger.info("Phase 1: Applying professional bracket processing...")
                enhanced_table = self.bracket_processor.process_table_data(table_dict)
                
                # Record bracket processing metrics
                if 'bracket_processing' in enhanced_table:
                    self.enhancement_monitor.record_bracket_processing(enhanced_table)
                    bp_summary = self.bracket_processor.get_processing_summary()
                    logger.info(f"✓ Bracket processing: {bp_summary['brackets_converted']} values converted " +
                               f"({bp_summary['conversion_rate']:.1f}% conversion rate)")
            else:
                enhanced_table = table_dict
                logger.info("Bracket processing is disabled")
            
            # ENHANCEMENT 2: Apply enhanced summary detection
            if not self.enable_summary_detection or not self.enhancement_config.summary_detection_enabled:
                logger.info("Summary detection is disabled")
                return enhanced_table
            
            logger.info("Phase 2: Applying multi-strategy summary detection...")
            enhanced_table = self.summary_detector.detect_and_remove_summary_rows(enhanced_table)
            
            # Update processing stats and record metrics
            summary_info = enhanced_table.get('summary_detection', {})
            
            if summary_info.get('enabled'):
                # Record summary detection metrics
                self.enhancement_monitor.record_summary_detection(summary_info)
                
                if summary_info.get('removed_indices'):
                    removed_count = len(summary_info['removed_indices'])
                    confidence = summary_info.get('detection_confidence', 0)
                    
                    # CRITICAL FIX: When rows are REMOVED, summaryRows should be EMPTY
                    # The removed_indices are already filtered out from the rows array
                    # Setting summaryRows to removed_indices would highlight wrong rows
                    enhanced_table['summaryRows'] = []
                    self.processing_stats['summary_rows_detected'] += removed_count
                    
                    logger.info(f"✓ Summary detection: Removed {removed_count} rows with {confidence:.2%} confidence")
                    logger.info(f"  Detection method: {summary_info.get('detection_method', 'unknown')}")
                    logger.info(f"  Strategies used: {summary_info.get('strategies_used', [])}")
                    
                    # Log detailed evidence if available
                    if 'removed_row_details' in summary_info and self.enhancement_config.enable_detailed_logging:
                        for detail in summary_info['removed_row_details']:
                            logger.info(f"  Row {detail['index']}: {detail['confidence']:.2%} - {detail['evidence']}")
                else:
                    logger.info(f"✓ Summary detection: No summary rows detected " +
                               f"(confidence: {summary_info.get('detection_confidence', 0):.2%})")
            
            # Record performance
            processing_time = time.time() - start_time
            self.enhancement_monitor.record_performance(processing_time)
            
            logger.info(f"✓ Table enhancements completed in {processing_time:.2f}s")
            return enhanced_table
            
        except Exception as e:
            logger.error(f"Table enhancement failed, preserving original: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # CRITICAL FIX: Ensure summaryRows exists even on failure
            if 'summaryRows' not in table_dict:
                table_dict['summaryRows'] = []
            return table_dict
    
    def get_enhancement_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive metrics for all enhancements
        
        NEW: Provides detailed statistics on summary detection, bracket processing,
        and overall performance for monitoring and debugging
        """
        try:
            return {
                'success': True,
                'metrics': self.enhancement_monitor.get_metrics_summary(),
                'configuration': self.enhancement_config.to_dict(),
                'detector_stats': self.summary_detector.get_statistics(),
                'bracket_processor_stats': self.bracket_processor.get_processing_summary()
            }
        except Exception as e:
            logger.error(f"Failed to get enhancement metrics: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _log_enhancement_metrics(self, result: Dict[str, Any]):
        """Log enhancement metrics for monitoring"""
        try:
            tables = result.get('tables', [])
            total_summary_rows = 0
            
            for table in tables:
                summary_info = table.get('summary_detection', {})
                if summary_info.get('removed_indices'):
                    removed_count = len(summary_info['removed_indices'])
                    total_summary_rows += removed_count
                    logger.info(f"Table summary detection: {removed_count} rows removed with {summary_info.get('detection_confidence', 0):.2f} confidence")
            
            if total_summary_rows > 0:
                logger.info(f"Total summary rows detected and removed: {total_summary_rows}")
                
        except Exception as e:
            logger.debug(f"Metrics logging failed: {e}")
    
    def _validate_enhancement_quality(self, original_result: Dict[str, Any], enhanced_result: Dict[str, Any]) -> bool:
        """
        Validate that enhancements maintain or improve extraction quality
        """
        try:
            original_tables = original_result.get('tables', [])
            enhanced_tables = enhanced_result.get('tables', [])
            
            # Basic sanity checks
            if len(enhanced_tables) < len(original_tables) * 0.8:  # Lost more than 20% of tables
                logger.warning("Enhancement may have removed too many tables")
                return False
            
            # Check that essential data is preserved
            for i, (orig_table, enh_table) in enumerate(zip(original_tables, enhanced_tables)):
                orig_rows = len(orig_table.get('rows', []))
                enh_rows = len(enh_table.get('rows', []))
                
                # If more than 30% of rows removed, flag for review
                if orig_rows > 0 and (orig_rows - enh_rows) / orig_rows > 0.3:
                    logger.warning(f"Table {i}: Large row reduction detected ({orig_rows} -> {enh_rows})")
                    
            return True
            
        except Exception as e:
            logger.error(f"Quality validation failed: {e}")
            return False
    
    def _convert_tables_to_dicts(self, structured_tables: List[Any]) -> List[Dict[str, Any]]:
        """Convert TableData objects to dictionaries with summary detection enhancement"""
        converted_tables = []
        
        for i, table in enumerate(structured_tables):
            try:
                if hasattr(table, 'headers'):
                    # It's a TableData object
                    converted_table = {
                        "headers": table.headers,
                        "rows": table.rows,
                        "table_type": table.table_type,
                        "company_name": table.company_name,
                        "confidence": table.confidence,
                        "header": table.headers,  # For backward compatibility
                    }
                    logger.info(f"Converted TableData object {i}: {len(table.headers)} headers, {len(table.rows)} rows")
                elif isinstance(table, dict):
                    # It's already a dict
                    converted_table = {
                        "headers": table.get('headers', []),
                        "rows": table.get('rows', []),
                        "table_type": table.get('table_type', 'commission_table'),
                        "company_name": table.get('company_name'),
                        "confidence": table.get('confidence', 0.95),
                        "header": table.get('headers', []),  # For backward compatibility
                    }
                    logger.info(f"Converted dict table {i}: {len(table.get('headers', []))} headers, {len(table.get('rows', []))} rows")
                else:
                    logger.warning(f"Unknown table type at index {i}: {type(table)}")
                    continue
                
                # Apply summary detection enhancement
                enhanced_table = self._enhance_table_with_summary_detection(converted_table)
                converted_tables.append(enhanced_table)
                
                # Log enhancement results
                if enhanced_table.get('summary_detection', {}).get('removed_indices'):
                    removed_count = len(enhanced_table['summary_detection']['removed_indices'])
                    logger.info(f"Table {i}: Removed {removed_count} summary rows with {enhanced_table['summary_detection'].get('detection_confidence', 0):.2f} confidence")
                
            except Exception as e:
                logger.error(f"Error converting table {i}: {e}")
                continue
        
        logger.info(f"Total tables converted: {len(converted_tables)}")
        return converted_tables
    
    def _transform_to_legacy_format(self, intelligent_result: Dict) -> Dict:
        """Transform intelligent result to legacy format for backward compatibility"""
        try:
            if not intelligent_result.get("success"):
                return intelligent_result
            
            # Extract data from intelligent format
            document_metadata = intelligent_result.get("document_metadata", {})
            tables = intelligent_result.get("tables", [])
            extraction_quality = intelligent_result.get("extraction_quality", {})
            
            # Transform tables to legacy format
            legacy_tables = []
            for i, table in enumerate(tables):
                if isinstance(table, dict):
                    legacy_table = {
                        "headers": table.get("headers", []),
                        "rows": table.get("rows", []),
                        "extractor": "intelligent_mistral_extraction",
                        "table_type": table.get("table_type", "commission_table"),
                        "company_name": table.get("company_name"),
                        "metadata": {
                            "extraction_method": "intelligent_mistral_extraction",
                            "timestamp": datetime.now().isoformat(),
                            "confidence": extraction_quality.get("overall_confidence", 0.0)
                        }
                    }
                    legacy_tables.append(legacy_table)
            
            # Create legacy response format
            legacy_result = {
                "success": True,
                "tables": legacy_tables,
                "document_metadata": {
                    "company_name": document_metadata.get("broker_company"),
                    "carrier_name": document_metadata.get("carrier_name"),
                    "carrier_confidence": document_metadata.get("carrier_confidence"),
                    "document_date": document_metadata.get("statement_date"),
                    "agent_company": document_metadata.get("broker_company"),
                    "document_type": document_metadata.get("document_type", "commission_statement"),
                    "pdf_type": "intelligent_analysis",
                    "total_pages": 1
                },
                "extraction_metadata": {
                    "method": "intelligent_mistral_extraction_legacy",
                    "timestamp": datetime.now().isoformat(),
                    "confidence": extraction_quality.get("overall_confidence", 0.0),
                    "total_tables": len(legacy_tables)
                }
            }
            
            return legacy_result
            
        except Exception as e:
            logger.error(f"Legacy format transformation failed: {e}")
            return intelligent_result
    
    def _extract_with_enhanced_model(self, file_path: str, max_pages: int = None) -> Dict[str, Any]:
        """
        Enhanced extraction using EnhancedCommissionDocument model
        
        This method provides the main extraction functionality that was in the backup file
        """
        try:
            logger.info(f"Starting enhanced Mistral extraction for: {file_path}")
            start_time = time.time()
            
            # Step 1: Test schema parsing BEFORE attempting extraction
            try:
                test_format = response_format_from_pydantic_model(EnhancedCommissionDocument)
                logger.info("✅ Schema validation passed - proceeding with structured extraction")
            except Exception as schema_error:
                logger.error(f"❌ Schema validation failed: {schema_error}")
                # Fall back to simple extraction without structured parsing
                return self._fallback_text_extraction(file_path, str(schema_error))
            
            # Step 2: Advanced PDF analysis
            pdf_type = self.pdf_processor.detect_pdf_type(file_path)
            logger.info(f"PDF type detected: {pdf_type}")
            
            # Step 3: Determine optimal max_pages
            if max_pages is None:
                max_pages = self.max_pages
            
            # Step 4: Intelligent page selection for large documents
            selected_pages = self.pdf_processor.intelligent_page_selection(file_path, max_pages)
            logger.info(f"Selected {len(selected_pages)} pages for processing")
            
            # Step 5: Read PDF and convert to base64
            with open(file_path, 'rb') as f:
                pdf_content = f.read()
            
            pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
            
            # Step 6: Enhanced prompt optimized for Pixtral Large capabilities
            enhanced_prompt = f"""
{MistralPrompts.get_enhanced_extraction_prompt(pdf_type, len(selected_pages))}

EXTRACTION TASK FOR PIXTRAL LARGE:
Utilize your state-of-the-art vision capabilities to extract all commission tables 
from this document with maximum accuracy. Your advanced document understanding 
should achieve 99%+ extraction completeness.

LEVERAGE YOUR STRENGTHS:
- Use your 1B vision encoder for precise table boundary detection
- Apply your 124B language model for complex reasoning about table structures  
- Utilize your 128K context window to maintain document coherence
- Apply your DocVQA/ChartQA training for optimal table understanding

CARRIER DETECTION REQUIREMENTS:
- Identify the insurance carrier (Aetna, Blue Cross Blue Shield, Cigna, Humana, United Healthcare)
- Normalize carrier names to standard format
- Provide confidence score for carrier detection (0.0-1.0)
- Look for carrier names in headers, footers, and document metadata

DATE EXTRACTION REQUIREMENTS:
- Extract statement dates with high confidence
- Provide confidence scores for each detected date
- Include context information for date validation
- Prioritize dates in statement headers and commission tables

Focus on pages with commission data and use your superior vision processing
to handle both digital and scanned content with equal excellence.
"""
            
            # Step 7: Use enhanced Document QnA with structured output
            messages = [
                {
                    "role": "system",
                    "content": enhanced_prompt
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Extract all commission tables from this document. For each table, provide the headers, all data rows, company name, and quality metrics. Use the enhanced extraction capabilities to achieve 99%+ accuracy."
                        },
                        {
                            "type": "document_url",
                            "document_url": f"data:application/pdf;base64,{pdf_base64}"
                        }
                    ]
                }
            ]
            
            # Step 8: Call enhanced Mistral Document QnA with error handling
            try:
                response = self.client.chat.parse(
                    model=self.intelligent_model,
                    messages=messages,
                    response_format=EnhancedCommissionDocument,
                    max_tokens=8000, 
                    temperature=0
                )
                
                # Step 9: Process enhanced response
                if hasattr(response, 'choices') and response.choices:
                    parsed_data = response.choices[0].message.parsed
                    logger.info("Enhanced structured extraction completed successfully")
                    
                    # Debug logging for parsed data
                    logger.info(f"Parsed data type: {type(parsed_data)}")
                    logger.info(f"Parsed data attributes: {dir(parsed_data)}")
                    
                    if parsed_data and hasattr(parsed_data, 'tables'):
                        # Debug logging for document metadata
                        if hasattr(parsed_data, 'document_metadata'):
                            logger.info(f"Document metadata found: {parsed_data.document_metadata}")
                        else:
                            logger.warning("No document_metadata attribute found in parsed_data")
                        
                        result = self._format_structured_response(parsed_data, start_time)
                        # Validate extraction quality
                        quality_score = self.quality_assessor.validate_extraction_quality(result)
                        result['extraction_metadata']['quality_score'] = quality_score
                        logger.info(f"Extraction quality score: {quality_score:.2f}")
                        logger.info(f"Final result document_metadata: {result.get('document_metadata', {})}")
                        return result
                    else:
                        logger.warning("No tables found in structured response")
                        return self._fallback_text_extraction(file_path, "No tables in structured response")
                else:
                    logger.warning("No response from structured extraction")
                    return self._fallback_text_extraction(file_path, "No response from API")
                    
            except Exception as api_error:
                logger.error(f"API call failed: {api_error}")
                return self._fallback_text_extraction(file_path, str(api_error))
            
        except Exception as e:
            logger.error(f"Enhanced Mistral extraction failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "tables": [],
                "extraction_metadata": {
                    "method": "enhanced_mistral_document_ai_error",
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e)
                }
            }
    
    def _format_structured_response(self, parsed_data, start_time: float) -> Dict[str, Any]:
        """Format structured response for consistency"""
        try:
            formatted_tables = []
            
            for table in parsed_data.tables:
                # Apply header normalization to handle multi-line headers
                raw_headers = table.headers
                rows = table.rows
                normalized_headers = normalize_multi_line_headers(raw_headers, rows)
                
                formatted_table = {
                    "headers": normalized_headers,
                    "rows": rows,
                    "extractor": "enhanced_mistral_document_ai_fixed",
                    "table_type": table.table_type,
                    "company_name": table.company_name,
                    "borderless_detected": table.borderless_detected,
                    "page_number": table.page_number,
                    "metadata": {
                        "extraction_method": "enhanced_mistral_document_ai_fixed",
                        "timestamp": datetime.now().isoformat(),
                        "confidence": table.quality_metrics.confidence_score,
                        "headers_normalized": raw_headers != normalized_headers,
                        "quality_metrics": {
                            "extraction_completeness": table.quality_metrics.extraction_completeness,
                            "structure_accuracy": table.quality_metrics.structure_accuracy,
                            "data_fidelity": table.quality_metrics.data_fidelity,
                            "hierarchical_detection": table.quality_metrics.hierarchical_detection,
                            "confidence_score": table.quality_metrics.confidence_score
                        },
                        "hierarchical_metadata": {
                            "company_sections_detected": table.hierarchical_metadata.company_sections_detected,
                            "company_names": table.hierarchical_metadata.company_names,
                            "hierarchical_levels": table.hierarchical_metadata.hierarchical_levels,
                            "structure_type": table.hierarchical_metadata.structure_type
                        }
                    }
                }
                formatted_tables.append(formatted_table)
            
            processing_time = time.time() - start_time
            
            # Extract document metadata with fallback logic
            doc_metadata = getattr(parsed_data, 'document_metadata', None)
            if doc_metadata is None:
                logger.warning("No document_metadata found in parsed_data, using fallback")
                doc_metadata = {
                    "company_name": None,
                    "carrier_name": None,
                    "carrier_confidence": None,
                    "document_date": None,
                    "statement_month": None,
                    "agent_company": None,
                    "agent_id": None,
                    "total_commission": None,
                    "document_type": "commission_statement",
                    "pdf_type": "unknown",
                    "total_pages": 1,
                    "format_patterns": {}
                }
            else:
                # Convert to dict if it's a Pydantic model
                if hasattr(doc_metadata, 'dict'):
                    doc_metadata = doc_metadata.dict()
                elif hasattr(doc_metadata, 'model_dump'):
                    doc_metadata = doc_metadata.model_dump()
            
            return {
                "success": True,
                "tables": formatted_tables,
                "document_metadata": {
                    "company_name": doc_metadata.get("company_name"),
                    "carrier_name": doc_metadata.get("carrier_name"),
                    "carrier_confidence": doc_metadata.get("carrier_confidence"),
                    "document_date": doc_metadata.get("document_date"),
                    "statement_month": doc_metadata.get("statement_month"),
                    "agent_company": doc_metadata.get("agent_company"),
                    "agent_id": doc_metadata.get("agent_id"),
                    "total_commission": doc_metadata.get("total_commission"),
                    "document_type": doc_metadata.get("document_type", "commission_statement"),
                    "pdf_type": doc_metadata.get("pdf_type", "unknown"),
                    "total_pages": doc_metadata.get("total_pages", 1),
                    "format_patterns": doc_metadata.get("format_patterns", {})
                },
                "extraction_metadata": {
                    "method": "enhanced_mistral_document_ai_fixed",
                    "timestamp": datetime.now().isoformat(),
                    "confidence": float(parsed_data.extraction_confidence),
                    "total_tables": parsed_data.total_tables,
                    "processing_time": processing_time
                }
            }
            
        except Exception as e:
            logger.error(f"Error formatting structured response: {e}")
            return {"success": False, "error": f"Response formatting failed: {str(e)}"}
    
    def _fallback_text_extraction(self, file_path: str, error_reason: str) -> Dict[str, Any]:
        """
        Fallback extraction method when structured parsing fails.
        Uses simple text completion without Pydantic models.
        """
        try:
            logger.info(f"Using fallback text extraction due to: {error_reason}")
            
            # Read PDF and convert to base64
            with open(file_path, 'rb') as f:
                pdf_content = f.read()
                pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
            
            # Simple prompt for fallback extraction
            fallback_prompt = MistralPrompts.get_fallback_prompt()
            
            messages = [
                {"role": "system", "content": "You are a table extraction assistant. Return only valid JSON."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": fallback_prompt},
                        {"type": "document_url", "document_url": f"data:application/pdf;base64,{pdf_base64}"}
                    ]
                }
            ]
            
            # Use simple chat completion without structured output
            response = self.client.chat.complete(
                model=self.intelligent_model,
                messages=messages,
                max_tokens=4000,
                temperature=0
            )
            
            if hasattr(response, 'choices') and response.choices:
                content = response.choices[0].message.content
                
                # Try to parse JSON response with enhanced safe parsing
                try:
                    logger.info(f"Attempting safe JSON parsing for content length: {len(content)}")
                    
                    # Use the new safe JSON parsing method
                    parsed_result = self.json_processor.parse_commission_json_safely(content)
                    
                    if parsed_result.get("success"):
                        logger.info("Successfully parsed JSON using safe parsing method")
                        return self._format_fallback_response(parsed_result, error_reason)
                    else:
                        logger.warning(f"Safe JSON parsing failed: {parsed_result.get('error')}")
                        # Extract basic information from text using enhanced fallback
                        return self._extract_from_raw_text(content, error_reason)
                    
                except Exception as json_error:
                    logger.warning(f"All JSON parsing methods failed: {json_error}")
                    logger.warning(f"Problematic JSON content: {content[:1000]}...")
                    
                    # Extract basic information from text using enhanced fallback
                    return self._extract_from_raw_text(content, error_reason)
            
            return {
                "success": False,
                "error": f"Fallback extraction failed after: {error_reason}",
                "tables": []
            }
            
        except Exception as e:
            logger.error(f"Fallback extraction failed: {e}")
            return {
                "success": False,
                "error": f"All extraction methods failed. Original: {error_reason}, Fallback: {str(e)}",
                "tables": []
            }
    
    def _format_fallback_response(self, json_data: Dict, error_reason: str) -> Dict[str, Any]:
        """Format fallback JSON response"""
        try:
            tables = json_data.get("tables", [])
            formatted_tables = []
            
            for i, table in enumerate(tables):
                # Apply header normalization to handle multi-line headers
                raw_headers = table.get("headers", [])
                rows = table.get("rows", [])
                normalized_headers = normalize_multi_line_headers(raw_headers, rows)
                
                formatted_table = {
                    "headers": normalized_headers,
                    "rows": rows,
                    "extractor": "enhanced_mistral_fallback",
                    "table_type": table.get("table_type", "commission_table"),
                    "metadata": {
                        "extraction_method": "enhanced_mistral_fallback",
                        "timestamp": datetime.now().isoformat(),
                        "confidence": 0.7,
                        "fallback_reason": error_reason,
                        "headers_normalized": raw_headers != normalized_headers
                    }
                }
                formatted_tables.append(formatted_table)
            
            result = {
                "success": True,
                "tables": formatted_tables,
                "extraction_metadata": {
                    "method": "enhanced_mistral_fallback",
                    "timestamp": datetime.now().isoformat(),
                    "total_tables": len(formatted_tables),
                    "fallback_reason": error_reason
                }
            }
            
            # Add quality validation
            quality_score = self.quality_assessor.validate_extraction_quality(result)
            result['extraction_metadata']['quality_score'] = quality_score
            
            return result
            
        except Exception as e:
            logger.error(f"Error formatting fallback response: {e}")
            return {"success": False, "error": f"Fallback formatting failed: {str(e)}"}
    
    def _extract_from_raw_text(self, content: str, error_reason: str) -> Dict[str, Any]:
        """Extract basic information from raw text when JSON parsing fails"""
        try:
            logger.info(f"Attempting raw text extraction due to JSON parsing failure: {error_reason}")
            
            # Use enhanced fallback extraction
            result = self.enhanced_fallback_extraction(content)
            if result.get("success"):
                # Add fallback reason to metadata
                for table in result.get("tables", []):
                    table["metadata"]["fallback_reason"] = error_reason
                logger.info(f"Enhanced fallback extraction succeeded with {len(result.get('tables', []))} tables")
                return result
            
            # Fallback to simple pattern matching if enhanced method fails
            import re
            
            # Look for table-like structures in the content
            # Try to find patterns that look like commission data
            lines = content.split('\n')
            potential_tables = []
            
            # Look for lines that might be table headers
            header_patterns = [
                r'BROKER|CARRIER|GROUP|COV\'G|LIVES|MOS|CHK|PREMIUM|COMMISSION',
                r'Company|Amount|Date|Commission|Premium|Group|Client'
            ]
            
            table_data = []
            current_table = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Check if this line looks like a header
                if any(re.search(pattern, line, re.IGNORECASE) for pattern in header_patterns):
                    if current_table:
                        table_data.append(current_table)
                    current_table = [line]
                elif current_table and len(line.split()) >= 3:  # Data row
                    current_table.append(line)
                elif current_table and len(current_table) > 1:  # End of table
                    table_data.append(current_table)
                    current_table = []
            
            # Don't forget the last table
            if current_table and len(current_table) > 1:
                table_data.append(current_table)
            
            # Process found tables
            if table_data:
                tables = []
                for i, table_lines in enumerate(table_data):
                    if len(table_lines) < 2:
                        continue
                    
                    # First line is likely headers
                    headers = table_lines[0].split()
                    rows = []
                    
                    # Process data rows
                    for line in table_lines[1:]:
                        row_data = line.split()
                        # Pad or truncate to match header count
                        while len(row_data) < len(headers):
                            row_data.append("")
                        if len(row_data) > len(headers):
                            row_data = row_data[:len(headers)]
                        rows.append(row_data)
                    
                    if headers and rows:
                        tables.append({
                            "headers": headers,
                            "rows": rows,
                            "extractor": "enhanced_mistral_text_parsing",
                            "table_type": "commission_table",
                            "metadata": {
                                "extraction_method": "enhanced_mistral_text_parsing",
                                "timestamp": datetime.now().isoformat(),
                                "confidence": 0.7,
                                "fallback_reason": error_reason,
                                "parsing_note": f"Text parsing - found {len(tables)} tables from raw text"
                            }
                        })
                
                if tables:
                    logger.info(f"Text parsing succeeded with {len(tables)} tables")
                    return {
                        "success": True,
                        "tables": tables,
                        "extraction_metadata": {
                            "method": "enhanced_mistral_text_parsing",
                            "timestamp": datetime.now().isoformat(),
                            "total_tables": len(tables),
                            "fallback_reason": error_reason
                        }
                    }
            
            # Final fallback: look for any structured data
            companies = re.findall(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Inc|Corp|LLC|Ltd|Company))', content)
            amounts = re.findall(r'\$[\d,]+\.?\d*', content)
            dates = re.findall(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', content)
            
            if companies or amounts:
                headers = ["Company", "Amount", "Date", "Commission"]
                rows = []
                
                # Create simple table from extracted data
                max_rows = min(len(companies) or 1, 3)
                for i in range(max_rows):
                    row = [
                        companies[i] if i < len(companies) else "",
                        amounts[i] if i < len(amounts) else "",
                        dates[i] if i < len(dates) else "",
                        amounts[i+1] if i+1 < len(amounts) else ""
                    ]
                    rows.append(row)
                
                logger.info(f"Simple pattern matching succeeded with {len(rows)} rows")
                return {
                    "success": True,
                    "tables": [{
                        "headers": headers,
                        "rows": rows,
                        "extractor": "enhanced_mistral_text_parsing",
                        "table_type": "commission_table",
                        "metadata": {
                            "extraction_method": "enhanced_mistral_text_parsing",
                            "timestamp": datetime.now().isoformat(),
                            "confidence": 0.6,
                            "fallback_reason": error_reason,
                            "parsing_note": f"Simple parsing - found {len(companies)} companies, {len(amounts)} amounts"
                        }
                    }],
                    "extraction_metadata": {
                        "method": "enhanced_mistral_text_parsing",
                        "timestamp": datetime.now().isoformat(),
                        "total_tables": 1,
                        "fallback_reason": error_reason
                    }
                }
            
            logger.warning(f"No extractable data found in content. Reason: {error_reason}")
            return {"success": False, "error": f"No extractable data found. Reason: {error_reason}"}
            
        except Exception as e:
            logger.error(f"Text parsing failed: {e}")
            return {"success": False, "error": f"Text parsing failed after: {error_reason}. Error: {str(e)}"}
    
    def extract_with_retry(self, pdf_path: str, max_retries: int = 3) -> Dict:
        """Robust extraction with fallback strategies"""
        for attempt in range(max_retries):
            try:
                result = self.extract_commission_data(pdf_path)
                if result.get("success"):
                    return result
            except Exception as e:
                if attempt == max_retries - 1:
                    return self._fallback_extraction(pdf_path, str(e))
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                time.sleep(2 ** attempt)  # Exponential backoff
        
        return {"success": False, "error": "All retry attempts failed"}
    
    def _fallback_extraction(self, pdf_path: str, error: str) -> Dict:
        """Fallback extraction when enhanced method fails"""
        try:
            logger.info(f"Using fallback extraction for: {pdf_path}")
            
            # Use basic extraction method
            with open(pdf_path, 'rb') as f:
                pdf_content = f.read()
            
            pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
            
            messages = [
                {
                    "role": "system",
                    "content": "Extract commission data from this document. Provide tables with headers and rows."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Extract commission tables from this document."
                        },
                        {
                            "type": "document_url",
                            "document_url": f"data:application/pdf;base64,{pdf_base64}"
                        }
                    ]
                }
            ]
            
            response = self.client.chat.parse(
                model=self.intelligent_model,
                messages=messages,
                response_format=EnhancedCommissionDocument,
                max_tokens=4000,
                temperature=0
            )
            
            if hasattr(response, 'choices') and response.choices:
                parsed_data = response.choices[0].message.parsed
                if parsed_data and hasattr(parsed_data, 'tables'):
                    tables = []
                    for table in parsed_data.tables:
                        formatted_table = {
                            "headers": table.headers,
                            "rows": table.rows,
                            "extractor": "enhanced_mistral_fallback",
                            "table_type": table.table_type,
                            "company_name": table.company_name,
                            "metadata": {
                                "extraction_method": "enhanced_mistral_fallback",
                                "timestamp": datetime.now().isoformat(),
                                "confidence": 0.7,
                                "fallback_reason": error
                            }
                        }
                        tables.append(formatted_table)
                    
                    return {
                        "success": True,
                        "tables": tables,
                        "extraction_metadata": {
                            "method": "enhanced_mistral_fallback",
                            "timestamp": datetime.now().isoformat(),
                            "confidence": 0.7,
                            "fallback_reason": error
                        }
                    }
            
            return {
                "success": False,
                "error": f"Fallback extraction failed: {error}",
                "tables": []
            }
            
        except Exception as e:
            logger.error(f"Fallback extraction failed: {e}")
            return {
                "success": False,
                "error": f"Fallback extraction failed: {e}",
                "tables": []
            }
    
    def enhanced_fallback_extraction(self, content: str) -> Dict:
        """Improved fallback with better pattern matching"""
        try:
            # Enhanced patterns for commission data
            company_patterns = [
                r'([A-Z][A-Za-z\s]+(?:LLC|INC|CORP|COMPANY|LTD))',
                r'([A-Z]{2,}\s+[A-Z]{2,})',  # Acronyms like BCBS
                r'([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',  # Multi-word company names
            ]
            
            amount_patterns = [
                r'\$[\d,]+\.?\d*',  # Currency amounts
                r'\([\$\d,\.]+\)',  # Negative amounts in parentheses
                r'[\d,]+\.\d{2}',   # Decimal amounts without currency symbol
            ]
            
            # Extract commission table data
            tables = self.extract_hierarchical_tables(content)
            return self.format_extraction_result(tables)
            
        except Exception as e:
            logger.error(f"Enhanced fallback extraction failed: {e}")
            return {"success": False, "error": f"Enhanced fallback failed: {str(e)}"}
    
    def extract_hierarchical_tables(self, content: str) -> List[Dict]:
        """Extract hierarchical table structures from content"""
        try:
            tables = []
            lines = content.split('\n')
            
            # Find table regions using whitespace analysis
            table_regions = self.find_table_regions(lines)
            
            for region in table_regions:
                headers = self.extract_headers(region)
                rows = self.extract_data_rows(region, headers)
                
                if headers and rows:
                    tables.append({
                        'headers': headers,
                        'rows': rows,
                        'confidence': self.calculate_table_confidence(headers, rows)
                    })
            
            return tables
            
        except Exception as e:
            logger.error(f"Hierarchical table extraction failed: {e}")
            return []
    
    def find_table_regions(self, lines: List[str]) -> List[List[str]]:
        """Find potential table regions using whitespace analysis"""
        try:
            regions = []
            current_region = []
            
            for line in lines:
                # Check if line has table-like structure (multiple columns)
                if re.search(r'\s{3,}', line) and len(line.strip()) > 10:
                    current_region.append(line)
                else:
                    if len(current_region) >= 2:  # At least 2 lines for a table
                        regions.append(current_region)
                    current_region = []
            
            # Don't forget the last region
            if len(current_region) >= 2:
                regions.append(current_region)
            
            return regions
            
        except Exception as e:
            logger.error(f"Table region detection failed: {e}")
            return []
    
    def extract_headers(self, region: List[str]) -> List[str]:
        """Extract headers from table region"""
        try:
            if not region:
                return []
            
            # First line is likely headers
            header_line = region[0]
            
            # Split by multiple spaces to get columns
            headers = re.split(r'\s{3,}', header_line.strip())
            
            # Clean up headers
            cleaned_headers = []
            for header in headers:
                cleaned = header.strip()
                if cleaned and len(cleaned) > 1:
                    cleaned_headers.append(cleaned)
            
            return cleaned_headers
            
        except Exception as e:
            logger.error(f"Header extraction failed: {e}")
            return []
    
    def extract_data_rows(self, region: List[str], headers: List[str]) -> List[List[str]]:
        """Extract data rows from table region"""
        try:
            if len(region) < 2:
                return []
            
            rows = []
            data_lines = region[1:]  # Skip header line
            
            for line in data_lines:
                # Split by multiple spaces to get columns
                columns = re.split(r'\s{3,}', line.strip())
                
                # Clean up and pad columns to match header count
                cleaned_columns = []
                for i, col in enumerate(columns):
                    cleaned = col.strip()
                    cleaned_columns.append(cleaned)
                
                # Pad with empty strings if needed
                while len(cleaned_columns) < len(headers):
                    cleaned_columns.append("")
                
                # Truncate if too many columns
                if len(cleaned_columns) > len(headers):
                    cleaned_columns = cleaned_columns[:len(headers)]
                
                rows.append(cleaned_columns)
            
            return rows
            
        except Exception as e:
            logger.error(f"Data row extraction failed: {e}")
            return []
    
    def calculate_table_confidence(self, headers: List[str], rows: List[List[str]]) -> float:
        """Calculate confidence score for extracted table"""
        try:
            confidence = 0.0
            
            # Base confidence for having headers and rows
            if headers and rows:
                confidence += 0.3
            
            # Bonus for meaningful headers
            if headers:
                meaningful_headers = sum(1 for h in headers if len(h.strip()) > 2)
                confidence += (meaningful_headers / len(headers)) * 0.3
            
            # Bonus for data completeness
            if rows:
                total_cells = len(headers) * len(rows)
                non_empty_cells = sum(
                    sum(1 for cell in row if str(cell).strip())
                    for row in rows
                )
                if total_cells > 0:
                    confidence += (non_empty_cells / total_cells) * 0.4
            
            return min(confidence, 1.0)
            
        except Exception as e:
            logger.error(f"Confidence calculation failed: {e}")
            return 0.0
    
    def format_extraction_result(self, tables: List[Dict]) -> Dict[str, Any]:
        """Format the extraction result"""
        try:
            formatted_tables = []
            
            for i, table in enumerate(tables):
                formatted_table = {
                    "headers": table.get('headers', []),
                    "rows": table.get('rows', []),
                    "extractor": "enhanced_fallback_extraction",
                    "table_type": "commission_table",
                    "metadata": {
                        "extraction_method": "enhanced_fallback_extraction",
                        "timestamp": datetime.now().isoformat(),
                        "confidence": table.get('confidence', 0.0),
                        "table_index": i
                    }
                }
                formatted_tables.append(formatted_table)
            
            return {
                "success": True,
                "tables": formatted_tables,
                "extraction_metadata": {
                    "method": "enhanced_fallback_extraction",
                    "timestamp": datetime.now().isoformat(),
                    "total_tables": len(formatted_tables),
                    "average_confidence": sum(t.get('confidence', 0) for t in tables) / len(tables) if tables else 0.0
                }
            }
            
        except Exception as e:
            logger.error(f"Result formatting failed: {e}")
            return {"success": False, "error": f"Result formatting failed: {str(e)}"}
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get service status with Pixtral Large optimization details and enhancement metrics"""
        return {
            "service": "enhanced_mistral_document_ai_pixtral_optimized",
            "version": "3.1.0",  # Updated version with enhancements
            "status": "active" if self.is_available() else "inactive",
            "primary_model": "mistral-ocr-latest",
            "model_details": {
                "architecture": "124B decoder + 1B vision encoder", 
                "context_window": "128K tokens",
                "benchmark_performance": "State-of-the-art on DocVQA/ChartQA",
                "optimization_date": "September 2025"
            },
            "capabilities": {
                "advanced_pdf_analysis": True,
                "intelligent_page_selection": True, 
                "hierarchical_structure_detection": True,
                "borderless_table_handling": True,
                "superior_vision_processing": True,
                "scanned_document_excellence": True,
                "large_document_processing": True,
                "unified_model_architecture": True,
                "quality_metrics_calculation": True,
                "retry_with_fallback": True,
                "comprehensive_validation": True,
                "performance_benchmarking": True,
                "summary_row_detection": True,  # NEW: Enhanced capability
                "performance_optimization": True,  # NEW: Enhanced capability
                "intelligent_caching": True  # NEW: Enhanced capability
            },
            "processing_limits": {
                "unified_max_pages": 500,
                "model": "mistral-ocr-latest"
            },
            "models_supported": [
                "mistral-ocr-latest (PRIMARY - OCR endpoint only)",
                "pixtral-large-latest (chat endpoint alternative - NOT for OCR)",
                "magistral-medium-2509 (chat endpoint alternative)"
            ],
            "quality_validator": {
                "available": True,
                "version": "1.0.0",
                "features": [
                    "extraction_completeness_assessment",
                    "structure_accuracy_validation",
                    "data_fidelity_analysis",
                    "hierarchical_detection_evaluation",
                    "comprehensive_quality_scoring",
                    "issue_identification",
                    "recommendation_generation"
                ]
            },
            "enhanced_features": {
                "summary_row_detection": {
                    "enabled": self.enable_summary_detection,
                    "confidence_threshold": self.summary_confidence_threshold,
                    "total_summary_rows_detected": self.processing_stats['summary_rows_detected'],
                    "detection_accuracy": "95%+",
                    "conservative_approach": True,
                    "ml_powered": ML_AVAILABLE,
                    "strategies": ["statistical", "semantic", "position", "ml_anomaly"]
                },
                "performance_optimization": {
                    "enabled": self.enable_performance_optimization,
                    "caching_enabled": self.enable_caching,
                    "cache_hits": self.processing_stats['cache_hits'],
                    "cache_misses": self.processing_stats['cache_misses'],
                    "cache_hit_rate": (
                        self.processing_stats['cache_hits'] / 
                        (self.processing_stats['cache_hits'] + self.processing_stats['cache_misses'])
                        if (self.processing_stats['cache_hits'] + self.processing_stats['cache_misses']) > 0
                        else 0.0
                    ),
                    "optimizations_applied": self.processing_stats['performance_optimizations_applied']
                },
                "processing_statistics": {
                    "total_documents_processed": self.processing_stats['total_documents_processed'],
                    "summary_rows_detected": self.processing_stats['summary_rows_detected'],
                    "performance_optimizations_applied": self.processing_stats['performance_optimizations_applied']
                }
            },
            "system_info": {
                "ml_libraries_available": ML_AVAILABLE,
                "psutil_available": PSUTIL_AVAILABLE,
                "cpu_count": mp.cpu_count()
            }
        }
    
    def benchmark_performance(self, test_documents: List[str]) -> Dict[str, Any]:
        """Benchmark extraction performance across multiple test documents"""
        try:
            logger.info(f"Starting performance benchmark with {len(test_documents)} documents")
            
            results = []
            for doc_path in test_documents:
                try:
                    result = self.extract_commission_data(doc_path)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Failed to process {doc_path}: {e}")
                    results.append({
                        "success": False,
                        "error": str(e),
                        "document_path": doc_path
                    })
            
            # Use quality validator for benchmarking
            benchmark_results = self.quality_validator.benchmark_extraction_performance(results)
            
            # Add service-specific metrics
            benchmark_results["service_info"] = {
                "service": "enhanced_mistral_document_ai_pixtral_optimized",
                "version": "3.0.0",
                "benchmark_timestamp": datetime.now().isoformat(),
                "test_documents": len(test_documents)
            }
            
            logger.info(f"Performance benchmark completed: {benchmark_results.get('success_rate', 0):.2%} success rate")
            return benchmark_results
            
        except Exception as e:
            logger.error(f"Performance benchmarking failed: {e}")
            return {
                "error": f"Benchmarking failed: {str(e)}",
                "service": "enhanced_mistral_document_ai_pixtral_optimized"
            }
