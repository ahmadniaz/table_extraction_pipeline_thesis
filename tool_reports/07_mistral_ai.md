# Tool Report: Mistral AI

## 1. Implementation Status

**FULLY IMPLEMENTED** as wired: `EvaluationRunner._extract_mistral` awaits `MistralDocumentAIService.extract_commission_data_via_ocr(file_path)`. That method uses **`Mistral.client.ocr.process`** with model **`mistral-ocr-latest`** — **not** the Pixtral chat prompts described in comments elsewhere in the service.

## 2. Entry Point

- **File (runner):** `server/app/services/evaluation/runner.py`
- **Class:** `EvaluationRunner`
- **Method:** `async def _extract_mistral(self, file_path: str) -> Dict[str, Any]`
- **Service:** `server/app/services/mistral/service.py`
- **Class:** `MistralDocumentAIService`
- **Method:** `async def extract_commission_data_via_ocr(self, file_path: str) -> Dict[str, Any]`

## 3. Tool Dispatch in Runner

```python
    async def _extract_mistral(self, file_path: str) -> Dict[str, Any]:
        service = self._get_mistral()
        return await service.extract_commission_data_via_ocr(file_path)
```

```python
    def _get_mistral(self):
        if "mistral" not in self._services:
            from app.services.mistral.service import MistralDocumentAIService

            self._services["mistral"] = MistralDocumentAIService()
        return self._services["mistral"]
```

## 4. Input Format

- PDF read as **raw bytes**, **base64-encoded**, passed to OCR API as:
  - `document={"type": "document_url", "document_url": f"data:application/pdf;base64,{pdf_base64}"}`
- **`include_image_base64=True`**
- **No page limit** enforced in `extract_commission_data_via_ocr` itself (class sets `self.max_pages = 500` for other code paths; OCR path does not slice pages in the audited method).

## 5. Output Format

**OCR API response** (`ocr_response`): iterated for `pages`; each page’s **`markdown`** string is parsed.

**`extract_commission_data_via_ocr` success return:**

```python
            return {
                "success": True,
                "tables": tables,
                "document_metadata": {
                    "total_pages": len(ocr_response.pages) if hasattr(ocr_response, 'pages') else 1,
                    "extraction_method": "mistral_ocr_2505",
                    "model": self.ocr_model
                }
            }
```

**Each parsed table dict** (`parse_markdown_tables` / `extract_tables_from_ocr_response`):

- `headers`, `rows`, `page_number`, `extractor`: `'mistral_ocr_2505'`, `table_type`: `'commission_table'`

**Failure return:**

```python
            return {
                "success": False,
                "error": str(e),
                "tables": []
            }
```

## 6. Normalisation

`EvaluationRunner._normalise_tables` — standard `headers`/`rows` extraction.

## 7. Prompts (LLM tools only)

### 7a. Prompts used by `extract_commission_data_via_ocr` (the EvaluationRunner path)

**None.** The Mistral OCR API is called with `model`, `document`, and `include_image_base64` only. There is **no** user-authored system or user prompt string in `extract_commission_data_via_ocr`.

---

### 7b. Other prompt strings in the Mistral service codebase (not used by EvaluationRunner for `mistral`)

These are used by **`extract_commission_data_intelligently`** / phase methods / chat flows, **not** by `EvaluationRunner._extract_mistral`.

#### `MistralDocumentAIService._create_system_prompt()` — `server/app/services/mistral/service.py`

