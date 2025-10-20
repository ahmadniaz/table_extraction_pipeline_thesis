from ..models import StatementUpload as StatementUploadModel
from ..schemas import StatementUpload, StatementUploadCreate, StatementUploadUpdate, PendingFile
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from uuid import UUID
from typing import List, Optional, Dict, Any

async def save_statement_upload(db, upload: StatementUpload):
    db_upload = StatementUploadModel(
        id=upload.id,
        company_id=upload.company_id,
        carrier_id=upload.carrier_id,  # CRITICAL FIX: Include carrier_id when saving
        user_id=upload.user_id,
        file_name=upload.file_name,
        file_hash=upload.file_hash,
        file_size=upload.file_size,
        uploaded_at=upload.uploaded_at,
        status=upload.status,
        current_step=upload.current_step,
        raw_data=upload.raw_data,
        mapping_used=upload.mapping_used,
        last_updated=upload.last_updated or datetime.utcnow()
    )
    db.add(db_upload)
    await db.commit()
    await db.refresh(db_upload)
    return db_upload

async def create_statement_upload(db: AsyncSession, upload: StatementUploadCreate) -> StatementUploadModel:
    """
    Create a new statement upload with pending status.
    """
    db_upload = StatementUploadModel(
        company_id=upload.company_id,
        user_id=upload.user_id,
        file_name=upload.file_name,
        file_hash=upload.file_hash,
        file_size=upload.file_size,
        status=upload.status,
        current_step=upload.current_step,
        progress_data=upload.progress_data,
        uploaded_at=datetime.utcnow(),
        last_updated=datetime.utcnow()
    )
    db.add(db_upload)
    await db.commit()
    await db.refresh(db_upload)
    return db_upload

