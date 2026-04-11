# Tool Report: GPT-5 Vision

## 1. Implementation Status

**FULLY IMPLEMENTED** as wiring: `EvaluationRunner` calls `GPT4oVisionService.extract_commission_data` in a thread pool. The implementation file is named `gpt4o_vision_service.py`, but all `chat.completions.create` calls in the audited paths use **`model="gpt-5"`** (not `gpt-4o`). Whether the OpenAI account supports that model ID is an operational concern outside this repository.

## 2. Entry Point

- **File (runner):** `server/app/services/evaluation/runner.py`
- **Class:** `EvaluationRunner`
- **Method:** `async def _extract_gpt5(self, file_path: str) -> Dict[str, Any]`
- **Service file:** `server/app/services/ai/gpt4o_vision_service.py`
- **Class:** `GPT4oVisionService`
- **Method:** `def extract_commission_data(self, pdf_path: str, max_pages: int = 30) -> Dict[str, Any]`

## 3. Tool Dispatch in Runner

```python
    async def _extract_gpt5(self, file_path: str) -> Dict[str, Any]:
        service = self._get_gpt()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, service.extract_commission_data, file_path)
```

```python
    def _get_gpt(self):
        if "gpt5" not in self._services:
            from app.services.ai.gpt4o_vision_service import GPT4oVisionService

            self._services["gpt5"] = GPT4oVisionService()
        return self._services["gpt5"]
```

## 4. Input Format

**Branching in `extract_commission_data`:**

1. **`is_digital_pdf(pdf_path)`** — PyMuPDF (`fitz`): samples first `min(3, len(doc))` pages, requires `text_length > 100` and keywords `COMMISSION`, `PREMIUM`, `COVERAGE`, `POLICY`, or `CUSTOMER` in text → digital; on error defaults to **False** (scanned path).

2. **Digital path:** `extract_from_digital_pdf_intelligent(pdf_path)`:
   - `_extract_pdf_text`: all pages, `page.get_text()`, non-empty pages only, prefixed with `--- PAGE n ---`.
   - Text truncated to **50 000** characters for the main extraction call.
   - `_analyze_document_context(doc_content)` uses first **2000** chars for context analysis.

3. **Scanned path:** `extract_from_scanned_pdf(pdf_path, max_pages)` — default **`max_pages=30`** from `extract_commission_data` signature.
   - For `total_pages <= max_pages`: all pages converted to images.
   - Else: `_select_representative_pages` / content scoring.
   - **Images:** `_convert_page_to_optimized_image` — adaptive DPI **400 / 500 / 600** via `_calculate_adaptive_dpi`, PNG base64 after PIL contrast/sharpness enhancement.

**Preprocessing after extraction:** If `success` and `tables` present, `CompanyNameDetectionService.detect_company_names_in_extracted_data(table, "gpt4o_vision_enhanced")` per table.

## 5. Output Format

- **Typical success:** `{"success": True, "tables": [...], ...}` with optional `extraction_metadata`, `company_detection_applied`, etc.
- **Each table:** Expects `headers` and `rows` (plus optional `hierarchical_metadata`, `validation_metadata` after intelligent parsing).
- **Failure:** `{"success": False, "error": "<message>", ...}` — runner treats `success is False` as error path (string heuristics for transient classification).

## 6. Normalisation

`EvaluationRunner._normalise_tables` (same as other tools): reads `raw.get("tables")`, maps `headers`/`header`, `rows`/`data`.

## 7. Prompts (LLM tools only — complete text from source)

The following are **verbatim** from `server/app/services/ai/gpt4o_vision_service.py` as used on the **`extract_commission_data`** code paths (digital → intelligent extraction; scanned → vision).  

**Alternate method `extract_from_digital_pdf` (text-only, not called by `extract_commission_data`)** uses the same `_create_digital_pdf_system_prompt()` and user content:

`f"Extract ONLY the data that is VISIBLY PRESENT in this digital PDF. DO NOT invent, infer, or guess any values. DO NOT create headers that don't exist. DO NOT fill empty cells. Extract the ACTUAL table structure as it appears in the document. If you cannot see something clearly, do not extract it. PRIORITIZE pages with commission amounts, premiums, and financial data over pages with 'No Commission Activity' or similar messages.\n\nText content:\n\n{text_content[:50000]}"`

---

### 7a. `_create_digital_pdf_system_prompt()` — used when context is `"unknown"` in intelligent digital path, and in non-intelligent `extract_from_digital_pdf`

