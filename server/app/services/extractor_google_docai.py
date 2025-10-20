import os
import sys
import json
import logging
import base64
import random
import time
from typing import Dict, List, Any, Optional, Tuple, TYPE_CHECKING
from datetime import datetime
import io

# Google Document AI imports
try:
    from google.cloud import documentai_v1 as documentai
    from google.cloud import storage
    from google.auth import default
    GOOGLE_DOCAI_AVAILABLE = True
except ImportError:
    GOOGLE_DOCAI_AVAILABLE = False
    print("Warning: Google Document AI not available. Install with: pip install google-cloud-documentai google-cloud-storage google-auth")

# Local service imports
from .company_name_service import CompanyNameDetectionService

# Critical Configuration Parameters
HEADER_CONFIDENCE_THRESHOLD = 0.3
CELL_CONFIDENCE_THRESHOLD = 0.2
PATTERN_MATCH_THRESHOLD = 0.6
HEADER_SIMILARITY_THRESHOLD = 0.8

# Processing parameters
MAX_RETRIES = 3


def extract_rows_from_tableblock(tableblock: Dict[str, Any]) -> Tuple[List[str], List[List[str]]]:
    """
    Extract headers and rows from a Google Document AI tableBlock object.
    
    This adapter function handles Document AI's Layout Parser JSON output format:
    tableBlock → bodyRows → cells → blocks → textBlock structure.
    
    Args:
        tableblock: Dictionary representing a tableBlock from Document AI Layout Parser
        
    Returns:
        Tuple of (headers, rows) where:
        - headers: List of strings representing column headers
        - rows: List of lists of strings representing table data rows
    """
    try:
        headers = []
        rows = []
        
        # Extract header rows if present
        header_rows = tableblock.get("headerRows", [])
        if header_rows:
            for header_row in header_rows:
                row_cells = []
                for cell in header_row.get("cells", []):
                    cell_text = ""
                    # Extract text from all blocks in the cell
                    for block in cell.get("blocks", []):
                        if "textBlock" in block and "text" in block["textBlock"]:
                            cell_text += block["textBlock"]["text"] + " "
                    row_cells.append(cell_text.strip())
                if row_cells:
                    headers.extend(row_cells)
        
        # Extract body rows
        body_rows = tableblock.get("bodyRows", [])
        for body_row in body_rows:
            row_cells = []
            for cell in body_row.get("cells", []):
                cell_text = ""
                # Extract text from all blocks in the cell
                for block in cell.get("blocks", []):
                    if "textBlock" in block and "text" in block["textBlock"]:
                        cell_text += block["textBlock"]["text"] + " "
                row_cells.append(cell_text.strip())
            if row_cells:
                rows.append(row_cells)
        
        # If no headers were extracted, try to use first row as headers
        if not headers and rows:
            headers = rows[0]
            rows = rows[1:]
        
        # Ensure all rows have the same number of columns as headers
        if headers:
            max_cols = len(headers)
            normalized_rows = []
            for row in rows:
                # Pad with empty strings if row has fewer columns
                normalized_row = row[:max_cols] + [""] * (max_cols - len(row))
                normalized_rows.append(normalized_row)
            rows = normalized_rows
        
        return headers, rows
        
    except Exception as e:
        print(f"Error extracting rows from tableBlock: {e}")
        return [], []


