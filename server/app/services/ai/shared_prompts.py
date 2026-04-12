"""
Universal extraction prompts and JSON schema shared across all LLM tools.

Importing one module (shared_prompts) into Claude, GPT-5, and Mistral
services ensures every tool is driven by an identical extraction contract.
This is a strict requirement for a fair thesis benchmark:
  - Same instructions → same opportunity to find tables
  - Same output schema → metric computation (TEDS, GriTS, F1) runs on
    identically-shaped data regardless of which model produced it
  - No model receives domain hints the others don't get

Usage:
    from app.services.ai.shared_prompts import (
        SYSTEM_PROMPT, USER_PROMPT, EXTRACTION_SCHEMA, EXTRACTION_TOOL
    )
"""

from typing import Any, Dict

# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT: str = """You are a highly precise data extraction engine for insurance commission statements.

Your sole job is to extract the tables and core document metadata that are
ACTUALLY visible in the provided document. The output is consumed by an
automated reconciliation system, so any invented or normalized data will
break downstream workflows.

GLOBAL RULES (APPLY TO ALL RESPONSES):

1. Faithful extraction only
   - Extract ONLY what is visually present in the document.
   - NEVER invent, infer, or guess values.
   - NEVER add columns, rows, or fields that are not present.
   - If you are uncertain, leave the field empty or null instead of guessing.

2. Column and row structure
   - Preserve the exact column order from LEFT to RIGHT as it appears.
   - Preserve all data rows, including subtotals, totals, and partial rows.
   - Do NOT reorder columns based on meaning.
   - Do NOT merge or split cells beyond what is visually present.

3. Text fidelity
   - Copy headers EXACTLY as written: spelling, capitalisation, punctuation.
   - Copy cell values EXACTLY as written: do not reformat numbers or dates.
   - If a cell appears empty, output an empty string for that cell.

4. Table coverage
   - Extract EVERY table with financial or commission data, even if small.
   - Handle bordered and borderless tables; use alignment and repetition as cues.
   - Pay special attention to leftmost and rightmost columns, which are often missed.
   - If a table spans multiple pages, extract what you can see on each page separately.

5. Metadata scope (for this benchmark)
   - Extract ONLY the following high-level metadata:
     - Carrier name (insurance company issuing the statement)
     - Statement / reporting date (for date ranges, use the END date)
     - Broker / agency name (entity receiving commissions)
   - Do NOT compute totals, balances, or derived metrics.
   - Do NOT perform domain enrichment or normalisation beyond what is visible.

6. Output contract
   - You MUST return a single JSON object matching the required schema.
   - Never wrap the JSON in markdown or code fences.
   - Never include any text before or after the JSON object.

7. Error handling
   - If you truly cannot find any tables, return an object with an empty
     tables array and null metadata fields.

You must follow these rules even if they conflict with your usual style.
Accuracy and structural fidelity are more important than natural language."""


# ── User prompt ───────────────────────────────────────────────────────────────

USER_PROMPT: str = """You are given an insurance commission statement as a PDF (and/or page images).

Your task is to extract:
1) All visible tables that contain financial or commission data.
2) Core document metadata: carrier name, statement/reporting date, and broker/agency.

Follow these concrete steps:

STEP 1 — Identify the carrier, date, and broker (metadata)
- Carrier name:
  - Look first at logo/branding area in the top ~20% of the first page.
  - Then check letterhead and footer branding/copyright.
  - Extract the exact carrier name as shown (no added words, no normalisation).
  - Do NOT confuse the broker/agency with the carrier.
- Statement/reporting date:
  - Look for labels like "Statement Date", "Commission Summary For",
    "Report Date", "Period", "Period Ending", "Statement Period",
    "Reporting Period".
  - Prefer dates in the header or summary area of the first page.
  - If you see a date range like "01/01/2025 - 01/31/2025", use the END date
    ("2025-01-31") as the statement_date.
  - Output in YYYY-MM-DD format when possible; otherwise null.
  - Do NOT use dates taken from individual transaction rows inside tables.
