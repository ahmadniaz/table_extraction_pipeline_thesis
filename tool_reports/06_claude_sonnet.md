# Tool Report: Claude Sonnet

## 1. Implementation Status

**FULLY IMPLEMENTED** for evaluation: `EvaluationRunner._extract_claude` awaits `ClaudeDocumentAIService.extract_commission_data(file_path)`.

## 2. Entry Point

- **File (runner):** `server/app/services/evaluation/runner.py`
- **Class:** `EvaluationRunner`
- **Method:** `async def _extract_claude(self, file_path: str) -> Dict[str, Any]`
- **Service:** `server/app/services/claude/service.py`
- **Class:** `ClaudeDocumentAIService`
- **Method:** `async def extract_commission_data(self, file_path: str, progress_tracker = None) -> Dict[str, Any]`

Primary extraction uses `_extract_standard_file` or `_extract_large_file`, which call `_call_claude_api` with **`self.prompts.get_table_extraction_prompt()`** and **`system=self.prompts.get_system_prompt()`**.

## 3. Tool Dispatch in Runner

```python
    async def _extract_claude(self, file_path: str) -> Dict[str, Any]:
        service = self._get_claude()
        return await service.extract_commission_data(file_path)
```

```python
    def _get_claude(self):
        if "claude_sonnet" not in self._services:
            from app.services.claude.service import ClaudeDocumentAIService

            self._services["claude_sonnet"] = ClaudeDocumentAIService()
        return self._services["claude_sonnet"]
```

## 4. Input Format

- **Standard path:** Full PDF read and **base64-encoded** (`ClaudePDFProcessor.encode_pdf_to_base64`), sent as Anthropic **`document`** block with `media_type: application/pdf`.
- **Large files:** `pdf_info['is_large_file']` when `file_size_mb > 20` **or** `page_count > 50` (`ClaudePDFProcessor.get_pdf_info`). Chunking uses `chunk_large_pdf(..., max_pages_per_chunk=40)` but **`_extract_chunk` still encodes the entire file** (comment: "For now, encode entire PDF (Claude handles page ranges internally)").
- **Limits:** `CLAUDE_MAX_FILE_SIZE` default **32** MB; `CLAUDE_MAX_PAGES` default **100**; `asyncio.wait_for(..., timeout=self.timeout_seconds)` with `CLAUDE_TIMEOUT_SECONDS` default **300** in `__init__` (note: service uses `CLAUDE_TIMEOUT_SECONDS`; `PROJECT_CONTEXT` mentions `CLAUDE_TIMEOUT` — verify env).

## 5. Output Format

On success, `_format_response` returns a dict including:

- `'success': True`
- `'tables'`: list of table dicts (`headers`, `rows`, plus optional fields from parsed JSON: `table_type`, `page_number`, `confidence_score`, `summary_rows`, `metadata`, etc.)
- `'document_metadata'`, `'extraction_method': 'claude'`, `'quality_summary'`, `'metadata'`, `'extraction_quality'`, etc.

On failure in `extract_commission_data` outer `except`:

```python
            return {
                'success': False,
                'error': str(e),
                'error_message': self.error_handler.format_error_message(e),
                'tables': [],
                'extraction_method': 'claude',
                'processing_time': processing_time
            }
```

## 6. Normalisation

`EvaluationRunner._normalise_tables` reads `raw.get("tables")` from the dict.

**Claude-specific preprocessing:** In `_extract_standard_file`, `normalize_multi_line_headers` from `extraction_utils` is applied to each table’s `headers`/`rows` before formatting.

## 7. Prompts (LLM tools only — complete text from source)

Anthropic **`system`** parameter and user **`text`** block:

### 7a. `ClaudePrompts.get_system_prompt()` — `server/app/services/claude/prompts.py`

```
You are an expert AI assistant specializing in document analysis and data extraction for insurance commission statements.

You have deep expertise in:
- Insurance industry terminology and structure
- Commission statement formats from major carriers
- Table detection and extraction from complex documents
- Financial data interpretation
- Document quality assessment

Your responses are:
- Precise and accurate
- Structured in valid JSON format
- Comprehensive without being verbose
- Focused on data integrity and completeness

You prioritize accuracy over speed and will flag uncertainties rather than guess.
```

### 7b. `ClaudePrompts.get_table_extraction_prompt()` — user text paired with PDF document in `_call_claude_api`

