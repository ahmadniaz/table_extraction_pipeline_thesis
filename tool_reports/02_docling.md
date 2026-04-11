# Tool Report: Docling

## 1. Implementation Status

**FULLY IMPLEMENTED** (in the sense that it is wired into `EvaluationRunner`, runs `ExtractionPipeline.extract_tables`, and persists results). The pipeline is large and may return partial results with errors recorded on the `TableExtractionResult` object (see section 5).

## 2. Entry Point

- **File:** `server/app/services/evaluation/runner.py`
- **Class:** `EvaluationRunner`
- **Method:** `async def _extract_docling(self, file_path: str) -> Any`
- **Pipeline class:** `ExtractionPipeline` from `server/app/services/docling/pipeline.py`, method `async def extract_tables(self, document_path: Union[str, Path], options: Optional[ExtractionOptions] = None) -> TableExtractionResult`
- **Lazy init:** `_get_docling()` constructs `ExtractionPipeline(Config())` with `Config` from `server/app/services/docling/utils/config.py`.

## 3. Tool Dispatch in Runner

```python
    async def _extract_docling(self, file_path: str) -> Any:
        pipeline = self._get_docling()
        return await pipeline.extract_tables(file_path)
```

Lazy initialisation:

```python
    def _get_docling(self):
        if "docling" not in self._services:
            from app.services.docling.pipeline import ExtractionPipeline
            from app.services.docling.utils.config import Config

            self._services["docling"] = ExtractionPipeline(Config())
        return self._services["docling"]
```

## 4. Input Format

- **How passed:** Local filesystem path as `str` (same as `Document.file_path`).
- **Preprocessing:** Handled inside `ExtractionPipeline.extract_tables`: document processing (`_process_document`), table detection/extraction, optional multipage linking, financial processing, merging, post-processing, validation. Exact behaviour depends on `ExtractionOptions` defaults when `options` is `None`.
- **Limits:** No explicit page cap in `runner.py`; internal pipeline and Docling/HF models impose practical limits. Not enumerated in `runner.py`.

## 5. Output Format

- **Type returned to runner:** `TableExtractionResult` dataclass (`server/app/services/docling/pipeline.py`) with fields including:
  - `tables: List[Dict[str, Any]]` — post-processed table dicts (see pipeline stages); typically include `headers`, `rows`, and often `cells`, `metadata`, `quality_score`, `structure`, etc. depending on pipeline path.
  - `metadata`, `confidence_scores`, `processing_time`, `warnings`, `errors`, `document_path`
- **`to_dict()`** exposes the same as a JSON-serialisable dict.
- **On exception inside `extract_tables`:** The `except` path appends to `result.errors`, sets `processing_time`, and **returns `result`** (may have empty `tables`).

`_json_safe` in the runner serialises the dataclass via `model_dump` if available, else best-effort.

## 6. Normalisation

`EvaluationRunner._normalise_tables` handles objects with `.tables`:

```python
    elif hasattr(raw, "tables"):
        raw_tables = raw.tables or []
```

Each dict `t` is reduced to:

```python
            headers = t.get("headers") or t.get("header") or []
            rows = t.get("rows") or t.get("data") or []
            tables.append({"headers": headers, "rows": rows})
```

Extra fields (`cells`, `confidence`, etc.) are **dropped** for DB storage and metrics inputs (except what metrics read from `extracted_headers`/`extracted_rows`).

## 7. Prompts (LLM tools only — skip for rule-based/CV tools)

Not applicable to the Docling path as invoked by the runner — local ML/OCR pipeline, not an LLM chat prompt in `runner.py`.

## 8. Configuration

- **Runner:** No Docling-specific environment variables in `runner.py`.
- **Pipeline:** `Config` from `app.services.docling.utils.config` (instantiated with `Config()`). For full parameter list, see that module and `ExtractionOptions` in `pipeline.py` (defaults when `options is None`).
- **Timeouts/retries:** Not set in `runner.py` for Docling.

## 9. Error Handling

- **Pipeline:** Internal `try`/`except` in `extract_tables` catches failures, logs, fills `result.errors`, returns `TableExtractionResult` without re-raising.
- **Runner:** If `extract_tables` returns a result with empty tables, `_empty_extracted_rows` may trigger `empty_output` or `tool_limitation` (with `docling` + non-digital PDF) as for `pymupdf`. If an exception propagates (e.g. from initialisation), `run_tool` catches `BaseException` and classifies via `_classify_exception`.

## 10. Cost Calculation

Same module for all tools — verbatim `server/app/services/evaluation/cost_calculator.py`:

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

`docling` uses `PRICE_PER_PAGE["docling"] = 0.0` → **0.0** USD.

## 11. Failure Classification

Same as all tools in `EvaluationRunner.run_tool` (`server/app/services/evaluation/runner.py`):

- **`_classify_exception`:** Maps OpenAI/Anthropic/Mistral rate limits, connection errors, `requests.ConnectionError`, and `asyncio`/`concurrent.futures` timeouts to transient reasons; default `("api_error", False, msg)`.
- **`success is False` dict:** String heuristics on error message for rate limit / timeout / connection.
- **Empty tables:** For `docling` with `not is_digital` → `failure_reason="tool_limitation"`; otherwise `failure_reason="empty_output"`.

## 12. Known Issues and Gaps

- **Silent pipeline errors:** `extract_tables` may return a result with `errors` populated but **no exception**; runner still normalises `tables` — may look like `empty_output` if `tables` empty.
- **Field stripping:** Rich Docling metadata is not stored in `ExtractionResult` except via `raw_output` snapshot on the first table row.
- **Reproducibility:** Pipeline is highly configurable and complex; thesis-level reproducibility may require pinning `ExtractionOptions` and model versions (not enforced in `runner.py`).

## 13. Wiring to Frontend

- **ToolSelector:** Yes — `id: 'docling'`, label `'Docling'`.
- **API / runner key:** `"docling"`.
- **Match:** Consistent across `ToolSelector.tsx`, `evaluation.py` `ALL_TOOLS`, and `runner.py` `_DISPATCH`.

## 14. End-to-End Trace

Same HTTP and DB flow as PyMuPDF (see `01_pymupdf.md` §14), except:

5. `await runner.run_tool("docling", doc.file_path, doc.id, db)`.
6. `_extract_docling` → `ExtractionPipeline.extract_tables(file_path)`.
7. Returns `TableExtractionResult`; `_json_safe(raw)` for `raw_output`; `_normalise_tables` uses `raw.tables`.
8–13. Identical persistence and scoring pattern for successful non-empty normalised tables.
