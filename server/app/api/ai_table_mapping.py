"""
AI Table Mapping API - Endpoints for intelligent table selection and switching

Provides endpoints for:
1. Switching the table used for AI field mapping
2. Re-running AI analysis on a different table
3. Analyzing table suitability
4. Managing table selection history
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import crud
from app.config import get_db
from app.dependencies.auth_dependencies import get_current_user_hybrid
from app.db.models import User
from app.utils.db_retry import with_db_retry
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import UUID
import logging
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["ai-table-mapping"])


class SwitchMappingTableRequest(BaseModel):
    """Request model for switching mapping table"""
    upload_id: str
    new_table_index: int
    reason: Optional[str] = "user_requested"


class AnalyzeTableSuitabilityRequest(BaseModel):
    """Request model for analyzing table suitability"""
    tables: List[Dict[str, Any]]
    document_context: Optional[Dict[str, Any]] = None


@router.post("/ai/switch-mapping-table")
async def switch_mapping_table(
    request: SwitchMappingTableRequest,
    current_user: User = Depends(get_current_user_hybrid),
    db: AsyncSession = Depends(get_db)
):
    """
    Switch the table used for AI field mapping and re-run analysis
    
    This endpoint allows users to:
    1. Change which table is used for AI field mapping
    2. Re-run AI field mapping on the new table
    3. Track table switching history for audit
    
    Args:
        request: SwitchMappingTableRequest with upload_id and new_table_index
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        New AI mappings and updated table selection data
    """
    try:
        logger.info(f"🔄 Table switch requested by user {current_user.id} for upload {request.upload_id} to table {request.new_table_index}")
        
        # Get upload record
        upload_record = await with_db_retry(db, crud.get_upload_by_id, request.upload_id)
        
        if not upload_record:
            raise HTTPException(status_code=404, detail="Upload not found")
        
        # Verify user has access to this upload
        if upload_record.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get tables from raw_data
        tables = upload_record.raw_data if isinstance(upload_record.raw_data, list) else []
        
        if not tables:
            raise HTTPException(status_code=400, detail="No tables found in upload")
        
        # Validate new table index
        if request.new_table_index < 0 or request.new_table_index >= len(tables):
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid table index. Must be between 0 and {len(tables) - 1}"
            )
        
        # Get the new table
        new_table = tables[request.new_table_index]
        headers = new_table.get('header', []) or new_table.get('headers', [])
        rows = new_table.get('rows', [])
        
        logger.info(f"🎯 Switching to table {request.new_table_index} with {len(headers)} headers and {len(rows)} rows")
        
        # Re-run AI field mapping on the new table
        from app.services.ai_field_mapping_service import AIFieldMappingService
        ai_mapping_service = AIFieldMappingService()
        
        if not ai_mapping_service.is_available():
            raise HTTPException(
                status_code=503,
                detail="AI field mapping service not available"
            )
        
        # Get document metadata
        carrier_name = upload_record.company_id  # This might be a UUID
        try:
            # Try to get carrier name from company
            company = await with_db_retry(db, crud.get_company_by_id, company_id=upload_record.company_id)
            if company:
                carrier_name = company.name
        except Exception:
            pass
        
        # Run AI field mapping
        new_mappings = await ai_mapping_service.get_intelligent_field_mappings(
            db=db,
            extracted_headers=headers,
            table_sample_data=rows[:5],  # First 5 rows
            carrier_id=upload_record.company_id,
            document_context={
                'carrier_name': carrier_name,
                'document_type': 'commission_statement'
            }
        )
        
        if not new_mappings.get('success'):
            raise HTTPException(
                status_code=500,
                detail=f"AI field mapping failed: {new_mappings.get('error', 'Unknown error')}"
            )
        
        # Get current AI intelligence data
        current_ai_intelligence = upload_record.ai_intelligence or {}
        
        # Create table switch history entry
        table_switch_history = current_ai_intelligence.get('table_switch_history', [])
        table_switch_history.append({
            'timestamp': datetime.now().isoformat(),
            'from_table': current_ai_intelligence.get('table_selection', {}).get('selected_table_index', 0),
            'to_table': request.new_table_index,
            'reason': request.reason,
            'user_id': str(current_user.id),
            'new_confidence': new_mappings.get('overall_confidence', 0.0)
        })
        
        # Update AI intelligence data with new table selection and mappings
        updated_ai_intelligence = {
            **current_ai_intelligence,
            'table_selection': {
                'enabled': True,
                'selected_table_index': request.new_table_index,
                'confidence': 1.0,  # User selection = high confidence
                'user_selected': True,
                'selection_timestamp': datetime.now().isoformat(),
                'total_tables': len(tables)
            },
            'field_mapping': {
                'ai_enabled': True,
                'mappings': new_mappings.get('mappings', []),
                'unmapped_fields': new_mappings.get('unmapped_fields', []),
                'confidence': new_mappings.get('overall_confidence', 0.0),
                'statistics': new_mappings.get('mapping_statistics', {}),
                'selected_table_index': request.new_table_index,
                'remapped_at': datetime.now().isoformat()
            },
            'table_switch_history': table_switch_history
        }
        
        # Save updated AI intelligence to database
        from app.db.schemas import StatementUploadUpdate
        update_data = StatementUploadUpdate(
            ai_intelligence=updated_ai_intelligence
        )
        
        await with_db_retry(
            db, 
            crud.update_statement_upload, 
            upload_id=UUID(request.upload_id), 
            update_data=update_data
        )
        
        logger.info(f"✅ Successfully switched to table {request.new_table_index} and updated AI mappings")
        
        return {
            'success': True,
            'new_table_index': request.new_table_index,
            'ai_mappings': new_mappings.get('mappings', []),
            'unmapped_fields': new_mappings.get('unmapped_fields', []),
            'confidence': new_mappings.get('overall_confidence', 0.0),
            'statistics': new_mappings.get('mapping_statistics', {}),
            'table_info': {
                'headers': headers,
                'row_count': len(rows),
                'selected_by': 'user'
            },
            'message': f'Successfully switched to table {request.new_table_index + 1} and re-ran AI field mapping',
            'timestamp': datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error switching mapping table: {e}")
        raise HTTPException(status_code=500, detail=f"Table switching failed: {str(e)}")


@router.post("/ai/analyze-table-suitability")
async def analyze_table_suitability(
    request: AnalyzeTableSuitabilityRequest,
    current_user: User = Depends(get_current_user_hybrid),
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze multiple tables for field mapping suitability
    
    This endpoint uses AI to analyze and rank tables based on their
    suitability for field mapping in commission tracking systems.
    
    Args:
        request: AnalyzeTableSuitabilityRequest with tables and context
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Analysis results with recommended table and confidence scores
    """
    try:
        logger.info(f"🔍 Table suitability analysis requested by user {current_user.id} for {len(request.tables)} tables")
        
        if not request.tables:
            raise HTTPException(status_code=400, detail="No tables provided for analysis")
        
        # Use table suitability service
        from app.services.table_suitability_service import TableSuitabilityService
        suitability_service = TableSuitabilityService()
        
        if not suitability_service.is_available():
            logger.warning("⚠️ AI table suitability service not available, using fallback")
        
        # Analyze tables
        analysis = await suitability_service.analyze_tables_for_mapping(
            tables=request.tables,
            document_context=request.document_context or {}
        )
        
        if not analysis.get('success'):
            raise HTTPException(
                status_code=500,
                detail=f"Table analysis failed: {analysis.get('error', 'Unknown error')}"
            )
        
        logger.info(f"✅ Table analysis complete: Recommended table {analysis.get('recommended_table_index')} with {analysis.get('confidence', 0):.2f} confidence")
        
        return {
            'success': True,
            'analysis': analysis,
            'recommended_table': analysis.get('recommended_table_index', 0),
            'confidence': analysis.get('confidence', 0.0),
            'requires_user_confirmation': analysis.get('requires_user_confirmation', False),
            'table_scores': analysis.get('table_analysis', []),
            'metadata': analysis.get('analysis_metadata', {}),
            'timestamp': datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error analyzing table suitability: {e}")
        raise HTTPException(status_code=500, detail=f"Table analysis failed: {str(e)}")


@router.get("/ai/table-selection-history/{upload_id}")
async def get_table_selection_history(
    upload_id: str,
    current_user: User = Depends(get_current_user_hybrid),
    db: AsyncSession = Depends(get_db)
):
    """
    Get table selection history for an upload
    
    Shows the history of table selections and switches for audit purposes.
    
    Args:
        upload_id: Upload ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Table selection history
    """
    try:
        # Get upload record
        upload_record = await with_db_retry(db, crud.get_upload_by_id, upload_id)
        
        if not upload_record:
            raise HTTPException(status_code=404, detail="Upload not found")
        
        # Verify user has access
        if upload_record.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get AI intelligence data
        ai_intelligence = upload_record.ai_intelligence or {}
        
        # Get table selection history
        history = ai_intelligence.get('table_switch_history', [])
        
        # Get current selection
        current_selection = ai_intelligence.get('table_selection', {})
        
        return {
            'success': True,
            'upload_id': upload_id,
            'current_selection': current_selection,
            'history': history,
            'total_switches': len(history),
            'timestamp': datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting table selection history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")


@router.get("/ai/table-mapping-status/{upload_id}")
async def get_table_mapping_status(
    upload_id: str,
    current_user: User = Depends(get_current_user_hybrid),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current table mapping status for an upload
    
    Returns the current table selection, AI mappings, and analysis data.
    
    Args:
        upload_id: Upload ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Current table mapping status
    """
    try:
        # Get upload record
        upload_record = await with_db_retry(db, crud.get_upload_by_id, upload_id)
        
        if not upload_record:
            raise HTTPException(status_code=404, detail="Upload not found")
        
        # Verify user has access
        if upload_record.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get AI intelligence data
        ai_intelligence = upload_record.ai_intelligence or {}
        
        # Get tables
        tables = upload_record.raw_data if isinstance(upload_record.raw_data, list) else []
        
        return {
            'success': True,
            'upload_id': upload_id,
            'table_selection': ai_intelligence.get('table_selection', {}),
            'field_mapping': ai_intelligence.get('field_mapping', {}),
            'plan_type_detection': ai_intelligence.get('plan_type_detection', {}),
            'total_tables': len(tables),
            'available_tables': [
                {
                    'index': i,
                    'headers': table.get('header', []) or table.get('headers', []),
                    'row_count': len(table.get('rows', [])),
                    'name': f"Table {i + 1}"
                }
                for i, table in enumerate(tables)
            ],
            'timestamp': datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting table mapping status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")

