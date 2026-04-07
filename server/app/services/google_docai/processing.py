"""
Document processing methods for Google Document AI.
"""

import io
import sys
import random
import time
from typing import Any, List, Dict
from .config import MAX_RETRIES, CHUNK_SIZE

# Google Document AI imports
try:
    from google.cloud import documentai_v1 as documentai
    GOOGLE_DOCAI_AVAILABLE = True
except ImportError:
    GOOGLE_DOCAI_AVAILABLE = False


class DocumentProcessor:
    """Handles document processing with different modes and chunking strategies."""
    
    def __init__(self, client, processor_name):
        self.client = client
        self.processor_name = processor_name
    
    def get_pdf_page_count(self, pdf_content: bytes) -> int:
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
                pdf_text = pdf_content.decode('latin-1', errors='ignore')
                # Count page markers (this is approximate)
                page_count = pdf_text.count('/Type /Page') + pdf_text.count('/Type/Page')
                return max(1, page_count)  # At least 1 page
        except Exception as e:
            print(f"⚠️ Warning: Could not determine page count: {e}")
            return 31  # Force chunked processing
    
    def process_document_with_retry(self, request: 'documentai.ProcessRequest') -> Any:
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
    
    def process_document_regular_mode(self, pdf_content: bytes) -> Any:
        """
        Process document in regular mode (≤15 pages).
        
        Args:
            pdf_content: PDF file content as bytes
            
        Returns:
            Processed document
        """
        request = documentai.ProcessRequest(
            name=self.processor_name,
            raw_document=documentai.RawDocument(
                content=pdf_content,
                mime_type="application/pdf"
            ),
            field_mask="text,pages.tables,pages.pageNumber,pages.dimension"
        )
        
        return self.process_document_with_retry(request)
    
    def process_document_imageless_mode(self, pdf_content: bytes) -> Any:
        """
        Process document in imageless mode (≤30 pages).
        
        Args:
            pdf_content: PDF file content as bytes
            
        Returns:
            Processed document
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
        
        return self.process_document_with_retry(request)
    
    def process_document_in_chunks(
        self, 
        pdf_content: bytes, 
        page_count: int,
        extract_tables_callback
    ) -> List[Dict[str, Any]]:
        """
        Process large documents by splitting them into chunks.
        
        Args:
            pdf_content: PDF file content as bytes
            page_count: Total number of pages in the document
            extract_tables_callback: Function to extract tables from document
            
        Returns:
            List of extracted tables from all chunks
        """
        try:
            import pypdf
            from io import BytesIO
            
            all_tables = []
            
            # Read the PDF
            pdf_reader = pypdf.PdfReader(io.BytesIO(pdf_content))
            
            for start_page in range(0, page_count, CHUNK_SIZE):
                end_page = min(start_page + CHUNK_SIZE, page_count)
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
                            document = self.process_document_regular_mode(chunk_content)
                            chunk_tables = extract_tables_callback(document)
                            
                            # Track sub-chunk processing results
                            chunk_rows = sum(len(table.get('rows', [])) for table in chunk_tables)
                            print(f"✅ Google Document AI: Extracted {len(chunk_tables)} tables ({chunk_rows} rows) from sub-chunk {sub_start + 1}-{sub_end}")
                            
                            # Log table details for each sub-chunk
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
                    document = self.process_document_regular_mode(chunk_content)
                    chunk_tables = extract_tables_callback(document)
                    
                    # Track chunk processing results
                    chunk_rows = sum(len(table.get('rows', [])) for table in chunk_tables)
                    print(f"✅ Google Document AI: Extracted {len(chunk_tables)} tables ({chunk_rows} rows) from pages {start_page + 1}-{end_page}")
                    
                    # Log table details for each chunk
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

