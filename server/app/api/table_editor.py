import os
import json
import logging
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import StatementUpload, Company
from app.db.crud import save_edited_tables, get_edited_tables, update_upload_tables, delete_edited_tables
from app.db import crud, schemas
from app.config import get_db
from app.utils.db_retry import with_db_retry
from app.services.format_learning_service import FormatLearningService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/table-editor", tags=["table-editor"])
format_learning_service = FormatLearningService()


class TableData(BaseModel):
    header: List[str]
    rows: List[List[str]]
    name: Optional[str] = None
    id: Optional[str] = None
    summaryRows: Optional[List[int]] = None  # Convert Set to List for JSON serialization
    extractor: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SaveTablesRequest(BaseModel):
    upload_id: str
    tables: List[TableData]
    company_id: str
    selected_statement_date: Optional[Dict[str, Any]] = None
    extracted_carrier: Optional[str] = None
    extracted_date: Optional[str] = None

class UpdateExtractionMetadataRequest(BaseModel):
    upload_id: str
    carrier_name: Optional[str] = None
    statement_date: Optional[str] = None


class GetTablesRequest(BaseModel):
    upload_id: str


@router.post("/save-tables/")
async def save_tables(request: SaveTablesRequest, db: AsyncSession = Depends(get_db)):
    """
    Save edited tables to the database and learn format patterns.
    """
    try:
        logger.info(f"🎯 Table Editor API: Saving edited tables for upload_id: {request.upload_id}")
        logger.info(f"🎯 Table Editor API: Tables count: {len(request.tables)}")
        logger.info(f"🎯 Table Editor API: Selected statement date: {request.selected_statement_date}")
        logger.info(f"🎯 Table Editor API: Company ID: {request.company_id}")
        
        # Convert tables to the format expected by the database
        tables_data = []
        for table in request.tables:
            # Clean metadata to ensure JSON serialization
            cleaned_metadata = {}
            if table.metadata:
                for key, value in table.metadata.items():
                    if isinstance(value, datetime):
                        cleaned_metadata[key] = value.isoformat()
                    else:
                        cleaned_metadata[key] = value
            
            table_data = {
                "name": table.name or "Unnamed Table",
                "header": table.header,
                "rows": table.rows,
                "upload_id": request.upload_id,
                "company_id": request.company_id,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "extractor": table.extractor,
                "metadata": cleaned_metadata
            }
            tables_data.append(table_data)
        
        logger.info(f"🎯 Table Editor API: Converted {len(tables_data)} tables to database format")
        
        # Save to database
        saved_upload = await save_edited_tables(db, tables_data)
        logger.info(f"🎯 Table Editor API: Saved edited tables to database")
        
        # Handle carrier creation and linking if carrier name is provided
        # CRITICAL: This handles user-corrected carrier names
        carrier_id = None
        if request.extracted_carrier:
            logger.info(f"🎯 Table Editor API: Processing carrier (potentially corrected by user): {request.extracted_carrier}")
            
            # Check if carrier already exists (use with_db_retry for consistency)
            existing_carrier = await with_db_retry(db, crud.get_company_by_name, name=request.extracted_carrier)
            if existing_carrier:
                carrier_id = existing_carrier.id
                logger.info(f"🎯 Table Editor API: Using existing carrier: {existing_carrier.id} ({existing_carrier.name})")
            else:
                # Create new carrier with corrected name
                carrier_data = schemas.CompanyCreate(name=request.extracted_carrier)
                new_carrier = await with_db_retry(db, crud.create_company, company=carrier_data)
                carrier_id = new_carrier.id
                logger.info(f"🎯 Table Editor API: Created new carrier with corrected name: {carrier_id} ({new_carrier.name})")
        
        # Update the original upload with the edited tables, selected statement date, and carrier info
        logger.info(f"🎯 Table Editor API: Updating upload with tables, statement date, and carrier")
        await update_upload_tables(db, request.upload_id, tables_data, request.selected_statement_date, carrier_id)
        logger.info(f"🎯 Table Editor API: Successfully updated upload with statement date and carrier")
        
        # Learn format patterns from the edited tables (use carrier_id for carrier-specific learning)
        if request.tables and len(request.tables) > 0 and carrier_id:
            try:
                logger.info(f"🎯 Table Editor API: Learning format patterns from edited tables for carrier {carrier_id}")
                
                # Use the first table for format learning (most common case)
                main_table = request.tables[0]
                
                # Extract table editor settings for learning
                table_editor_settings = {
                    'headers': main_table.header,
                    'summary_rows': main_table.summaryRows if main_table.summaryRows else [],
                    'table_structure': {
                        'column_count': len(main_table.header),
                        'row_count': len(main_table.rows),
                        'has_summary_rows': bool(main_table.summaryRows and len(main_table.summaryRows) > 0),
                        'summary_row_patterns': []
                    }
                }
                
                # Generate format signature for table editor settings
                format_signature = format_learning_service.generate_format_signature(
                    main_table.header, 
                    table_editor_settings['table_structure']
                )
                
                # Create format learning record for table editor settings
                # IMPORTANT: Use carrier_id (not user's company_id) for carrier-specific format learning
                format_learning_data = {
                    'company_id': carrier_id,  # Use carrier_id for carrier-specific learning
                    'format_signature': format_signature,
                    'headers': main_table.header,
                    'table_structure': table_editor_settings['table_structure'],
                    'table_editor_settings': table_editor_settings,
                    'confidence_score': 90,  # High confidence for manually edited tables
                    'usage_count': 1
                }
                
                # Save table editor format learning
                await save_table_editor_format_learning(db, format_learning_data)
                
                logger.info(f"🎯 Table Editor API: Successfully learned format with signature: {format_signature} for carrier {carrier_id}")
                logger.info(f"🎯 Table Editor API: Successfully learned table editor format patterns")
                
            except Exception as e:
                logger.error(f"🎯 Table Editor API: Error learning table editor format: {e}")
                # Don't fail the save operation if format learning fails
        elif not carrier_id:
            logger.warning(f"🎯 Table Editor API: Skipping format learning - no carrier_id available")
        
        logger.info(f"🎯 Table Editor API: Successfully saved {len(tables_data)} edited tables")
        
        # Get carrier name for response
        carrier_name = None
        if carrier_id:
            carrier = await with_db_retry(db, crud.get_company_by_id, company_id=carrier_id)
            if carrier:
                carrier_name = carrier.name
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"Successfully saved {len(tables_data)} edited tables",
                "saved_tables": tables_data,
                "carrier_id": str(carrier_id) if carrier_id else None,
                "carrier_name": carrier_name
            }
        )
        
    except Exception as e:
        logger.error(f"🎯 Table Editor API: Error saving tables: {e}")
        raise HTTPException(status_code=500, detail=f"Error saving tables: {str(e)}")

