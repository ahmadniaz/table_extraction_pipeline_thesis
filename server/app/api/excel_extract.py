"""
Excel Extraction API - Robust Excel file processing with multi-sheet support
This API provides endpoints for Excel file extraction while maintaining compatibility
with the existing server structure and returning results in the same format.
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import crud, schemas
from app.services.excel_extraction_service import get_excel_extraction_service
from app.config import get_db
from app.utils.db_retry import with_db_retry
import os
import shutil
from datetime import datetime
from uuid import uuid4
from app.services.gcs_utils import upload_file_to_gcs, get_gcs_file_url, download_file_from_gcs, generate_gcs_signed_url
import logging
import asyncio
from typing import Optional, Dict, Any, List
from fastapi.responses import JSONResponse
import uuid

router = APIRouter(prefix="/api", tags=["excel-extract"])
logger = logging.getLogger(__name__)

UPLOAD_DIR = "pdfs"  # Reuse existing upload directory
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Initialize the Excel extraction service
excel_extraction_service = None

async def get_excel_extraction_service_instance(company_id: str = None):
    """Get or create the Excel extraction service instance."""
    return get_excel_extraction_service()


@router.post("/extract-tables-excel/")
async def extract_tables_excel(
    file: UploadFile = File(...),
    company_id: str = Form(...),
    sheet_names: Optional[str] = Form(None),  # Comma-separated sheet names
    max_tables_per_sheet: int = Form(10),
    enable_quality_checks: bool = Form(True),
    db: AsyncSession = Depends(get_db)
):
    """
    Extract tables from Excel files with multi-sheet support.
    This endpoint can handle Excel files with multiple sheets and dynamically
    find tables across all sheets, returning results in the same format as
    other extraction pipelines.
    """
    start_time = datetime.now()
    logger.info(f"Starting Excel extraction for {file.filename}")
    
    # Validate file type
    allowed_extensions = ['.xlsx', '.xls', '.xlsm', '.xlsb']
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type. Allowed Excel formats: {', '.join(allowed_extensions)}"
        )
    
    # Check file size (limit to 50MB)
    file_size = 0
    file_content = b""
    while chunk := await file.read(8192):
        file_content += chunk
        file_size += len(chunk)
        if file_size > 50 * 1024 * 1024:  # 50MB limit
            raise HTTPException(
                status_code=413, 
                detail="File too large. Maximum size is 50MB."
            )
    
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    
    try:
        # Save uploaded file
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)

        # Get company info with retry
        company = await with_db_retry(db, crud.get_company_by_id, company_id=company_id)
        if not company:
            os.remove(file_path)
            raise HTTPException(status_code=404, detail="Company not found")

        # Upload to GCS using upload_id for consistent path (not company_id which changes with carrier detection)
        gcs_key = f"statements/{upload_id}/{file.filename}"
        logger.info(f"📤 Uploading file to GCS: {gcs_key}")
        
        # Verify GCS is available before uploading
        from app.services.gcs_utils import gcs_service
        if not gcs_service.is_available():
            logger.error("❌ GCS service is not available. Check GOOGLE_APPLICATION_CREDENTIALS.")
            raise HTTPException(
                status_code=503, 
                detail="Cloud storage service is not available. Please contact support."
            )
        
        uploaded = upload_file_to_gcs(file_path, gcs_key)
        if not uploaded:
            logger.error(f"❌ Failed to upload file to GCS: {gcs_key}")
            raise HTTPException(status_code=500, detail="Failed to upload file to GCS.")
        
        # Verify file was actually uploaded
        if not gcs_service.file_exists(gcs_key):
            logger.error(f"❌ File upload verification failed - file not found in GCS: {gcs_key}")
            raise HTTPException(status_code=500, detail="File upload verification failed.")
        
        logger.info(f"✅ Successfully uploaded and verified file in GCS: {gcs_key}")
        
        # Generate signed URL for PDF preview
        gcs_url = generate_gcs_signed_url(gcs_key)
        if not gcs_url:
            # Fallback to public URL if signed URL generation fails
            gcs_url = get_gcs_file_url(gcs_key)

        # Get Excel extraction service
        excel_service = await get_excel_extraction_service_instance(company_id=company_id)
        
        # Parse sheet names if provided
        sheet_names_list = None
        if sheet_names:
            sheet_names_list = [name.strip() for name in sheet_names.split(',') if name.strip()]
        
        # Extract tables from Excel
        extraction_result = excel_service.extract_tables_from_excel(
            file_path=file_path,
            sheet_names=sheet_names_list,
            max_tables_per_sheet=max_tables_per_sheet,
            enable_quality_checks=enable_quality_checks
        )
        
        # Convert to client format
        response_data = excel_service.convert_to_client_format(extraction_result, file.filename)
        
        # Create statement upload record for database (same as PDF flow)
        upload_id = uuid.uuid4()
        db_upload = schemas.StatementUpload(
            id=upload_id,
            company_id=company_id,
            carrier_id=company_id,  # Set carrier_id for proper carrier association
            file_name=gcs_key,
            uploaded_at=datetime.utcnow(),
            status="extracted",
            current_step="extracted",
            raw_data=response_data.get("tables", []),
            mapping_used=None
        )
        
        # Save statement upload with retry
        await with_db_retry(db, crud.save_statement_upload, upload=db_upload)
        
        # Add format learning (same as PDF flow)
        format_learning_data = None
        if response_data.get("tables") and len(response_data["tables"]) > 0:
            try:
                from app.services.format_learning_service import FormatLearningService
                format_learning_service = FormatLearningService()
                
                # Get first table for format learning
                first_table = response_data["tables"][0]
                headers = first_table.get("header", [])
                
                # Generate table structure for format learning
                table_structure = {
                    "row_count": len(first_table.get("rows", [])),
                    "column_count": len(headers),
                    "has_financial_data": any(keyword in ' '.join(headers).lower() for keyword in [
                        'premium', 'commission', 'billed', 'group', 'client', 'invoice',
                        'total', 'amount', 'due', 'paid', 'rate', 'percentage', 'period'
                    ])
                }
                
                # Find matching format
                learned_format, match_score = await format_learning_service.find_matching_format(
                    db=db,
                    company_id=company_id,
                    headers=headers,
                    table_structure=table_structure
                )
                
                if learned_format and match_score > 0.5:
                    logger.info(f"🎯 Excel: Found matching format with score {match_score}")
                    
                    # Apply table editor settings if available (same logic as PDF flow)
                    if learned_format.get("table_editor_settings"):
                        table_editor_settings = learned_format["table_editor_settings"]
                        logger.info(f"🎯 Excel: Applying table editor settings: {table_editor_settings}")
                        
                        # Apply learned headers with intelligent matching
                        if table_editor_settings.get("headers"):
                            learned_headers = table_editor_settings["headers"]
                            current_headers = first_table.get("header", [])
                            
                            logger.info(f"🎯 Excel: Learned headers: {learned_headers}")
                            logger.info(f"🎯 Excel: Current headers: {current_headers}")
                            logger.info(f"🎯 Excel: Learned count: {len(learned_headers)}, Current count: {len(current_headers)}")
                            
                            # For financial tables, the learned headers are usually correct
                            # Check if this looks like a financial table that needs header correction
                            is_financial_table = any(keyword in ' '.join(current_headers).lower() for keyword in [
                                'premium', 'commission', 'billed', 'group', 'client', 'invoice',
                                'total', 'amount', 'due', 'paid', 'rate', 'percentage', 'period'
                            ])
                            
                            if is_financial_table and match_score > 0.5:
                                # For financial tables with good match score, apply learned headers
                                # and adjust the data rows accordingly
                                logger.info(f"🎯 Excel: Financial table detected - applying learned headers")
                                
                                # Apply learned headers
                                first_table["header"] = learned_headers
                                logger.info(f"🎯 Excel: Applied learned headers: {learned_headers}")
                                
                                # Adjust data rows if column count changed
                                current_rows = first_table.get("rows", [])
                                if current_rows and len(learned_headers) != len(current_headers):
                                    logger.info(f"🎯 Excel: Adjusting data rows for header correction")
                                    adjusted_rows = []
                                    
                                    for row in current_rows:
                                        if len(learned_headers) > len(current_headers):
                                            # Add empty columns if learned has more columns
                                            adjusted_row = row + [""] * (len(learned_headers) - len(current_headers))
                                        else:
                                            # Truncate row if learned has fewer columns
                                            adjusted_row = row[:len(learned_headers)]
                                        
                                        adjusted_rows.append(adjusted_row)
                                    
                                    first_table["rows"] = adjusted_rows
                                    logger.info(f"🎯 Excel: Adjusted {len(adjusted_rows)} rows to match {len(learned_headers)} columns")
                                
                            else:
                                # For non-financial tables or low confidence, use length-based matching
                                if len(learned_headers) == len(current_headers):
                                    # Apply headers directly if count matches
                                    first_table["header"] = learned_headers
                                    logger.info(f"🎯 Excel: Applied learned headers (length match): {learned_headers}")
                                elif len(learned_headers) > len(current_headers):
                                    # Pad current headers if learned has more columns
                                    padded_headers = current_headers + [f"Column_{i+1}" for i in range(len(current_headers), len(learned_headers))]
                                    first_table["header"] = learned_headers[:len(padded_headers)]
                                    logger.info(f"🎯 Excel: Applied learned headers with padding: {learned_headers[:len(padded_headers)]}")
                                else:
                                    # Truncate learned headers if current has more columns
                                    first_table["header"] = learned_headers + [f"Column_{i+1}" for i in range(len(learned_headers), len(current_headers))]
                                    logger.info(f"🎯 Excel: Applied learned headers with truncation: {first_table['header']}")
                        else:
                            logger.info(f"🎯 Excel: No learned headers to apply")
                        
                        # Apply learned summary rows
                        if table_editor_settings.get("summary_rows"):
                            summary_rows_set = set(table_editor_settings["summary_rows"])
                            first_table["summaryRows"] = summary_rows_set
                            logger.info(f"🎯 Excel: Applied learned summary rows: {list(summary_rows_set)}")
                        else:
                            logger.info(f"🎯 Excel: No summary rows to apply")
                    else:
                        logger.info(f"🎯 Excel: No table editor settings found in learned format")
                    
                    format_learning_data = {
                        "found_match": True,
                        "match_score": match_score,
                        "learned_format": learned_format,
                        "suggested_mapping": learned_format.get("field_mapping", {}),
                        "table_editor_settings": learned_format.get("table_editor_settings")
                    }
                else:
                    logger.info(f"🎯 Excel: No matching format found (score: {match_score})")
                    format_learning_data = {
                        "found_match": False,
                        "match_score": match_score or 0,
                        "learned_format": None,
                        "suggested_mapping": {},
                        "table_editor_settings": None
                    }
                    
            except Exception as e:
                logger.warning(f"Excel: Format learning failed: {str(e)}")
                format_learning_data = {
                    "found_match": False,
                    "match_score": 0,
                    "learned_format": None,
                    "suggested_mapping": {},
                    "table_editor_settings": None
                }
        
        # Add additional metadata
        response_data.update({
            "upload_id": str(upload_id),
            "extraction_id": str(uuid.uuid4()),
            "company_id": company_id,
            "gcs_url": gcs_url,
            "gcs_key": gcs_key,  # Add GCS key for consistency with PDF flow
            "file_name": gcs_key,  # Use full GCS path as file_name for PDF preview
            "file_type": "excel",
            "extraction_method": "excel_extraction",
            "format_learning": format_learning_data
        })
        
        # Clean up local file
        try:
            os.remove(file_path)
        except Exception as cleanup_error:
            logger.warning(f"Failed to clean up local file: {str(cleanup_error)}")
        
        logger.info(f"Excel extraction completed successfully. Found {len(response_data.get('tables', []))} tables.")
        return JSONResponse(content=response_data)
        
    except Exception as e:
        # Clean up on error
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except:
            pass
        
        logger.error(f"Excel extraction failed: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Excel extraction failed: {str(e)}"
        )


@router.post("/extract-tables-excel-bytes/")
async def extract_tables_excel_bytes(
    file: UploadFile = File(...),
    company_id: str = Form(...),
    sheet_names: Optional[str] = Form(None),
    max_tables_per_sheet: int = Form(10),
    enable_quality_checks: bool = Form(True),
    db: AsyncSession = Depends(get_db)
):
    """
    Extract tables from Excel file bytes (for direct processing without saving).
    """
    start_time = datetime.now()
    logger.info(f"Starting Excel extraction from bytes for {file.filename}")
    
    # Validate file type
    allowed_extensions = ['.xlsx', '.xls', '.xlsm', '.xlsb']
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type. Allowed Excel formats: {', '.join(allowed_extensions)}"
        )
    
    try:
        # Read file content
        file_content = await file.read()
        
        # Create temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name
        
        try:
            # Get company info with retry
            company = await with_db_retry(db, crud.get_company_by_id, company_id=company_id)
            if not company:
                raise HTTPException(status_code=404, detail="Company not found")

            # Get Excel extraction service
            excel_service = await get_excel_extraction_service_instance(company_id=company_id)
            
            # Parse sheet names if provided
            sheet_names_list = None
            if sheet_names:
                sheet_names_list = [name.strip() for name in sheet_names.split(',') if name.strip()]
            
            # Extract tables from Excel
            extraction_result = excel_service.extract_tables_from_excel(
                file_path=temp_file_path,
                sheet_names=sheet_names_list,
                max_tables_per_sheet=max_tables_per_sheet,
                enable_quality_checks=enable_quality_checks
            )
            
            # Convert to client format
            response_data = excel_service.convert_to_client_format(extraction_result, file.filename)
            
            # Create statement upload record for database (same as PDF flow)
            upload_id = uuid.uuid4()
            db_upload = schemas.StatementUpload(
                id=upload_id,
                company_id=company_id,
                file_name=file.filename,
                uploaded_at=datetime.utcnow(),
                status="extracted",
                current_step="extracted",
                raw_data=response_data.get("tables", []),
                mapping_used=None
            )
            
            # Save statement upload with retry
            await with_db_retry(db, crud.save_statement_upload, upload=db_upload)
            
            # Add format learning (same as PDF flow)
            format_learning_data = None
            if response_data.get("tables") and len(response_data["tables"]) > 0:
                try:
                    from app.services.format_learning_service import FormatLearningService
                    format_learning_service = FormatLearningService()
                    
                    # Get first table for format learning
                    first_table = response_data["tables"][0]
                    headers = first_table.get("header", [])
                    
                    # Generate table structure for format learning
                    table_structure = {
                        "row_count": len(first_table.get("rows", [])),
                        "column_count": len(headers),
                        "has_financial_data": any(keyword in ' '.join(headers).lower() for keyword in [
                            'premium', 'commission', 'billed', 'group', 'client', 'invoice',
                            'total', 'amount', 'due', 'paid', 'rate', 'percentage', 'period'
                        ])
                    }
                    
                    # Find matching format
                    learned_format, match_score = await format_learning_service.find_matching_format(
                        db=db,
                        company_id=company_id,
                        headers=headers,
                        table_structure=table_structure
                    )
                    
                    if learned_format and match_score > 0.5:
                        logger.info(f"🎯 Excel Bytes: Found matching format with score {match_score}")
                        
                        # Apply table editor settings if available (same logic as PDF flow)
                        if learned_format.get("table_editor_settings"):
                            table_editor_settings = learned_format["table_editor_settings"]
                            logger.info(f"🎯 Excel Bytes: Applying table editor settings: {table_editor_settings}")
                            
                            # Apply learned headers with intelligent matching
                            if table_editor_settings.get("headers"):
                                learned_headers = table_editor_settings["headers"]
                                current_headers = first_table.get("header", [])
                                
                                logger.info(f"🎯 Excel Bytes: Learned headers: {learned_headers}")
                                logger.info(f"🎯 Excel Bytes: Current headers: {current_headers}")
                                logger.info(f"🎯 Excel Bytes: Learned count: {len(learned_headers)}, Current count: {len(current_headers)}")
                                
                                # For financial tables, the learned headers are usually correct
                                # Check if this looks like a financial table that needs header correction
                                is_financial_table = any(keyword in ' '.join(current_headers).lower() for keyword in [
                                    'premium', 'commission', 'billed', 'group', 'client', 'invoice',
                                    'total', 'amount', 'due', 'paid', 'rate', 'percentage', 'period'
                                ])
                                
                                if is_financial_table and match_score > 0.5:
                                    # For financial tables with good match score, apply learned headers
                                    # and adjust the data rows accordingly
                                    logger.info(f"🎯 Excel Bytes: Financial table detected - applying learned headers")
                                    
                                    # Apply learned headers
                                    first_table["header"] = learned_headers
                                    logger.info(f"🎯 Excel Bytes: Applied learned headers: {learned_headers}")
                                    
                                    # Adjust data rows if column count changed
                                    current_rows = first_table.get("rows", [])
                                    if current_rows and len(learned_headers) != len(current_headers):
                                        logger.info(f"🎯 Excel Bytes: Adjusting data rows for header correction")
                                        adjusted_rows = []
                                        
                                        for row in current_rows:
                                            if len(learned_headers) > len(current_headers):
                                                # Add empty columns if learned has more columns
                                                adjusted_row = row + [""] * (len(learned_headers) - len(current_headers))
                                            else:
                                                # Truncate row if learned has fewer columns
                                                adjusted_row = row[:len(learned_headers)]
                                            
                                            adjusted_rows.append(adjusted_row)
                                        
                                        first_table["rows"] = adjusted_rows
                                        logger.info(f"🎯 Excel Bytes: Adjusted {len(adjusted_rows)} rows to match {len(learned_headers)} columns")
                                    
                                else:
                                    # For non-financial tables or low confidence, use length-based matching
                                    if len(learned_headers) == len(current_headers):
                                        # Apply headers directly if count matches
                                        first_table["header"] = learned_headers
                                        logger.info(f"🎯 Excel Bytes: Applied learned headers (length match): {learned_headers}")
                                    elif len(learned_headers) > len(current_headers):
                                        # Pad current headers if learned has more columns
                                        padded_headers = current_headers + [f"Column_{i+1}" for i in range(len(current_headers), len(learned_headers))]
                                        first_table["header"] = learned_headers[:len(padded_headers)]
                                        logger.info(f"🎯 Excel Bytes: Applied learned headers with padding: {learned_headers[:len(padded_headers)]}")
                                    else:
                                        # Truncate learned headers if current has more columns
                                        first_table["header"] = learned_headers + [f"Column_{i+1}" for i in range(len(learned_headers), len(current_headers))]
                                        logger.info(f"🎯 Excel Bytes: Applied learned headers with truncation: {first_table['header']}")
                            else:
                                logger.info(f"🎯 Excel Bytes: No learned headers to apply")
                            
                            # Apply learned summary rows
                            if table_editor_settings.get("summary_rows"):
                                summary_rows_set = set(table_editor_settings["summary_rows"])
                                first_table["summaryRows"] = summary_rows_set
                                logger.info(f"🎯 Excel Bytes: Applied learned summary rows: {list(summary_rows_set)}")
                            else:
                                logger.info(f"🎯 Excel Bytes: No summary rows to apply")
                        else:
                            logger.info(f"🎯 Excel Bytes: No table editor settings found in learned format")
                        
                        format_learning_data = {
                            "found_match": True,
                            "match_score": match_score,
                            "learned_format": learned_format,
                            "suggested_mapping": learned_format.get("field_mapping", {}),
                            "table_editor_settings": learned_format.get("table_editor_settings")
                        }
                    else:
                        logger.info(f"🎯 Excel Bytes: No matching format found (score: {match_score})")
                        format_learning_data = {
                            "found_match": False,
                            "match_score": match_score or 0,
                            "learned_format": None,
                            "suggested_mapping": {},
                            "table_editor_settings": None
                        }
                        
                except Exception as e:
                    logger.warning(f"Excel Bytes: Format learning failed: {str(e)}")
                    format_learning_data = {
                        "found_match": False,
                        "match_score": 0,
                        "learned_format": None,
                        "suggested_mapping": {},
                        "table_editor_settings": None
                    }
            
            # Add additional metadata
            response_data.update({
                "upload_id": str(upload_id),
                "extraction_id": str(uuid.uuid4()),
                "company_id": company_id,
                "file_type": "excel",
                "extraction_method": "excel_extraction",
                "format_learning": format_learning_data
            })
            
            logger.info(f"Excel extraction from bytes completed successfully. Found {len(response_data.get('tables', []))} tables.")
            return JSONResponse(content=response_data)
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except Exception as cleanup_error:
                logger.warning(f"Failed to clean up temporary file: {str(cleanup_error)}")
        
    except Exception as e:
        logger.error(f"Excel extraction from bytes failed: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Excel extraction failed: {str(e)}"
        )


@router.get("/excel-sheet-info/{company_id}")
async def get_excel_sheet_info(
    company_id: str,
    file_name: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get information about sheets in an Excel file.
    """
    try:
        # Get company info
        company = await with_db_retry(db, crud.get_company_by_id, company_id=company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Construct GCS key
        gcs_key = f"statements/{company_id}/{file_name}"
        
        # Download file from GCS
        local_path = download_file_from_gcs(gcs_key)
        if not local_path:
            raise HTTPException(status_code=404, detail="File not found in GCS")
        
        try:
            # Get sheet information
            import pandas as pd
            excel_file = pd.ExcelFile(local_path)
            
            sheet_info = []
            for sheet_name in excel_file.sheet_names:
                try:
                    df = pd.read_excel(excel_file, sheet_name=sheet_name, nrows=5)  # Read first 5 rows
                    sheet_info.append({
                        "name": sheet_name,
                        "rows": len(pd.read_excel(excel_file, sheet_name=sheet_name)),
                        "columns": len(df.columns) if not df.empty else 0,
                        "has_data": not df.empty,
                        "sample_data": df.head(3).to_dict('records') if not df.empty else []
                    })
                except Exception as e:
                    sheet_info.append({
                        "name": sheet_name,
                        "rows": 0,
                        "columns": 0,
                        "has_data": False,
                        "error": str(e)
                    })
            
            return {
                "success": True,
                "file_name": file_name,
                "total_sheets": len(excel_file.sheet_names),
                "sheets": sheet_info
            }
            
        finally:
            # Clean up local file
            try:
                os.remove(local_path)
            except:
                pass
                
    except Exception as e:
        logger.error(f"Failed to get Excel sheet info: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get Excel sheet info: {str(e)}"
        )


@router.post("/extract-tables-excel-s3/")
async def extract_tables_excel_s3(
    company_id: str = Form(...),
    file_name: str = Form(...),
    sheet_names: Optional[str] = Form(None),
    max_tables_per_sheet: int = Form(10),
    enable_quality_checks: bool = Form(True),
    db: AsyncSession = Depends(get_db)
):
    """
    Extract tables from Excel file stored in GCS.
    """
    start_time = datetime.now()
    logger.info(f"Starting Excel extraction from GCS for {file_name}")
    
    try:
        # Get company info
        company = await with_db_retry(db, crud.get_company_by_id, company_id=company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Construct GCS key and download file
        gcs_key = f"statements/{company_id}/{file_name}"
        local_path = download_file_from_gcs(gcs_key)
        if not local_path:
            raise HTTPException(status_code=404, detail="File not found in GCS")
        
        try:
            # Get Excel extraction service
            excel_service = await get_excel_extraction_service_instance(company_id=company_id)
            
            # Parse sheet names if provided
            sheet_names_list = None
            if sheet_names:
                sheet_names_list = [name.strip() for name in sheet_names.split(',') if name.strip()]
            
            # Extract tables from Excel
            extraction_result = excel_service.extract_tables_from_excel(
                file_path=local_path,
                sheet_names=sheet_names_list,
                max_tables_per_sheet=max_tables_per_sheet,
                enable_quality_checks=enable_quality_checks
            )
            
            # Convert to client format
            response_data = excel_service.convert_to_client_format(extraction_result, file_name)
            
            # Create statement upload record for database (same as PDF flow)
            upload_id = uuid.uuid4()
            db_upload = schemas.StatementUpload(
                id=upload_id,
                company_id=company_id,
                file_name=gcs_key,
                uploaded_at=datetime.utcnow(),
                status="extracted",
                current_step="extracted",
                raw_data=response_data.get("tables", []),
                mapping_used=None
            )
            
            # Save statement upload with retry
            await with_db_retry(db, crud.save_statement_upload, upload=db_upload)
            
            # Add format learning (same as PDF flow)
            format_learning_data = None
            if response_data.get("tables") and len(response_data["tables"]) > 0:
                try:
                    from app.services.format_learning_service import FormatLearningService
                    format_learning_service = FormatLearningService()
                    
                    # Get first table for format learning
                    first_table = response_data["tables"][0]
                    headers = first_table.get("header", [])
                    
                    # Generate table structure for format learning
                    table_structure = {
                        "row_count": len(first_table.get("rows", [])),
                        "column_count": len(headers),
                        "has_financial_data": any(keyword in ' '.join(headers).lower() for keyword in [
                            'premium', 'commission', 'billed', 'group', 'client', 'invoice',
                            'total', 'amount', 'due', 'paid', 'rate', 'percentage', 'period'
                        ])
                    }
                    
                    # Find matching format
                    learned_format, match_score = await format_learning_service.find_matching_format(
                        db=db,
                        company_id=company_id,
                        headers=headers,
                        table_structure=table_structure
                    )
                    
                    if learned_format and match_score > 0.5:
                        logger.info(f"🎯 Excel GCS: Found matching format with score {match_score}")
                        
                        # Apply table editor settings if available (same logic as PDF flow)
                        if learned_format.get("table_editor_settings"):
                            table_editor_settings = learned_format["table_editor_settings"]
                            logger.info(f"🎯 Excel GCS: Applying table editor settings: {table_editor_settings}")
                            
                            # Apply learned headers with intelligent matching
                            if table_editor_settings.get("headers"):
                                learned_headers = table_editor_settings["headers"]
                                current_headers = first_table.get("header", [])
                                
                                logger.info(f"🎯 Excel GCS: Learned headers: {learned_headers}")
                                logger.info(f"🎯 Excel GCS: Current headers: {current_headers}")
                                logger.info(f"🎯 Excel GCS: Learned count: {len(learned_headers)}, Current count: {len(current_headers)}")
                                
                                # For financial tables, the learned headers are usually correct
                                # Check if this looks like a financial table that needs header correction
                                is_financial_table = any(keyword in ' '.join(current_headers).lower() for keyword in [
                                    'premium', 'commission', 'billed', 'group', 'client', 'invoice',
                                    'total', 'amount', 'due', 'paid', 'rate', 'percentage', 'period'
                                ])
                                
                                if is_financial_table and match_score > 0.5:
                                    # For financial tables with good match score, apply learned headers
                                    # and adjust the data rows accordingly
                                    logger.info(f"🎯 Excel GCS: Financial table detected - applying learned headers")
                                    
                                    # Apply learned headers
                                    first_table["header"] = learned_headers
                                    logger.info(f"🎯 Excel GCS: Applied learned headers: {learned_headers}")
                                    
                                    # Adjust data rows if column count changed
                                    current_rows = first_table.get("rows", [])
                                    if current_rows and len(learned_headers) != len(current_headers):
                                        logger.info(f"🎯 Excel GCS: Adjusting data rows for header correction")
                                        adjusted_rows = []
                                        
                                        for row in current_rows:
                                            if len(learned_headers) > len(current_headers):
                                                # Add empty columns if learned has more columns
                                                adjusted_row = row + [""] * (len(learned_headers) - len(current_headers))
                                            else:
                                                # Truncate row if learned has fewer columns
                                                adjusted_row = row[:len(learned_headers)]
                                            
                                            adjusted_rows.append(adjusted_row)
                                        
                                        first_table["rows"] = adjusted_rows
                                        logger.info(f"🎯 Excel GCS: Adjusted {len(adjusted_rows)} rows to match {len(learned_headers)} columns")
                                    
                                else:
                                    # For non-financial tables or low confidence, use length-based matching
                                    if len(learned_headers) == len(current_headers):
                                        # Apply headers directly if count matches
                                        first_table["header"] = learned_headers
                                        logger.info(f"🎯 Excel GCS: Applied learned headers (length match): {learned_headers}")
                                    elif len(learned_headers) > len(current_headers):
                                        # Pad current headers if learned has more columns
                                        padded_headers = current_headers + [f"Column_{i+1}" for i in range(len(current_headers), len(learned_headers))]
                                        first_table["header"] = learned_headers[:len(padded_headers)]
                                        logger.info(f"🎯 Excel GCS: Applied learned headers with padding: {learned_headers[:len(padded_headers)]}")
                                    else:
                                        # Truncate learned headers if current has more columns
                                        first_table["header"] = learned_headers + [f"Column_{i+1}" for i in range(len(learned_headers), len(current_headers))]
                                        logger.info(f"🎯 Excel GCS: Applied learned headers with truncation: {first_table['header']}")
                            else:
                                logger.info(f"🎯 Excel GCS: No learned headers to apply")
                            
                            # Apply learned summary rows
                            if table_editor_settings.get("summary_rows"):
                                summary_rows_set = set(table_editor_settings["summary_rows"])
                                first_table["summaryRows"] = summary_rows_set
                                logger.info(f"🎯 Excel GCS: Applied learned summary rows: {list(summary_rows_set)}")
                            else:
                                logger.info(f"🎯 Excel GCS: No summary rows to apply")
                        else:
                            logger.info(f"🎯 Excel GCS: No table editor settings found in learned format")
                        
                        format_learning_data = {
                            "found_match": True,
                            "match_score": match_score,
                            "learned_format": learned_format,
                            "suggested_mapping": learned_format.get("field_mapping", {}),
                            "table_editor_settings": learned_format.get("table_editor_settings")
                        }
                    else:
                        logger.info(f"🎯 Excel GCS: No matching format found (score: {match_score})")
                        format_learning_data = {
                            "found_match": False,
                            "match_score": match_score or 0,
                            "learned_format": None,
                            "suggested_mapping": {},
                            "table_editor_settings": None
                        }
                        
                except Exception as e:
                    logger.warning(f"Excel GCS: Format learning failed: {str(e)}")
                    format_learning_data = {
                        "found_match": False,
                        "match_score": 0,
                        "learned_format": None,
                        "suggested_mapping": {},
                        "table_editor_settings": None
                    }
            
            # Add additional metadata
            response_data.update({
                "upload_id": str(upload_id),
                "extraction_id": str(uuid.uuid4()),
                "company_id": company_id,
                "gcs_url": generate_gcs_signed_url(gcs_key) or get_gcs_file_url(gcs_key),
                "gcs_key": gcs_key,
                "file_name": gcs_key,  # Use full GCS path as file_name for PDF preview
                "file_type": "excel",
                "extraction_method": "excel_extraction",
                "format_learning": format_learning_data
            })
            
            logger.info(f"Excel extraction from GCS completed successfully. Found {len(response_data.get('tables', []))} tables.")
            return JSONResponse(content=response_data)
            
        finally:
            # Clean up local file
            try:
                os.remove(local_path)
            except Exception as cleanup_error:
                logger.warning(f"Failed to clean up local file: {str(cleanup_error)}")
        
    except Exception as e:
        logger.error(f"Excel extraction from GCS failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Excel extraction failed: {str(e)}"
        )