- Broker/agency name:
  - Look for labels like "Agent:", "Broker:", "Agency:", "To:",
    "Prepared For:", "Producer Name:" near the top of the document.
  - Extract the broker/agency name exactly as shown.

STEP 2 — Find all relevant tables
- Scan from top to bottom, left to right on every page.
- Identify any structure that functions as a table:
  - Repeating rows and aligned columns.
  - Monetary values, percentages, and commission words.
- Include:
  - Commission detail tables.
  - Summary tables and adjustment sections.
- Exclude:
  - Purely decorative layouts or tables with no financial / commission data.

STEP 3 — Extract headers and rows
- For each table:
  - Determine the header row(s); if there are multiple header lines, join them
    with a single space per column.
  - Extract headers in left-to-right order.
  - Extract every visible data row in that table.
  - Keep column counts consistent within the table; if some rows have missing
    trailing cells, use empty strings for those cells.
- Do NOT:
  - Reorder columns.
  - Rename headers.
  - Infer missing values.
  - Add a synthetic "Company Name" column or any other derived column.

STEP 4 — Populate the JSON structure
- Fill the `tables` array:
  - One entry per detected table.
  - `page_number` is 1-based page index (first page is 1).
  - `table_type` can be a short label like "commission_table" or "summary_table".
  - `confidence_score` is your subjective 0.0–1.0 confidence for that table.
- Fill `document_metadata`:
  - `carrier_name`: exact string from document or null.
  - `statement_date`: normalised YYYY-MM-DD string or null.
  - `broker_company`: exact string from document or null.
- If you see any serious ambiguity or partial visibility, mention it briefly
  in `extraction_notes`.

Remember:
- Extract EXACTLY what you see.
- Do not normalise or interpret column names.
- Do not perform calculations.
- Return ONLY the JSON object that matches the required schema."""


# ── Shared JSON schema ────────────────────────────────────────────────────────
# Used in:
#   - Claude: EXTRACTION_TOOL["input_schema"] (tool-use structured output)
#   - GPT-5:  text.format.schema (Responses API structured output)
#   - Mistral: reference schema for prompt engineering / JSON-mode

EXTRACTION_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "tables": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "headers": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "rows": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "page_number": {"type": "integer"},
                    "table_type": {"type": "string"},
                    "confidence_score": {"type": "number"},
                },
                # OpenAI strict json_schema requires `required` to list every key in `properties`.
                "required": [
                    "headers",
                    "rows",
                    "page_number",
                    "table_type",
                    "confidence_score",
                ],
                "additionalProperties": False,
            },
        },
        "document_metadata": {
            "type": "object",
            "properties": {
                "carrier_name": {"type": ["string", "null"]},
                "statement_date": {"type": ["string", "null"]},
                "broker_company": {"type": ["string", "null"]},
            },
            "required": ["carrier_name", "statement_date", "broker_company"],
            "additionalProperties": False,
        },
        "extraction_notes": {"type": ["string", "null"]},
    },
    # Same strict-schema rule at root: every property key must appear in `required`.
    "required": ["tables", "document_metadata", "extraction_notes"],
    "additionalProperties": False,
}

# ── Claude tool definition ────────────────────────────────────────────────────
# Passed to the Anthropic Messages API as tools=[EXTRACTION_TOOL] with
# tool_choice={"type":"tool","name":"extract_tables"} to force structured output.
# The model MUST call this tool, guaranteeing schema-valid JSON in block.input.

EXTRACTION_TOOL: Dict[str, Any] = {
    "name": "extract_tables",
    "description": (
        "Extract all tables and core document metadata from the insurance "
        "commission statement. Return every table with commission or financial "
        "data, plus the carrier name, statement date, and broker/agency name."
    ),
    "input_schema": EXTRACTION_SCHEMA,
}
