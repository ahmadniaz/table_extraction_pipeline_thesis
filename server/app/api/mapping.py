from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import crud, schemas
from app.config import get_db
from app.utils.db_retry import with_db_retry
from app.services.format_learning_service import FormatLearningService
from app.dependencies.auth_dependencies import get_current_user_hybrid
from app.db.models import User
from typing import List, Dict, Any
from datetime import datetime
from uuid import UUID
import re
import logging

router = APIRouter(prefix="/api")
format_learning_service = FormatLearningService()
logger = logging.getLogger(__name__)

# --- New Pydantic schema for mapping config ---
from pydantic import BaseModel

class MappingConfig(BaseModel):
    mapping: Dict[str, str]
    plan_types: List[str] = []
    table_names: List[str] = []
    field_config: List[Dict[str, str]] = []
    table_data: List[List[str]] = []  # Add table data for learning
    headers: List[str] = []  # Add headers for learning
    selected_statement_date: Dict[str, Any] = None  # Add selected statement date

@router.get("/companies/{company_id}/mapping/", response_model=MappingConfig)
async def get_company_mapping(
    company_id: str, 
    db: AsyncSession = Depends(get_db),
    upload_id: str = None  # Optional upload_id parameter to retrieve carrier_id
):
    """
    Get mapping configuration for a company (carrier).
    company_id parameter is actually the carrier_id in the new flow.
    
    If upload_id is provided, we retrieve the carrier_id from the statement_upload
    and use that instead of the company_id parameter.
    """
    logger.info(f"🎯 Mapping API: Getting mapping for carrier/company {company_id}")
    logger.info(f"🎯 Mapping API: Upload ID: {upload_id}")
    
    # If upload_id is provided, retrieve the carrier_id from statement_upload
    carrier_id = company_id  # Default to provided company_id
    if upload_id:
        try:
            from uuid import UUID
            upload_uuid = UUID(upload_id)
            upload_record = await with_db_retry(db, crud.get_statement_upload_by_id, upload_id=upload_uuid)
            if upload_record and upload_record.carrier_id:
                carrier_id = str(upload_record.carrier_id)
                logger.info(f"🎯 Mapping API: Retrieved carrier_id from upload: {carrier_id}")
            else:
                logger.warning(f"🎯 Mapping API: No carrier_id found in upload record, using provided company_id")
        except Exception as e:
            logger.error(f"🎯 Mapping API: Error retrieving carrier_id from upload: {e}")
            logger.warning(f"🎯 Mapping API: Falling back to provided company_id")
    
    logger.info(f"🎯 Mapping API: Final carrier_id to use: {carrier_id}")
    
    # Fetch mapping from company_field_mappings table with retry
    mapping_rows = await with_db_retry(db, crud.get_company_mappings, company_id=carrier_id)
    mapping = {row.display_name: row.column_name for row in mapping_rows}
    logger.info(f"🎯 Mapping API: Found {len(mapping)} existing mappings for carrier {carrier_id}")
    
    # Fetch company configuration (field_config, plan_types, table_names) with retry
    company_config = await with_db_retry(db, crud.get_company_configuration, company_id=carrier_id)
    
    # Use company configuration if available, otherwise fall back to defaults
    plan_types = company_config.plan_types if company_config and company_config.plan_types else []
    table_names = company_config.table_names if company_config and company_config.table_names else []
    
    # Get field_config from company configuration if available, otherwise return empty list for new carriers
    if company_config and company_config.field_config:
        field_config = company_config.field_config
        logger.info(f"🎯 Mapping API: Found existing field_config with {len(field_config)} fields for carrier {carrier_id}")
    else:
        # For new carriers with no existing configuration, return empty field_config
        # This allows the frontend to start with empty fields and let users add them manually
        field_config = []
        logger.info(f"🎯 Mapping API: No existing field_config found for carrier {carrier_id}")
    
    return MappingConfig(
        mapping=mapping,
        plan_types=plan_types,
        table_names=table_names,
        field_config=field_config
    )

