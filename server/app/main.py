from app.services.docling.utils.compatibility import apply_compatibility_fixes
apply_compatibility_fixes()

import time
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import documents, ground_truth, evaluation, eval_websocket
from sqlalchemy import text

from app.db.models import Base
from app.db.database import engine

logger = logging.getLogger(__name__)

app = FastAPI(title="Thesis Table Extraction Evaluator")

_PG_ADD_IS_DRAFT = """
DO $$
BEGIN
  ALTER TABLE extraction_results ADD COLUMN is_draft BOOLEAN NOT NULL DEFAULT false;
EXCEPTION
  WHEN duplicate_column THEN NULL;
END $$;
"""


@app.on_event("startup")
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text(_PG_ADD_IS_DRAFT))
    logger.info("Database tables verified/created")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "thesis-table-extraction-evaluator",
        "timestamp": time.time(),
    }


app.include_router(documents.router)
app.include_router(ground_truth.router)
app.include_router(evaluation.router)
app.include_router(eval_websocket.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
