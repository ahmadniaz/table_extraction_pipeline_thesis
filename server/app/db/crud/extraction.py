from ..models import Extraction
from ..schemas import ExtractionCreate

async def create_extraction(db, extraction: ExtractionCreate):
    """
    Create a new extraction record.
    """
    # Convert quality_score from float (0-1) to integer (0-100)
    quality_score_int = int(extraction.quality_score * 100)
    
    db_extraction = Extraction(
        company_id=extraction.company_id,
        filename=extraction.filename,
        s3_url=extraction.s3_url,
        total_tables=extraction.total_tables,
        valid_tables=extraction.valid_tables,
        quality_score=quality_score_int,
        confidence=extraction.confidence,
        extraction_metadata=extraction.extraction_metadata,
        quality_metadata=extraction.quality_metadata
    )
    db.add(db_extraction)
    await db.commit()
    await db.refresh(db_extraction)
    return db_extraction