@router.post("/companies/{company_id}/mapping/")
async def update_company_mapping(
    company_id: str, 
    config: MappingConfig, 
    current_user: User = Depends(get_current_user_hybrid),
    db: AsyncSession = Depends(get_db),
    upload_id: str = None  # Optional upload_id parameter to retrieve carrier_id
):
    """
    Update mapping configuration for a company (carrier).
    company_id parameter is actually the carrier_id in the new flow.
    
    If upload_id is provided, we retrieve the carrier_id from the statement_upload
    and use that instead of the company_id parameter.
    """
    logger.info(f"🎯 Mapping API: Received mapping request for carrier/company {company_id}")
    logger.info(f"🎯 Mapping API: Upload ID: {upload_id}")
    logger.info(f"🎯 Mapping API: Config received - mapping keys: {list(config.mapping.keys()) if config.mapping else 'None'}")
    logger.info(f"🎯 Mapping API: Selected statement date: {config.selected_statement_date}")
    logger.info(f"🎯 Mapping API: Table data rows: {len(config.table_data) if config.table_data else 0}")
    logger.info(f"🎯 Mapping API: Headers: {config.headers}")
    
    # If upload_id is provided, retrieve the carrier_id from statement_upload
    carrier_id = company_id  # Default to provided company_id
    if upload_id:
        try:
            from uuid import UUID
            upload_uuid = UUID(upload_id)
            upload_record = await with_db_retry(db, crud.get_statement_upload_by_id, upload_id=upload_uuid)
            if upload_record and upload_record.carrier_id:
                carrier_id = str(upload_record.carrier_id)
                logger.info(f"🎯 Mapping API: Retrieved carrier_id from upload: {carrier_id}")
            else:
                logger.warning(f"🎯 Mapping API: No carrier_id found in upload record, using provided company_id")
        except Exception as e:
            logger.error(f"🎯 Mapping API: Error retrieving carrier_id from upload: {e}")
            logger.warning(f"🎯 Mapping API: Falling back to provided company_id")
    
    logger.info(f"🎯 Mapping API: Final carrier_id to use: {carrier_id}")
    
    # Save field mapping to company_field_mappings table with retry
    # This saves mapping for the CARRIER (not user's company)
    for display_name, column_name in config.mapping.items():
        mapping_obj = schemas.CompanyFieldMappingCreate(
            company_id=carrier_id,  # carrier_id (retrieved from upload or provided as parameter)
            display_name=display_name,
            column_name=column_name,
        )
        await with_db_retry(db, crud.save_company_mapping, mapping=mapping_obj)
    logger.info(f"🎯 Mapping API: Saved {len(config.mapping)} field mappings for carrier {carrier_id}")
    
    # Save field_config, plan_types, and table_names to company_configurations table with retry
    await with_db_retry(
        db, 
        crud.save_company_configuration,
        company_id=carrier_id,  # carrier_id (retrieved from upload or provided as parameter)
        field_config=config.field_config,
        plan_types=config.plan_types,
        table_names=config.table_names
    )
    logger.info(f"🎯 Mapping API: Saved configuration for carrier {carrier_id}")
    
    # Learn from the processed file if table data is provided
    # This learns format patterns for the CARRIER
    if config.table_data and config.headers and config.mapping:
        try:
            logger.info(f"🎯 Mapping API: Learning format from processed file for carrier {carrier_id}")
            logger.info(f"🎯 Mapping API: Table data length: {len(config.table_data)}")
            logger.info(f"🎯 Mapping API: Headers: {config.headers}")
            logger.info(f"🎯 Mapping API: Mapping: {config.mapping}")
            
            # Get carrier name from database to pass to format learning
            carrier_name = None
            try:
                carrier_record = await with_db_retry(db, crud.get_company_by_id, company_id=carrier_id)
                if carrier_record:
                    carrier_name = carrier_record.name
                    logger.info(f"🎯 Mapping API: Retrieved carrier name for format learning: {carrier_name}")
            except Exception as carrier_error:
                logger.warning(f"🎯 Mapping API: Could not retrieve carrier name: {carrier_error}")
            
            await format_learning_service.learn_from_processed_file(
                db=db,
                company_id=carrier_id,  # carrier_id - format learning for this carrier
                table_data=config.table_data,
                headers=config.headers,
                field_mapping=config.mapping,
                confidence_score=85,  # Higher confidence for manually mapped data
                table_editor_settings=None,  # Will be learned from table editor save
                carrier_name=carrier_name,  # CRITICAL: Pass carrier name for format learning
                statement_date=config.selected_statement_date.get('date') if config.selected_statement_date else None
            )
            logger.info(f"🎯 Mapping API: Format learning completed successfully for carrier {carrier_id}")
        except Exception as e:
            # Log error but don't fail the mapping save
            logger.error(f"🎯 Mapping API: Error learning from processed file: {e}")
            print(f"Error learning from processed file: {e}")
    
    # Process commission data with statement date if provided
    if config.selected_statement_date and config.table_data:
        try:
            logger.info(f"🎯 Mapping API: Processing commission data with statement date")
            logger.info(f"🎯 Mapping API: Statement date object: {config.selected_statement_date}")
            await process_commission_data_with_date(
                db=db,
                company_id=carrier_id,  # carrier_id (retrieved from upload or provided as parameter)
                table_data=config.table_data,
                headers=config.headers,
                mapping=config.mapping,
                statement_date=config.selected_statement_date,
                user_id=current_user.id  # CRITICAL: Pass user_id for proper data isolation
            )
            logger.info(f"🎯 Mapping API: Commission data processing completed successfully")
        except Exception as e:
            # Log error but don't fail the mapping save
            logger.error(f"🎯 Mapping API: Error processing commission data: {e}")
            print(f"Error processing commission data: {e}")
    else:
        logger.warning(f"🎯 Mapping API: No statement date or table data provided for commission processing")
        if not config.selected_statement_date:
            logger.warning(f"🎯 Mapping API: selected_statement_date is None or empty")
        if not config.table_data:
            logger.warning(f"🎯 Mapping API: table_data is None or empty")
    
    logger.info(f"🎯 Mapping API: Mapping update completed successfully for carrier {carrier_id}")
    return {"ok": True}


