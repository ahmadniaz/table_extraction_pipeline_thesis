from ..models import CarrierFormatLearning
from ..schemas import CarrierFormatLearningCreate, CarrierFormatLearningUpdate
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from uuid import UUID
from typing import List, Optional
from difflib import SequenceMatcher
import re


async def save_carrier_format_learning(db: AsyncSession, format_learning: CarrierFormatLearningCreate):
    """
    Save or update carrier format learning data.
    """
    now = datetime.utcnow()
    
    # Check if format already exists for this company
    existing_format = await get_carrier_format_by_signature(db, format_learning.company_id, format_learning.format_signature)
    
    if existing_format:
        # Update existing format
        existing_format.usage_count += 1
        existing_format.last_used = now
        existing_format.updated_at = now
        
        # Update fields if provided
        if format_learning.header_patterns is not None:
            existing_format.header_patterns = format_learning.header_patterns
        if format_learning.column_types is not None:
            existing_format.column_types = format_learning.column_types
        if format_learning.column_patterns is not None:
            existing_format.column_patterns = format_learning.column_patterns
        if format_learning.sample_values is not None:
            existing_format.sample_values = format_learning.sample_values
        if format_learning.table_structure is not None:
            existing_format.table_structure = format_learning.table_structure
        if format_learning.data_quality_metrics is not None:
            existing_format.data_quality_metrics = format_learning.data_quality_metrics
        if format_learning.field_mapping is not None:
            existing_format.field_mapping = format_learning.field_mapping
        if format_learning.table_editor_settings is not None:
            existing_format.table_editor_settings = format_learning.table_editor_settings
        
        await db.commit()
        await db.refresh(existing_format)
        return existing_format
    else:
        # Create new format
        new_format = CarrierFormatLearning(
            company_id=format_learning.company_id,
            format_signature=format_learning.format_signature,
            headers=format_learning.headers,
            header_patterns=format_learning.header_patterns,
            column_types=format_learning.column_types,
            column_patterns=format_learning.column_patterns,
            sample_values=format_learning.sample_values,
            table_structure=format_learning.table_structure,
            data_quality_metrics=format_learning.data_quality_metrics,
            field_mapping=format_learning.field_mapping,
            table_editor_settings=format_learning.table_editor_settings,
            confidence_score=format_learning.confidence_score,
            usage_count=format_learning.usage_count,
            last_used=now,
            created_at=now,
            updated_at=now
        )
        db.add(new_format)
        await db.commit()
        await db.refresh(new_format)
        return new_format

async def get_carrier_format_by_signature(db: AsyncSession, company_id: UUID, format_signature: str):
    """
    Get carrier format learning by company ID and format signature.
    """
    result = await db.execute(
        select(CarrierFormatLearning)
        .where(CarrierFormatLearning.company_id == company_id)
        .where(CarrierFormatLearning.format_signature == format_signature)
    )
    return result.scalar_one_or_none()

async def get_carrier_formats_for_company(db: AsyncSession, company_id: UUID):
    """
    Get all carrier format learning records for a company.
    """
    result = await db.execute(
        select(CarrierFormatLearning)
        .where(CarrierFormatLearning.company_id == company_id)
        .order_by(CarrierFormatLearning.last_used.desc())
    )
    return result.scalars().all()

async def find_best_matching_format(db: AsyncSession, company_id: UUID, headers: List[str], table_structure: dict):
    """
    Find the best matching format for given headers and structure with improved matching logic.
    """
    print(f"🎯 CRUD: Finding best matching format for company {company_id}")
    print(f"🎯 CRUD: Input headers: {headers}")
    print(f"🎯 CRUD: Input table structure: {table_structure}")
    
    # Get all formats for this company
    formats = await get_carrier_formats_for_company(db, company_id)
    print(f"🎯 CRUD: Found {len(formats)} saved formats for company")
    
    best_match = None
    best_score = 0
    
    for format_record in formats:
        # Calculate similarity score using improved logic
        header_similarity = calculate_header_similarity(headers, format_record.headers)
        structure_similarity = calculate_structure_similarity(table_structure, format_record.table_structure)
        
        # Combined score (weighted average) - header similarity is more important
        total_score = (header_similarity * 0.8) + (structure_similarity * 0.2)
        
        print(f"🎯 CRUD: Comparing with saved format:")
        print(f"🎯 CRUD:   Saved headers: {format_record.headers}")
        print(f"🎯 CRUD:   Header similarity: {header_similarity}")
        print(f"🎯 CRUD:   Structure similarity: {structure_similarity}")
        print(f"🎯 CRUD:   Total score: {total_score}")
        
        # Lower threshold for better matching - 0.5 instead of 0.6
        if total_score > best_score and total_score > 0.5:  # Even more flexible threshold
            best_score = total_score
            best_match = format_record
            print(f"🎯 CRUD:   -> New best match with score {total_score}")
    
    return best_match, best_score