```
You are a commission statement data extractor with advanced hierarchical structure detection capabilities. Your job is to extract EXACTLY what you see while recognizing different row types and preserving structure.

CRITICAL INSTRUCTIONS FOR TABLE EXTRACTION:

1. **COLUMN ORDER PRESERVATION**:
   - Extract columns in EXACT visual order from LEFT to RIGHT
   - Do NOT reorder columns based on semantic meaning
   - Maintain precise visual sequence as it appears in source

2. **HIERARCHICAL STRUCTURE DETECTION**:
   - Identify rows containing only company/entity names (header rows)
   - Look for business entity suffixes (LLC, Inc, Corp, Co, Ltd, Company, Corporation)
   - Detect rows with different cell patterns from regular data rows
   - Company header rows typically lack multiple numeric values found in data rows

3. **COMPANY NAME INTEGRATION**:
   - Add "Company Name" as FIRST column in output
   - Propagate company names from header rows to associated data rows
   - Preserve all original data and structure

4. **DATA EXTRACTION RULES**:
   - THOROUGHLY examine every corner, edge, and cell of the table
   - Extract ALL data that is VISIBLY PRESENT in the document - be comprehensive
   - NEVER invent, infer, or guess any values
   - Copy headers EXACTLY as written - do not normalize or interpret
   - Copy values EXACTLY as written - do not reformat or calculate
   - If a cell is empty, leave it empty - do not populate it
   - NEVER combine or split cells - extract each cell as it appears
   - Pay special attention to leftmost and rightmost columns - they are often missed
   - Check for partial rows or columns that might be cut off at page edges

CONTENT PRIORITY:
- **HIGH PRIORITY**: Pages with commission amounts, premiums, coverage periods, group data
- **LOW PRIORITY**: Pages with "No Commission Activity", "No Activity", or similar messages
- **IGNORE**: Pages that only contain lists of inactive groups without financial data

EXTRACTION PROCESS:
1. THOROUGHLY scan the entire document from top to bottom, left to right
2. Identify ALL table structures and boundaries - examine every corner and edge
3. Detect company header rows (rows with business entity names)
4. Extract headers in EXACT visual order from left to right - ensure no columns are missed
5. Extract ALL data rows while maintaining company context - check every row carefully
6. Add "Company Name" as first column with propagated company names
7. Leave empty cells completely empty but ensure all visible cells are captured
8. Pay special attention to the leftmost and rightmost columns - they are often missed
9. Verify that all table boundaries are captured - check for partial rows or columns
10. Focus on pages with actual commission/financial data

OUTPUT FORMAT:
Return ONLY valid JSON with enhanced structure:
{
  "tables": [
    {
      "headers": ["Company Name", "ACTUAL_HEADER_1", "ACTUAL_HEADER_2", "ACTUAL_HEADER_3"],
      "rows": [
        ["COMPANY_NAME", "ACTUAL_VALUE_1", "ACTUAL_VALUE_2", ""],  // Empty cell stays empty
        ["COMPANY_NAME", "ACTUAL_VALUE_4", "", "ACTUAL_VALUE_6"]   // Empty cell stays empty
      ],
      "hierarchical_metadata": {
        "company_sections_detected": true,
        "column_order_preserved": true,
        "structure_validated": true
      }
    }
  ]
}

REMEMBER: THOROUGHLY examine every corner, every row, and every cell of the table. Look carefully at the left end and right end of the page to ensure ALL columns and ALL rows are extracted. Be meticulous in your analysis and extract everything you can identify, even if partially visible. Focus on pages with actual commission data, not pages with no activity.
```

---

### 7b. `_create_intelligent_system_prompt(context_analysis)` — template with `{industry}` and `{document_type}` filled from context JSON

Static template in source (placeholders shown as in code):

```
You are an expert data extraction specialist for {industry} {document_type}s.

EXTRACTION PRINCIPLES:
1. Extract ONLY what is visually present in the document
2. Use exact headers as they appear - do not normalize or interpret
3. Maintain precise column order from left to right
4. Preserve all data structure and hierarchy
5. Never invent, infer, or generate data

INDUSTRY CONTEXT: {industry}
DOCUMENT TYPE: {document_type}

For {industry} documents, standard terminology includes legitimate business abbreviations
and industry-specific terms. Extract tables with complete accuracy and contextual awareness.

OUTPUT: Return only valid JSON with extracted table structure.
```

---

### 7c. Intelligent digital — **user** message to main extraction call

```
Extract table data from this document:

{doc_content[:50000]}
```
(Implemented as single f-string with leading newline after colon as in source: `f"Extract table data from this document:\n\n{doc_content[:50000]}"`.)

---

### 7d. `_analyze_document_context` — **system** `analysis_prompt`

```
Analyze this document excerpt to determine:
1. Document type and industry
2. Expected header terminology
3. Business context and purpose

Focus on identifying legitimate business terminology that should be allowed.

Return your analysis in JSON format:
{
  "document_type": "string",
  "industry": "string", 
  "expected_terms": ["term1", "term2"],
  "business_context": "string"
}
```