async def process_commission_data_with_date(
    db: AsyncSession,
    company_id: str,
    table_data: List[List[str]],
    headers: List[str],
    mapping: Dict[str, str],
    statement_date: Dict[str, Any],
    user_id: UUID = None
):
    """
    Process commission data and create/update earned commission records with statement date.
    Includes user_id for proper data isolation in multi-user environments.
    """
    try:
        logger.info(f"🎯 Commission Processing: Starting commission data processing")
        logger.info(f"🎯 Commission Processing: Company ID: {company_id}")
        logger.info(f"🎯 Commission Processing: Table data rows: {len(table_data)}")
        logger.info(f"🎯 Commission Processing: Headers: {headers}")
        logger.info(f"🎯 Commission Processing: Mapping: {mapping}")
        logger.info(f"🎯 Commission Processing: Statement date: {statement_date}")
        
        # Parse the statement date
        date_value = statement_date.get('date') or statement_date.get('date_value', '')
        if not date_value:
            logger.warning(f"🎯 Commission Processing: No statement date provided")
            print("No statement date provided")
            return
        
        logger.info(f"🎯 Commission Processing: Date value extracted: {date_value}")
        
        # Parse the date string to get month and year
        parsed_date = parse_statement_date(date_value)
        if not parsed_date:
            logger.error(f"🎯 Commission Processing: Could not parse statement date: {date_value}")
            print(f"Could not parse statement date: {date_value}")
            return
        
        logger.info(f"🎯 Commission Processing: Parsed date: {parsed_date}")
        statement_month = parsed_date.month
        statement_year = parsed_date.year
        logger.info(f"🎯 Commission Processing: Month: {statement_month}, Year: {statement_year}")
        
        # Find the relevant columns from the mapping
        client_name_col = None
        invoice_total_col = None
        commission_col = None
        auto_fill_invoice = False
        
        # Look for common field names in the mapping
        # mapping is { original_header: mapped_database_field }
        # We need to use original_header to find the column index in headers array
        for original_header, mapped_field in mapping.items():
            mapped_lower = mapped_field.lower()
            
            # Check the mapped field name to understand what this column represents
            if any(keyword in mapped_lower for keyword in ['client', 'company', 'group']) and 'name' in mapped_lower:
                client_name_col = original_header  # Use original header, not mapped field
                logger.info(f"🎯 Commission Processing: Found client name column: {original_header} -> {mapped_field}")
            elif any(keyword in mapped_lower for keyword in ['invoice', 'premium']) and 'total' in mapped_lower:
                invoice_total_col = original_header  # Use original header, not mapped field
                logger.info(f"🎯 Commission Processing: Found invoice total column: {original_header} -> {mapped_field}")
                
                # Check if this is auto-filled with zero
                if mapped_field == '__AUTO_FILL_ZERO__':
                    auto_fill_invoice = True
                    invoice_total_col = None  # We'll handle this specially
                    logger.info(f"🎯 Commission Processing: Invoice total will be auto-filled with $0.00")
            elif any(keyword in mapped_lower for keyword in ['commission']) and any(k in mapped_lower for k in ['earned', 'paid', 'amount']):
                commission_col = original_header  # Use original header, not mapped field
                logger.info(f"🎯 Commission Processing: Found commission column: {original_header} -> {mapped_field}")
        
        # If we can't find the columns, try to infer from headers
        if not client_name_col:
            for i, header in enumerate(headers):
                header_lower = header.lower()
                if any(keyword in header_lower for keyword in ['company', 'client', 'group', 'name']):
                    client_name_col = headers[i]
                    logger.info(f"🎯 Commission Processing: Inferred client name column from headers: {headers[i]}")
                    break
        
        if not invoice_total_col:
            for i, header in enumerate(headers):
                header_lower = header.lower()
                if any(keyword in header_lower for keyword in ['invoice', 'premium', 'total', 'amount']):
                    invoice_total_col = headers[i]
                    logger.info(f"🎯 Commission Processing: Inferred invoice total column from headers: {headers[i]}")
                    break
        
        if not commission_col:
            for i, header in enumerate(headers):
                header_lower = header.lower()
                if any(keyword in header_lower for keyword in ['commission', 'earned', 'paid']):
                    commission_col = headers[i]
                    logger.info(f"🎯 Commission Processing: Inferred commission column from headers: {headers[i]}")
                    break
        
        logger.info(f"🎯 Commission Processing: Final column mapping - Client: {client_name_col}, Invoice: {invoice_total_col}, Commission: {commission_col}")
        
        # Process each row in the table data
        processed_rows = 0
        for row_idx, row in enumerate(table_data):
            if len(row) != len(headers):
                logger.warning(f"🎯 Commission Processing: Row {row_idx} length mismatch - expected {len(headers)}, got {len(row)}")
                continue
            
            # Extract values
            client_name = row[headers.index(client_name_col)] if client_name_col else "Unknown"
            
            # Handle invoice total - either from column or auto-filled with zero
            if auto_fill_invoice:
                invoice_total_str = "0"  # Auto-fill with zero
                logger.info(f"🎯 Commission Processing: Auto-filling invoice total with $0.00 for {client_name}")
            else:
                invoice_total_str = row[headers.index(invoice_total_col)] if invoice_total_col else "0"
            
            commission_str = row[headers.index(commission_col)] if commission_col else "0"
            
            logger.info(f"🎯 Commission Processing: Row {row_idx} - Client: {client_name}, Invoice: {invoice_total_str}, Commission: {commission_str}")
            
            # Skip if no client name or if it's a summary row
            if not client_name or client_name.lower() in ['total', 'summary', 'subtotal', '']:
                logger.info(f"🎯 Commission Processing: Skipping row {row_idx} - summary row or no client name")
                continue
            
            # Parse numeric values
            invoice_total = parse_currency(invoice_total_str)
            commission_earned = parse_currency(commission_str)
            
            logger.info(f"🎯 Commission Processing: Row {row_idx} - Parsed values - Invoice: {invoice_total}, Commission: {commission_earned}")
            
            if commission_earned <= 0:
                logger.info(f"🎯 Commission Processing: Skipping row {row_idx} - commission <= 0")
                continue
            
            # Create or update commission record
            await create_or_update_commission_record(
                db=db,
                carrier_id=company_id,
                client_name=client_name,
                invoice_total=invoice_total,
                commission_earned=commission_earned,
                statement_date=parsed_date,
                statement_month=statement_month,
                statement_year=statement_year,
                user_id=user_id  # CRITICAL: Pass user_id for proper data isolation
            )
            processed_rows += 1
            logger.info(f"🎯 Commission Processing: Successfully processed row {row_idx}")
        
        logger.info(f"🎯 Commission Processing: Completed processing {processed_rows} rows with statement date {date_value}")
        print(f"Processed commission data for {len(table_data)} rows with statement date {date_value}")
        
    except Exception as e:
        logger.error(f"🎯 Commission Processing: Error processing commission data: {e}")
        print(f"Error processing commission data: {e}")
        raise