```
You are an expert document analyst specializing in insurance commission statements. 

Your task is to extract ALL tables AND document metadata from this PDF with maximum accuracy. Pay special attention to:

1. **Table Structure**: Preserve exact column headers and row relationships
2. **Financial Data**: Accurately capture commission amounts, dates, and percentages  
3. **Document Metadata**: Extract carrier name, statement date, and broker company
4. **Company Information**: Identify carrier names, broker details, and client companies
5. **Data Types**: Recognize dates, currency, names, IDs, and percentages correctly
6. **Summary Rows**: Detect and flag summary/total rows separately
7. **Empty Cells**: Include empty cells to preserve table structure

METADATA EXTRACTION GUIDELINES:
- **CARRIER NAME**: The insurance company that issued this statement (e.g., Aetna, Blue Cross, Cigna, UnitedHealthcare, Allied Benefit Systems, Redirect Health). Look in document headers, footers, logos, and letterhead. DO NOT extract from table data columns.
- **STATEMENT DATE**: The date of this commission statement. CRITICAL INSTRUCTIONS:
  * Extract the ACTUAL date shown in the document - NEVER use current date or any default/fallback date
  * Look for "Statement Date:", "Commission Summary For:", "Report Date:", "Period:", "Period Ending:", "Date Range:", "Statement Period:", "Reporting Period:" in headers, titles, and top of document
  * **FOR DATE RANGES**: If you see a date range (e.g., "Period: 01/01/2025 - 01/31/2025" or "01/01/2025 - 01/31/2025"), USE THE END DATE (the second date) as the statement date
  * For date ranges like "MM/DD/YYYY - MM/DD/YYYY", always extract the SECOND date (end date)
  * Format as YYYY-MM-DD. Example: "Period: 01/01/2025 - 01/31/2025" → use "2025-01-31"
  * If no date is visible or you cannot confidently extract it, return null instead of guessing
  * DO NOT extract dates from table cells, policy effective dates, or transaction dates - only extract the statement/report date from the document header
- **BROKER COMPANY**: The broker/agent entity receiving commissions. Look for "Agent:", "Broker:", "Agency:", "To:", "Prepared For:" labels near the top of document. This is different from the carrier.

CRITICAL REQUIREMENTS:
- Extract EVERY table, even if partially visible
- Maintain exact table structure (headers + data rows)
- Handle borderless tables and complex layouts
- Detect hierarchical data (company sections, sub-totals)
- Flag data quality issues
- Preserve multi-line headers by joining them with spaces

Return tables in this exact JSON structure:
{
  "tables": [
    {
      "headers": ["Column 1", "Column 2", "Column 3"],
      "rows": [
        ["data1", "data2", "data3"],
        ["data4", "data5", "data6"]
      ],
      "table_type": "commission_table",
      "page_number": 1,
      "confidence_score": 0.95,
      "summary_rows": [5, 10],
      "metadata": {
        "borderless": false,
        "hierarchical": false,
        "company_sections": []
      }
    }
  ],
  "document_metadata": {
    "carrier_name": "Detected Carrier Name",
    "carrier_confidence": 0.95,
    "statement_date": "2024-01-31",
    "date_confidence": 0.92,
    "broker_company": "Broker/Agent Company Name",
    "broker_confidence": 0.90,
    "document_type": "commission_statement"
  },
  "extraction_notes": "Any important observations about the document or extraction challenges"
}

IMPORTANT EXTRACTION RULES:
1. For multi-line column headers, join them with a space (e.g., "First Name" + "Last Name" = "First Name Last Name")
2. Preserve exact spacing and formatting in data cells
3. Convert accounting brackets to negative numbers: (1,234.56) → -1234.56
4. Identify summary rows by looking for keywords: "Total", "Subtotal", "Grand Total", "Sum"
5. If a table spans multiple pages, extract each page separately
6. Include confidence scores based on text clarity and structure completeness

Analyze the document thoroughly and extract all tabular data with precision.
```

**Chunk / other prompts** (`get_chunk_extraction_prompt`, `get_metadata_extraction_prompt`, etc.) exist in the same file but are **not** used for the standard single-call path in `_extract_standard_file` (chunks use `get_chunk_extraction_prompt`).

## 8. Configuration

From `ClaudeDocumentAIService.__init__` (`service.py`):

