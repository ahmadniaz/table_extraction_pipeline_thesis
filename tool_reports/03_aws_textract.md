# Tool Report: AWS Textract

## 1. Implementation Status

**NOT IMPLEMENTED** in the active evaluation pipeline. There is **no** `aws_textract` (or `textract`) entry in `EvaluationRunner._DISPATCH`, no `_extract_aws_textract` method, and `aws_textract` is **not** listed in `server/app/api/evaluation.py` `ALL_TOOLS`.

## 2. Entry Point

**None** for thesis evaluation. The `EvaluationRunner` never calls AWS Textract.

A **cost placeholder** exists only in `cost_calculator.py` (`PRICE_PER_PAGE["aws_textract"] = 0.015`). No code path invokes `calculate_cost("aws_textract", ...)`.

## 3. Tool Dispatch in Runner

No dispatch block exists for AWS Textract. The only related mention in active evaluation code is the **comment** on `ExtractionResult.tool_name` in `server/app/db/models.py` listing `'aws_textract'` as an allowed-style name — this does **not** register or run the tool.

Relevant `_DISPATCH` in `runner.py` (excerpt — **does not include aws_textract**):

```python
    _DISPATCH = {
        "pymupdf": "_extract_pymupdf",
        "docling": "_extract_docling",
        "google_docai": "_extract_google_docai",
        "gpt5": "_extract_gpt5",
        "claude_sonnet": "_extract_claude",
        "mistral": "_extract_mistral",
    }
```

## 4. Input Format

N/A — no integrated extractor.

## 5. Output Format

N/A — no integrated extractor.

## 6. Normalisation

N/A — no raw output from Textract in this codebase path. Generic normalisation remains `_normalise_tables` in `runner.py` for other tools.

## 7. Prompts (LLM tools only — skip for rule-based/CV tools)

N/A.

## 8. Configuration

- **`server/.env` / `PROJECT_CONTEXT.md`:** `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `S3_BUCKET_NAME` are documented as legacy/inactive for the thesis app.
- **No Textract-specific** processor ID, feature types, or boto3 client code was found under `server/app/services/evaluation` or wired to `EvaluationRunner`.

## 9. Error Handling

N/A for Textract specifically. If a client sent `tool_name: "aws_textract"`, `run_tool` would hit the **unknown tool** branch:

```python
        if not method_name:
            er = ExtractionResult(
                ...
                error_message=f"Unknown tool: {tool_name}",
                ...
                failure_reason="api_error",
                is_transient_failure=False,
                ...
            )
```

(Current API layer rejects unknown tools before `run_tool` via `_resolve_tools` / `ALL_TOOLS`.)

## 10. Cost Calculation

Full `server/app/services/evaluation/cost_calculator.py` (includes unused `aws_textract` rate):

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

**Hardcoded rate for `aws_textract`:** **USD 0.015 per page** in `PRICE_PER_PAGE` — **never applied** because no caller uses `tool_name="aws_textract"`.

## 11. Failure Classification

No tool-specific logic. Unknown tool handling sets `failure_reason="api_error"`, `is_transient_failure=False` (see §9).

## 12. Known Issues and Gaps

- **Dead cost entry:** `aws_textract` in `PRICE_PER_PAGE` suggests planned support; implementation is absent from `runner.py` and the frontend tool list.
- **Schema comment vs reality:** `models.py` comment lists `aws_textract`; active `ALL_TOOLS` does not.

## 13. Wiring to Frontend

- **ToolSelector:** **No** — `ALL_TOOLS` in `ToolSelector.tsx` has six entries; `aws_textract` is not included.
- **API:** **No** — `evaluation.py` `ALL_TOOLS` has six strings; `aws_textract` is absent.
- **Mismatch:** N/A (tool not exposed).

## 14. End-to-End Trace

**Does not occur** for AWS Textract in the current codebase: batch/single evaluation never selects this tool, and the runner cannot dispatch it.

To support it, a new `_extract_aws_textract`, `_DISPATCH` entry, `ALL_TOOLS` + frontend checkbox, env/credential wiring, and normalisation from Textract JSON to `{headers, rows}` would be required — **none of this exists** in the audited paths.