def parse_statement_date(date_str: str) -> datetime:
    """
    Parse various date formats from statement date string.
    """
    try:
        logger.info(f"🎯 Date Parsing: Attempting to parse date: {date_str}")
        
        # Remove any extra whitespace
        date_str = date_str.strip()
        
        # Try different date formats
        formats = [
            '%m/%d/%Y',  # 01/15/2025
            '%m-%d-%Y',  # 01-15-2025
            '%Y-%m-%d',  # 2025-01-15
            '%m/%d/%y',  # 01/15/25
            '%m-%d-%y',  # 01-15-25
            '%B %d, %Y',  # January 15, 2025
            '%b %d, %Y',  # Jan 15, 2025
            '%B%d, %Y',   # January28, 2025 (no space between month and day)
            '%b%d, %Y',   # Jan28, 2025 (no space between month and day)
        ]
        
        for fmt in formats:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                logger.info(f"🎯 Date Parsing: Successfully parsed date '{date_str}' with format '{fmt}' -> {parsed_date}")
                return parsed_date
            except ValueError:
                continue
        
        # If none of the formats work, try to extract date using regex
        import re
        
        # Match MM/DD/YYYY or MM-DD-YYYY
        match = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', date_str)
        if match:
            month, day, year = match.groups()
            parsed_date = datetime(int(year), int(month), int(day))
            logger.info(f"🎯 Date Parsing: Successfully parsed date '{date_str}' with regex MM/DD/YYYY -> {parsed_date}")
            return parsed_date
        
        # Match YYYY-MM-DD
        match = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', date_str)
        if match:
            year, month, day = match.groups()
            parsed_date = datetime(int(year), int(month), int(day))
            logger.info(f"🎯 Date Parsing: Successfully parsed date '{date_str}' with regex YYYY-MM-DD -> {parsed_date}")
            return parsed_date
        
        # **NEW: Handle month names without spaces (e.g., "January28,2025")
        month_names = ['January', 'February', 'March', 'April', 'May', 'June', 
                      'July', 'August', 'September', 'October', 'November', 'December']
        month_abbrevs = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        # Try full month names without space
        for month_name in month_names:
            pattern = f'^{month_name}(\\d{{1,2}}),?(\\d{{4}})$'
            match = re.search(pattern, date_str, re.IGNORECASE)
            if match:
                day, year = match.groups()
                month_num = datetime.strptime(month_name, '%B').month
                parsed_date = datetime(int(year), month_num, int(day))
                logger.info(f"🎯 Date Parsing: Successfully parsed date '{date_str}' with regex {month_name}DD,YYYY -> {parsed_date}")
                return parsed_date
        
        # Try abbreviated month names without space
        for month_abbrev in month_abbrevs:
            pattern = f'^{month_abbrev}(\\d{{1,2}}),?(\\d{{4}})$'
            match = re.search(pattern, date_str, re.IGNORECASE)
            if match:
                day, year = match.groups()
                month_num = datetime.strptime(month_abbrev, '%b').month
                parsed_date = datetime(int(year), month_num, int(day))
                logger.info(f"🎯 Date Parsing: Successfully parsed date '{date_str}' with regex {month_abbrev}DD,YYYY -> {parsed_date}")
                return parsed_date
        
        logger.error(f"🎯 Date Parsing: Could not parse date '{date_str}' with any format")
        return None
        
    except Exception as e:
        logger.error(f"🎯 Date Parsing: Error parsing date {date_str}: {e}")
        print(f"Error parsing date {date_str}: {e}")
        return None