async def save_table_editor_format_learning(db: AsyncSession, format_data: Dict[str, Any]):
    """
    Save table editor format learning data.
    """
    try:
        from app.db import crud, schemas
        
        # Create format learning record
        format_learning = schemas.CarrierFormatLearningCreate(
            company_id=format_data['company_id'],
            format_signature=format_data['format_signature'],
            headers=format_data['headers'],
            table_structure=format_data['table_structure'],
            field_mapping={},  # Empty for table editor settings
            table_editor_settings=format_data['table_editor_settings'],
            confidence_score=format_data['confidence_score'],
            usage_count=format_data['usage_count']
        )
        
        # Save to database using the format learning service
        await crud.save_carrier_format_learning(db, format_learning)
        
    except Exception as e:
        logger.error(f"Error saving table editor format learning: {e}")
        raise


@router.get("/get-tables/{upload_id}")
async def get_tables(upload_id: str, db: AsyncSession = Depends(get_db)):
    """
    Retrieve edited tables for a specific upload.
    """
    try:
        logger.info(f"Retrieving edited tables for upload_id: {upload_id}")
        
        tables = await get_edited_tables(db, upload_id)
        
        # Convert to the format expected by the frontend
        tables_data = []
        if tables:
            for i, table in enumerate(tables):
                table_data = {
                    "id": str(i),  # Generate an ID since we don't have database IDs
                    "name": table.get('name', f'Table {i+1}'),
                    "header": table.get('header', []),
                    "rows": table.get('rows', []),
                    "upload_id": table.get('upload_id', upload_id),
                    "company_id": table.get('company_id', ''),
                    "created_at": table.get('created_at'),
                    "updated_at": table.get('updated_at'),
                    "extractor": table.get('extractor'),
                    "metadata": table.get('metadata', {})
                }
                tables_data.append(table_data)
        
        logger.info(f"Retrieved {len(tables_data)} edited tables")
        
        return JSONResponse({
            "success": True,
            "tables": tables_data,
            "tables_count": len(tables_data),
            "upload_id": upload_id
        })
        
    except Exception as e:
        logger.error(f"Error retrieving edited tables: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve tables: {str(e)}")