**User message:** `f"Document content: {content[:2000]}"`  
**API:** `model="gpt-5"`, `max_completion_tokens=300`.

---

### 7e. `_create_vision_system_prompt()` — scanned / image path (`_extract_tables_with_vision`)

```
You are a commission statement data extractor with advanced hierarchical structure detection capabilities. Your job is to extract EXACTLY what you see while recognizing different row types and preserving structure.

CRITICAL INSTRUCTIONS FOR TABLE EXTRACTION:

1. **COLUMN ORDER PRESERVATION**:
   - Extract columns in EXACT visual order from LEFT to RIGHT
   - Do NOT reorder columns based on semantic meaning
   - Maintain precise visual sequence as it appears in source

2. **HIERARCHICAL STRUCTURE DETECTION**:
   - Identify rows containing only company/entity names (header rows)
   - Look for business entity suffixes (LLC, Inc, Corp, Co, Ltd, Company, Corporation)
   - Detect rows with different cell patterns from regular data rows
   - Company header rows typically lack multiple numeric values found in data rows

3. **COMPANY NAME INTEGRATION**:
   - Add "Company Name" as FIRST column in output
   - Propagate company names from header rows to associated data rows
   - Preserve all original data and structure

4. **DATA EXTRACTION RULES**:
   - THOROUGHLY examine every corner, edge, and cell of the table
   - Extract ALL data that is VISIBLY PRESENT in the images - be comprehensive
   - NEVER invent, infer, or guess any values
   - Copy headers EXACTLY as written - do not normalize or interpret
   - Copy values EXACTLY as written - do not reformat or calculate
   - If a cell is empty, leave it empty - do not populate it
   - NEVER combine or split cells - extract each cell as it appears
   - Pay special attention to leftmost and rightmost columns - they are often missed
   - Check for partial rows or columns that might be cut off at page edges

CONTENT PRIORITY:
- **HIGH PRIORITY**: Pages with commission amounts, premiums, coverage periods, group data
- **LOW PRIORITY**: Pages with "No Commission Activity", "No Activity", or similar messages
- **IGNORE**: Pages that only contain lists of inactive groups without financial data

EXTRACTION PROCESS:
1. THOROUGHLY scan the entire image from top to bottom, left to right
2. Identify ALL table structures and boundaries - examine every corner and edge
3. Detect company header rows (rows with business entity names)
4. Extract headers in EXACT visual order from left to right - ensure no columns are missed
5. Extract ALL data rows while maintaining company context - check every row carefully
6. Add "Company Name" as first column with propagated company names
7. Leave empty cells completely empty but ensure all visible cells are captured
8. Pay special attention to the leftmost and rightmost columns - they are often missed
9. Verify that all table boundaries are captured - check for partial rows or columns
10. Do not apply patterns from other documents
11. Focus on pages with actual commission/financial data

OUTPUT FORMAT:
Return ONLY valid JSON with enhanced structure:
{
  "tables": [
    {
      "headers": ["Company Name", "ACTUAL_HEADER_1", "ACTUAL_HEADER_2", "ACTUAL_HEADER_3"],
      "rows": [
        ["COMPANY_NAME", "ACTUAL_VALUE_1", "ACTUAL_VALUE_2", ""],  // Empty cell stays empty
        ["COMPANY_NAME", "ACTUAL_VALUE_4", "", "ACTUAL_VALUE_6"]   // Empty cell stays empty
      ],
      "hierarchical_metadata": {
        "company_sections_detected": true,
        "column_order_preserved": true,
        "structure_validated": true
      }
    }
  ]
}

REMEMBER: THOROUGHLY examine every corner, every row, and every cell of the table. Look carefully at the left end and right end of the page to ensure ALL columns and ALL rows are extracted. Be meticulous in your analysis and extract everything you can identify, even if partially visible. Focus on pages with actual commission data, not pages with no activity.
```

---

### 7f. `_create_vision_user_prompt(num_pages)` — first element of multimodal user content

```
THOROUGHLY examine these {num_pages} page images and extract ALL visible data. CRITICAL INSTRUCTIONS: 1) Extract columns in EXACT visual order from LEFT to RIGHT - examine every corner and edge of the page. 2) Detect company header rows (rows with business entity names like LLC, Inc, Corp). 3) Add 'Company Name' as FIRST column and propagate company names from header rows to associated data rows. 4) Extract ALL rows and ALL columns - pay special attention to leftmost and rightmost columns which are often missed. 5) Be meticulous in your analysis - check every cell, every row, every column. 6) DO NOT invent, infer, or guess any values. 7) DO NOT create headers that don't exist. 8) DO NOT fill empty cells. 9) Extract the ACTUAL table structure as it appears in the document. 10) PRIORITIZE pages with commission amounts, premiums, and financial data over pages with 'No Commission Activity' or similar messages. 11) Ensure complete extraction - capture everything visible, even if partially obscured.
```
(Implemented as an f-string substituting `{num_pages}`.)

