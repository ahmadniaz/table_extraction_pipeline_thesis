import os
import json
import logging
import hashlib
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import SummaryRowPattern, Company
from app.config import get_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/summary-rows", tags=["summary-rows"])

# Enhanced summary row detection patterns
SUMMARY_ROW_PATTERNS = [
    # Total for Group patterns
    r'^Total for Group:?\s*[A-Za-z\s]+$',
    r'^Total\s+for\s+Group:?\s*[A-Za-z\s]+$',
    r'^Group\s+Total:?\s*[A-Za-z\s]+$',
    
    # General total patterns
    r'^Total:?\s*[A-Za-z\s]*$',
    r'^Subtotal:?\s*[A-Za-z\s]*$',
    r'^Grand Total:?\s*[A-Za-z\s]*$',
    r'^Summary:?\s*[A-Za-z\s]*$',
    
    # Company/group specific patterns
    r'^[A-Za-z\s]+\s+Total$',
    r'^Total\s+[A-Za-z\s]+$',
    
    # Row patterns that start with summary indicators
    r'^(Total|Subtotal|Summary|Group|Grand)\s+',
    r'^.*\s+(Total|Subtotal|Summary)$',
    
    # Patterns with numbers and totals
    r'^.*\s+\d+\s+.*\s+\$\d+\.?\d*$',  # Pattern like "FALCON EXPRESS LOGISTI 29 $1,270.91"
]

# Keywords that indicate summary rows
SUMMARY_KEYWORDS = [
    'total', 'subtotal', 'summary', 'grand', 'group', 'sum', 'count', 'amount',
    'balance', 'net', 'final', 'overall', 'combined', 'aggregate'
]


class TableData(BaseModel):
    header: List[str]
    rows: List[List[str]]


class LearnPatternRequest(BaseModel):
    company_id: str
    table_data: TableData
    summary_row_indices: List[int]


class DetectSummaryRowsRequest(BaseModel):
    company_id: str
    table_data: TableData


class SummaryRowPatternResponse(BaseModel):
    id: str
    pattern_name: str
    confidence_score: int
    usage_count: int
    created_at: str
    updated_at: str


def generate_table_signature(header: List[str], rows: List[List[str]]) -> str:
    """Generate a unique signature for the table structure."""
    # Create a signature based on header count and structure
    header_str = "|".join(header)
    row_count = len(rows)
    avg_cols = sum(len(row) for row in rows) / max(len(rows), 1)
    
    signature_data = f"{len(header)}|{row_count}|{avg_cols:.2f}|{header_str}"
    return hashlib.md5(signature_data.encode()).hexdigest()


