"""
Evaluation metrics for table extraction quality.

Implements:
- Cell-level precision / recall / F1
- TEDS (Tree Edit Distance based Similarity)
- GriTS (Grid Table Similarity) — topology, content, location
"""

import re
import logging
from typing import List, Any, Dict
from collections import Counter

import editdistance

logger = logging.getLogger(__name__)


def normalise_cell(value: Any) -> str:
    """Canonical form for cell comparison: lowercase, strip whitespace,
    remove currency symbols and thousand separators."""
    s = str(value) if value is not None else ""
    s = s.strip().lower()
    s = re.sub(r"[$€£¥₹]", "", s)
    s = re.sub(r"(?<=\d),(?=\d{3})", "", s)  # 1,234 → 1234
    s = re.sub(r"\s+", " ", s)
    return s


# ---------------------------------------------------------------------------
# Cell-level F1
# ---------------------------------------------------------------------------

def compute_cell_f1(
    extracted_rows: List[List[Any]],
    ground_truth_rows: List[List[Any]],
) -> Dict[str, float]:
    """Compute precision, recall, F1 based on multiset cell matching."""
    pred_cells = Counter(normalise_cell(c) for row in extracted_rows for c in row)
    gt_cells = Counter(normalise_cell(c) for row in ground_truth_rows for c in row)

    tp = sum((pred_cells & gt_cells).values())
    fp = sum((pred_cells - gt_cells).values())
    fn = sum((gt_cells - pred_cells).values())

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    return {"precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4)}


# ---------------------------------------------------------------------------
# TEDS  (Tree Edit Distance based Similarity)
# ---------------------------------------------------------------------------

def _table_to_html(table: Dict[str, Any]) -> str:
    """Convert {"headers": [...], "rows": [[...], ...]} to a minimal HTML table."""
    parts = ["<table>"]
    headers = table.get("headers") or []
    rows = table.get("rows") or []

    if headers:
        parts.append("<tr>")
        for h in headers:
            parts.append(f"<td>{normalise_cell(h)}</td>")
        parts.append("</tr>")

    for row in rows:
        parts.append("<tr>")
        for cell in row:
            parts.append(f"<td>{normalise_cell(cell)}</td>")
        parts.append("</tr>")

    parts.append("</table>")
    return "".join(parts)


def _tokenise_tree(html: str) -> List[str]:
    """Flatten an HTML table into a sequence of tags + text tokens for edit distance."""
    tokens: List[str] = []
    i = 0
    while i < len(html):
        if html[i] == "<":
            end = html.index(">", i)
            tokens.append(html[i : end + 1])
            i = end + 1
        else:
            end = html.find("<", i)
            if end == -1:
                end = len(html)
            text = html[i:end].strip()
            if text:
                tokens.append(text)
            i = end
    return tokens


def compute_teds(
    extracted_table: Dict[str, Any],
    ground_truth_table: Dict[str, Any],
) -> float:
    """TEDS = 1 - edit_distance(pred_tree, gt_tree) / max(|pred|, |gt|)."""
    pred_html = _table_to_html(extracted_table)
    gt_html = _table_to_html(ground_truth_table)

    pred_tokens = _tokenise_tree(pred_html)
    gt_tokens = _tokenise_tree(gt_html)

    if not pred_tokens and not gt_tokens:
        return 1.0

    dist = editdistance.eval(pred_tokens, gt_tokens)
    max_len = max(len(pred_tokens), len(gt_tokens))
    return round(1.0 - dist / max_len, 4) if max_len else 1.0


# ---------------------------------------------------------------------------
# GriTS  (Grid Table Similarity)
# ---------------------------------------------------------------------------

def _build_grid(table: Dict[str, Any]) -> List[List[str]]:
    """Build a 2-D grid (list of rows, each a list of normalised cell strings)
    with headers as the first row."""
    headers = [normalise_cell(h) for h in (table.get("headers") or [])]
    rows = [[normalise_cell(c) for c in row] for row in (table.get("rows") or [])]
    grid = []
    if headers:
        grid.append(headers)
    grid.extend(rows)
    return grid


def _row_sim(row_a: List[str], row_b: List[str]) -> float:
    """Jaccard-like similarity between two rows."""
    if not row_a and not row_b:
        return 1.0
    set_a = Counter(row_a)
    set_b = Counter(row_b)
    inter = sum((set_a & set_b).values())
    union = sum((set_a | set_b).values())
    return inter / union if union else 0.0


def _col_sim(grid_a: List[List[str]], grid_b: List[List[str]], col_a: int, col_b: int) -> float:
    """Similarity of two columns extracted from their respective grids."""
    vals_a = [row[col_a] for row in grid_a if col_a < len(row)]
    vals_b = [row[col_b] for row in grid_b if col_b < len(row)]
    if not vals_a and not vals_b:
        return 1.0
    set_a = Counter(vals_a)
    set_b = Counter(vals_b)
    inter = sum((set_a & set_b).values())
    union = sum((set_a | set_b).values())
    return inter / union if union else 0.0


def _best_match_score(
    items_a: int,
    items_b: int,
    sim_fn,
) -> float:
    """Greedy best-match: for each item in A find the best match in B,
    return average of best similarities."""
    if items_a == 0 and items_b == 0:
        return 1.0
    if items_a == 0 or items_b == 0:
        return 0.0

    total = 0.0
    for i in range(items_a):
        best = max(sim_fn(i, j) for j in range(items_b))
        total += best
    return total / items_a


def compute_grits(
    extracted_table: Dict[str, Any],
    ground_truth_table: Dict[str, Any],
) -> Dict[str, float]:
    """Compute GriTS topology, content, and location scores."""
    pred_grid = _build_grid(extracted_table)
    gt_grid = _build_grid(ground_truth_table)

    n_pred_rows = len(pred_grid)
    n_gt_rows = len(gt_grid)
    n_pred_cols = max((len(r) for r in pred_grid), default=0)
    n_gt_cols = max((len(r) for r in gt_grid), default=0)

    # --- Topology: do the grids have matching shape? ---
    if n_pred_rows == 0 and n_gt_rows == 0:
        top = 1.0
    elif n_pred_rows == 0 or n_gt_rows == 0:
        top = 0.0
    else:
        row_ratio = min(n_pred_rows, n_gt_rows) / max(n_pred_rows, n_gt_rows)
        col_ratio = min(n_pred_cols, n_gt_cols) / max(n_pred_cols, n_gt_cols) if max(n_pred_cols, n_gt_cols) else 1.0
        top = row_ratio * col_ratio

    # --- Content: best-match row similarity (Jaccard on cell multisets) ---
    def row_content_sim(i, j):
        return _row_sim(
            pred_grid[i] if i < n_pred_rows else [],
            gt_grid[j] if j < n_gt_rows else [],
        )

    con = _best_match_score(n_pred_rows, n_gt_rows, row_content_sim)

    # --- Location: best-match column similarity ---
    def col_loc_sim(i, j):
        return _col_sim(pred_grid, gt_grid, i, j)

    loc = _best_match_score(n_pred_cols, n_gt_cols, col_loc_sim)

    return {
        "top": round(top, 4),
        "con": round(con, 4),
        "loc": round(loc, 4),
    }
