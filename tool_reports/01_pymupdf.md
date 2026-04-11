# Tool Report: PyMuPDF

## 1. Implementation Status

**PARTIALLY IMPLEMENTED** — The tool is registered as `pymupdf` and runs in the evaluation pipeline, but extraction uses **`pdfplumber`**, not PyMuPDF (`fitz`). PyMuPDF is used elsewhere (upload analysis, GPT/Mistral helpers) but not in `_extract_pymupdf`.

## 2. Entry Point

- **File:** `server/app/services/evaluation/runner.py`
- **Class:** `EvaluationRunner`
- **Method:** `async def _extract_pymupdf(self, file_path: str) -> Dict[str, Any]`
- **Invocation:** `EvaluationRunner.run_tool(...)` dispatches to `_extract_pymupdf` when `tool_name == "pymupdf"`.

## 3. Tool Dispatch in Runner

```python
    async def _extract_pymupdf(self, file_path: str) -> Dict[str, Any]:
        """Rule-based extraction using pdfplumber (no AI)."""
        import pdfplumber

        tables = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                for raw_table in page.extract_tables() or []:
                    if not raw_table:
                        continue
                    headers = [str(c) if c else "" for c in raw_table[0]]
                    rows = [[str(c) if c else "" for c in row] for row in raw_table[1:]]
                    tables.append({"headers": headers, "rows": rows})
        return {"tables": tables}
```

Dispatch registration (same file):

```python
    _DISPATCH = {
        "pymupdf": "_extract_pymupdf",
        ...
    }
```

## 4. Input Format

- **How passed:** Local filesystem path (`file_path`) to the PDF; same path as `Document.file_path` (e.g. `data/pdfs/{uuid}.pdf`).
- **Preprocessing:** None inside `_extract_pymupdf`. `pdfplumber.open(file_path)` reads the file directly.
- **Limits:** No maximum page count, file size, or byte limit in this method. Every page is processed sequentially.

## 5. Output Format

- **Before normalisation:** `dict` with key `"tables"` → `list` of dicts, each:
  - `"headers"`: `list[str]` — first row of each `pdfplumber` table, cells coerced with `str(c) if c else ""`.
  - `"rows"`: `list[list[str]]` — remaining rows, same cell coercion.
- **Structure:** List of tables (one entry per `extract_tables()` result per page). No `confidence`, `page_number`, or metadata fields at this stage.

## 6. Normalisation

Shared helper in `server/app/services/evaluation/runner.py`:

```python
def _normalise_tables(raw: Any) -> List[Dict[str, Any]]:
    """Convert varied service outputs into a list of {headers, rows} dicts."""
    tables: List[Dict[str, Any]] = []

    if isinstance(raw, dict):
        raw_tables = raw.get("tables") or []
    elif isinstance(raw, list):
        raw_tables = raw
    elif hasattr(raw, "tables"):
        raw_tables = raw.tables or []
    else:
        return tables

    for t in raw_tables:
        if isinstance(t, dict):
            headers = t.get("headers") or t.get("header") or []
            rows = t.get("rows") or t.get("data") or []
            tables.append({"headers": headers, "rows": rows})
    return tables
```

For `pymupdf`, `raw` is already `{"tables": [...]}` with `headers`/`rows`; normalisation passes them through unchanged.

**Metrics note:** `compute_cell_f1` in `server/app/services/evaluation/metrics.py` takes **rows only** (`extracted_rows`, `ground_truth_rows`); headers are **not** included in the cell multiset. TEDS/GriTS use `{"headers", "rows"}` via `evaluation.py`.

## 7. Prompts (LLM tools only — skip for rule-based/CV tools)

Not applicable — rule-based `pdfplumber` extraction; no LLM prompts.

## 8. Configuration

- No tool-specific env vars for `pymupdf` in `runner.py`.
- Dependency: `pdfplumber` (see `server/requirements.txt`).
- No timeouts or retries in `_extract_pymupdf`.

## 9. Error Handling

- **`_extract_pymupdf`:** No `try`/`except`; failures (missing file, corrupt PDF, `pdfplumber` errors) propagate to `EvaluationRunner.run_tool`, which catches `BaseException`, calls `_classify_exception(exc)`, and persists an `ExtractionResult` with `error_message`, `failure_reason`, `is_transient_failure`.
- **Runner:** See section 11.

## 10. Cost Calculation

Exact file `server/app/services/evaluation/cost_calculator.py`:

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

For `pymupdf`: `PRICE_PER_PAGE["pymupdf"]` is **0.0** → `calculate_cost` returns **0.0** (no token branch).

## 11. Failure Classification

**`_classify_exception`** (`server/app/services/evaluation/runner.py`):