def analyze_column_patterns(header: List[str], rows: List[List[str]], summary_indices: List[int]) -> Dict[str, Any]:
    """Analyze patterns in columns to identify summary row characteristics."""
    column_patterns = {}
    
    for col_idx, col_name in enumerate(header):
        # Get all values for this column
        all_values = [row[col_idx] if col_idx < len(row) else "" for row in rows]
        summary_values = [rows[idx][col_idx] if col_idx < len(rows[idx]) else "" for idx in summary_indices if idx < len(rows)]
        
        # Analyze patterns
        patterns = {
            "keywords": [],
            "regex_patterns": [],
            "data_type": "string",
            "summary_characteristics": {}
        }
        
        # Check for common keywords in summary rows
        summary_keywords = set()
        for value in summary_values:
            if value:
                # Extract potential keywords
                words = re.findall(r'\b[A-Za-z]+\b', value)
                summary_keywords.update(words)
        
        # Find keywords that appear more in summary rows than regular rows
        regular_values = [v for i, v in enumerate(all_values) if i not in summary_indices]
        regular_keywords = set()
        for value in regular_values:
            if value:
                words = re.findall(r'\b[A-Za-z]+\b', value)
                regular_keywords.update(words)
        
        # Keywords that are more common in summary rows
        summary_specific_keywords = summary_keywords - regular_keywords
        patterns["keywords"] = list(summary_specific_keywords)[:10]  # Limit to top 10
        
        # Check for numeric patterns
        numeric_count = sum(1 for v in summary_values if re.match(r'^\d+(\.\d+)?$', str(v).replace(',', '')))
        if numeric_count > len(summary_values) * 0.5:
            patterns["data_type"] = "numeric"
        
        # Check for currency patterns
        currency_count = sum(1 for v in summary_values if re.match(r'^\$?\d+(,\d{3})*(\.\d{2})?$', str(v)))
        if currency_count > len(summary_values) * 0.3:
            patterns["data_type"] = "currency"
        
        # Check for date patterns
        date_count = sum(1 for v in summary_values if re.match(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', str(v)))
        if date_count > len(summary_values) * 0.3:
            patterns["data_type"] = "date"
        
        # Analyze summary row characteristics
        patterns["summary_characteristics"] = {
            "avg_length": sum(len(str(v)) for v in summary_values) / max(len(summary_values), 1),
            "empty_ratio": sum(1 for v in summary_values if not v.strip()) / max(len(summary_values), 1),
            "numeric_ratio": numeric_count / max(len(summary_values), 1),
            "contains_totals": any("total" in str(v).lower() for v in summary_values),
            "contains_summary": any("summary" in str(v).lower() for v in summary_values),
            "contains_subtotal": any("subtotal" in str(v).lower() for v in summary_values)
        }
        
        column_patterns[col_name] = patterns
    
    return column_patterns


def analyze_row_characteristics(rows: List[List[str]], summary_indices: List[int]) -> Dict[str, Any]:
    """Analyze characteristics that identify summary rows."""
    summary_rows = [rows[idx] for idx in summary_indices if idx < len(rows)]
    regular_rows = [rows[idx] for idx in range(len(rows)) if idx not in summary_indices]
    
    characteristics = {
        "position_patterns": {},
        "content_patterns": {},
        "structural_patterns": {}
    }
    
    # Position patterns
    if summary_indices:
        positions = [idx / len(rows) for idx in summary_indices]
        characteristics["position_patterns"] = {
            "avg_position": sum(positions) / len(positions),
            "end_of_section": any(pos > 0.8 for pos in positions),
            "start_of_section": any(pos < 0.2 for pos in positions)
        }
    
    # Content patterns
    if summary_rows and regular_rows:
        # Compare content characteristics
        summary_avg_length = sum(len(" ".join(row)) for row in summary_rows) / len(summary_rows)
        regular_avg_length = sum(len(" ".join(row)) for row in regular_rows) / len(regular_rows)
        
        characteristics["content_patterns"] = {
            "avg_length_ratio": summary_avg_length / max(regular_avg_length, 1),
            "contains_totals": any("total" in " ".join(row).lower() for row in summary_rows),
            "contains_summary": any("summary" in " ".join(row).lower() for row in summary_rows),
            "contains_subtotal": any("subtotal" in " ".join(row).lower() for row in summary_rows),
            "numeric_density": sum(1 for row in summary_rows for cell in row if re.match(r'^\d+(\.\d+)?$', str(cell).replace(',', ''))) / max(sum(len(row) for row in summary_rows), 1)
        }
    
    # Structural patterns
    characteristics["structural_patterns"] = {
        "empty_cell_ratio": sum(1 for row in summary_rows for cell in row if not cell.strip()) / max(sum(len(row) for row in summary_rows), 1),
        "repeated_values": any(len(set(row)) < len(row) * 0.5 for row in summary_rows),
        "all_caps_ratio": sum(1 for row in summary_rows for cell in row if cell.isupper()) / max(sum(len(row) for row in summary_rows), 1)
    }
    
    return characteristics


@router.post("/learn-pattern/")
async def learn_pattern(request: LearnPatternRequest, db: AsyncSession = Depends(get_db)):
    """
    Learn a pattern from marked summary rows for a specific company.
    """
    try:
        logger.info(f"Learning summary row pattern for company: {request.company_id}")
        
        # Generate table signature
        table_signature = generate_table_signature(
            request.table_data.header, 
            request.table_data.rows
        )
        
        # Analyze patterns
        column_patterns = analyze_column_patterns(
            request.table_data.header,
            request.table_data.rows,
            request.summary_row_indices
        )
        
        row_characteristics = analyze_row_characteristics(
            request.table_data.rows,
            request.summary_row_indices
        )
        
        # Get sample rows
        sample_rows = [request.table_data.rows[idx] for idx in request.summary_row_indices if idx < len(request.table_data.rows)]
        
        # Create pattern name
        pattern_name = f"Summary Pattern {datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Check if pattern already exists
        stmt = select(SummaryRowPattern).where(
            SummaryRowPattern.company_id == request.company_id,
            SummaryRowPattern.table_signature == table_signature
        )
        result = await db.execute(stmt)
        existing_pattern = result.scalar_one_or_none()
        
        if existing_pattern:
            # Update existing pattern
            existing_pattern.column_patterns = column_patterns
            existing_pattern.row_characteristics = row_characteristics
            existing_pattern.sample_rows = sample_rows
            existing_pattern.usage_count += 1
            existing_pattern.last_used = datetime.now()
            existing_pattern.updated_at = datetime.now()
            
            # Increase confidence if pattern is used multiple times
            if existing_pattern.usage_count > 1:
                existing_pattern.confidence_score = min(100, existing_pattern.confidence_score + 5)
            
            await db.commit()
            
            logger.info(f"Updated existing summary row pattern: {existing_pattern.id}")
            
            return JSONResponse({
                "success": True,
                "message": "Updated existing summary row pattern",
                "pattern_id": str(existing_pattern.id),
                "pattern_name": existing_pattern.pattern_name,
                "confidence_score": existing_pattern.confidence_score,
                "usage_count": existing_pattern.usage_count,
                "summary_rows_count": len(request.summary_row_indices)
            })
        else:
            # Create new pattern
            new_pattern = SummaryRowPattern(
                company_id=request.company_id,
                pattern_name=pattern_name,
                table_signature=table_signature,
                column_patterns=column_patterns,
                row_characteristics=row_characteristics,
                sample_rows=sample_rows,
                confidence_score=80,
                usage_count=1
            )
            
            db.add(new_pattern)
            await db.commit()
            await db.refresh(new_pattern)
            
            logger.info(f"Created new summary row pattern: {new_pattern.id}")
            
            return JSONResponse({
                "success": True,
                "message": "Learned new summary row pattern",
                "pattern_id": str(new_pattern.id),
                "pattern_name": new_pattern.pattern_name,
                "confidence_score": new_pattern.confidence_score,
                "usage_count": new_pattern.usage_count,
                "summary_rows_count": len(request.summary_row_indices)
            })
        
    except Exception as e:
        logger.error(f"Error learning summary row pattern: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to learn pattern: {str(e)}")


@router.post("/detect-summary-rows/")
async def detect_summary_rows(request: DetectSummaryRowsRequest, db: AsyncSession = Depends(get_db)):
    """
    Detect summary rows in a table using learned patterns for a specific company.
    """
    try:
        logger.info(f"Detecting summary rows for company: {request.company_id}")
        
        # Generate table signature
        table_signature = generate_table_signature(
            request.table_data.header, 
            request.table_data.rows
        )
        
        # Find matching patterns
        stmt = select(SummaryRowPattern).where(
            SummaryRowPattern.company_id == request.company_id
        )
        result = await db.execute(stmt)
        patterns = result.scalars().all()
        
        detected_rows = []
        confidence_scores = {}
        
        for pattern in patterns:
            # Check if table signature matches (exact match or similar)
            if pattern.table_signature == table_signature:
                # Exact match - find rows that match the sample rows
                for sample_row in pattern.sample_rows:
                    for row_idx, row in enumerate(request.table_data.rows):
                        if row == sample_row:
                            detected_rows.append(row_idx)
                            break
                confidence_scores[pattern.id] = pattern.confidence_score
            else:
                # Try to apply pattern to current table
                matches = apply_pattern_to_table(
                    pattern,
                    request.table_data.header,
                    request.table_data.rows
                )
                
                if matches:
                    detected_rows.extend(matches)
                    confidence_scores[pattern.id] = pattern.confidence_score * 0.8  # Reduce confidence for non-exact matches
        
        # Remove duplicates and sort by row index
        unique_detected_rows = list(set(detected_rows))
        unique_detected_rows.sort()
        
        # Filter by confidence threshold
        min_confidence = 60
        final_detected_rows = [
            row_idx for row_idx in unique_detected_rows
            if any(score >= min_confidence for score in confidence_scores.values())
        ]
        
        # Use enhanced detection as a fallback and to catch additional patterns
        enhanced_detected_rows = enhanced_detect_summary_rows(
            request.table_data.header, 
            request.table_data.rows
        )
        
        # Combine both detection methods
        all_detected_rows = list(set(final_detected_rows + enhanced_detected_rows))
        all_detected_rows.sort()
        
        logger.info(f"Detected {len(all_detected_rows)} summary rows (pattern-based: {len(final_detected_rows)}, enhanced: {len(enhanced_detected_rows)})")
        
        return JSONResponse({
            "success": True,
            "detected_summary_rows": all_detected_rows,
            "patterns_used": len(patterns),
            "confidence_scores": confidence_scores,
            "total_rows_analyzed": len(request.table_data.rows),
            "pattern_based_detected": final_detected_rows,
            "enhanced_detected": enhanced_detected_rows
        })
        
    except Exception as e:
        logger.error(f"Error detecting summary rows: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to detect summary rows: {str(e)}")


def apply_pattern_to_table(pattern: SummaryRowPattern, header: List[str], rows: List[List[str]]) -> List[int]:
    """
    Apply a learned pattern to detect summary rows in a table.
    """
    detected_rows = []
    
    # Check column patterns
    for col_idx, col_name in enumerate(header):
        if col_name in pattern.column_patterns:
            col_pattern = pattern.column_patterns[col_name]
            
            # Check for keywords
            for row_idx, row in enumerate(rows):
                if col_idx < len(row):
                    cell_value = str(row[col_idx]).lower()
                    
                    # Check for summary keywords
                    if any(keyword.lower() in cell_value for keyword in col_pattern.get("keywords", [])):
                        detected_rows.append(row_idx)
                    
                    # Check for summary characteristics
                    summary_chars = col_pattern.get("summary_characteristics", {})
                    if summary_chars.get("contains_totals") and "total" in cell_value:
                        detected_rows.append(row_idx)
                    if summary_chars.get("contains_summary") and "summary" in cell_value:
                        detected_rows.append(row_idx)
                    if summary_chars.get("contains_subtotal") and "subtotal" in cell_value:
                        detected_rows.append(row_idx)
    
    # Check row characteristics
    row_chars = pattern.row_characteristics
    if row_chars:
        for row_idx, row in enumerate(rows):
            row_text = " ".join(row).lower()
            
            # Check for summary content patterns
            content_patterns = row_chars.get("content_patterns", {})
            if content_patterns.get("contains_totals") and "total" in row_text:
                detected_rows.append(row_idx)
            if content_patterns.get("contains_summary") and "summary" in row_text:
                detected_rows.append(row_idx)
            if content_patterns.get("contains_subtotal") and "subtotal" in row_text:
                detected_rows.append(row_idx)
    
    return list(set(detected_rows))  # Remove duplicates


def enhanced_detect_summary_rows(header: List[str], rows: List[List[str]]) -> List[int]:
    """
    Enhanced summary row detection using multiple strategies.
    """
    detected_rows = []
    
    for row_idx, row in enumerate(rows):
        if not row:  # Skip empty rows
            continue
            
        # Convert row to string for pattern matching
        row_text = " ".join(str(cell) for cell in row).strip()
        row_lower = row_text.lower()
        
        # Strategy 1: Check against predefined patterns
        for pattern in SUMMARY_ROW_PATTERNS:
            if re.search(pattern, row_text, re.IGNORECASE):
                detected_rows.append(row_idx)
                break
        
        # Strategy 2: Check for summary keywords in first few columns
        if len(row) > 0:
            first_cell = str(row[0]).lower()
            if any(keyword in first_cell for keyword in SUMMARY_KEYWORDS):
                detected_rows.append(row_idx)
                continue
        
        # Strategy 3: Check for "Total for Group" pattern specifically
        if "total for group" in row_lower:
            detected_rows.append(row_idx)
            continue
        
        # Strategy 4: Check for rows that have summary characteristics
        # - Start with "Total" or similar words
        # - Contain numeric totals in later columns
        # - Have empty cells in certain positions (typical of summary rows)
        
        if len(row) >= 3:
            # Check if first column contains summary indicators
            first_col = str(row[0]).lower()
            if any(keyword in first_col for keyword in ['total', 'subtotal', 'summary', 'group']):
                # Check if later columns contain numeric values (totals)
                has_numeric_totals = False
                for i in range(1, min(5, len(row))):  # Check first 5 columns
                    cell_value = str(row[i]).strip()
                    if re.match(r'^\$?[\d,]+\.?\d*$', cell_value) or re.match(r'^\d+$', cell_value):
                        has_numeric_totals = True
                        break
                
                if has_numeric_totals:
                    detected_rows.append(row_idx)
                    continue
        
        # Strategy 5: Check for rows that have a specific structure
        # - First column: "Total for Group: [NAME]"
        # - Later columns: numeric values
        # - Some columns empty (typical pattern)
        if len(row) >= 4:
            first_col = str(row[0]).strip()
            if first_col.startswith("Total for Group:"):
                # Check if there are numeric values in columns 3-5
                numeric_count = 0
                for i in range(2, min(5, len(row))):
                    cell_value = str(row[i]).strip()
                    if re.match(r'^\$?[\d,]+\.?\d*$', cell_value) or re.match(r'^\d+$', cell_value):
                        numeric_count += 1
                
                if numeric_count >= 1:  # At least one numeric value
                    detected_rows.append(row_idx)
                    continue
    
    return list(set(detected_rows))  # Remove duplicates


@router.get("/patterns/{company_id}")
async def get_summary_row_patterns(company_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get all summary row patterns for a specific company.
    """
    try:
        logger.info(f"Getting summary row patterns for company: {company_id}")
        
        # Get patterns
        stmt = select(SummaryRowPattern).where(
            SummaryRowPattern.company_id == company_id
        ).order_by(SummaryRowPattern.last_used.desc())
        result = await db.execute(stmt)
        patterns = result.scalars().all()
        
        pattern_data = []
        for pattern in patterns:
            pattern_data.append({
                "id": str(pattern.id),
                "pattern_name": pattern.pattern_name,
                "confidence_score": pattern.confidence_score,
                "usage_count": pattern.usage_count,
                "created_at": pattern.created_at.isoformat(),
                "updated_at": pattern.updated_at.isoformat(),
                "last_used": pattern.last_used.isoformat()
            })
        
        logger.info(f"Retrieved {len(pattern_data)} patterns")
        
        return JSONResponse({
            "success": True,
            "patterns": pattern_data,
            "total_patterns": len(pattern_data)
        })
        
    except Exception as e:
        logger.error(f"Error getting summary row patterns: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get patterns: {str(e)}")


@router.delete("/patterns/{pattern_id}")
async def delete_summary_row_pattern(pattern_id: str, db: AsyncSession = Depends(get_db)):
    """
    Delete a specific summary row pattern.
    """
    try:
        logger.info(f"Deleting summary row pattern: {pattern_id}")
        
        # Find and delete pattern
        stmt = select(SummaryRowPattern).where(SummaryRowPattern.id == pattern_id)
        result = await db.execute(stmt)
        pattern = result.scalar_one_or_none()
        
        if not pattern:
            raise HTTPException(status_code=404, detail="Pattern not found")
        
        await db.delete(pattern)
        await db.commit()
        
        logger.info(f"Successfully deleted pattern: {pattern_id}")
        
        return JSONResponse({
            "success": True,
            "message": "Pattern deleted successfully",
            "pattern_id": pattern_id
        })
        
    except Exception as e:
        logger.error(f"Error deleting summary row pattern: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete pattern: {str(e)}")


@router.get("/health")
async def health_check():
    """
    Health check endpoint for summary rows API.
    """
    return JSONResponse({
        "status": "healthy",
        "service": "summary-rows",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    })