async def update_statement_upload(db: AsyncSession, upload_id: UUID, update_data: StatementUploadUpdate) -> Optional[StatementUploadModel]:
    """
    Update statement upload with progress data and status changes.
    """
    result = await db.execute(select(StatementUploadModel).where(StatementUploadModel.id == upload_id))
    db_upload = result.scalar_one_or_none()
    
    if not db_upload:
        return None
    
    # Update fields if provided
    update_dict = update_data.dict(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(db_upload, field, value)
    
    # Update last_updated timestamp
    db_upload.last_updated = datetime.utcnow()
    
    # Set completed_at if status is approved or rejected
    if update_data.status in ['approved', 'rejected']:
        db_upload.completed_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(db_upload)
    return db_upload

async def get_pending_files_for_company(db: AsyncSession, company_id: UUID) -> List[PendingFile]:
    """
    Get all pending files for a specific company.
    """
    result = await db.execute(
        select(StatementUploadModel).where(
            StatementUploadModel.company_id == company_id,
            StatementUploadModel.status == 'pending'
        ).order_by(StatementUploadModel.last_updated.desc())
    )
    uploads = result.scalars().all()
    
    pending_files = []
    for upload in uploads:
        # Create human-readable progress summary
        progress_summary = get_progress_summary(upload.current_step, upload.progress_data)
        
        pending_file = PendingFile(
            id=upload.id,
            company_id=upload.company_id,
            file_name=upload.file_name,
            uploaded_at=upload.uploaded_at,
            current_step=upload.current_step,
            last_updated=upload.last_updated,
            progress_summary=progress_summary
        )
        pending_files.append(pending_file)
    
    return pending_files

async def get_pending_files_for_company_by_user(db: AsyncSession, company_id: UUID, user_id: UUID) -> List[PendingFile]:
    """
    Get all pending files for a specific company filtered by user.
    """
    result = await db.execute(
        select(StatementUploadModel).where(
            StatementUploadModel.company_id == company_id,
            StatementUploadModel.user_id == user_id,
            StatementUploadModel.status == 'pending'
        ).order_by(StatementUploadModel.last_updated.desc())
    )
    uploads = result.scalars().all()
    
    pending_files = []
    for upload in uploads:
        # Create human-readable progress summary
        progress_summary = get_progress_summary(upload.current_step, upload.progress_data)
        
        pending_file = PendingFile(
            id=upload.id,
            company_id=upload.company_id,
            file_name=upload.file_name,
            uploaded_at=upload.uploaded_at,
            current_step=upload.current_step,
            last_updated=upload.last_updated,
            progress_summary=progress_summary
        )
        pending_files.append(pending_file)
    
    return pending_files

async def get_statement_upload_by_id(db: AsyncSession, upload_id: UUID) -> Optional[StatementUploadModel]:
    """
    Get statement upload by ID with all progress data.
    """
    result = await db.execute(select(StatementUploadModel).where(StatementUploadModel.id == upload_id))
    return result.scalar_one_or_none()

async def save_progress_data(db: AsyncSession, upload_id: UUID, step: str, data: dict, session_id: Optional[str] = None) -> bool:
    """
    Save progress data for a specific step.
    """
    result = await db.execute(select(StatementUploadModel).where(StatementUploadModel.id == upload_id))
    db_upload = result.scalar_one_or_none()
    
    if not db_upload:
        return False
    
    # Update progress data
    if not db_upload.progress_data:
        db_upload.progress_data = {}
    
    db_upload.progress_data[step] = data
    db_upload.current_step = step
    db_upload.last_updated = datetime.utcnow()
    
    if session_id:
        db_upload.session_id = session_id
    
    await db.commit()
    return True

async def get_progress_data(db: AsyncSession, upload_id: UUID, step: str) -> Optional[dict]:
    """
    Get progress data for a specific step.
    """
    result = await db.execute(select(StatementUploadModel).where(StatementUploadModel.id == upload_id))
    db_upload = result.scalar_one_or_none()
    
    if not db_upload or not db_upload.progress_data:
        return None
    
    return db_upload.progress_data.get(step)

async def resume_upload_session(db: AsyncSession, upload_id: UUID) -> Optional[dict]:
    """
    Resume an upload session with all saved progress data.
    """
    result = await db.execute(select(StatementUploadModel).where(StatementUploadModel.id == upload_id))
    db_upload = result.scalar_one_or_none()
    
    if not db_upload or db_upload.status != 'pending':
        return None
    
    return {
        'id': db_upload.id,
        'company_id': db_upload.company_id,
        'file_name': db_upload.file_name,
        'current_step': db_upload.current_step,
        'progress_data': db_upload.progress_data,
        'raw_data': db_upload.raw_data,
        'edited_tables': db_upload.edited_tables,
        'field_mapping': db_upload.field_mapping,
        'field_config': db_upload.field_config,
        'last_updated': db_upload.last_updated
    }

async def delete_pending_upload(db: AsyncSession, upload_id: UUID) -> bool:
    """
    Delete a pending upload.
    """
    result = await db.execute(select(StatementUploadModel).where(StatementUploadModel.id == upload_id))
    db_upload = result.scalar_one_or_none()
    
    if not db_upload or db_upload.status != 'pending':
        return False
    
    await db.delete(db_upload)
    await db.commit()
    return True

async def save_statement_review(
    db, *,
    upload_id,
    final_data,
    status: str,
    field_config,
    rejection_reason: str = None,
    plan_types: list = None,
    selected_statement_date: dict = None
):
    """
    Save statement review with updated status tracking.
    """
    # Convert string to UUID if needed
    try:
        if isinstance(upload_id, str):
            upload_id_uuid = UUID(upload_id)
        else:
            upload_id_uuid = upload_id
    except (ValueError, AttributeError):
        print(f"💾 Invalid upload_id format: {upload_id}")
        return None
    
    result = await db.execute(select(StatementUploadModel).where(StatementUploadModel.id == upload_id_uuid))
    db_upload = result.scalar_one_or_none()
    
    if not db_upload:
        print(f"💾 Upload not found for ID: {upload_id_uuid}")
        return None
    
    print(f"💾 Saving statement review: upload_id={upload_id_uuid}, status={status}")
    print(f"📋 Field config being saved: {field_config}")
    print(f"📊 Final data rows: {len(final_data) if final_data else 0}")
    print(f"📅 Selected statement date being saved: {selected_statement_date}")
    
    # Update the upload with final data
    db_upload.final_data = final_data
    db_upload.status = status
    db_upload.current_step = 'completed'
    db_upload.field_config = field_config
    db_upload.rejection_reason = rejection_reason
    db_upload.plan_types = plan_types
    db_upload.selected_statement_date = selected_statement_date
    db_upload.completed_at = datetime.utcnow()
    db_upload.last_updated = datetime.utcnow()
    
    # If the statement is approved, process commission data BEFORE committing
    if status == "Approved":
        print(f"✅ Statement approved, processing commission data with BULK OPTIMIZATION...")
        from .earned_commission import bulk_process_commissions
        await bulk_process_commissions(db, db_upload)
    
    # Commit all changes together (statement + commission data)
    await db.commit()
    await db.refresh(db_upload)
    
    return db_upload

async def get_all_statement_reviews(db):
    """
    Get all statement reviews with pending files included.
    """
    result = await db.execute(
        select(StatementUploadModel).order_by(StatementUploadModel.last_updated.desc())
    )
    return result.scalars().all()

async def get_statements_for_company(db, company_id):
    """
    Get all statements for a company including pending files.
    """
    result = await db.execute(
        select(StatementUploadModel).where(StatementUploadModel.company_id == company_id)
        .order_by(StatementUploadModel.last_updated.desc())
    )
    return result.scalars().all()

async def get_statements_for_carrier(db, carrier_id):
    """
    Get all statements for a specific carrier.
    NOTE: Support both old (company_id) and new (carrier_id) format for backwards compatibility.
    Old format: carrier stored in company_id, carrier_id is NULL
    New format: carrier stored in carrier_id
    """
    from sqlalchemy import or_, and_
    result = await db.execute(
        select(StatementUploadModel).where(
            or_(
                StatementUploadModel.carrier_id == carrier_id,
                and_(
                    StatementUploadModel.company_id == carrier_id,
                    StatementUploadModel.carrier_id.is_(None)
                )
            )
        )
        .order_by(StatementUploadModel.last_updated.desc())
    )
    return result.scalars().all()

async def get_statement_by_id(db: AsyncSession, statement_id: str):
    try:
        # Convert string to UUID if needed
        if isinstance(statement_id, str):
            statement_id = UUID(statement_id)
        result = await db.execute(select(StatementUploadModel).where(StatementUploadModel.id == statement_id))
        return result.scalar_one_or_none()
    except ValueError:
        # Invalid UUID format
        return None

async def delete_statement(db: AsyncSession, statement_id: str):
    statement = await get_statement_by_id(db, statement_id)
    if not statement:
        raise ValueError(f"Statement with ID {statement_id} not found")
    
    try:
        # Check if edited_tables table exists before trying to delete from it
        from sqlalchemy import text
        result = await db.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'edited_tables'
        """))
        edited_tables_exists = result.fetchone() is not None
        
        # Delete related edited tables first (only if table exists)
        if edited_tables_exists:
            await db.execute(
                text("DELETE FROM edited_tables WHERE upload_id = :upload_id"),
                {"upload_id": statement_id}
            )
        
        # Remove this upload from earned commission records
        from .earned_commission import remove_upload_from_earned_commissions
        await remove_upload_from_earned_commissions(db, statement_id)
        
         # Delete user data contributions that reference this upload
        await db.execute(
            text("DELETE FROM user_data_contributions WHERE upload_id = :upload_id"),
            {"upload_id": statement_id}
        )
        
        # Delete file duplicate records that reference this upload
        await db.execute(
            text("DELETE FROM file_duplicates WHERE original_upload_id = :upload_id OR duplicate_upload_id = :upload_id"),
            {"upload_id": statement_id}
        )
        
        # Delete the statement
        await db.delete(statement)
        await db.commit()
        return True
    except Exception as e:
        await db.rollback()
        raise ValueError(f"Failed to delete statement: {str(e)}")

async def save_edited_tables(db: AsyncSession, tables_data: list):
    """
    Save edited tables with progress tracking.
    """
    if not tables_data:
        return None
    
    # Get the upload_id from the first table
    upload_id = tables_data[0].get('upload_id')
    if not upload_id:
        return None
    
    # Update the upload with edited tables
    result = await db.execute(select(StatementUploadModel).where(StatementUploadModel.id == upload_id))
    db_upload = result.scalar_one_or_none()
    
    if not db_upload:
        return None
    
    db_upload.edited_tables = tables_data
    db_upload.current_step = 'table_editor'
    db_upload.last_updated = datetime.utcnow()
    
    # Save in progress_data
    if not db_upload.progress_data:
        db_upload.progress_data = {}
    
    db_upload.progress_data['table_editor'] = {
        'tables': tables_data,
        'table_count': len(tables_data)
    }
    
    await db.commit()
    await db.refresh(db_upload)
    return db_upload

async def get_edited_tables(db: AsyncSession, upload_id: str):
    """
    Get edited tables for an upload.
    """
    # Convert string to UUID if needed
    try:
        if isinstance(upload_id, str):
            upload_id_uuid = UUID(upload_id)
        else:
            upload_id_uuid = upload_id
    except (ValueError, AttributeError):
        return None
    
    result = await db.execute(select(StatementUploadModel).where(StatementUploadModel.id == upload_id_uuid))
    db_upload = result.scalar_one_or_none()
    
    if not db_upload:
        return None
    
    return db_upload.edited_tables

async def update_upload_tables(db: AsyncSession, upload_id: str, tables_data: list, selected_statement_date: Optional[Dict[str, Any]] = None, carrier_id: Optional[str] = None):
    """
    Update upload tables with progress tracking, selected statement date, and carrier information.
    """
    print(f"🎯 CRUD: update_upload_tables called for upload_id: {upload_id}")
    print(f"🎯 CRUD: Tables data length: {len(tables_data) if tables_data else 0}")
    print(f"🎯 CRUD: Selected statement date: {selected_statement_date}")
    print(f"🎯 CRUD: Carrier ID: {carrier_id}")
    
    # Convert string to UUID if needed
    try:
        if isinstance(upload_id, str):
            upload_id_uuid = UUID(upload_id)
        else:
            upload_id_uuid = upload_id
    except (ValueError, AttributeError) as e:
        print(f"🎯 CRUD: Invalid upload_id format: {upload_id}, error: {e}")
        return None
    
    result = await db.execute(select(StatementUploadModel).where(StatementUploadModel.id == upload_id_uuid))
    db_upload = result.scalar_one_or_none()
    
    if not db_upload:
        print(f"🎯 CRUD: Upload not found for ID: {upload_id_uuid}")
        return None
    
    print(f"🎯 CRUD: Found upload, updating with tables, statement date, and carrier")
    
    # Save edited tables to edited_tables field, not raw_data
    db_upload.edited_tables = tables_data
    db_upload.current_step = 'table_editor'
    db_upload.last_updated = datetime.utcnow()
    
    # Save selected statement date if provided
    if selected_statement_date:
        db_upload.selected_statement_date = selected_statement_date
        print(f"🎯 CRUD: Saved selected statement date to database: {selected_statement_date}")
        print(f"🎯 CRUD: Statement date type: {type(selected_statement_date)}")
        print(f"🎯 CRUD: Statement date keys: {list(selected_statement_date.keys()) if isinstance(selected_statement_date, dict) else 'Not a dict'}")
    else:
        print(f"🎯 CRUD: No selected statement date provided")
    
    # Update carrier_id if provided (this links the statement to the carrier)
    # CRITICAL FIX: Update both carrier_id AND company_id for backwards compatibility
    if carrier_id:
        db_upload.carrier_id = carrier_id
        db_upload.company_id = carrier_id  # Also update company_id for backwards compatibility
        print(f"🎯 CRUD: Linking statement to carrier: carrier_id={carrier_id}, company_id={carrier_id}")
    
    # Save in progress_data
    if not db_upload.progress_data:
        db_upload.progress_data = {}
    
    db_upload.progress_data['extraction'] = {
        'tables': tables_data,
        'table_count': len(tables_data)
    }
    
    # Also save selected statement date and carrier info in progress data
    if selected_statement_date or carrier_id:
        db_upload.progress_data['table_editor'] = {
            'selected_statement_date': selected_statement_date,
            'carrier_id': carrier_id
        }
        print(f"🎯 CRUD: Also saved statement date and carrier to progress_data")
    
    await db.commit()
    await db.refresh(db_upload)
    
    print(f"🎯 CRUD: Successfully updated upload {upload_id_uuid} with tables, statement date, and carrier")
    print(f"🎯 CRUD: Final selected_statement_date in database: {db_upload.selected_statement_date}")
    
    return db_upload

async def delete_edited_tables(db: AsyncSession, upload_id: str):
    """
    Delete edited tables for an upload.
    """
    # Convert string to UUID if needed
    try:
        if isinstance(upload_id, str):
            upload_id_uuid = UUID(upload_id)
        else:
            upload_id_uuid = upload_id
    except (ValueError, AttributeError):
        return False
    
    result = await db.execute(select(StatementUploadModel).where(StatementUploadModel.id == upload_id_uuid))
    db_upload = result.scalar_one_or_none()
    
    if not db_upload:
        return False
    
    db_upload.edited_tables = None
    
    # Remove from progress_data
    if db_upload.progress_data and 'table_editor' in db_upload.progress_data:
        del db_upload.progress_data['table_editor']
    
    await db.commit()
    return True

async def get_upload_by_id(db: AsyncSession, upload_id: str):
    """
    Get upload by ID with all progress data.
    """
    # Convert string to UUID if needed
    try:
        if isinstance(upload_id, str):
            upload_id_uuid = UUID(upload_id)
        else:
            upload_id_uuid = upload_id
    except (ValueError, AttributeError):
        return None
    
    result = await db.execute(select(StatementUploadModel).where(StatementUploadModel.id == upload_id_uuid))
    return result.scalar_one_or_none()

def get_progress_summary(current_step: str, progress_data: Optional[dict]) -> str:
    """
    Generate a human-readable summary of the current progress.
    """
    step_descriptions = {
        'upload': 'File uploaded, ready for processing',
        'table_editor': 'Tables extracted, ready for editing',
        'field_mapper': 'Tables edited, ready for field mapping',
        'dashboard': 'Field mapping completed, ready for review',
        'completed': 'Processing completed'
    }
    
    base_description = step_descriptions.get(current_step, f'At step: {current_step}')
    
    if progress_data:
        if current_step == 'table_editor' and 'tables' in progress_data:
            table_count = len(progress_data['tables'])
            return f'{base_description} ({table_count} tables)'
        elif current_step == 'field_mapper' and 'mapping' in progress_data:
            mapped_fields = len(progress_data['mapping'])
            return f'{base_description} ({mapped_fields} fields mapped)'
    
    return base_description
