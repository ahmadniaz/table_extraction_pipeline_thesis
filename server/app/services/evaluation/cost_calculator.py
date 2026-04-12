"""
Cost estimation for each extraction tool.

Rates are hardcoded snapshots at the time of this study (April 2026).
Local/open-source tools have zero marginal cost.
"""

PRICE_PER_PAGE = {
    "pymupdf": 0.0,
    "docling": 0.0,
    "aws_textract": 0.015,
    "google_docai": 0.01,
    "gpt5": 0.0,       # estimated from tokens below
    "claude_sonnet": 0.0,  # estimated from tokens below
    "mistral": 0.0,     # estimated from tokens below
}

# Per-token pricing (USD) — input / output
_TOKEN_PRICING = {
    "gpt5": {"input": 2.00 / 1_000_000, "output": 8.00 / 1_000_000},
    "claude_sonnet": {"input": 3.00 / 1_000_000, "output": 15.00 / 1_000_000},
    "mistral": {"input": 0.5 / 1_000_000, "output": 1.5 / 1_000_000},
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
