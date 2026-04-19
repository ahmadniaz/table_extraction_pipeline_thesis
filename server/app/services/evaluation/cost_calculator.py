"""
Cost estimation for each extraction tool.

Rates are hardcoded snapshots — April 2026.
Mistral uses a two-component cost:
  (a) OCR: mistral-ocr-latest billed per page ($0.002/page)
  (b) Structured extraction: pixtral-large-2411 billed per token
      input $2.00/M, output $6.00/M (prices in USD; Mistral invoices in EUR)
If Mistral changes pricing, update _TOKEN_PRICING["mistral"] and
PRICE_PER_PAGE["mistral"] here AND re-run recalculate_mistral_costs.py.

Local/open-source tools have zero marginal cost.
"""

PRICE_PER_PAGE = {
    "pymupdf": 0.0,
    "docling": 0.0,
    "aws_textract": 0.015,
    "google_docai": 0.01,
    "gpt5": 0.0,       # estimated from tokens below
    "claude_sonnet": 0.0,  # estimated from tokens below
    # mistral-ocr-latest / mistral-ocr-2512 ($0.002 per page)
    "mistral": 0.002,     # mistral-ocr-latest = $2.00 per 1000 pages
}

# Per-token pricing (USD) — input / output
_TOKEN_PRICING = {
    "gpt5": {"input": 2.00 / 1_000_000, "output": 8.00 / 1_000_000},
    "claude_sonnet": {"input": 3.00 / 1_000_000, "output": 15.00 / 1_000_000},
    # pixtral-large-2411 (chat/structured extraction, Mistral API EUR-billed)
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