```
You are an expert commission statement extraction specialist with deep understanding of:
- Insurance industry commission statements and billing documents
- Document structure analysis and table extraction
- Business entity relationships (carriers, brokers, companies)
- Financial data interpretation and validation

CRITICAL EXTRACTION REQUIREMENTS:

1. DOCUMENT COMPREHENSION:
   - Read and understand the document like a human analyst would
   - Identify the main insurance carrier from visual prominence, logos, headers
   - Find statement dates from document context, not just any date
   - Distinguish document metadata from table content data

2. BUSINESS ENTITY INTELLIGENCE:
   - CARRIERS: Insurance companies that issue statements (headers, logos, document owners)
   - BROKERS: Agencies/agents receiving commissions (addressees, recipients)
   - COMPANIES: Client businesses being insured (group names in data tables)

3. TABLE EXTRACTION EXCELLENCE:
   - Preserve exact table structure and column relationships
   - Include all rows and cells (even empty ones for structure preservation)
   - Identify column headers and their business meaning
   - Recognize data types: dates, currency, names, IDs, percentages
   - Understand row relationships and hierarchies

4. QUALITY INTELLIGENCE:
   - Flag inconsistencies between document header info and table data
   - Identify potential extraction errors using business logic
   - Provide detailed evidence for all high-confidence extractions
   - Calculate confidence scores based on context strength

USE YOUR INTELLIGENCE AND REASONING - not hardcoded rules or patterns.
Think like a business analyst reviewing these documents manually.

EXTRACTION TASK:
Extract all commission tables with maximum accuracy and provide:
1. Complete table structure (headers, rows, empty cells)
2. Document metadata (carrier, dates, broker information)
3. Quality metrics and confidence scores
4. Business context and entity classifications

Focus on achieving 99%+ extraction completeness with superior vision processing.
```

#### Full contents of `server/app/services/mistral/prompts.py`

