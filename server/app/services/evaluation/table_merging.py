"""
Tool-agnostic merge of neighbouring tables that share the same logical headers.

Used by EvaluationRunner after normalisation so every extractor shares one policy.
"""

from __future__ import annotations

from typing import Any, Dict, List

TableDict = Dict[str, Any]


def _normalised_headers(headers: Any) -> List[str]:
    return [str(h).strip().lower() for h in (headers or [])]


def _headers_all_empty(norm: List[str]) -> bool:
    return not norm or all(not h for h in norm)


def _headers_match(t1: TableDict, t2: TableDict) -> bool:
    h1 = _normalised_headers(t1.get("headers") or t1.get("header"))
    h2 = _normalised_headers(t2.get("headers") or t2.get("header"))
    if _headers_all_empty(h1) or _headers_all_empty(h2):
        return False
    return h1 == h2 and len(h1) == len(h2)


def _row_count(t: TableDict) -> int:
    rows = t.get("rows") or t.get("data") or []
    return len(rows) if isinstance(rows, list) else 0


def _adjacent(prev: TableDict, curr: TableDict) -> bool:
    """Contiguous in reading order; cross-page only when both have explicit page_number."""
    pn_p = prev.get("page_number", 0)
    pn_c = curr.get("page_number", 0)
    ti_p = prev.get("table_index", 0)
    ti_c = curr.get("table_index", 0)
    exp_p = "page_number" in prev
    exp_c = "page_number" in curr

    if pn_p == pn_c:
        return ti_c == ti_p + 1

    if exp_p and exp_c and pn_c == pn_p + 1 and ti_c in (0, 1):
        return True
    return False


def _can_extend_group(first: TableDict, last: TableDict, cand: TableDict) -> bool:
    if _row_count(last) == 0 or _row_count(cand) == 0:
        return False
    if not _headers_match(first, cand):
        return False
    h0 = first.get("headers") or first.get("header") or []
    h1 = cand.get("headers") or cand.get("header") or []
    if len(h0) != len(h1):
        return False
    return _adjacent(last, cand)


def _merge_group(group: List[TableDict]) -> TableDict:
    base = group[0]
    headers = list(base.get("headers") or base.get("header") or [])
    merged_rows: List[Any] = []
    for t in group:
        rows = t.get("rows") or t.get("data") or []
        if isinstance(rows, list):
            merged_rows.extend(rows)

    merged: TableDict = dict(base)
    merged["headers"] = headers
    merged["rows"] = merged_rows
    merged["row_count"] = len(merged_rows)
    merged["col_count"] = len(headers)

    pages = [t.get("page_number", 0) for t in group]
    lo, hi = min(pages), max(pages)
    merge_info = {
        "merged_from": len(group),
        "merged_page_range": (lo, hi),
    }
    meta = dict(merged.get("metadata") or {})
    meta["merge_info"] = merge_info
    merged["metadata"] = meta
    merged["merged_from"] = len(group)
    merged["merged_page_range"] = (lo, hi)
    return merged


def merge_similar_tables_global(tables: List[TableDict]) -> List[TableDict]:
    """
    Merge tables that appear to be fragments of the same logical table.

    Strategy (tool-agnostic):

    1. Sort by (page_number, table_index); missing keys use 0.
    2. Group consecutive tables with identical normalised headers, same column
       count, all non-empty headers, each with at least one row, and adjacent
       in reading order (same page + table_index+1, or explicit consecutive
       pages with table_index in {0,1}).
    3. Groups of one table are unchanged. Larger groups are merged: rows
       concatenated, metadata.merge_info and top-level merged_from /
       merged_page_range set.
    """
    if not tables:
        return []

    sorted_tables = sorted(
        tables,
        key=lambda t: (t.get("page_number", 0), t.get("table_index", 0)),
    )

    out: List[TableDict] = []
    i = 0
    n = len(sorted_tables)
    while i < n:
        group = [sorted_tables[i]]
        j = i + 1
        while j < n and _can_extend_group(group[0], group[-1], sorted_tables[j]):
            group.append(sorted_tables[j])
            j += 1

        if len(group) == 1:
            out.append(group[0])
        else:
            out.append(_merge_group(group))
        i = j

    return out