**Vision call:** `model="gpt-5"`, `max_completion_tokens=20000`; images appended as `data:image/png;base64,...`.

---

### 7g. Header validation (`_parse_extraction_response_intelligent` → `_validate_extracted_headers_with_ai`) — **system** `_create_header_validation_prompt()`

```
You are an expert document analyst specializing in business document validation.

Your task is to determine if table headers are legitimate business document headers or AI-generated templates.

ANALYSIS CRITERIA:

1. **Legitimate Headers Characteristics:**
   - Industry-specific terminology (e.g., "Premium", "Commission", "Coverage")
   - Standard business abbreviations (e.g., "Eff Date" for Effective Date)
   - Financial/insurance terms (e.g., "Paid Amount", "Group", "Medical")
   - Consistent with document context and industry

2. **Template/AI-Generated Headers Characteristics:**
   - Generic placeholders (e.g., "Column_1", "Field_A", "Data_Point")
   - Inconsistent with document context
   - Overly generic or nonsensical combinations
   - Headers that don't match the document content

3. **Context Analysis:**
   - Do headers match the document type and industry?
   - Are abbreviations standard business practice?
   - Is terminology consistent with insurance/commission statements?

OUTPUT FORMAT (JSON only):
{
  "is_template": boolean,
  "confidence": float (0.0-1.0),
  "analysis": "Detailed explanation of reasoning",
  "legitimacy_score": float (0.0-1.0),
  "industry_alignment": "assessment of industry terminology alignment"
}

Be conservative - only flag as template if you're highly confident the headers are AI-generated.
```

**User template** (`validation_request`):

```
        HEADERS TO VALIDATE: {headers_text}
        
        DOCUMENT CONTEXT: {context_snippet}
        
        Analyze whether these headers are legitimate business document headers or AI-generated templates.
        Consider industry terminology, document type, and contextual consistency.
```

(`headers_text` = comma-joined headers; `context_snippet` = first 1000 chars of document or `"No document content available"`.)

**API:** `model="gpt-5"`, `max_completion_tokens=500`, `temperature=0.1`.

## 8. Configuration

- **`OPENAI_API_KEY`:** Required for `OpenAI` client (`_initialize_client`).
- **Model:** `"gpt-5"` on all audited `chat.completions.create` calls.
- **`max_completion_tokens`:** 20000 (main digital/vision), 300 (context), 500 (validation).
- **No `GPT_TIMEOUT` read inside `GPT4oVisionService`** in the audited excerpts; `config/timeouts.py` defines `gpt_api` for other layers.

## 9. Error Handling

- **Service methods:** Many return `{"success": False, "error": "..."}` instead of raising.
- **`_extract_tables_with_vision`:** Catches `Exception`, returns dict with error string.
- **Runner:** `success is False` → error branch with substring classification; uncaught exceptions → `_classify_exception` (OpenAI `RateLimitError` / `APIConnectionError` mapped when SDK import succeeds).

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

**Hardcoded token rates for `gpt5`:** input **USD 5.00 / 1e6**, output **USD 15.00 / 1e6**. **`calculate_cost` is never passed real token counts from this service** — estimates use `1500 * page_count` input and `2000 * page_count` output by default.

## 11. Failure Classification

Shared `EvaluationRunner` logic (`_classify_exception` + `success is False` string checks + empty-output handling). **No** `tool_limitation` branch for `gpt5` on empty tables.

## 12. Known Issues and Gaps

- **Filename vs branding:** `gpt4o_vision_service.py` / class `GPT4oVisionService` vs tool id `gpt5` and model `gpt-5`.
- **Intelligent parsing** may drop tables if AI validation marks template with confidence > 0.8 — can yield `success: False` with message about templates.
- **Digital detection** heuristic may misclassify some PDFs.
- **Large PDFs:** Scanned path caps at **30** pages by default (`max_pages` not overridden by runner).

## 13. Wiring to Frontend

- **ToolSelector:** `id: 'gpt5'`, label `'GPT-5 Vision'`.
- **API:** `"gpt5"` in `ALL_TOOLS`.
- **Match:** Consistent with `_DISPATCH` key `"gpt5"`.

## 14. End-to-End Trace

Same pattern as `01_pymupdf.md` §14, substituting:

- `tool_name="gpt5"`.
- Synchronous `extract_commission_data` executed in `run_in_executor`.
- Cost from token formula with estimated tokens, **not** actual usage from API responses in `calculate_cost` call.