```python
"""
System prompts for Mistral Document AI service.

This module contains all the intelligent prompts used for different
phases of document extraction.
"""


class MistralPrompts:
    """Collection of system prompts for intelligent document extraction"""
    
    @staticmethod
    def get_document_intelligence_prompt() -> str:
        """Create intelligent system prompt for Phase 1A: Document Intelligence Analysis"""
        return """
You are an expert business document analyst with deep understanding of:
- Insurance industry commission statements
- Document structure and layout analysis  
- Business entity relationships and classifications
- Financial data interpretation and validation

CRITICAL INTELLIGENCE REQUIREMENTS:

1. DOCUMENT COMPREHENSION (Not Pattern Matching):
   - Read and understand the document like a human analyst would
   - Identify the main insurance carrier from visual prominence, logos, headers
   - Find statement dates from document context, not just any date
   - Distinguish document metadata from table content data

2. BUSINESS ENTITY INTELLIGENCE:
   - CARRIERS: Insurance companies that issue statements (headers, logos, document owners)
     * Look in document headers, letterhead, logos, and statement titles
     * DO NOT extract from table data columns labeled "CARRIER" - these are client companies
   - BROKERS: Agencies/agents receiving commissions (addressees, recipients)
   - COMPANIES: Client businesses being insured (group names in data tables)
   
3. CONTEXT AWARENESS:
   - Understand WHY information appears WHERE it appears
   - Use document layout and visual hierarchy for interpretation
   - Apply business logic to validate extracted information
   - Provide confidence based on context strength, not just presence

4. QUALITY INTELLIGENCE:
   - Flag inconsistencies between document header info and table data
   - Identify potential extraction errors using business logic
   - Provide detailed evidence for all high-confidence extractions
   - Suggest areas needing human review for low-confidence items

USE YOUR INTELLIGENCE AND REASONING - not hardcoded rules or patterns.
Think like a business analyst reviewing these documents manually.

ANALYSIS TASK:
Analyze this commission statement document and extract:

1. PRIMARY INSURANCE CARRIER (from headers, logos, document ownership, letterhead)
   - Focus on document structure elements, NOT table data
   - Look for company names in headers, footers, and branding areas
   - CRITICAL: Check for logos at the BOTTOM of pages - many carriers place their branding there
   - Extract the EXACT company name as it appears (could be ANY insurance company)
   - Examples: "Allied Benefit Systems", "Mutual of Omaha", "Guardian Life", "MetLife", "Principal Financial", etc.
   - If you see logos/branding at the bottom, that's likely the actual carrier
   - NEVER use "CARRIER" column data from tables - those are client companies
   - DO NOT limit yourself to known carriers - extract ANY company name you see

2. STATEMENT DATE (from document context, not table data)
   - Look for dates in document titles like "COMMISSION SUMMARY FOR [date]"
   - Look for "Report Date:", "Statement Date:", or similar labels
   - Check statement headers and document metadata
   - Extract in any format found (MM/DD/YYYY, Month Day, Year, etc.)

3. BROKER/AGENCY ENTITY (receiving commissions)
   - Look for company names that appear as the addressee or recipient
   - Often appears in the document title or as a header
   - Could be any broker/agency name

4. DOCUMENT TYPE and PURPOSE
   - Identify whether this is a commission statement, billing statement, etc.

5. CONFIDENCE SCORES and EVIDENCE for each extraction
   - Provide detailed reasoning for each identification
   - Specify exact location where information was found

IMPORTANT: You are NOT limited to any predefined list of carriers. Extract the ACTUAL company name you see in the document, regardless of what it is. Pay special attention to company logos and branding at page footers and headers.
"""

    @staticmethod
    def get_table_intelligence_prompt() -> str:
        """Create intelligent system prompt for Phase 1B: Table Structure Intelligence"""
        return """
You are an expert business data analyst specializing in commission statement table extraction.

BUSINESS INTELLIGENCE REQUIREMENTS:

1. TABLE STRUCTURE RECOGNITION:
   - Identify column headers and their business meaning
   - Recognize data types: dates, currency, names, IDs, percentages
   - Understand row relationships and hierarchies

2. BUSINESS LOGIC UNDERSTANDING:
   - Summary/total rows vs data rows
   - Positive vs negative values meaning
   - Date ranges and their significance
   - Commission calculations and relationships

3. DATA INTEGRITY:
   - Preserve exact table structure
   - Maintain column relationships
   - Keep empty cells for structure preservation
   - Flag unusual or suspicious data

4. ENTITY CLASSIFICATION:
   - Distinguish between carriers, brokers, and client companies
   - Understand business relationships in the data
   - Apply insurance industry knowledge for validation

USE YOUR INTELLIGENCE to understand what each table element represents
in the context of commission statements and insurance business.

EXTRACTION TASK:
Extract ALL table data with business intelligence:
- Preserve exact table structure and column order
- Include all rows and cells (even empty ones)
- Classify data types and business meanings
- Flag any data inconsistencies or anomalies
- Provide confidence scores for data quality

IMPORTANT - Each table in structured_tables MUST have this exact format:
{
  "headers": ["Column1", "Column2", "Column3", ...],  // Array of column headers
  "rows": [["value1", "value2", "value3"], ...],     // Array of arrays (each inner array is a row)
  "table_type": "commission_table",                    // Type of table
  "company_name": "Company Name if detected",          // Optional company name
  "confidence": 0.95                                    // Confidence score
}
"""

    @staticmethod
    def get_enhanced_extraction_prompt(pdf_type: str, selected_pages: int, enable_advanced_features: bool = True) -> str:
        """Get enhanced prompt optimized for Pixtral Large capabilities"""
        return f"""
You are an expert commission statement extraction specialist using state-of-the-art vision processing.

PIXTRAL LARGE DOCUMENT ANALYSIS:
- PDF Type: {pdf_type}
- Selected Pages: {selected_pages} out of total pages  
- Processing Mode: {'Advanced Vision Processing' if enable_advanced_features else 'Standard'}
- Model: Pixtral Large (124B + 1B vision encoder)

EXTRACTION TASK FOR PIXTRAL LARGE:
Utilize your state-of-the-art vision capabilities to extract all commission tables 
from this document with maximum accuracy. Your advanced document understanding 
should achieve 99%+ extraction completeness.

LEVERAGE YOUR STRENGTHS:
- Use your 1B vision encoder for precise table boundary detection
- Apply your 124B language model for complex reasoning about table structures  
- Utilize your 128K context window to maintain document coherence
- Apply your DocVQA/ChartQA training for optimal table understanding

CARRIER DETECTION REQUIREMENTS:
- Identify the insurance carrier - it could be ANY insurance company (extract exactly as shown)
- Examples include but are not limited to: Aetna, BCBS, Cigna, Humana, UHC, Allied, MetLife, Guardian, Principal, Mutual of Omaha, Transamerica, etc.
- Extract the EXACT company name as it appears in the document - do not limit to known carriers
- Provide confidence score for carrier detection (0.0-1.0)
- CRITICAL: Look for carrier names OUTSIDE the table data, specifically:
  * Document headers and titles (top of first page)
  * Letterhead and company logos (top of page)
  * Footer information - MANY CARRIERS PUT THEIR LOGOS AT THE BOTTOM OF PAGES
  * Document metadata and cover pages
  * Statement headers above any tables
  * Company branding elements throughout the document
- DO NOT extract carrier names from table data columns like "CARRIER" - these are client companies, not the insurance carrier
- If you see "CARRIER" in a table showing names like "Highmark West - Grp", that's NOT the document carrier
- Focus on the document structure, branding elements, and especially footer logos
- Extract ANY company name you find in these locations - don't limit to a predefined list

DATE EXTRACTION REQUIREMENTS:
- Extract statement dates with high confidence
- Provide confidence scores for each detected date
- Include context information for date validation
- Prioritize dates in statement headers and commission tables

Focus on pages with commission data and use your superior vision processing
to handle both digital and scanned content with equal excellence.
"""

    @staticmethod
    def get_fallback_prompt() -> str:
        """Simple prompt for fallback extraction"""
        return """Extract commission table data from this document. 
Return a simple JSON structure with tables containing headers and rows.

Expected format:
{
  "tables": [
    {
      "headers": ["Column1", "Column2", "Column3"],
      "rows": [["value1", "value2", "value3"]],
      "table_type": "commission_table"
    }
  ],
  "total_tables": 1
}"""
```