def parse_currency(currency_str: str) -> float:
    """
    Parse currency string to float value, handling parentheses and minus signs.
    """
    try:
        if not currency_str:
            return 0.0
        
        # Remove currency symbols and commas
        clean_str = currency_str.replace('$', '').replace(',', '').strip()
        
        # Handle negative values in parentheses
        is_negative_parentheses = clean_str.startswith('(') and clean_str.endswith(')')
        if is_negative_parentheses:
            clean_str = clean_str.replace('(', '').replace(')', '')
        
        # Handle negative values with minus sign
        is_negative_minus = clean_str.startswith('-')
        if is_negative_minus:
            clean_str = clean_str[1:]  # Remove the minus sign
        
        # Remove any remaining non-numeric characters except dots
        clean_str = re.sub(r'[^\d.]', '', clean_str)
        
        if not clean_str:
            return 0.0
        
        amount = float(clean_str)
        
        # Apply negative sign if value was in parentheses or had minus sign
        if is_negative_parentheses or is_negative_minus:
            return -amount
        else:
            return amount
        
    except Exception as e:
        logger.error(f"🎯 Currency Parsing: Error parsing currency {currency_str}: {e}")
        print(f"Error parsing currency {currency_str}: {e}")
        return 0.0


async def create_or_update_commission_record(
    db: AsyncSession,
    carrier_id: str,
    client_name: str,
    invoice_total: float,
    commission_earned: float,
    statement_date: datetime,
    statement_month: int,
    statement_year: int,
    user_id: UUID = None
):
    """
    Create or update commission record with monthly breakdown.
    Includes user_id for proper data isolation in multi-user environments.
    """
    try:
        logger.info(f"🎯 Commission Record: Creating/updating record for {carrier_id} - {client_name} - {statement_date} - user: {user_id}")
        
        # Check if record exists for this carrier, client, statement date, AND user_id
        # CRITICAL: Must pass user_id to ensure we only find THIS user's record
        existing_record = await crud.get_commission_record(
            db, 
            carrier_id=carrier_id,
            client_name=client_name,
            statement_date=statement_date,
            user_id=user_id  # CRITICAL: Filter by user_id for proper data isolation
        )
        
        if existing_record:
            logger.info(f"🎯 Commission Record: Updating existing record ID {existing_record.id}")
            # Update existing record
            await crud.update_commission_record(
                db,
                record_id=existing_record.id,
                invoice_total=invoice_total,
                commission_earned=commission_earned,
                statement_month=statement_month,
                statement_year=statement_year
            )
            logger.info(f"🎯 Commission Record: Successfully updated existing record")
        else:
            logger.info(f"🎯 Commission Record: Creating new record with user_id: {user_id}")
            # Create new record
            commission_record = schemas.EarnedCommissionCreate(
                carrier_id=carrier_id,
                client_name=client_name,
                invoice_total=invoice_total,
                commission_earned=commission_earned,
                statement_date=statement_date,
                statement_month=statement_month,
                statement_year=statement_year,
                statement_count=1,
                user_id=user_id  # CRITICAL: Set user_id for proper data isolation
            )
            
            # Set the appropriate month column
            month_columns = {
                1: 'jan_commission', 2: 'feb_commission', 3: 'mar_commission',
                4: 'apr_commission', 5: 'may_commission', 6: 'jun_commission',
                7: 'jul_commission', 8: 'aug_commission', 9: 'sep_commission',
                10: 'oct_commission', 11: 'nov_commission', 12: 'dec_commission'
            }
            
            if statement_month in month_columns:
                setattr(commission_record, month_columns[statement_month], commission_earned)
                logger.info(f"🎯 Commission Record: Set {month_columns[statement_month]} = {commission_earned}")
            
            await crud.create_commission_record(db, commission_record)
            logger.info(f"🎯 Commission Record: Successfully created new record")
        
    except Exception as e:
        logger.error(f"🎯 Commission Record: Error creating/updating commission record: {e}")
        print(f"Error creating/updating commission record: {e}")
        raise
