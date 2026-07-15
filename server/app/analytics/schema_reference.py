"""
Step 1 — Data inspection reference for the Results Analytics page.

Source of truth: PostgreSQL (see app.db.database / models). Live counts were
sampled on an inspection run (extractions and scores are not static).

Core tables for evaluation analytics:
- documents: one row per commission-statement PDF in the study corpus
- ground_truth_tables: human tables per document (confirmed GT drives scoring)
- extraction_results: one row per (document, tool, table_index) extraction
- evaluation_scores: one row per scored extraction_result_id (1:1 when present)

Other public tables (carrier_format_learning, companies, etc.) are outside the
metrics path used by /api/evaluation and /api/results.

Field map (thesis / analytics):
- tool_name, document identity, tier: ExtractionResult.tool_name, Document.id,
  Document.filename, Document.complexity_tier ('low'|'medium'|'high'|'unconfirmed', lowercase in DB)
- generation: not stored; derive from tool (see TOOL_ID_TO_GENERATION)
- metrics: evaluation_scores.precision, recall, f1_score, teds_score, grits_top, grits_con, grits_loc
- operational: ExtractionResult.processing_time_ms, cost_usd (nullable; free tools often NULL/0);
  cost per page: not a column; compute as (sum of cost_usd for the tool on that doc) / Document.page_count
- failure / quality of run: ExtractionResult.failure_reason, is_transient_failure, error_message, is_draft
- scan vs digital: Document.is_digital (nullable bool)
- page_count: Document.page_count (nullable int)

API caveat — GET /api/results/ only returns rows with an inner join to evaluation_scores, so
extractions that were never scored (e.g. extra table_index with no matching GT) do not appear.
Per-document views should use /api/results/export/per-document-csv or a dedicated query if those
rows must appear as “missing score” (see extractions without scores in DB).

API caveat — serializing scores uses `float(x) if x else None`; Numeric 0.0 is falsy in Python,
so true zeros may appear as null in JSON. The analytics layer should use `x is not None` when
adding a fixed export path or accept scores from a raw query.

Carrier: not stored on documents. Filters must use filename heuristics, a sidecar mapping, or
a future migration — do not assume a DB column exists.
"""

from __future__ import annotations

from typing import Dict, Literal

ToolGeneration = Literal["rule", "cv", "llm"]

# Canonical tool ids (server/app/api/evaluation.py ALL_TOOLS)
ALL_TOOL_IDS: tuple[str, ...] = (
    "pymupdf",
    "docling",
    "aws_textract",
    "google_docai",
    "gpt5",
    "claude_sonnet",
    "mistral",
)

# Maps tool id -> thesis “generation” bucket for UI palette / filters
TOOL_ID_TO_GENERATION: Dict[str, ToolGeneration] = {
    "pymupdf": "rule",
    "aws_textract": "cv",
    "google_docai": "cv",
    "docling": "cv",
    "gpt5": "llm",
    "claude_sonnet": "llm",
    "mistral": "llm",
}

# Human-readable labels (align with client results page where applicable)
TOOL_ID_TO_LABEL: Dict[str, str] = {
    "pymupdf": "PyMuPDF",
    "docling": "Docling",
    "google_docai": "Google DocAI",
    "aws_textract": "AWS Textract",
    "gpt5": "GPT-5 Vision",
    "claude_sonnet": "Claude Sonnet",
    "mistral": "Mistral AI",
}

# Column names on evaluation_scores / API JSON (snake_case)
SCORE_METRIC_KEYS: tuple[str, ...] = (
    "precision",
    "recall",
    "f1_score",
    "teds_score",
    "grits_top",
    "grits_con",
    "grits_loc",
)