```python
def _classify_exception(exc: BaseException) -> Tuple[str, bool, str]:
    """
    Map exception to (failure_reason, is_transient_failure, error_message).
    """
    msg = str(exc)

    try:
        import openai

        if isinstance(exc, openai.RateLimitError):
            return "rate_limit", True, msg
        if isinstance(exc, openai.APIConnectionError):
            return "server_down", True, msg
    except ImportError:
        pass

    try:
        import anthropic

        if isinstance(exc, anthropic.RateLimitError):
            return "rate_limit", True, msg
        if isinstance(exc, anthropic.APIConnectionError):
            return "server_down", True, msg
        if isinstance(exc, anthropic.APIStatusError):
            code = getattr(exc, "status_code", None)
            if code in (429, 529, 503):
                return "rate_limit", True, msg
    except ImportError:
        pass

    try:
        import mistralai

        rl = getattr(mistralai, "RateLimitError", None)
        if rl is not None and isinstance(exc, rl):
            return "rate_limit", True, msg
    except ImportError:
        pass

    try:
        import requests

        if isinstance(exc, requests.exceptions.ConnectionError):
            return "server_down", True, msg
    except ImportError:
        pass

    if isinstance(exc, (asyncio.TimeoutError, concurrent.futures.TimeoutError)):
        return "timeout", True, msg

    return "api_error", False, msg
```

**Inside `run_tool` after extraction:**

- If `raw` is a `dict` and `raw.get("success") is False`: substring checks on `error_msg` for `rate limit`/`429`/`529`/`overloaded` → `failure_reason="rate_limit"`, `is_transient_failure=True`; `timeout` → `timeout`, transient; `connection`/`connect` → `server_down`, transient; else `api_error`, not transient.
- If an exception was raised: `failure_reason, is_transient, error_msg` from `_classify_exception`.
- If `_empty_extracted_rows(tables)`:
  - If `tool_name in ("pymupdf", "docling")` **and** `not is_digital` (from `Document.is_digital`, defaulting to `True` if null): `failure_reason="tool_limitation"`, `is_transient_failure=False`, `error_message="No tables extracted"`.
  - Else: `failure_reason="empty_output"`, `is_transient_failure=False`, same message.

## 12. Known Issues and Gaps

- **Naming mismatch:** UI label "PyMuPDF" / tool id `pymupdf` does not match implementation (`pdfplumber`).
- **Scanned PDFs:** Empty extraction for non-digital PDFs is classified as `tool_limitation` (not `empty_output`) for `pymupdf` and `docling` only.
- **No page attribution:** Output tables are not tagged with `page_number` in `_extract_pymupdf`.
- **DB comment:** `models.py` mentions `aws_textract` in a comment alongside other tools; `aws_textract` is not in `EvaluationRunner._DISPATCH`.

## 13. Wiring to Frontend

- **ToolSelector:** Yes — `ALL_TOOLS` includes `{ id: 'pymupdf', label: 'PyMuPDF', ... }` in `client/src/app/components/evaluation/ToolSelector.tsx`.
- **API tool string:** `"pymupdf"`.
- **Match:** Matches `runner.py` `_DISPATCH` key and `server/app/api/evaluation.py` `ALL_TOOLS`.

## 14. End-to-End Trace

Example: `POST /api/evaluate/{doc_id}` with `tools` including `pymupdf`, 3-page **digital** PDF, ground truth present, extraction succeeds with at least one non-empty row.

1. **HTTP:** FastAPI routes to `evaluate_document` in `server/app/api/evaluation.py`.
2. **Document load:** `select(Document)` by `doc_id`; 404 if missing.
3. **Ground truth:** `select(GroundTruthTable)` for `document_id`, ordered by `table_index`; 422 if none.
4. **Tools:** `_resolve_tools` ensures `pymupdf` is valid.
5. **Runner:** `EvaluationRunner()` instantiated; `await runner.run_tool("pymupdf", doc.file_path, doc.id, db)`.
6. **`run_tool`:** Looks up `_DISPATCH["pymupdf"]` → `_extract_pymupdf`; records `start = time.perf_counter()`.
7. **Extract:** `await _extract_pymupdf(file_path)` opens PDF with `pdfplumber`, builds `{"tables": [...]}`.
8. **Normalise:** `_normalise_tables(raw)` produces list of `{headers, rows}`.
9. **Document metadata:** `select(Document)` for `page_count` / `is_digital`; `calculate_cost("pymupdf", page_count)` → **0.0**.
10. **Persist:** For each table index, `ExtractionResult` inserted (`extracted_headers`, `extracted_rows`, `processing_time_ms` on first row only, `cost_usd` on first row only, `raw_output` JSON snapshot on first row), `db.add` + `flush` + `commit` per row (`_persist_and_commit`).
11. **Back in `evaluate_document`:** For each `ExtractionResult`, finds matching `GroundTruthTable` by `table_index`; if match and no `error_message`, computes `compute_cell_f1(er.extracted_rows or [], gt_match.rows or [])`, `compute_teds`, `compute_grits`; builds `EvaluationScore`, `db.add(score)`.
12. **Final commit:** `await db.commit()` after the tool loop completes.
13. **Response:** JSON with per-tool summary in `results`.
