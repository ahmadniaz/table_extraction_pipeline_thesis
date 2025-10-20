from ..models import SummaryRowPattern
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import List, Optional

async def save_summary_row_pattern(db: AsyncSession, pattern_data: dict) -> SummaryRowPattern:
    """
    Save a new summary row pattern or update existing one.
    """
    now = datetime.utcnow()
    
    # Check if pattern already exists
    existing_pattern = await db.execute(
        select(SummaryRowPattern).where(
            SummaryRowPattern.company_id == pattern_data['company_id'],
            SummaryRowPattern.table_signature == pattern_data['table_signature']
        )
    )
    existing_pattern = existing_pattern.scalar_one_or_none()
    
    if existing_pattern:
        # Update existing pattern
        existing_pattern.column_patterns = pattern_data['column_patterns']
        existing_pattern.row_characteristics = pattern_data['row_characteristics']
        existing_pattern.sample_rows = pattern_data['sample_rows']
        existing_pattern.usage_count += 1
        existing_pattern.last_used = now
        existing_pattern.updated_at = now
        await db.commit()
        await db.refresh(existing_pattern)
        return existing_pattern
    else:
        # Create new pattern
        new_pattern = SummaryRowPattern(
            company_id=pattern_data['company_id'],
            pattern_name=pattern_data['pattern_name'],
            table_signature=pattern_data['table_signature'],
            column_patterns=pattern_data['column_patterns'],
            row_characteristics=pattern_data['row_characteristics'],
            sample_rows=pattern_data['sample_rows'],
            confidence_score=pattern_data.get('confidence_score', 80),
            usage_count=1,
            last_used=now,
            created_at=now,
            updated_at=now
        )
        db.add(new_pattern)
        await db.commit()
        await db.refresh(new_pattern)
        return new_pattern

async def get_summary_row_patterns_for_company(db: AsyncSession, company_id: str) -> List[SummaryRowPattern]:
    """
    Get all summary row patterns for a company.
    """
    result = await db.execute(
        select(SummaryRowPattern)
        .where(SummaryRowPattern.company_id == company_id)
        .order_by(SummaryRowPattern.last_used.desc())
    )
    return result.scalars().all()

async def get_summary_row_pattern_by_signature(db: AsyncSession, company_id: str, table_signature: str) -> Optional[SummaryRowPattern]:
    """
    Get a specific summary row pattern by table signature.
    """
    result = await db.execute(
        select(SummaryRowPattern).where(
            SummaryRowPattern.company_id == company_id,
            SummaryRowPattern.table_signature == table_signature
        )
    )
    return result.scalar_one_or_none()

async def delete_summary_row_pattern(db: AsyncSession, pattern_id: str, company_id: str) -> bool:
    """
    Delete a summary row pattern.
    """
    pattern = await db.execute(
        select(SummaryRowPattern).where(
            SummaryRowPattern.id == pattern_id,
            SummaryRowPattern.company_id == company_id
        )
    )
    pattern = pattern.scalar_one_or_none()
    
    if pattern:
        await db.delete(pattern)
        await db.commit()
        return True
    
    return False
