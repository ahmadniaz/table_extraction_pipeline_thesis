from ..models import CompanyFieldMapping, CompanyConfiguration
from ..schemas import CompanyFieldMappingCreate
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.future import select
from datetime import datetime

async def save_company_mapping(db, mapping):
    """
    Upsert company field mapping.
    """
    now = datetime.utcnow()
    stmt = pg_insert(CompanyFieldMapping).values(
        company_id=mapping.company_id,
        display_name=mapping.display_name,
        column_name=mapping.column_name,
        created_at=now,
        updated_at=now,
    ).on_conflict_do_update(
        index_elements=['company_id', 'display_name'],
        set_={
            "column_name": mapping.column_name,
            "updated_at": now
        }
    ).returning(CompanyFieldMapping)
    result = await db.execute(stmt)
    await db.commit()
    return result.fetchone()

async def get_company_configuration(db, company_id):
    """
    Get company configuration (field_config, plan_types, table_names).
    """
    result = await db.execute(
        select(CompanyConfiguration)
        .where(CompanyConfiguration.company_id == company_id)
    )
    return result.scalar_one_or_none()

async def save_company_configuration(db, company_id, field_config=None, plan_types=None, table_names=None):
    """
    Upsert company configuration.
    """
    now = datetime.utcnow()
    
    # Check if configuration exists
    existing_config = await get_company_configuration(db, company_id)
    
    if existing_config:
        # Update existing configuration
        if field_config is not None:
            existing_config.field_config = field_config
        if plan_types is not None:
            existing_config.plan_types = plan_types
        if table_names is not None:
            existing_config.table_names = table_names
        existing_config.updated_at = now
        await db.commit()
        await db.refresh(existing_config)
        return existing_config
    else:
        # Create new configuration
        new_config = CompanyConfiguration(
            company_id=company_id,
            field_config=field_config,
            plan_types=plan_types,
            table_names=table_names,
            created_at=now,
            updated_at=now
        )
        db.add(new_config)
        await db.commit()
        await db.refresh(new_config)
        return new_config

async def get_company_mappings(db, company_id):
    result = await db.execute(select(CompanyFieldMapping).where(CompanyFieldMapping.company_id == company_id))
    return result.scalars().all()

async def save_company_mapping_config(db, company_id, plan_types, table_names, field_config):
    """
    Save company mapping configuration with progress tracking.
    """
    # Find the latest upload for this company
    from .company import get_latest_statement_upload_for_company
    latest_upload = await get_latest_statement_upload_for_company(db, company_id)
    
    if latest_upload:
        # Update the upload with mapping configuration
        latest_upload.field_config = field_config
        latest_upload.plan_types = plan_types
        latest_upload.current_step = 'field_mapper'
        latest_upload.last_updated = datetime.utcnow()
        
        # Save mapping data in progress_data
        if not latest_upload.progress_data:
            latest_upload.progress_data = {}
        
        latest_upload.progress_data['field_mapper'] = {
            'plan_types': plan_types,
            'table_names': table_names,
            'field_config': field_config
        }
        
        await db.commit()
        await db.refresh(latest_upload)
        return latest_upload
    
    return None
