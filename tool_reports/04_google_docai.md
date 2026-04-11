# Tool Report: Google DocAI

## 1. Implementation Status

**FULLY IMPLEMENTED** for the evaluation runner: `GoogleDocAIExtractor.extract_tables_async` is called from `_extract_google_docai`. Operation requires Google Cloud credentials, project/processor env configuration, and a working Document AI client (`extractor.is_available()`).

## 2. Entry Point

- **File (runner):** `server/app/services/evaluation/runner.py`
- **Class:** `EvaluationRunner`
- **Method:** `async def _extract_google_docai(self, file_path: str) -> Dict[str, Any]`
- **Service:** `GoogleDocAIExtractor` in `server/app/services/google_docai/extractor.py`
- **Method invoked:** `async def extract_tables_async(self, pdf_path: str) -> Dict[str, Any]` — wraps synchronous `extract_tables` via `run_in_executor`.

## 3. Tool Dispatch in Runner

```python
    async def _extract_google_docai(self, file_path: str) -> Dict[str, Any]:
        extractor = self._get_google_docai()
        return await extractor.extract_tables_async(file_path)
```

```python
    def _get_google_docai(self):
        if "google_docai" not in self._services:
            from app.services.google_docai.extractor import GoogleDocAIExtractor

            self._services["google_docai"] = GoogleDocAIExtractor()
        return self._services["google_docai"]
```

## 4. Input Format

- **How passed:** Local file path `pdf_path`; `extract_tables` does `open(pdf_path, "rb")` and reads **raw PDF bytes**.
- **Preprocessing:** Page count from PDF; strategy selection:
  - `page_count <= REGULAR_MODE_MAX_PAGES` (15): `process_document_regular_mode`
  - up to `IMAGELESS_MODE_MAX_PAGES` (30): imageless mode or chunked fallback on page limit errors
  - larger: `process_document_in_chunks` with `CHUNK_SIZE` 15
- **Post-merge:** Optional `stitch_multipage_tables` from `app.services.extraction.extraction_utils`.
- **Further:** `_post_process_tables` — text cleaning, empty cell removal, company name detection.

Constants from `server/app/services/google_docai/config.py`:

- `REGULAR_MODE_MAX_PAGES = 15`
- `IMAGELESS_MODE_MAX_PAGES = 30`
- `CHUNK_SIZE = 15`
- `MAX_RETRIES = 3` (defined; usage is in other modules, not re-audited here per extractor flow)

## 5. Output Format

**From `extract_tables`:** `List[Dict[str, Any]]` — each table after post-processing typically includes:

- `"header"`: cleaned header strings (note: **not** `"headers"` at this stage — see normalisation)
- `"rows"`: cleaned rows
- `"confidence"`, `"bbox"`, `"page_number"`, `"table_index"`, `"extractor"`, `"post_processed"`, `"metadata"`, plus any extra keys copied from the original table

**From `extract_tables_async`:** If the list result is a `list`, wraps as:

```python
            return {
                "success": True,
                "tables": result,
                "extraction_metadata": {
                    "method": "google_docai",
                    "timestamp": datetime.now().isoformat(),
                    "confidence": 0.8
                }
            }
```

If `extract_tables` raises, the exception propagates to the executor caller (no `success: False` dict from `extract_tables_async` on error — the await will raise).

## 6. Normalisation

`_normalise_tables` accepts `t.get("headers") or t.get("header")`, so Google’s `"header"` key is mapped to `headers` in the normalised list.

## 7. Prompts (LLM tools only — skip for rule-based/CV tools)

Not applicable — Google Document AI Form Parser API, not an LLM prompt in application code.

## 8. Configuration

From `server/app/services/google_docai/config.py`:

- `DEFAULT_PROJECT_ID = "pdf-tables-extractor-465009"`
- `DEFAULT_PROCESSOR_ID = "521303e404fb7809"`
- `DEFAULT_LOCATION = "us"`
- `CREDENTIALS_PATHS` — list including `/etc/secrets/...` and `/app/...`

From `GoogleDocAIExtractor._initialize_client`:

- Sets `GOOGLE_APPLICATION_CREDENTIALS` from first existing file in `CREDENTIALS_PATHS` plus local fallbacks under server cwd.
- Sets `GOOGLE_CLOUD_PROJECT_ID` and `GOOGLE_DOCAI_PROCESSOR_ID` from defaults if unset.
- `processor_id` from `os.getenv("GOOGLE_DOCAI_PROCESSOR_ID", DEFAULT_PROCESSOR_ID)`.

**Note:** `PROJECT_CONTEXT.md` names `DOCAI_PROJECT_ID`; the extractor code shown uses `GOOGLE_CLOUD_PROJECT_ID` when unset. Verify env var names against deployment.

## 9. Error Handling

- **`extract_tables`:** Broad `try`/`except` prints and **re-raises** `Exception` after `"❌ Google Document AI extraction failed"`.
- **Imageless mode:** Catches page-limit errors and falls back to chunked processing.
- **Table merge:** `stitch_multipage_tables` failures are caught; processing continues with unmerged tables.
- **Post-process per table:** `except` appends original `table` to `processed_tables`.
- **Runner:** Uncaught exceptions → `_classify_exception` (likely `api_error` unless `requests` connection error).

## 10. Cost Calculation

Full file `server/app/services/evaluation/cost_calculator.py`:

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

**`google_docai`:** **USD 0.0065 × page_count** (hardcoded `PRICE_PER_PAGE`).

## 11. Failure Classification

Same shared `EvaluationRunner.run_tool` logic as other tools. **No** special case for `google_docai` on empty output (unlike `pymupdf`/`docling` scanned → `tool_limitation`). Empty tables → `empty_output`.

## 12. Known Issues and Gaps

- **Env naming:** Possible mismatch between docs (`DOCAI_PROJECT_ID`) and code (`GOOGLE_CLOUD_PROJECT_ID`).
- **Cost vs billing:** `0.0065` per page must be validated against current Google Cloud Document AI Form Parser pricing for the processor/region used.
- **`success: True` always** when list returned — even if inner table list is empty (runner then classifies as empty output).

## 13. Wiring to Frontend

- **ToolSelector:** `id: 'google_docai'`, label `'Google DocAI'`.
- **API:** `"google_docai"` in `ALL_TOOLS`.
- **Match:** Aligns with `runner.py`.

## 14. End-to-End Trace

Same as PyMuPDF (see `01_pymupdf.md` §14) with:

- `tool_name="google_docai"`.
- `_extract_google_docai` → `extract_tables_async` → thread pool `extract_tables` → async result dict → `_normalise_tables`.
- Cost: `0.0065 * page_count` for a 3-page doc = **0.0195** USD (before rounding: `round(base, 6)`).