- `CLAUDE_MODEL_PRIMARY` → default `'claude-sonnet-4-20250514'`
- `CLAUDE_MODEL_FALLBACK` → default `'claude-sonnet-4-20250514'`
- `CLAUDE_MAX_FILE_SIZE` → default **32** (MB)
- `CLAUDE_MAX_PAGES` → default **100**
- `CLAUDE_TIMEOUT_SECONDS` → default **300**
- API key: `CLAUDE_API_KEY` (required for client init)

`_call_claude_api`:

- `max_tokens=16000`
- `temperature=0.1`
- `max_retries=3` with `ClaudeErrorHandler.get_retry_delay` (exponential, cap 60s)
- `asyncio.wait_for(..., timeout=self.timeout_seconds)`

## 9. Error Handling

- **`extract_commission_data`:** Catches exceptions → `success: False` dict (does not re-raise).
- **`_call_claude_api`:** Retries on timeout / retriable errors per `ClaudeErrorHandler.is_retriable_error` (string patterns: rate limit, timeout, connection, network, overloaded, unavailable).
- **`_extract_standard_file`:** On failure may attempt `_extract_with_fallback`; may **raise** if unrecoverable — caught by outer `extract_commission_data`.
- **Runner:** `success is False` → error_message from `raw.get("error", ...)` path.

## 10. Cost Calculation

Full `server/app/services/evaluation/cost_calculator.py`:

```python
"""
Cost estimation for each extraction tool.

Rates are hardcoded snapshots at the time of this study (April 2026).
Local/open-source tools have zero marginal cost.
"""

PRICE_PER_PAGE = {
    "pymupdf": 0.0,
    "docling": 0.0,
    "aws_textract": 0.015,
    "google_docai": 0.0065,
    "gpt5": 0.0,       # estimated from tokens below
    "claude_sonnet": 0.0,  # estimated from tokens below
    "mistral": 0.0,     # estimated from tokens below
}

# Per-token pricing (USD) — input / output
_TOKEN_PRICING = {
    "gpt5": {"input": 5.00 / 1_000_000, "output": 15.00 / 1_000_000},
    "claude_sonnet": {"input": 3.00 / 1_000_000, "output": 15.00 / 1_000_000},
    "mistral": {"input": 2.00 / 1_000_000, "output": 6.00 / 1_000_000},
}

# Rough tokens-per-page estimate when actual counts are unavailable
_DEFAULT_TOKENS_PER_PAGE = {"input": 1500, "output": 2000}


def calculate_cost(
    tool_name: str,
    page_count: int,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
) -> float:
    """Return estimated USD cost for a single extraction run."""
    base = PRICE_PER_PAGE.get(tool_name, 0.0) * page_count

    if tool_name in _TOKEN_PRICING:
        pricing = _TOKEN_PRICING[tool_name]
        inp = input_tokens or (_DEFAULT_TOKENS_PER_PAGE["input"] * page_count)
        out = output_tokens or (_DEFAULT_TOKENS_PER_PAGE["output"] * page_count)
        token_cost = inp * pricing["input"] + out * pricing["output"]
        return round(base + token_cost, 6)

    return round(base, 6)
```

**`claude_sonnet` token rates:** input **USD 3.00 / 1e6**, output **USD 15.00 / 1e6**. **`calculate_cost` does not receive actual `usage` from `_call_claude_api`** in `runner.py`.

## 11. Failure Classification

Standard `EvaluationRunner` behaviour. Additionally, Claude failures often surface as `success: False` dicts → runner’s `error_msg` substring classification.

## 12. Known Issues and Gaps

- **Chunking sends full PDF** per chunk — may not reduce payload size as intended.
- **`document_metadata` vs `metadata`:** Parser uses `parsed_data.get('document_metadata', {})` but prompt schema shows `document_metadata` at top level — consistent.
- **Quality assessor:** Uses heuristics in Python, not necessarily the separate `get_quality_assessment_prompt()` LLM call for the main extraction path.

## 13. Wiring to Frontend

- **ToolSelector:** `id: 'claude_sonnet'`, label `'Claude Sonnet'`.
- **API:** `"claude_sonnet"` in `ALL_TOOLS`.
- **Match:** Aligns with `_DISPATCH`.

## 14. End-to-End Trace

Same as `01_pymupdf.md` §14 with `tool_name="claude_sonnet"`, async `extract_commission_data` (no thread pool), and token-based cost estimate as in §10.
