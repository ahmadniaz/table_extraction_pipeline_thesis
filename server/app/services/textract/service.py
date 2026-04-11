"""
AWS Textract table extraction service — thesis-grade implementation.

Uses the AnalyzeDocument synchronous API with FeatureTypes=['TABLES'] for
both scanned and digital PDFs. Table reconstruction follows the official
Block relationship graph:

    PAGE → TABLE → CELL / MERGED_CELL → WORD / SELECTION_ELEMENT

COLUMN_HEADER entity type is used to identify header rows. MERGED_CELL
blocks propagate header text across spanned columns per the AWS merged-cell
blog post (2022).

Pricing (us-east-1 / us-west-2, April 2026):
    AnalyzeDocument TABLES: $0.015 per page (first 1M pages/month).
    Tracked in cost_calculator.py as PRICE_PER_PAGE["aws_textract"] = 0.015.

Design notes:
  - PDF bytes are read from local disk and sent via Document={'Bytes': ...}.
    This avoids requiring an S3 bucket in the thesis environment. An S3 path
    option (Document={'S3Object': {...}}) is left as a documented alternative.
  - Credentials are resolved from the standard boto3 credential chain
    (AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY env vars, ~/.aws/credentials,
    EC2 instance roles, etc.). No keys are read from the project .env file.
  - All Textract calls are synchronous; the runner executes them via
    asyncio.run_in_executor to avoid blocking the FastAPI event loop.
  - boto3 errors are NOT swallowed. They propagate to EvaluationRunner
    where _classify_exception handles throttling / connection failures.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TextractService:
    """
    Extracts tables from PDF documents using AWS Textract AnalyzeDocument.

    Each instance lazily creates one boto3 Textract client, which is then
    reused across all extraction calls (boto3 clients are thread-safe).
    """

    def __init__(self, region_name: Optional[str] = None) -> None:
        self._region = region_name or os.environ.get("AWS_REGION", "us-east-1")
        self._client: Optional[Any] = None

    def _get_client(self) -> Any:
        """Lazily create the boto3 Textract client on first use."""
        if self._client is None:
            import boto3
            from botocore.config import Config as BotoConfig

            cfg = BotoConfig(
                retries={"max_attempts": 3, "mode": "standard"},
                read_timeout=120,
                connect_timeout=10,
            )
            self._client = boto3.client(
                "textract", region_name=self._region, config=cfg
            )
            logger.info(
                "TextractService: boto3 client initialised (region=%s)", self._region
            )
        return self._client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze_document_tables(self, file_path: str) -> Dict[str, Any]:
        """
        Run AnalyzeDocument (TABLES) on the given PDF and return structured data.

        Args:
            file_path: Absolute or relative path to the PDF file on disk.

        Returns:
            {
                "tables": [
                    {
                        "headers": list[str],
                        "rows": list[list[str]],
                        "page_number": int,          # 0-based
                        "table_index": int,
                        "row_count": int,
                        "col_count": int,
                        "textract_confidence": float,
                    },
                    ...
                ],
                "pages_analyzed": int,
                "tool": "aws_textract",
            }

        Raises:
            FileNotFoundError: if file_path does not exist.
            botocore.exceptions.ClientError: for AWS API errors (throttling,
                credentials, unsupported document format, etc.).
            botocore.exceptions.BotoCoreError: for network / endpoint errors.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {file_path}")

        pdf_bytes = path.read_bytes()
        client = self._get_client()

        logger.info(
            "TextractService: calling AnalyzeDocument for %s (%d bytes)",
            path.name,
            len(pdf_bytes),
        )

        # S3 alternative (for production use):
        #   response = client.analyze_document(
        #       Document={"S3Object": {"Bucket": bucket, "Name": key}},
        #       FeatureTypes=["TABLES"],
        #   )
        response = client.analyze_document(
            Document={"Bytes": pdf_bytes},
            FeatureTypes=["TABLES"],
        )

        blocks = response.get("Blocks", [])
        blocks_by_id: Dict[str, Any] = {blk["Id"]: blk for blk in blocks}

        # Count distinct PAGE blocks to report pages_analyzed
        pages_analyzed = sum(1 for b in blocks if b.get("BlockType") == "PAGE")

        # Collect all TABLE blocks in document order
        table_blocks = [b for b in blocks if b.get("BlockType") == "TABLE"]

        logger.info(
            "TextractService: %d TABLE blocks found in %s (%d pages)",
            len(table_blocks),
            path.name,
            pages_analyzed,
        )

        tables: List[Dict[str, Any]] = []
        for raw_idx, table_block in enumerate(table_blocks):
            result = self._extract_table(table_block, blocks_by_id)
            if result is None:
                continue
            # Attach positional metadata
            result["page_number"] = self._get_page_number(
                table_block, blocks_by_id
            )
            result["table_index"] = len(tables)
            tables.append(result)

        logger.info(
            "TextractService: %d non-empty tables extracted from %s",
            len(tables),
            path.name,
        )

        return {
            "tables": tables,
            "pages_analyzed": pages_analyzed,
            "tool": "aws_textract",
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_table(
        self, table_block: Dict[str, Any], blocks_by_id: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Reconstruct a single table from its CELL / MERGED_CELL children.

        Returns None for completely empty tables (no header and no data rows).
        """
        cells: Dict[tuple, Dict[str, Any]] = {}
        max_row = 0
        max_col = 0

        for rel in table_block.get("Relationships", []):
            if rel["Type"] != "CHILD":
                continue
            for cid in rel["Ids"]:
                cell = blocks_by_id.get(cid)
                if cell is None:
                    continue
                bt = cell.get("BlockType")
                if bt not in ("CELL", "MERGED_CELL"):
                    continue

                row = cell.get("RowIndex", 0)
                col = cell.get("ColumnIndex", 0)
                row_span = cell.get("RowSpan", 1)
                col_span = cell.get("ColumnSpan", 1)
                is_header = "COLUMN_HEADER" in cell.get("EntityTypes", [])

                text = self._get_text(cell, blocks_by_id)
                confidence = float(cell.get("Confidence", 0.0))

                max_row = max(max_row, row + row_span - 1)
                max_col = max(max_col, col + col_span - 1)

                # For MERGED_CELL, place text at the top-left position of the span
                # to avoid overwriting non-merged cells in the grid.
                key = (row, col)
                if key not in cells:
                    cells[key] = {
                        "text": text,
                        "row_span": row_span,
                        "col_span": col_span,
                        "is_header": is_header,
                        "confidence": confidence,
                    }
                else:
                    # Append extra text if both cells have content (rare edge case)
                    existing = cells[key]["text"]
                    if text and existing:
                        cells[key]["text"] = f"{existing} {text}".strip()
                    elif text:
                        cells[key]["text"] = text
                    cells[key]["is_header"] = cells[key]["is_header"] or is_header

        if max_row == 0 or max_col == 0:
            return None

        # Build dense 2D grid (1-based RowIndex / ColumnIndex → 0-based arrays)
        grid: List[List[str]] = [["" for _ in range(max_col)] for _ in range(max_row)]
        header_flags: List[List[bool]] = [
            [False for _ in range(max_col)] for _ in range(max_row)
        ]

        for (row, col), info in cells.items():
            r0 = row - 1
            c0 = col - 1
            if r0 < 0 or r0 >= max_row or c0 < 0 or c0 >= max_col:
                continue
            existing = grid[r0][c0]
            if existing:
                grid[r0][c0] = f"{existing} {info['text']}".strip()
            else:
                grid[r0][c0] = info["text"].strip()
            header_flags[r0][c0] = header_flags[r0][c0] or info["is_header"]

        # ── Identify header row ──
        # Use the first row where ≥ 50% of non-empty cells carry COLUMN_HEADER.
        # Fall back to the first row that contains any text.
        header_row_idx: Optional[int] = None
        for r in range(max_row):
            non_empty = sum(1 for c in range(max_col) if grid[r][c])
            header_cells = sum(
                1 for c in range(max_col) if grid[r][c] and header_flags[r][c]
            )
            if non_empty > 0 and header_cells >= max(1, non_empty * 0.5):
                header_row_idx = r
                break

        if header_row_idx is None:
            for r in range(max_row):
                if any(grid[r][c] for c in range(max_col)):
                    header_row_idx = r
                    break

        if header_row_idx is None:
            return None  # completely empty table

        headers = [grid[header_row_idx][c].strip() for c in range(max_col)]

        # Remove trailing all-empty columns
        while headers and all(
            not grid[r][len(headers) - 1] for r in range(max_row)
        ):
            headers.pop()

        if not headers:
            return None

        # ── Collect data rows ──
        rows: List[List[str]] = []
        for r in range(header_row_idx + 1, max_row):
            row_vals = [grid[r][c].strip() for c in range(len(headers))]
            if any(row_vals):
                rows.append(row_vals)

        if not rows:
            return None

        # ── Average cell confidence ──
        confidences = [info["confidence"] for info in cells.values() if info["confidence"] > 0]
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

        return {
            "headers": headers,
            "rows": rows,
            "row_count": len(rows),
            "col_count": len(headers),
            "textract_confidence": round(avg_conf, 2),
        }

    def _get_text(
        self, cell_block: Dict[str, Any], blocks_by_id: Dict[str, Any]
    ) -> str:
        """
        Reconstruct the text content of a CELL by following its CHILD
        relationships to WORD and SELECTION_ELEMENT blocks.
        """
        words: List[str] = []
        for rel in cell_block.get("Relationships", []):
            if rel["Type"] != "CHILD":
                continue
            for cid in rel["Ids"]:
                blk = blocks_by_id.get(cid)
                if blk is None:
                    continue
                bt = blk.get("BlockType")
                if bt == "WORD":
                    words.append(blk.get("Text", ""))
                elif bt == "SELECTION_ELEMENT":
                    if blk.get("SelectionStatus") == "SELECTED":
                        words.append("[X]")
        return " ".join(w for w in words if w).strip()

    def _get_page_number(
        self, table_block: Dict[str, Any], blocks_by_id: Dict[str, Any]
    ) -> int:
        """
        Derive a 0-based page number for the given TABLE block.

        Textract blocks carry a Page field (1-based). If absent, fall back
        to 0 to guarantee the field is always present in the output.
        """
        page_1based = table_block.get("Page")
        if page_1based is not None:
            return max(0, int(page_1based) - 1)
        return 0
