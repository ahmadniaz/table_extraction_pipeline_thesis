"""
Main Google Document AI extractor for PDF documents.
"""

import os
import sys
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

# Google Document AI imports
try:
    from google.cloud import documentai_v1 as documentai
    from google.cloud import storage
    from google.auth import default
    GOOGLE_DOCAI_AVAILABLE = True
except ImportError:
    GOOGLE_DOCAI_AVAILABLE = False
    print("Warning: Google Document AI not available. Install with: pip install google-cloud-documentai google-cloud-storage google-auth")

# Local imports
from .config import (
    DEFAULT_PROJECT_ID,
    DEFAULT_PROCESSOR_ID,
    DEFAULT_LOCATION,
    CREDENTIALS_PATHS,
    REGULAR_MODE_MAX_PAGES,
    IMAGELESS_MODE_MAX_PAGES
)
from .processing import DocumentProcessor
from .table_extraction import TableExtractor
from .post_processing import TextCleaner
from app.services.data_processing.company_name_service import CompanyNameDetectionService


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
        self.location = DEFAULT_LOCATION
        self.processor_id = None
        self.company_detector = CompanyNameDetectionService()
        self.table_extractor = TableExtractor()
        self.text_cleaner = TextCleaner()
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
                possible_paths = CREDENTIALS_PATHS + [
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
                os.environ["GOOGLE_CLOUD_PROJECT_ID"] = DEFAULT_PROJECT_ID
                print(f"✅ Set GOOGLE_CLOUD_PROJECT_ID to: {DEFAULT_PROJECT_ID}")
            
            # Set processor ID if not already set
            if not os.getenv("GOOGLE_DOCAI_PROCESSOR_ID"):
                os.environ["GOOGLE_DOCAI_PROCESSOR_ID"] = DEFAULT_PROCESSOR_ID
                print(f"✅ Set GOOGLE_DOCAI_PROCESSOR_ID to: {DEFAULT_PROCESSOR_ID}")
            
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
            self.processor_id = os.getenv("GOOGLE_DOCAI_PROCESSOR_ID", DEFAULT_PROCESSOR_ID)
            
            # Construct processor name
            self.processor_name = self.client.processor_path(
                self.project_id, self.location, self.processor_id
            )
            
            # Initialize document processor
            self.document_processor = DocumentProcessor(self.client, self.processor_name)
            
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
            sys.stdout.flush()
            
            # Read the PDF file directly
            with open(pdf_path, "rb") as pdf_file:
                pdf_content = pdf_file.read()
            
            # Get page count to determine processing strategy
            page_count = self.document_processor.get_pdf_page_count(pdf_content)
            print(f"📄 Google Document AI: Document has {page_count} pages")
            
            # Track processing strategy and results
            processing_mode = "unknown"
            tables = []
            
            # Determine processing strategy based on page count
            if page_count <= REGULAR_MODE_MAX_PAGES:
                # Use regular mode for small documents
                processing_mode = "regular"
                print(f"🔄 Google Document AI: Using regular mode (≤{REGULAR_MODE_MAX_PAGES} pages)")
                document = self.document_processor.process_document_regular_mode(pdf_content)
                tables = self.table_extractor.extract_tables_from_document(document)
                print(f"✅ Google Document AI: Regular mode extracted {len(tables)} tables")
                
            elif page_count <= IMAGELESS_MODE_MAX_PAGES:
                # Use imageless mode for medium documents
                processing_mode = "imageless"
                print(f"🔄 Google Document AI: Using imageless mode ({page_count} pages)")
                try:
                    document = self.document_processor.process_document_imageless_mode(pdf_content)
                    tables = self.table_extractor.extract_tables_from_document(document)
                    print(f"✅ Google Document AI: Imageless mode extracted {len(tables)} tables")
                except Exception as e:
                    if "PAGE_LIMIT_EXCEEDED" in str(e) or "page limit" in str(e).lower():
                        processing_mode = "chunked"
                        print(f"⚠️ Google Document AI: Imageless mode failed, falling back to chunked processing")
                        tables = self.document_processor.process_document_in_chunks(
                            pdf_content, 
                            page_count,
                            self.table_extractor.extract_tables_from_document
                        )
                        print(f"✅ Google Document AI: Chunked processing extracted {len(tables)} tables")
                    else:
                        print(f"❌ Google Document AI: Imageless mode failed with non-page-limit error: {e}")
                        raise
                        
            else:
                # Use chunked processing for large documents
                processing_mode = "chunked"
                print(f"🔄 Google Document AI: Using chunked processing ({page_count} pages)")
                tables = self.document_processor.process_document_in_chunks(
                    pdf_content, 
                    page_count,
                    self.table_extractor.extract_tables_from_document
                )
                print(f"✅ Google Document AI: Chunked processing extracted {len(tables)} tables")
            
            # Calculate extraction metrics
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
            
            # Alert for suspicious extraction patterns
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
            
            # Apply table merging to consolidate similar tables
            if len(tables) > 1:
                print(f"🔗 Google Document AI: Applying table merging to {len(tables)} tables")
                try:
                    from app.services.extraction.extraction_utils import stitch_multipage_tables
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
            
            # Post-process tables
            processed_tables = self._post_process_tables(tables)
            
            return processed_tables
            
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
        # Run the synchronous extract_tables method in a thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self.extract_tables, pdf_path)
        
        # Convert the result to the expected format
        if isinstance(result, list):
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
            return result

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
                headers = table.get("header", [])
                print(f"🔍 Post-processing: Original headers: {headers}")
                cleaned_headers = [self.text_cleaner.clean_text(header) for header in headers]
                print(f"🔍 Post-processing: Cleaned headers: {cleaned_headers}")
                
                # Clean and normalize rows
                rows = table.get("rows", [])
                cleaned_rows = []
                for row in rows:
                    cleaned_row = [self.text_cleaner.clean_text(cell) for cell in row]
                    cleaned_rows.append(cleaned_row)
                
                # Remove empty rows and columns
                print(f"🔍 Before removing empty cells: {len(cleaned_headers)} headers, {len(cleaned_rows)} rows")
                cleaned_headers, cleaned_rows = self.text_cleaner.remove_empty_cells(cleaned_headers, cleaned_rows)
                print(f"🔍 After removing empty cells: {len(cleaned_headers)} headers, {len(cleaned_rows)} rows")
                
                # Ensure table dict matches utility requirements
                print(f"📊 Post-processing: Final headers: {cleaned_headers}")
                table_dict = {
                    "header": cleaned_headers,
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

