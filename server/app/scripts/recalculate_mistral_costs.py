"""
Recalculate cost_usd for all Mistral extraction rows using current pricing in cost_calculator.

Run from the ``server`` directory:
    python -m app.scripts.recalculate_mistral_costs
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any

from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.models import Document, ExtractionResult
from app.services.evaluation.cost_calculator import calculate_cost


def _usage_tokens_from_raw(raw_output: Any) -> tuple[int | None, int | None]:
    """
    Read top-level ``usage`` with ``input_tokens`` / ``output_tokens``.
    Missing, null, or zero counts are returned as None so calculate_cost uses the same
    fallbacks as the evaluation runner.
    """
    if not raw_output or not isinstance(raw_output, dict):
        return None, None
    usage = raw_output.get("usage")
    if not isinstance(usage, dict):
        return None, None

    def _one(key: str) -> int | None:
        v = usage.get(key)
        if v is None:
            return None
        try:
            n = int(v)
        except (TypeError, ValueError):
            return None
        return None if n == 0 else n

    return _one("input_tokens"), _one("output_tokens")


async def main() -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ExtractionResult, Document)
            .join(Document, ExtractionResult.document_id == Document.id)
            .where(ExtractionResult.tool_name == "mistral")
            .order_by(ExtractionResult.document_id, ExtractionResult.table_index)
        )
        pairs = result.all()

        by_doc: dict[Any, list[tuple[ExtractionResult, Document]]] = defaultdict(list)
        for er, doc in pairs:
            by_doc[er.document_id].append((er, doc))

        sum_old = 0.0
        sum_new = 0.0
        total_rows = 0

        for _doc_id, group in by_doc.items():
            _, doc0 = group[0]
            page_count = doc0.page_count or 1

            raw_output = None
            for er, _d in group:
                if er.raw_output:
                    raw_output = er.raw_output
                    break

            input_tokens, output_tokens = _usage_tokens_from_raw(raw_output)
            run_cost = calculate_cost("mistral", page_count, input_tokens, output_tokens)

            for er, _doc in group:
                total_rows += 1
                sum_old += float(er.cost_usd or 0)
                # Match EvaluationRunner: full run cost on table_index 0 only; other tables store 0.
                if er.table_index == 0:
                    er.cost_usd = run_cost
                    sum_new += run_cost
                else:
                    er.cost_usd = 0
                    sum_new += 0.0

        await session.commit()

    delta = sum_new - sum_old
    print("Mistral cost_usd recalculation complete.")
    print(f"  Total rows updated: {total_rows}")
    print(f"  Sum of old cost_usd: {sum_old:.6f}")
    print(f"  Sum of new cost_usd: {sum_new:.6f}")
    print(f"  Delta (new - old):   {delta:+.6f}")


if __name__ == "__main__":
    asyncio.run(main())