def calculate_header_similarity(headers1: List[str], headers2: List[str]) -> float:
    """
    Calculate similarity between two header lists using improved matching.
    """
    if not headers1 or not headers2:
        return 0.0
    
    # Normalize headers
    headers1_normalized = [_normalize_header(h) for h in headers1 if h]
    headers2_normalized = [_normalize_header(h) for h in headers2 if h]
    
    if not headers1_normalized or not headers2_normalized:
        return 0.0
    
    # Calculate similarity using multiple methods
    exact_matches = 0
    fuzzy_matches = 0
    total_headers = max(len(headers1_normalized), len(headers2_normalized))
    
    # Find exact matches first
    used_headers2 = set()
    for h1 in headers1_normalized:
        for i, h2 in enumerate(headers2_normalized):
            if i not in used_headers2 and h1 == h2:
                exact_matches += 1
                used_headers2.add(i)
                break
    
    # Find fuzzy matches for remaining headers
    remaining_headers1 = [h for i, h in enumerate(headers1_normalized) if i not in used_headers2]
    remaining_headers2 = [h for i, h in enumerate(headers2_normalized) if i not in used_headers2]
    
    for h1 in remaining_headers1:
        best_match_score = 0
        best_match_idx = -1
        
        for i, h2 in enumerate(remaining_headers2):
            if i not in used_headers2:
                similarity = SequenceMatcher(None, h1, h2).ratio()
                if similarity > best_match_score and similarity > 0.6:  # Lower threshold to 60% for better matching
                    best_match_score = similarity
                    best_match_idx = i
        
        if best_match_idx >= 0:
            fuzzy_matches += 1
            used_headers2.add(best_match_idx)
    
    # Calculate weighted score
    exact_score = exact_matches / total_headers if total_headers > 0 else 0
    fuzzy_score = fuzzy_matches / total_headers if total_headers > 0 else 0
    
    # Weight exact matches higher than fuzzy matches
    total_score = (exact_score * 0.8) + (fuzzy_score * 0.2)
    
    return total_score

def _normalize_header(header: str) -> str:
    """
    Normalize a header string for better matching.
    """
    if not header:
        return ""
    
    # Convert to lowercase and remove extra spaces
    normalized = header.lower().strip()
    
    # Handle semantic synonyms before removing prefixes/suffixes
    # Replace common synonyms that mean the same thing
    synonyms = {
        'group': 'company',
        'company': 'company',
        'client': 'company',
        'organization': 'company',
        'account': 'account',
        'policy': 'policy',
        'plan': 'policy',
        'premium': 'premium',
        'commission': 'commission',
        'earned': 'commission',
        'payment': 'payment',
        'paid': 'payment',
        'amount': 'amount',
        'total': 'total',
        'invoice': 'invoice',
        'billing': 'billing',
        'period': 'period',
        'date': 'date',
        'number': 'number',
        'no': 'number',
        'name': 'name',
        'rate': 'rate',
        'method': 'method',
        'calculation': 'calculation',
        'census': 'census',
        'subscribers': 'subscribers',
        'stoploss': 'stoploss',
        'adjustment': 'adjustment',
        'adj': 'adjustment'
    }
    
    # Apply synonyms
    for synonym, replacement in synonyms.items():
        normalized = re.sub(r'\b' + re.escape(synonym) + r'\b', replacement, normalized)
    
    # Remove punctuation and extra spaces
    normalized = re.sub(r'[^\w\s]', '', normalized)
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    return normalized

def calculate_structure_similarity(structure1: dict, structure2: dict) -> float:
    """
    Calculate similarity between two table structures with more flexible matching.
    """
    if not structure1 or not structure2:
        return 0.0
    
    # Compare key structural elements
    score = 0.0
    comparisons = 0
    
    # Compare column count with more tolerance
    if 'column_count' in structure1 and 'column_count' in structure2:
        col_diff = abs(structure1['column_count'] - structure2['column_count'])
        max_cols = max(structure1['column_count'], structure2['column_count'])
        if max_cols > 0:
            # More tolerant of column count differences
            if col_diff <= 2:  # Allow up to 2 column difference
                score += 1.0
            elif col_diff <= 4:  # Allow up to 4 column difference with partial score
                score += 0.7
            else:
                score += max(0, 1.0 - (col_diff / max_cols))
        comparisons += 1
    
    # Compare row count (if available) with more tolerance
    if 'typical_row_count' in structure1 and 'typical_row_count' in structure2:
        row_diff = abs(structure1['typical_row_count'] - structure2['typical_row_count'])
        max_rows = max(structure1['typical_row_count'], structure2['typical_row_count'])
        if max_rows > 0:
            # More tolerant of row count differences
            if row_diff <= 5:  # Allow up to 5 row difference
                score += 1.0
            elif row_diff <= 10:  # Allow up to 10 row difference with partial score
                score += 0.8
            else:
                score += max(0, 1.0 - (row_diff / max_rows))
        comparisons += 1
    
    # Compare has_header_row
    if 'has_header_row' in structure1 and 'has_header_row' in structure2:
        if structure1['has_header_row'] == structure2['has_header_row']:
            score += 1.0
        else:
            score += 0.5  # Partial score for mismatch
        comparisons += 1
    
    return score / comparisons if comparisons > 0 else 0.0