@router.delete("/delete-tables/{upload_id}")
async def delete_tables(upload_id: str, db: AsyncSession = Depends(get_db)):
    """
    Delete all edited tables for a specific upload.
    """
    try:
        logger.info(f"Deleting edited tables for upload_id: {upload_id}")
        
        # Delete edited tables using the CRUD layer
        success = await delete_edited_tables(db, upload_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Upload not found: {upload_id}")
        
        logger.info(f"Successfully deleted edited tables for upload_id: {upload_id}")
        
        return JSONResponse({
            "success": True,
            "message": "Successfully deleted edited tables",
            "upload_id": upload_id,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error deleting edited tables: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete tables: {str(e)}")


@router.post("/export-tables/{upload_id}")
async def export_tables(upload_id: str, format: str = "csv", db: AsyncSession = Depends(get_db)):
    """
    Export edited tables in various formats.
    """
    try:
        logger.info(f"Exporting tables for upload_id: {upload_id} in format: {format}")
        
        tables = await get_edited_tables(db, upload_id)
        
        if format.lower() == "csv":
            # Generate CSV content
            csv_content = ""
            if tables:
                for table in tables:
                    csv_content += f"Table: {table.get('name', 'Unnamed Table')}\n"
                    csv_content += ",".join(table.get('header', [])) + "\n"
                    for row in table.get('rows', []):
                        csv_content += ",".join([f'"{cell}"' for cell in row]) + "\n"
                    csv_content += "\n"
            
            return JSONResponse({
                "success": True,
                "format": "csv",
                "content": csv_content,
                "filename": f"edited_tables_{upload_id}.csv"
            })
        
        elif format.lower() == "json":
            # Generate JSON content
            tables_data = []
            if tables:
                for table in tables:
                    table_data = {
                        "name": table.get('name', 'Unnamed Table'),
                        "header": table.get('header', []),
                        "rows": table.get('rows', [])
                    }
                    tables_data.append(table_data)
            
            return JSONResponse({
                "success": True,
                "format": "json",
                "content": tables_data,
                "filename": f"edited_tables_{upload_id}.json"
            })
        
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")
        
    except Exception as e:
        logger.error(f"Error exporting tables: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to export tables: {str(e)}")


@router.post("/update-extraction-metadata/")
async def update_extraction_metadata(
    request: UpdateExtractionMetadataRequest, 
    db: AsyncSession = Depends(get_db)
):
    """
    Update extracted carrier name and statement date metadata.
    """
    try:
        logger.info(f"🎯 Table Editor API: Updating extraction metadata for upload_id: {request.upload_id}")
        logger.info(f"🎯 Table Editor API: Carrier name: {request.carrier_name}")
        logger.info(f"🎯 Table Editor API: Statement date: {request.statement_date}")
        
        # Update the upload record with new metadata
        from app.db.crud import update_upload_metadata
        
        update_data = {}
        if request.carrier_name is not None:
            update_data['extracted_carrier'] = request.carrier_name
        if request.statement_date is not None:
            update_data['extracted_date'] = request.statement_date
        
        if update_data:
            success = await update_upload_metadata(db, request.upload_id, update_data)
            
            if success:
                logger.info(f"🎯 Table Editor API: Successfully updated extraction metadata")
                return JSONResponse(
                    status_code=200,
                    content={
                        "success": True,
                        "message": "Extraction metadata updated successfully",
                        "updated_fields": list(update_data.keys())
                    }
                )
            else:
                logger.error(f"🎯 Table Editor API: Failed to update extraction metadata")
                raise HTTPException(status_code=404, detail=f"Upload not found: {request.upload_id}")
        else:
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": "No updates needed",
                    "updated_fields": []
                }
            )
        
    except Exception as e:
        logger.error(f"🎯 Table Editor API: Error updating extraction metadata: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating extraction metadata: {str(e)}")


@router.post("/learn-format-patterns")
async def learn_format_patterns(
    request: SaveTablesRequest,
    db: AsyncSession = Depends(get_db)
):
    """Learn format patterns from user edits and corrections.
    CRITICAL: This endpoint receives corrected carrier names from user edits.
    """
    try:
        if not request.tables or len(request.tables) == 0:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "No tables provided for learning"}
            )
        
        # Get carrier_id from extracted carrier name (which may have been corrected by user)
        carrier_id = None
        if request.extracted_carrier:
            logger.info(f"🎯 Format Learning: Processing carrier (may be user-corrected): {request.extracted_carrier}")
            existing_carrier = await with_db_retry(db, crud.get_company_by_name, name=request.extracted_carrier)
            if existing_carrier:
                carrier_id = existing_carrier.id
                logger.info(f"🎯 Format Learning: Using existing carrier: {carrier_id}")
            else:
                carrier_data = schemas.CompanyCreate(name=request.extracted_carrier)
                new_carrier = await with_db_retry(db, crud.create_company, company=carrier_data)
                carrier_id = new_carrier.id
                logger.info(f"🎯 Format Learning: Created new carrier with corrected name: {carrier_id}")
        
        if not carrier_id:
            logger.warning(f"🎯 Format Learning: No carrier_id available, using user's company_id")
            carrier_id = request.company_id
        
        # Extract learning data from the edited tables
        main_table = request.tables[0]
        
        # Create comprehensive format signature
        format_signature = format_learning_service.generate_format_signature(
            main_table.header,
            {
                "column_count": len(main_table.header),
                "row_count": len(main_table.rows), 
                "has_summary_rows": bool(main_table.summaryRows if hasattr(main_table, 'summaryRows') else False),
                "carrier_name": request.extracted_carrier,
                "date_pattern": request.extracted_date
            }
        )
        
        # Store format learning with enhanced metadata
        # IMPORTANT: Use carrier_id for carrier-specific format learning
        # CRITICAL: Store corrected_carrier_name at top level for extraction process to find it
        table_editor_settings = {
            "headers": main_table.header,
            "summary_rows": main_table.summaryRows if hasattr(main_table, 'summaryRows') and main_table.summaryRows else [],
            "corrected_carrier_name": request.extracted_carrier,  # CRITICAL: Top-level for format learning
            "corrected_statement_date": request.extracted_date,  # CRITICAL: Top-level for format learning
            "user_corrections": {
                "carrier_name": request.extracted_carrier,
                "statement_date": request.extracted_date
            }
        }
        
        # Create format learning record using Pydantic schema
        format_learning = schemas.CarrierFormatLearningCreate(
            company_id=carrier_id,  # Use carrier_id for carrier-specific learning
            format_signature=format_signature,
            headers=main_table.header,
            table_structure={
                "column_count": len(main_table.header),
                "row_count": len(main_table.rows),
                "has_summary_rows": bool(main_table.summaryRows if hasattr(main_table, 'summaryRows') else False),
                "summary_row_patterns": main_table.summaryRows if hasattr(main_table, 'summaryRows') and main_table.summaryRows else []
            },
            field_mapping={},  # Empty for this endpoint
            table_editor_settings=table_editor_settings,
            confidence_score=95,  # High confidence for manually edited tables
            usage_count=1
        )
        
        # Save the learning data using crud
        await with_db_retry(db, crud.save_carrier_format_learning, format_learning=format_learning)
        
        logger.info(f"Successfully learned format patterns with signature: {format_signature} for carrier {carrier_id}")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Format patterns learned successfully",
                "format_signature": format_signature,
                "carrier_id": str(carrier_id),
                "learned_patterns": {
                    "headers": len(main_table.header),
                    "rows": len(main_table.rows),
                    "summary_patterns": len(main_table.summaryRows) if hasattr(main_table, 'summaryRows') and main_table.summaryRows else 0
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Format learning failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Format learning failed: {str(e)}")

@router.get("/health")
async def health_check():
    """
    Health check endpoint for table editor API.
    """
    return JSONResponse({
        "status": "healthy",
        "service": "table-editor",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }) 