def adapt_tableblock_to_standard_format(tableblock: Dict[str, Any], page_num: int = 0, table_index: int = 0) -> Dict[str, Any]:
    """
    Adapt a Google Document AI tableBlock to the standard table format expected by utilities.
    
    Args:
        tableblock: Dictionary representing a tableBlock from Document AI Layout Parser
        page_num: Page number where the table was found
        table_index: Index of the table on the page
        
    Returns:
        Standard table dictionary with headers, rows, and metadata
    """
    try:
        # Extract headers and rows using the adapter
        headers, rows = extract_rows_from_tableblock(tableblock)
        
        # Generate default headers if none were detected
        if not headers and rows:
            max_cols = max(len(row) for row in rows) if rows else 0
            headers = [f"Column_{i+1}" for i in range(max_cols)]
        
        # Extract metadata from tableBlock
        confidence = tableblock.get("confidence", 0.0)
        bbox = tableblock.get("boundingBox", {})
        
        # Convert bbox format if present
        bbox_dict = {}
        if bbox and "vertices" in bbox:
            vertices = bbox["vertices"]
            if len(vertices) >= 4:
                bbox_dict = {
                    "x0": vertices[0].get("x", 0),
                    "y0": vertices[0].get("y", 0),
                    "x1": vertices[2].get("x", 0),
                    "y1": vertices[2].get("y", 0)
                }
        
        # Create standard table format
        table_dict = {
            "header": headers,  # Fixed: use "header" to match frontend expectations
            "rows": rows,
            "confidence": confidence,
            "bbox": bbox_dict,
            "page_number": page_num + 1,
            "table_index": table_index,
            "extractor": "google_docai_layout_parser",
            "metadata": {
                "page_number": page_num + 1,
                "table_index": table_index,
                "extraction_method": "google_docai_layout_parser",
                "timestamp": datetime.now().isoformat(),
                "source_format": "tableBlock"
            }
        }
        
        return table_dict
        
    except Exception as e:
        print(f"Error adapting tableBlock to standard format: {e}")
        return {
            "header": [],  # Fixed: use "header" to match frontend expectations
            "rows": [],
            "confidence": 0.0,
            "bbox": {},
            "page_number": page_num + 1,
            "table_index": table_index,
            "extractor": "google_docai_layout_parser",
            "metadata": {
                "page_number": page_num + 1,
                "table_index": table_index,
                "extraction_method": "google_docai_layout_parser",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
        }


class GoogleDocAIExtractor:
    """
    Google Document AI extractor for PDF documents.
    
    Features:
    - Direct PDF processing without image conversion
    - Form Parser with table detection and form field extraction
    - Table detection and extraction from forms and documents
    - Whitespace analysis and spatial clustering (fallback)
    - Multiple output formats (JSON, HTML, CSV)
    - Confidence scoring and annotation
    - Automatic format detection and adaptation
    - JSON response logging for debugging
    """
    
    def __init__(self):
        self.name = "google_docai"
        self.description = "Google Document AI Form Parser for scanned PDFs with table detection"
        self.client = None
        self.project_id = None
        self.location = "us"  # or "eu"
        self.processor_id = None
        self.company_detector = CompanyNameDetectionService()
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Google Document AI client."""
        if not GOOGLE_DOCAI_AVAILABLE:
            print("❌ Google Document AI SDK not available")
            return
        
        try:
            # Set up environment variables if not already set
            if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
                # Look for the credentials file in multiple possible locations
                possible_paths = [
                    # Render secrets directory (production - root access)
                    "/etc/secrets/pdf-tables-extractor-465009-d9172fd0045d.json",
                    # Docker container path (production - fallback)
                    "/app/pdf-tables-extractor-465009-d9172fd0045d.json",
                    # Local development path (your server directory)
                    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "pdf-tables-extractor-465009-d9172fd0045d.json"),
                    # Current working directory
                    os.path.join(os.getcwd(), "pdf-tables-extractor-465009-d9172fd0045d.json"),
                ]
                
                creds_file = None
                for path in possible_paths:
                    if os.path.exists(path):
                        creds_file = path
                        break
                
                if creds_file:
                    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_file
                    print(f"✅ Set GOOGLE_APPLICATION_CREDENTIALS to: {creds_file}")
                else:
                    print(f"❌ Credentials file not found. Tried paths: {possible_paths}")
                    return
            
            # Set project ID if not already set
            if not os.getenv("GOOGLE_CLOUD_PROJECT_ID"):
                os.environ["GOOGLE_CLOUD_PROJECT_ID"] = "pdf-tables-extractor-465009"
                print("✅ Set GOOGLE_CLOUD_PROJECT_ID to: pdf-tables-extractor-465009")
            
            # Set processor ID if not already set
            if not os.getenv("GOOGLE_DOCAI_PROCESSOR_ID"):
                os.environ["GOOGLE_DOCAI_PROCESSOR_ID"] = "521303e404fb7809"
                print("✅ Set GOOGLE_DOCAI_PROCESSOR_ID to: 521303e404fb7809")
            
            # Get credentials from environment
            credentials, self.project_id = default()
            
            if not self.project_id:
                self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID")
            
            if not self.project_id:
                print("❌ Google Cloud Project ID not found. Set GOOGLE_CLOUD_PROJECT_ID environment variable")
                return
            
            # Initialize Document AI client
            self.client = documentai.DocumentProcessorServiceClient(
                credentials=credentials
            )
            
            # Get processor ID from environment
            self.processor_id = os.getenv("GOOGLE_DOCAI_PROCESSOR_ID", "521303e404fb7809")
            
            # Construct processor name
            self.processor_name = self.client.processor_path(
                self.project_id, self.location, self.processor_id
            )
            
            print(f"✅ Google Document AI initialized - Project: {self.project_id}, Processor: {self.processor_id}")
            
        except Exception as e:
            print(f"❌ Failed to initialize Google Document AI: {e}")
            self.client = None
    
    def is_available(self) -> bool:
        """Check if Google Document AI is available and properly configured."""
        return (
            GOOGLE_DOCAI_AVAILABLE and 
            self.client is not None and 
            self.project_id is not None
        )
    
    def extract_tables(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extract tables from PDF using Google Document AI with smart page handling.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of extracted tables with metadata
        """
        if not self.is_available():
            raise Exception("Google Document AI not available or not properly configured")
        
        try:
            print(f"🔍 Google Document AI: Processing {pdf_path}")
            import sys
            sys.stdout.flush()  # Force flush the output
            
            # Read the PDF file directly
            with open(pdf_path, "rb") as pdf_file:
                pdf_content = pdf_file.read()
            
            # Get page count to determine processing strategy
            page_count = self._get_pdf_page_count(pdf_content)
            print(f"📄 Google Document AI: Document has {page_count} pages")
            
            # **ENHANCED DEBUGGING: Track processing strategy and results**
            processing_mode = "unknown"
            tables = []
            
            # Determine processing strategy based on page count
            if page_count <= 15:
                # Use regular mode for small documents
                processing_mode = "regular"
                print("🔄 Google Document AI: Using regular mode (≤15 pages)")
                tables = self._process_document_regular_mode(pdf_content)
                print(f"✅ Google Document AI: Regular mode extracted {len(tables)} tables")
                
            elif page_count <= 30:
                # Use imageless mode for medium documents
                processing_mode = "imageless"
                print(f"🔄 Google Document AI: Using imageless mode ({page_count} pages)")
                try:
                    tables = self._process_document_imageless_mode(pdf_content)
                    print(f"✅ Google Document AI: Imageless mode extracted {len(tables)} tables")
                except Exception as e:
                    if "PAGE_LIMIT_EXCEEDED" in str(e) or "page limit" in str(e).lower():
                        processing_mode = "chunked"
                        print(f"⚠️ Google Document AI: Imageless mode failed, falling back to chunked processing")
                        tables = self._process_document_in_chunks(pdf_content, page_count)
                        print(f"✅ Google Document AI: Chunked processing extracted {len(tables)} tables")
                    else:
                        print(f"❌ Google Document AI: Imageless mode failed with non-page-limit error: {e}")
                        raise
                        
            else:
                # Use chunked processing for large documents
                processing_mode = "chunked"
                print(f"🔄 Google Document AI: Using chunked processing ({page_count} pages)")
                tables = self._process_document_in_chunks(pdf_content, page_count)
                print(f"✅ Google Document AI: Chunked processing extracted {len(tables)} tables")
            
            # **ENHANCED DEBUGGING: Calculate extraction metrics**
            tables_per_page = len(tables) / page_count if page_count > 0 else 0
            total_rows = sum(len(table.get('rows', [])) for table in tables)
            avg_rows_per_table = total_rows / len(tables) if tables else 0
            
            print(f"📊 EXTRACTION METRICS:")
            print(f"   Processing mode: {processing_mode}")
            print(f"   Total pages: {page_count}")
            print(f"   Tables extracted: {len(tables)}")
            print(f"   Tables per page: {tables_per_page:.3f}")
            print(f"   Total rows: {total_rows}")
            print(f"   Average rows per table: {avg_rows_per_table:.1f}")
            
            # **ALERT: Check for suspicious extraction patterns**
            if page_count > 15 and len(tables) < 5:
                print(f"⚠️ ALERT: Large document ({page_count} pages) with very few tables ({len(tables)})")
                print(f"   Expected: 15-{page_count*3} tables, Got: {len(tables)} tables")
            elif tables_per_page < 0.5:
                print(f"⚠️ ALERT: Low table density ({tables_per_page:.3f} tables/page)")
                print(f"   Expected: 0.5-3.0 tables/page for commission statements")
            elif avg_rows_per_table > 50:
                print(f"⚠️ ALERT: Unusually large tables ({avg_rows_per_table:.1f} rows/table)")
                print(f"   This may indicate over-aggressive table merging")
            
            print(f"📊 Google Document AI: Found {len(tables)} tables in document")
            sys.stdout.flush()
            
            # **NEW: Apply table merging to consolidate similar tables**
            if len(tables) > 1:
                print(f"🔗 Google Document AI: Applying table merging to {len(tables)} tables")
                try:
                    from .extraction_utils import stitch_multipage_tables
                    merged_tables = stitch_multipage_tables(tables)
                    print(f"🔗 Google Document AI: Table merging completed: {len(tables)} → {len(merged_tables)} tables")
                    
                    # Update metrics after merging
                    merged_tables_per_page = len(merged_tables) / page_count if page_count > 0 else 0
                    merged_total_rows = sum(len(table.get('rows', [])) for table in merged_tables)
                    merged_avg_rows_per_table = merged_total_rows / len(merged_tables) if merged_tables else 0
                    
                    print(f"📊 MERGED EXTRACTION METRICS:")
                    print(f"   Tables after merging: {len(merged_tables)}")
                    print(f"   Tables per page: {merged_tables_per_page:.3f}")
                    print(f"   Total rows: {merged_total_rows}")
                    print(f"   Average rows per table: {merged_avg_rows_per_table:.1f}")
                    
                    tables = merged_tables
                    
                except Exception as e:
                    print(f"⚠️ Warning: Table merging failed: {e}")
                    print(f"   Proceeding with original {len(tables)} tables")
            
            # Log extraction method used
            form_parser_count = sum(1 for table in tables if table.get("metadata", {}).get("extraction_method") == "google_docai_form_parser")
            spatial_count = len(tables) - form_parser_count
            
            if form_parser_count > 0:
                print(f"✅ Google Document AI: Extracted {len(tables)} tables ({form_parser_count} using Form Parser, {spatial_count} using spatial clustering)")
            else:
                print(f"✅ Google Document AI: Extracted {len(tables)} tables using spatial clustering")
            sys.stdout.flush()
            
            return tables
            
        except Exception as e:
            print(f"❌ Google Document AI extraction failed: {e}")
            raise

    async def extract_tables_async(self, pdf_path: str) -> Dict[str, Any]:
        """
        Async wrapper for extract_tables method.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary with extraction results
        """
        import asyncio
        
        # Run the synchronous extract_tables method in a thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self.extract_tables, pdf_path)
        
        # Convert the result to the expected format
        if isinstance(result, list):
            # If result is a list of tables, wrap it in the expected format
            return {
                "success": True,
                "tables": result,
                "extraction_metadata": {
                    "method": "google_docai",
                    "timestamp": datetime.now().isoformat(),
                    "confidence": 0.8
                }
            }
        else:
            # If result is already a dictionary, return it as is
            return result



    def _process_document_with_retry(self, request: documentai.ProcessRequest) -> Any:
        """
        Process document with retry logic and exponential backoff.
        
        Args:
            request: Document AI processing request
            
        Returns:
            Processed document
        """
        for attempt in range(MAX_RETRIES):
            try:
                print(f"🔄 Google Document AI: Processing document (attempt {attempt + 1}/{MAX_RETRIES})...")
                sys.stdout.flush()
                
                # Add random delay to avoid rate limiting
                if attempt > 0:
                    delay = (2 ** attempt) + random.uniform(0, 1)
                    print(f"⏳ Waiting {delay:.1f} seconds before retry...")
                    sys.stdout.flush()
                    time.sleep(delay)
                
                result = self.client.process_document(request=request)
                document = result.document
                
                print(f"✅ Google Document AI: Processing successful on attempt {attempt + 1}")
                sys.stdout.flush()
                return document
                
            except Exception as e:
                print(f"❌ Google Document AI: Processing failed on attempt {attempt + 1}: {e}")
                
                if attempt == MAX_RETRIES - 1:
                    print(f"❌ Google Document AI: All {MAX_RETRIES} attempts failed")
                    raise
                else:
                    print(f"🔄 Google Document AI: Retrying...")
        
        raise Exception("All retry attempts failed")
    
    def _get_pdf_page_count(self, pdf_content: bytes) -> int:
        """
        Get the number of pages in a PDF document.
        
        Args:
            pdf_content: PDF file content as bytes
            
        Returns:
            Number of pages in the PDF
        """
        try:
            # Try to use pypdf library to count pages
            try:
                import pypdf
                pdf_reader = pypdf.PdfReader(io.BytesIO(pdf_content))
                return len(pdf_reader.pages)
            except ImportError:
                # Fallback: try to estimate from PDF structure
                # This is a rough estimation based on PDF markers
                pdf_text = pdf_content.decode('latin-1', errors='ignore')
                # Count page markers (this is approximate)
                page_count = pdf_text.count('/Type /Page') + pdf_text.count('/Type/Page')
                return max(1, page_count)  # At least 1 page
        except Exception as e:
            print(f"⚠️ Warning: Could not determine page count: {e}")
            # Default to assuming it's a large document to be safe
            return 31  # Force chunked processing
    
    def _process_document_regular_mode(self, pdf_content: bytes) -> List[Dict[str, Any]]:
        """
        Process document in regular mode (≤15 pages).
        
        Args:
            pdf_content: PDF file content as bytes
            
        Returns:
            List of extracted tables
        """
        request = documentai.ProcessRequest(
            name=self.processor_name,
            raw_document=documentai.RawDocument(
                content=pdf_content,
                mime_type="application/pdf"
            ),
            field_mask="text,pages.tables,pages.pageNumber,pages.dimension"
        )
        
        document = self._process_document_with_retry(request)
        return self._extract_tables_from_document(document)
    
    def _process_document_imageless_mode(self, pdf_content: bytes) -> List[Dict[str, Any]]:
        """
        Process document in imageless mode (≤30 pages).
        
        Args:
            pdf_content: PDF file content as bytes
            
        Returns:
            List of extracted tables
        """
        request = documentai.ProcessRequest(
            name=self.processor_name,
            raw_document=documentai.RawDocument(
                content=pdf_content,
                mime_type="application/pdf"
            ),
            # Enable imageless mode for larger documents
            process_options=documentai.ProcessOptions(
                ocr_config=documentai.OcrConfig(
                    enable_image_quality_scores=False,
                    enable_symbol=False,
                    premium_features=documentai.OcrConfig.PremiumFeatures(
                        compute_style_info=False,
                        enable_math_ocr=False,
                        enable_selection_mark_detection=False
                    )
                )
            ),
            field_mask="text,pages.tables,pages.pageNumber,pages.dimension"
        )
        
        document = self._process_document_with_retry(request)
        return self._extract_tables_from_document(document)
    
    def _process_document_in_chunks(self, pdf_content: bytes, page_count: int) -> List[Dict[str, Any]]:
        """
        Process large documents by splitting them into chunks.
        
        Args:
            pdf_content: PDF file content as bytes
            page_count: Total number of pages in the document
            
        Returns:
            List of extracted tables from all chunks
        """
        try:
            import pypdf
            from io import BytesIO
            
            all_tables = []
            chunk_size = 15  # Process 15 pages at a time (DocAI non-imageless limit)
            
            # Read the PDF
            pdf_reader = pypdf.PdfReader(io.BytesIO(pdf_content))
            
            for start_page in range(0, page_count, chunk_size):
                end_page = min(start_page + chunk_size, page_count)
                chunk_pages = end_page - start_page
                
                print(f"🔄 Google Document AI: Processing pages {start_page + 1}-{end_page} ({chunk_pages} pages)")
                
                # Ensure chunk doesn't exceed limits
                if chunk_pages > 15:
                    print(f"⚠️ Warning: Chunk has {chunk_pages} pages, splitting further...")
                    # Split this chunk into smaller pieces
                    for sub_start in range(start_page, end_page, 15):
                        sub_end = min(sub_start + 15, end_page)
                        sub_chunk_pages = sub_end - sub_start
                        print(f"🔄 Processing sub-chunk: pages {sub_start + 1}-{sub_end} ({sub_chunk_pages} pages)")
                        
                        # Create PDF for sub-chunk
                        pdf_writer = pypdf.PdfWriter()
                        for page_num in range(sub_start, sub_end):
                            pdf_writer.add_page(pdf_reader.pages[page_num])
                        
                        # Convert to bytes
                        chunk_buffer = BytesIO()
                        pdf_writer.write(chunk_buffer)
                        chunk_content = chunk_buffer.getvalue()
                        
                        # Process sub-chunk
                        try:
                            chunk_tables = self._process_document_regular_mode(chunk_content)
                            
                            # **ENHANCED DEBUGGING: Track sub-chunk processing results**
                            chunk_rows = sum(len(table.get('rows', [])) for table in chunk_tables)
                            print(f"✅ Google Document AI: Extracted {len(chunk_tables)} tables ({chunk_rows} rows) from sub-chunk {sub_start + 1}-{sub_end}")
                            
                            # **DEBUG: Log table details for each sub-chunk**
                            for i, table in enumerate(chunk_tables):
                                table_rows = len(table.get('rows', []))
                                table_headers = len(table.get('headers', []))
                                print(f"   Sub-chunk Table {i+1}: {table_headers} headers, {table_rows} rows")
                            
                            # Adjust page numbers in the results
                            for table in chunk_tables:
                                if 'page_number' in table:
                                    table['page_number'] += sub_start
                                if 'metadata' in table:
                                    table['metadata']['original_page_number'] = table.get('page_number', 0)
                                    table['metadata']['chunk_start_page'] = sub_start + 1
                                    table['metadata']['chunk_end_page'] = sub_end
                            
                            all_tables.extend(chunk_tables)
                            
                        except Exception as e:
                            print(f"⚠️ Warning: Failed to process sub-chunk {sub_start + 1}-{sub_end}: {e}")
                            print(f"   This sub-chunk will be skipped, potentially losing data")
                            continue
                    continue
                
                # Create a new PDF with just these pages
                pdf_writer = pypdf.PdfWriter()
                for page_num in range(start_page, end_page):
                    pdf_writer.add_page(pdf_reader.pages[page_num])
                
                # Convert to bytes
                chunk_buffer = BytesIO()
                pdf_writer.write(chunk_buffer)
                chunk_content = chunk_buffer.getvalue()
                
                # Process this chunk
                try:
                    chunk_tables = self._process_document_regular_mode(chunk_content)
                    
                    # **ENHANCED DEBUGGING: Track chunk processing results**
                    chunk_rows = sum(len(table.get('rows', [])) for table in chunk_tables)
                    print(f"✅ Google Document AI: Extracted {len(chunk_tables)} tables ({chunk_rows} rows) from pages {start_page + 1}-{end_page}")
                    
                    # **DEBUG: Log table details for each chunk**
                    for i, table in enumerate(chunk_tables):
                        table_rows = len(table.get('rows', []))
                        table_headers = len(table.get('headers', []))
                        print(f"   Table {i+1}: {table_headers} headers, {table_rows} rows")
                    
                    # Adjust page numbers in the results
                    for table in chunk_tables:
                        if 'page_number' in table:
                            table['page_number'] += start_page
                        if 'metadata' in table:
                            table['metadata']['original_page_number'] = table.get('page_number', 0)
                            table['metadata']['chunk_start_page'] = start_page + 1
                            table['metadata']['chunk_end_page'] = end_page
                    
                    all_tables.extend(chunk_tables)
                    
                except Exception as e:
                    print(f"⚠️ Warning: Failed to process pages {start_page + 1}-{end_page}: {e}")
                    print(f"   This chunk will be skipped, potentially losing data")
                    continue
            
            return all_tables
            
        except ImportError:
            print("❌ Error: pypdf not available for chunked processing. Install with: pip install pypdf")
            raise Exception("pypdf required for processing large documents")
        except Exception as e:
            print(f"❌ Error in chunked processing: {e}")
            raise
    
    # Removed _save_json_response method to prevent timeouts
    
    # Removed _create_docai_detection_overlays method to prevent timeouts
    
    # Removed _create_processing_summary method to prevent timeouts
    

    
    def _extract_tables_from_document(self, document: Any) -> List[Dict[str, Any]]:
        """
        Extract tables from processed Google Document AI document.
        
        Args:
            document: Processed Document AI document
            
        Returns:
            List of extracted tables
        """
        tables = []
        
        try:
            # Extract tables from each page
            for page_num, page in enumerate(document.pages):
                page_tables = self._extract_tables_from_page(page, page_num, document)
                tables.extend(page_tables)
            
            # Post-process tables for better structure
            processed_tables = self._post_process_tables(tables)
            
            return processed_tables
            
        except Exception as e:
            print(f"Error extracting tables from document: {e}")
            return []
    
    def _extract_tables_from_page(self, page: Any, page_num: int, document: Any) -> List[Dict[str, Any]]:
        """
        Extract tables from a single page.
        
        Args:
            page: Document AI page
            page_num: Page number
            
        Returns:
            List of tables from this page
        """
        tables = []
        
        try:
            # First, try to detect and process Form Parser format (tables structure)
            form_parser_tables = self._extract_form_parser_tables(page, page_num, document)
            if form_parser_tables:
                tables.extend(form_parser_tables)
                return tables
            
            # Fall back to traditional spatial clustering approach
            table_blocks = [block for block in page.blocks if block.layout.text_anchor.text_segments]
            
            for table_idx, table_block in enumerate(table_blocks):
                try:
                    # Extract table structure
                    table_data = self._extract_table_structure(table_block, page)
                    
                    if table_data and table_data.get("rows"):
                        # Add metadata
                        table_data.update({
                            "table_index": len(tables),
                            "page_number": page_num + 1,
                            "extractor": self.name,
                            "confidence": self._calculate_table_confidence(table_block),
                            "metadata": {
                                "page_number": page_num + 1,
                                "table_index": table_idx,
                                "extraction_method": "google_docai",
                                "timestamp": datetime.now().isoformat()
                            }
                        })
                        
                        tables.append(table_data)
                
                except Exception as e:
                    print(f"Error extracting table {table_idx} from page {page_num}: {e}")
                    continue
            
            return tables
            
        except Exception as e:
            print(f"Error extracting tables from page {page_num}: {e}")
            return []
    
    def _extract_form_parser_tables(self, page: Any, page_num: int, document: Any) -> List[Dict[str, Any]]:
        """
        Extract tables using Document AI Form Parser format (tables structure).
        
        Args:
            page: Document AI page
            page_num: Page number
            
        Returns:
            List of extracted tables in standard format
        """
        tables = []
        
        try:
            # Check if page has tables (Form Parser format)
            if hasattr(page, 'tables') and page.tables:
                for table_idx, table in enumerate(page.tables):
                    try:
                        # Convert Form Parser table to standard format
                        table_data = self._convert_form_parser_table_to_standard_format(
                            table, page_num, table_idx, document
                        )
                        
                        if table_data and table_data.get("rows"):
                            tables.append(table_data)
                            print(f"✅ Successfully converted Form Parser table: {len(table_data.get('headers', []))} headers, {len(table_data.get('rows', []))} rows")
                        else:
                            # Fallback: Try to extract table from raw text using spatial analysis
                            print(f"⚠️ Form Parser table {table_idx} has no rows, trying fallback extraction...")
                            fallback_table = self._extract_table_from_raw_text(page, page_num, table_idx, document)
                            if fallback_table and fallback_table.get("rows"):
                                tables.append(fallback_table)
                                print(f"✅ Fallback extraction successful: {len(fallback_table.get('headers', []))} headers, {len(fallback_table.get('rows', []))} rows")
                    
                    except Exception as e:
                        print(f"Error extracting Form Parser table {table_idx} from page {page_num}: {e}")
                        # Try fallback extraction
                        try:
                            fallback_table = self._extract_table_from_raw_text(page, page_num, table_idx, document)
                            if fallback_table and fallback_table.get("rows"):
                                tables.append(fallback_table)
                                print(f"✅ Fallback extraction successful after error: {len(fallback_table.get('headers', []))} headers, {len(fallback_table.get('rows', []))} rows")
                        except Exception as fallback_error:
                            print(f"Fallback extraction also failed: {fallback_error}")
                        continue
            
            return tables
            
        except Exception as e:
            print(f"Error extracting Form Parser tables from page {page_num}: {e}")
            return []

    def _extract_text_from_text_anchor(self, text_anchor: Any, document: Any) -> str:
        """
        Extract text from a Document AI text anchor using the document's text.
        
        Args:
            text_anchor: Document AI text anchor object
            document: Document AI document object
            
        Returns:
            Extracted text string
        """
        try:
            if not text_anchor or not text_anchor.text_segments:
                return ""
            
            text_parts = []
            for segment in text_anchor.text_segments:
                if hasattr(segment, 'start_index') and hasattr(segment, 'end_index'):
                    start_idx = segment.start_index
                    end_idx = segment.end_index
                    if start_idx < len(document.text) and end_idx <= len(document.text):
                        text_parts.append(document.text[start_idx:end_idx])
            
            return " ".join(text_parts).strip()
        except Exception as e:
            print(f"Error extracting text from text anchor: {e}")
            return ""

    def _extract_table_from_raw_text(self, page: Any, page_num: int, table_idx: int, document: Any) -> Dict[str, Any]:
        """
        Fallback method to extract table from raw text when Document AI table structure is incomplete.
        
        Args:
            page: Document AI page
            page_num: Page number
            table_idx: Table index
            document: Document AI document
            
        Returns:
            Table dictionary in standard format
        """
        try:
            # Get all text blocks from the page
            text_blocks = []
            if hasattr(page, 'blocks'):
                for block in page.blocks:
                    if hasattr(block, 'layout') and hasattr(block.layout, 'text_anchor'):
                        text = self._extract_text_from_text_anchor(block.layout.text_anchor, document)
                        if text.strip():
                            # Get bounding box for spatial analysis
                            bbox = None
                            if hasattr(block.layout, 'bounding_poly') and block.layout.bounding_poly.vertices:
                                vertices = block.layout.bounding_poly.vertices
                                if len(vertices) >= 4:
                                    bbox = {
                                        'x': vertices[0].x,
                                        'y': vertices[0].y,
                                        'width': vertices[2].x - vertices[0].x,
                                        'height': vertices[2].y - vertices[0].y
                                    }
                            
                            text_blocks.append({
                                'text': text.strip(),
                                'bbox': bbox,
                                'confidence': getattr(block.layout, 'confidence', 0.0)
                            })
            
            if not text_blocks:
                return {"header": [], "rows": [], "confidence": 0.0}  # Fixed: use "header" to match frontend expectations
            
            # Sort text blocks by vertical position (top to bottom)
            text_blocks.sort(key=lambda x: x['bbox']['y'] if x['bbox'] else 0)
            
            # Group text blocks into rows based on vertical proximity
            rows = []
            current_row = []
            last_y = None
            
            for block in text_blocks:
                if block['bbox']:
                    current_y = block['bbox']['y']
                    if last_y is None or abs(current_y - last_y) < 20:  # 20px tolerance
                        current_row.append(block)
                    else:
                        if current_row:
                            rows.append(current_row)
                        current_row = [block]
                    last_y = current_y
                else:
                    current_row.append(block)
            
            if current_row:
                rows.append(current_row)
            
            # Extract headers from first row
            headers = []
            if rows:
                header_blocks = rows[0]
                headers = [block['text'] for block in header_blocks]
                rows = rows[1:]  # Remove header row from data rows
            
            # Extract data rows
            data_rows = []
            for row_blocks in rows:
                row_data = [block['text'] for block in row_blocks]
                if any(cell.strip() for cell in row_data):  # Only add non-empty rows
                    data_rows.append(row_data)
            
            # Normalize row lengths
            if headers:
                max_cols = len(headers)
                normalized_rows = []
                for row in data_rows:
                    normalized_row = row[:max_cols] + [""] * (max_cols - len(row))
                    normalized_rows.append(normalized_row)
                data_rows = normalized_rows
            
            return {
                "header": headers,  # Fixed: use "header" to match frontend expectations
                "rows": data_rows,
                "confidence": 0.5,  # Lower confidence for fallback method
                "bbox": {},
                "page_number": page_num + 1,
                "table_index": table_idx,
                "extractor": "google_docai_fallback",
                "metadata": {
                    "page_number": page_num + 1,
                    "table_index": table_idx,
                    "extraction_method": "google_docai_fallback",
                    "timestamp": datetime.now().isoformat(),
                    "source_format": "raw_text_analysis"
                }
            }
            
        except Exception as e:
            print(f"Error in fallback table extraction: {e}")
            return {"header": [], "rows": [], "confidence": 0.0}  # Fixed: use "header" to match frontend expectations
    
    def _extract_cell_text_with_confidence(self, cell: Any, document: Any) -> Tuple[str, float]:
        """
        Extract text from a Document AI cell object with confidence scoring.
        
        Args:
            cell: Document AI cell object
            document: Document AI document object
            
        Returns:
            Tuple of (extracted_text, confidence_score)
        """
        try:
            if not hasattr(cell, 'layout') or not cell.layout:
                return "", 0.0
            
            text_anchor = cell.layout.text_anchor
            if not text_anchor:
                return "", 0.0
            
            text = self._extract_text_from_text_anchor(text_anchor, document)
            confidence = getattr(cell.layout, 'confidence', 0.0)
            
            return text, confidence
            
        except Exception as e:
            print(f"Error extracting cell text with confidence: {e}")
            return "", 0.0

    def _extract_cell_text(self, cell: Any, document: Any) -> str:
        """
        Extract text from a Document AI table cell (legacy method).
        
        Args:
            cell: Document AI table cell object
            document: Document AI document object
            
        Returns:
            Extracted cell text
        """
        text, _ = self._extract_cell_text_with_confidence(cell, document)
        return text

    def _extract_alternative_text(self, cell: Any, document: Any) -> str:
        """
        Extract alternative text for low-confidence cells using multiple strategies.
        
        Args:
            cell: Document AI cell object
            document: Document AI document object
            
        Returns:
            Alternative text string
        """
        try:
            # Strategy 1: Try to get text from bounding box
            if hasattr(cell, 'layout') and hasattr(cell.layout, 'bounding_poly'):
                bbox = cell.layout.bounding_poly
                # Extract text from the bounding box area
                return self._extract_text_from_bbox(bbox, document)
            
            # Strategy 2: Try to get text from text segments
            if hasattr(cell, 'layout') and hasattr(cell.layout, 'text_anchor'):
                text_anchor = cell.layout.text_anchor
                if text_anchor and hasattr(text_anchor, 'text_segments'):
                    # Try to extract from all text segments
                    text_parts = []
                    for segment in text_anchor.text_segments:
                        if hasattr(segment, 'start_index') and hasattr(segment, 'end_index'):
                            try:
                                text_part = document.text[segment.start_index:segment.end_index]
                                text_parts.append(text_part)
                            except (IndexError, AttributeError):
                                continue
                    if text_parts:
                        return " ".join(text_parts)
            
            return ""
            
        except Exception as e:
            print(f"Error extracting alternative text: {e}")
            return ""

    def _extract_text_from_bbox(self, bbox: Any, document: Any) -> str:
        """
        Extract text from a bounding box area.
        
        Args:
            bbox: Bounding box object
            document: Document AI document object
            
        Returns:
            Extracted text string
        """
        try:
            # This is a simplified implementation
            # In a full implementation, you would extract text from the specific area
            return ""
        except Exception as e:
            print(f"Error extracting text from bbox: {e}")
            return ""

    def _generate_header_from_data(self, rows: List[List[str]], column_index: int) -> str:
        """
        Generate a header based on the data in a specific column.
        
        Args:
            rows: Table data rows
            column_index: Index of the column to analyze
            
        Returns:
            Generated header string
        """
        try:
            if not rows or column_index >= len(rows[0]):
                return f"Column_{column_index+1}"
            
            # Get all values in this column
            column_values = []
            for row in rows:
                if column_index < len(row):
                    value = row[column_index].strip()
                    if value:
                        column_values.append(value)
            
            if not column_values:
                return f"Column_{column_index+1}"
            
            # Analyze the data to generate a meaningful header
            # Look for patterns like dates, numbers, names, etc.
            sample_values = column_values[:5]  # Look at first 5 values
            
            # Check if it looks like dates
            date_pattern = any(self._looks_like_date(val) for val in sample_values)
            if date_pattern:
                return "Date"
            
            # Check if it looks like numbers
            number_pattern = any(self._looks_like_number(val) for val in sample_values)
            if number_pattern:
                return "Amount"
            
            # Check if it looks like names
            name_pattern = any(self._looks_like_name(val) for val in sample_values)
            if name_pattern:
                return "Name"
            
            # Default to a generic header
            return f"Column_{column_index+1}"
            
        except Exception as e:
            print(f"Error generating header from data: {e}")
            return f"Column_{column_index+1}"

    def _looks_like_date(self, value: str) -> bool:
        """Check if a value looks like a date."""
        import re
        date_patterns = [
            r'\d{1,2}/\d{1,2}/\d{2,4}',
            r'\d{1,2}-\d{1,2}-\d{2,4}',
            r'\d{4}-\d{2}-\d{2}'
        ]
        return any(re.match(pattern, value) for pattern in date_patterns)

    def _looks_like_number(self, value: str) -> bool:
        """Check if a value looks like a number."""
        import re
        # Remove common currency symbols and commas
        cleaned = re.sub(r'[$,£€¥₹]', '', value)
        return bool(re.match(r'^[\d,]+\.?\d*$', cleaned))

    def _looks_like_name(self, value: str) -> bool:
        """Check if a value looks like a name."""
        import re
        # Simple heuristic: contains letters and spaces, no numbers
        return bool(re.match(r'^[A-Za-z\s]+$', value))

    def _convert_form_parser_table_to_standard_format(self, table: Any, page_num: int, table_index: int, document: Any = None) -> Dict[str, Any]:
        """
        Convert a Document AI Form Parser table to standard format with enhanced header detection.
        
        Args:
            table: Document AI Form Parser table object
            page_num: Page number where the table was found
            table_index: Index of the table on the page
            
        Returns:
            Standard table dictionary with headers, rows, and metadata
        """
        try:
            headers = []
            rows = []
            header_confidence_scores = []
            
            # Enhanced header extraction with confidence scoring
            if hasattr(table, 'header_rows') and table.header_rows:
                for header_row in table.header_rows:
                    row_cells = []
                    row_confidence = []
                    for cell in header_row.cells:
                        cell_text, confidence = self._extract_cell_text_with_confidence(cell, document)
                        row_cells.append(cell_text)
                        row_confidence.append(confidence)
                    if row_cells:
                        headers.extend(row_cells)
                        header_confidence_scores.extend(row_confidence)
                        print(f"🔍 Header row extracted: {row_cells} with confidence: {row_confidence}")
            
            # Extract body rows with confidence tracking
            if hasattr(table, 'body_rows') and table.body_rows:
                for body_row in table.body_rows:
                    row_cells = []
                    for cell in body_row.cells:
                        cell_text, confidence = self._extract_cell_text_with_confidence(cell, document)
                        # Only include cells with sufficient confidence
                        if confidence >= CELL_CONFIDENCE_THRESHOLD:
                            row_cells.append(cell_text)
                        else:
                            # Try alternative text extraction for low-confidence cells
                            alt_text = self._extract_alternative_text(cell, document)
                            row_cells.append(alt_text if alt_text else cell_text)
                    if row_cells:
                        rows.append(row_cells)
            
            # Enhanced header detection with fallback mechanisms
            if not headers and rows:
                print("⚠️ No headers detected, using first row as headers")
                headers = rows[0]
                rows = rows[1:]
                header_confidence_scores = [0.5] * len(headers)  # Default confidence for inferred headers
            
            # Filter low-confidence headers and generate alternatives
            if headers and header_confidence_scores:
                print(f"🔍 Processing {len(headers)} headers with confidence scores: {header_confidence_scores}")
                filtered_headers = []
                for i, (header, confidence) in enumerate(zip(headers, header_confidence_scores)):
                    if confidence >= HEADER_CONFIDENCE_THRESHOLD:
                        filtered_headers.append(header)
                        print(f"✅ Header '{header}' (confidence: {confidence:.2f}) accepted")
                    else:
                        # Generate alternative header for low-confidence cells
                        alt_header = self._generate_header_from_data(rows, i) if rows else f"Column_{i+1}"
                        filtered_headers.append(header)  # Keep original header even if low confidence
                        print(f"🔄 Low confidence header '{header}' (confidence: {confidence:.2f}) kept as is")
                headers = filtered_headers
                print(f"📋 Final headers: {headers}")
            else:
                print(f"⚠️ No headers or confidence scores: headers={len(headers) if headers else 0}, confidence_scores={len(header_confidence_scores) if header_confidence_scores else 0}")
            
            # Ensure all rows have the same number of columns as headers
            if headers:
                max_cols = len(headers)
                normalized_rows = []
                for row in rows:
                    # Pad with empty strings if row has fewer columns
                    normalized_row = row[:max_cols] + [""] * (max_cols - len(row))
                    normalized_rows.append(normalized_row)
                rows = normalized_rows
            
            # Generate default headers if none were detected
            if not headers and rows:
                max_cols = max(len(row) for row in rows) if rows else 0
                headers = [f"Column_{i+1}" for i in range(max_cols)]
                print(f"📋 Generated default headers: {headers}")
            
            # Extract metadata
            confidence = getattr(table, 'confidence', 0.0)
            bbox = {}
            if hasattr(table, 'layout') and hasattr(table.layout, 'bounding_poly'):
                vertices = table.layout.bounding_poly.vertices
                if len(vertices) >= 4:
                    bbox = {
                        "x0": vertices[0].x,
                        "y0": vertices[0].y,
                        "x1": vertices[2].x,
                        "y1": vertices[2].y
                    }
            
            # Create standard table format
            print(f"📊 Creating table with {len(headers)} headers and {len(rows)} rows")
            print(f"📋 Headers: {headers}")
            table_dict = {
                "header": headers,  # Fixed: use "header" to match frontend expectations
                "rows": rows,
                "confidence": confidence,
                "bbox": bbox,
                "page_number": page_num + 1,
                "table_index": table_index,
                "extractor": "google_docai_form_parser",
                "metadata": {
                    "page_number": page_num + 1,
                    "table_index": table_index,
                    "extraction_method": "google_docai_form_parser",
                    "timestamp": datetime.now().isoformat(),
                    "source_format": "form_parser_table"
                }
            }
            print(f"✅ Table created with header field: {table_dict.get('header', [])}")
            
            return table_dict
            
        except Exception as e:
            print(f"Error converting Form Parser table to standard format: {e}")
            return {
                "header": [],  # Fixed: use "header" to match frontend expectations
                "rows": [],
                "confidence": 0.0,
                "bbox": {},
                "page_number": page_num + 1,
                "table_index": table_index,
                "extractor": "google_docai_form_parser",
                "metadata": {
                    "page_number": page_num + 1,
                    "table_index": table_index,
                    "extraction_method": "google_docai_form_parser",
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e)
                }
            }

    def _extract_table_structure(self, table_block: Any, page: Any) -> Dict[str, Any]:
        """
        Extract table structure from a table block.
        
        Args:
            table_block: Table block from Document AI
            page: Page containing the table
            
        Returns:
            Table structure dictionary
        """
        try:
            # Get table layout
            table_layout = table_block.layout
            
            # Extract text segments
            text_segments = []
            for segment in table_layout.text_anchor.text_segments:
                text_segments.append({
                    "text": segment.text,
                    "start_index": segment.start_index,
                    "end_index": segment.end_index
                })
            
            # Analyze table structure using whitespace and spatial clustering
            table_structure = self._analyze_table_structure(text_segments, table_layout, page)
            
            return table_structure
            
        except Exception as e:
            print(f"Error extracting table structure: {e}")
            return {}
    
    def _analyze_table_structure(self, text_segments: List[Dict], layout: Any, page: Any) -> Dict[str, Any]:
        """
        Analyze table structure using whitespace analysis and spatial clustering.
        
        Args:
            text_segments: Text segments from the table
            layout: Table layout
            page: Page containing the table
            
        Returns:
            Analyzed table structure
        """
        try:
            # Get bounding box
            bbox = layout.bounding_poly.vertices
            
            # Extract all text elements within the table area
            table_texts = []
            for token in page.tokens:
                token_bbox = token.layout.bounding_poly.vertices
                if self._is_inside_bbox(token_bbox, bbox):
                    table_texts.append({
                        "text": token.layout.text_anchor.text_segments[0].text if token.layout.text_anchor.text_segments else "",
                        "bbox": token_bbox,
                        "confidence": token.layout.confidence
                    })
            
            # Cluster text elements into rows and columns
            rows, columns = self._cluster_table_elements(table_texts, bbox)
            
            # Build table structure
            headers = []
            table_rows = []
            
            # Extract headers (first row or column)
            if rows:
                headers = [cell.get("text", "") for cell in rows[0]]
            
            # Extract data rows
            for row in rows[1:] if len(rows) > 1 else []:
                table_rows.append([cell.get("text", "") for cell in row])
            
            return {
                "header": headers,  # Fixed: use "header" to match frontend expectations
                "rows": table_rows,
                "confidence": layout.confidence,
                "bbox": {
                    "x0": bbox[0].x,
                    "y0": bbox[0].y,
                    "x1": bbox[2].x,
                    "y1": bbox[2].y
                }
            }
            
        except Exception as e:
            print(f"Error analyzing table structure: {e}")
            return {"header": [], "rows": [], "confidence": 0.0}  # Fixed: use "header" to match frontend expectations
    
    def _cluster_table_elements(self, table_texts: List[Dict], table_bbox: List) -> Tuple[List[List[Dict]], List[List[Dict]]]:
        """
        Cluster table text elements into rows and columns using spatial analysis.
        
        Args:
            table_texts: List of text elements in the table
            table_bbox: Table bounding box
            
        Returns:
            Tuple of (rows, columns) where each is a list of lists of text elements
        """
        try:
            if not table_texts:
                return [], []
            
            # Sort by Y coordinate (rows)
            sorted_by_y = sorted(table_texts, key=lambda x: x["bbox"][0].y)
            
            # Group into rows based on Y proximity
            rows = []
            current_row = []
            row_threshold = 20  # pixels
            
            for i, text in enumerate(sorted_by_y):
                if not current_row:
                    current_row = [text]
                else:
                    # Check if this text is in the same row
                    avg_y = sum(t["bbox"][0].y for t in current_row) / len(current_row)
                    if abs(text["bbox"][0].y - avg_y) <= row_threshold:
                        current_row.append(text)
                    else:
                        # Sort current row by X coordinate
                        current_row.sort(key=lambda x: x["bbox"][0].x)
                        rows.append(current_row)
                        current_row = [text]
            
            # Add last row
            if current_row:
                current_row.sort(key=lambda x: x["bbox"][0].x)
                rows.append(current_row)
            
            # Create columns (transpose rows)
            columns = []
            if rows:
                max_cols = max(len(row) for row in rows)
                for col_idx in range(max_cols):
                    column = []
                    for row in rows:
                        if col_idx < len(row):
                            column.append(row[col_idx])
                    columns.append(column)
            
            return rows, columns
            
        except Exception as e:
            print(f"Error clustering table elements: {e}")
            return [], []
    
    def _is_inside_bbox(self, inner_bbox: List, outer_bbox: List) -> bool:
        """Check if inner bounding box is inside outer bounding box."""
        try:
            inner_center_x = (inner_bbox[0].x + inner_bbox[2].x) / 2
            inner_center_y = (inner_bbox[0].y + inner_bbox[2].y) / 2
            
            return (
                outer_bbox[0].x <= inner_center_x <= outer_bbox[2].x and
                outer_bbox[0].y <= inner_center_y <= outer_bbox[2].y
            )
        except:
            return False
    
    def _calculate_table_confidence(self, table_block: Any) -> float:
        """Calculate confidence score for table extraction."""
        try:
            # Use layout confidence as base
            base_confidence = table_block.layout.confidence
            
            # Additional confidence factors
            confidence_factors = []
            
            # Check for table-like structure indicators
            if hasattr(table_block.layout, 'text_anchor') and table_block.layout.text_anchor.text_segments:
                confidence_factors.append(0.1)  # Has text content
            
            # Check bounding box quality
            if hasattr(table_block.layout, 'bounding_poly') and table_block.layout.bounding_poly.vertices:
                bbox = table_block.layout.bounding_poly.vertices
                if len(bbox) >= 4:
                    # Check if bounding box is reasonable size
                    width = bbox[2].x - bbox[0].x
                    height = bbox[2].y - bbox[0].y
                    if width > 50 and height > 50:  # Minimum reasonable size
                        confidence_factors.append(0.1)
            
            # Calculate final confidence
            final_confidence = base_confidence + sum(confidence_factors)
            return min(final_confidence, 1.0)
            
        except Exception as e:
            print(f"Error calculating confidence: {e}")
            return 0.5
    
    def _post_process_tables(self, tables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Post-process extracted tables for better structure and formatting.
        
        Args:
            tables: Raw extracted tables
            
        Returns:
            Post-processed tables
        """
        processed_tables = []
        
        for table in tables:
            try:
                # Clean and normalize headers
                headers = table.get("header", [])  # Fixed: use "header" to match frontend expectations
                print(f"🔍 Post-processing: Original headers: {headers}")
                cleaned_headers = [self._clean_text(header) for header in headers]
                print(f"🔍 Post-processing: Cleaned headers: {cleaned_headers}")
                
                # Clean and normalize rows
                rows = table.get("rows", [])
                cleaned_rows = []
                for row in rows:
                    cleaned_row = [self._clean_text(cell) for cell in row]
                    cleaned_rows.append(cleaned_row)
                
                # Remove empty rows and columns
                print(f"🔍 Before removing empty cells: {len(cleaned_headers)} headers, {len(cleaned_rows)} rows")
                cleaned_headers, cleaned_rows = self._remove_empty_cells(cleaned_headers, cleaned_rows)
                print(f"🔍 After removing empty cells: {len(cleaned_headers)} headers, {len(cleaned_rows)} rows")
                
                # Ensure table dict matches utility requirements
                print(f"📊 Post-processing: Final headers: {cleaned_headers}")
                table_dict = {
                    "header": cleaned_headers,  # Fixed: use "header" to match frontend expectations
                    "rows": cleaned_rows,
                    "confidence": table.get("confidence", 0.0),
                    "bbox": table.get("bbox", {}),
                    "page_number": table.get("page_number", 1),
                    "table_index": table.get("table_index", 0),
                    "extractor": table.get("extractor", self.name),
                    "post_processed": True,
                    "metadata": table.get("metadata", {})
                }
                print(f"✅ Post-processing: Table created with header field: {table_dict.get('header', [])}")
                
                # Add any additional metadata from the original table
                for key, value in table.items():
                    if key not in table_dict:
                        table_dict[key] = value
                
                # Apply company name detection
                enhanced_table = self.company_detector.detect_company_names_in_extracted_data(
                    table_dict, "google_docai"
                )
                
                processed_tables.append(enhanced_table)
                
            except Exception as e:
                print(f"Error post-processing table: {e}")
                processed_tables.append(table)
        
        return processed_tables
    
    def _fix_ocr_errors(self, text: str) -> str:
        """Fix common OCR errors, particularly O to 0 in numeric contexts."""
        if not text:
            return text
        
        import re
        original_text = text
        
        # Fix O to 0 in numeric contexts
        # Pattern 1: O between digits (e.g., 2O25 -> 2025)
        text = re.sub(r'(\d)O(\d)', r'\g<1>0\g<2>', text)
        
        # Pattern 2: O after currency symbol (e.g., $O -> $0)
        text = re.sub(r'(\$)O(\d)', r'\g<1>0\g<2>', text)
        
        # Pattern 3: Years like 2O25 -> 2025
        text = re.sub(r'2O2[0-9]', lambda m: m.group().replace('O', '0'), text)
        
        # Pattern 4: O in decimal contexts (e.g., 1O9.O1 -> 109.01)
        text = re.sub(r'(\d)O(\d)\.O(\d)', r'\g<1>0\g<2>.0\g<3>', text)
        
        # Pattern 4b: O in decimal contexts without leading digit (e.g., O1 -> 01)
        text = re.sub(r'\.O(\d)', r'.0\g<1>', text)
        
        # Pattern 5: O in percentage contexts (e.g., 2O.O% -> 20.0%)
        text = re.sub(r'(\d)O\.O%', r'\g<1>0.0%', text)
        
        # Pattern 6: O in state codes (e.g., MNOO867 -> MN00867)
        text = re.sub(r'([A-Z]{2})O+(\d+)', r'\g<1>00\g<2>', text)
        
        # Pattern 6b: Fix remaining O's in state codes (e.g., MD005OO -> MD00500)
        text = re.sub(r'([A-Z]{2}\d+)O+', r'\g<1>0', text)
        
        # Pattern 7: O in standalone numeric contexts
        text = re.sub(r' O(\d) ', r' 0\g<1> ', text)
        
        # Debug logging for OCR corrections
        if original_text != text:
            print(f"🔧 OCR correction: '{original_text}' -> '{text}'")
        
        return text

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        if not text:
            return ""
        
        original_text = text
        
        # Remove excessive underscores (common in form fields and OCR artifacts)
        # Replace multiple consecutive underscores with a single space
        import re
        cleaned = re.sub(r'_+', ' ', text)
        
        # Remove excessive dashes (common in form fields)
        cleaned = re.sub(r'-+', ' ', cleaned)
        
        # Remove excessive dots/periods
        cleaned = re.sub(r'\.+', '.', cleaned)
        
        # Remove excessive spaces
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Remove common OCR artifacts
        cleaned = cleaned.replace("|", "I")  # Common OCR mistake
        
        # Fix OCR errors - O to 0 in numeric contexts (CRITICAL FIX)
        cleaned = self._fix_ocr_errors(cleaned)
        
        # Remove leading/trailing whitespace
        cleaned = cleaned.strip()
        
        # If the result is just whitespace or empty, return empty string
        if not cleaned or cleaned.isspace():
            return ""
        
        # Debug logging for header cleaning
        if original_text != cleaned:
            print(f"🔧 Text cleaned: '{original_text}' -> '{cleaned}'")
        
        return cleaned
    
    def _remove_empty_cells(self, headers: List[str], rows: List[List[str]]) -> Tuple[List[str], List[List[str]]]:
        """
        Data-preserving empty cell removal with enhanced logic.
        
        Args:
            headers: Table headers
            rows: Table data rows
            
        Returns:
            Tuple of (cleaned_headers, cleaned_rows) with preserved data
        """
        try:
            print(f"📊 Data preservation: Starting with {len(headers)} headers and {len(rows)} rows")
            
            # Only remove columns that are completely empty across ALL rows AND headers
            non_empty_cols = []
            max_cols = max(len(headers), max(len(row) for row in rows) if rows else 0)
            
            for col_idx in range(max_cols):
                # Check header
                header_value = headers[col_idx] if col_idx < len(headers) else ""
                
                # Check all rows in this column
                col_values = [header_value]
                for row in rows:
                    cell_value = row[col_idx] if col_idx < len(row) else ""
                    col_values.append(cell_value)
                
                # Debug logging for column analysis
                print(f"🔍 Column {col_idx}: header='{header_value}', has_content={any(value.strip() for value in col_values)}")
                
                # Only remove column if ALL values are empty (including header)
                if any(value.strip() for value in col_values):
                    non_empty_cols.append(col_idx)
                    print(f"✅ Keeping column {col_idx} with header '{header_value}'")
                else:
                    print(f"🗑️ Removing completely empty column {col_idx}")
            
            # Rebuild headers and rows with only non-empty columns
            new_headers = []
            for col_idx in non_empty_cols:
                if col_idx < len(headers):
                    new_headers.append(headers[col_idx])
                else:
                    new_headers.append(f"Column_{col_idx+1}")
            
            print(f"🔍 Rebuilt headers: {new_headers}")
            
            new_rows = []
            for row_idx, row in enumerate(rows):
                new_row = []
                for col_idx in non_empty_cols:
                    if col_idx < len(row):
                        new_row.append(row[col_idx])
                    else:
                        new_row.append("")  # Pad with empty string
                new_rows.append(new_row)
            
            # Only remove rows that are completely empty (all cells empty)
            filtered_rows = []
            for row_idx, row in enumerate(new_rows):
                if any(cell.strip() for cell in row):
                    filtered_rows.append(row)
                else:
                    print(f"🗑️ Removing completely empty row {row_idx}")
            
            print(f"📊 Data preservation: Final result - {len(new_headers)} headers and {len(filtered_rows)} rows")
            print(f"📊 Data preservation: Kept {len(filtered_rows)}/{len(rows)} rows ({len(filtered_rows)/len(rows)*100:.1f}% preserved)")
            
            return new_headers, filtered_rows
            
        except Exception as e:
            print(f"Error in data-preserving empty cell removal: {e}")
            return headers, rows
    
    def get_extraction_info(self) -> Dict[str, Any]:
        """Get information about this extractor."""
        return {
            "name": self.name,
            "description": self.description,
            "available": self.is_available(),
            "features": [
                "OCR with 600 DPI resolution",
                "Auto-rotate and deskew",
                "Form Parser with table detection",
                "Table extraction from forms and documents",
                "Whitespace analysis and spatial clustering (fallback)",
                "Contrast enhancement and denoising",
                "Multiple output formats",
                "Confidence scoring",
                "Automatic format detection and adaptation",
                "JSON response logging for debugging"
            ],
            "configuration": {
                "project_id": self.project_id,
                "location": self.location,
                "processor_id": self.processor_id
            }
        }
    
    def test_form_parser_adapter(self) -> Dict[str, Any]:
        """
        Test the Form Parser adapter with sample data.
        
        Returns:
            Test results showing adapter functionality
        """
        # Create a mock Form Parser table object for testing
        class MockTextSegment:
            def __init__(self, start_idx, end_idx):
                self.start_index = start_idx
                self.end_index = end_idx
        
        class MockTextAnchor:
            def __init__(self, text_segments):
                self.text_segments = text_segments
        
        class MockLayout:
            def __init__(self, text_anchor):
                self.text_anchor = text_anchor
        
        class MockCell:
            def __init__(self, text, start_idx):
                # Create text segments that would work with document.text indexing
                self.layout = MockLayout(MockTextAnchor([MockTextSegment(start_idx, start_idx + len(text))]))
        
        class MockRow:
            def __init__(self, texts, start_idx=0):
                self.cells = []
                current_idx = start_idx
                for text in texts:
                    self.cells.append(MockCell(text, current_idx))
                    current_idx += len(text) + 1  # +1 for space
        
        class MockTable:
            def __init__(self):
                self.confidence = 0.95
                self.header_rows = [MockRow(["Product", "Price", "Quantity"], 0)]
                self.body_rows = [
                    MockRow(["Laptop", "$999", "5"], 22),  # After "Product Price Quantity "
                    MockRow(["Mouse", "$25", "10"], 35)    # After "Laptop $999 5 "
                ]
        
        class MockDocument:
            def __init__(self):
                # Create text that matches the expected indices
                self.text = "Product Price Quantity Laptop $999 5 Mouse $25 10"
        
        sample_form_parser_table = MockTable()
        sample_document = MockDocument()
        
        try:
            # Test the Form Parser adapter function
            table_dict = self._convert_form_parser_table_to_standard_format(sample_form_parser_table, 0, 0, sample_document)
            
            return {
                "success": True,
                "test_data": {
                    "input_form_parser_table": sample_form_parser_table,
                    "standard_format": table_dict
                },
                "validation": {
                    "headers_count": len(table_dict.get("header", [])),  # Fixed: use "header" to match frontend expectations
                    "rows_count": len(table_dict.get("rows", [])),
                    "has_standard_format": "header" in table_dict and "rows" in table_dict,  # Fixed: use "header" to match frontend expectations
                    "confidence_preserved": table_dict.get("confidence") == 0.95,
                    "extractor_type": table_dict.get("extractor") == "google_docai_form_parser"
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "test_data": {
                    "input_form_parser_table": sample_form_parser_table
                }
            } 