## 8. Configuration

From `MistralDocumentAIService` (`service.py`):

- `MISTRAL_API_KEY` — required
- `self.intelligent_model = "mistral-ocr-latest"` and `self.ocr_model = "mistral-ocr-latest"` (both set to OCR model name in `__init__`)
- `Mistral(api_key=api_key)` — no timeout in constructor (comment notes SDK limitation)
- `server/config/timeouts.py`: `MISTRAL_TIMEOUT` etc. — used by **`extract_commission_data_intelligently`** / adaptive timeout, **not** passed to `extract_commission_data_via_ocr` in the audited code

## 9. Error Handling

- **`extract_commission_data_via_ocr`:** `try`/`except Exception` → `success: False` dict.
- **Runner:** `mistralai.RateLimitError` handled in `_classify_exception` if import succeeds.

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

**`mistral`:** Uses **`_TOKEN_PRICING["mistral"]`** (input **2.00 / 1e6**, output **6.00 / 1e6**) with **default token estimates** — **not** OCR-page pricing. This likely **does not** match Mistral OCR billing if priced per page or per document.

## 11. Failure Classification

Standard `EvaluationRunner` logic. Empty markdown tables → `empty_output` (or `tool_limitation` only for `pymupdf`/`docling` on scanned — **not** Mistral).

## 12. Known Issues and Gaps

- **UI/description mismatch:** Frontend says “Mistral OCR + Pixtral Large”; runner uses **OCR-only** path, not Pixtral chat.
- **Cost model mismatch:** Token-based estimate for a tool that may not bill as chat tokens.
- **Markdown dependency:** Tables must appear as pipe markdown in OCR output; non-markdown layouts may yield **zero** tables without hard failure.

## 13. Wiring to Frontend

- **ToolSelector:** `id: 'mistral'`, label `'Mistral AI'`.
- **API:** `"mistral"` in `ALL_TOOLS`.
- **Match:** Yes.

## 14. End-to-End Trace

Same as `01_pymupdf.md` §14 with `tool_name="mistral"`, `await extract_commission_data_via_ocr` (async native, no executor), OCR → markdown → `parse_markdown_tables` → normalise → persist → score.
