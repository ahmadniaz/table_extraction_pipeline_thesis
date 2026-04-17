"""
AWS Textract table extraction service — thesis-grade implementation.

Single-page PDFs: synchronous AnalyzeDocument with Document={"Bytes": ...}.

Multi-page PDFs: asynchronous StartDocumentAnalysis / GetDocumentAnalysis with
the document in S3 (sync Bytes API is single-page only per AWS). Table
reconstruction follows the official Block relationship graph:

    PAGE → TABLE → CELL / MERGED_CELL → WORD / SELECTION_ELEMENT

COLUMN_HEADER entity type is used to identify header rows. MERGED_CELL
blocks propagate header text across spanned columns per the AWS merged-cell
blog post (2022).

Pricing (us-east-1 / us-west-2, April 2026):
    AnalyzeDocument TABLES: $0.015 per page (first 1M pages/month).
    Tracked in cost_calculator.py as PRICE_PER_PAGE["aws_textract"] = 0.015.

Environment:
  - AWS_REGION — Textract and S3 client region (bucket should match).
  - AWS_S3_BUCKET — recommended for multi-page PDFs: async StartDocumentAnalysis
    (one job, S3 upload → poll → delete). If unset, multi-page PDFs fall back to
    one synchronous AnalyzeDocument call per page (same AWS per-page TABLE pricing,
    more round-trips; fine for dev/small docs).
  - Standard boto3 credential chain for both Textract and S3.

Design notes:
  - boto3 errors are NOT swallowed; they propagate to EvaluationRunner.
  - Runner executes this service via asyncio.run_in_executor (blocking I/O).
"""

import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TextractService:
    """
    Extracts tables from PDF documents using AWS Textract (sync or async API).

    Each instance lazily creates boto3 Textract (and S3) clients, reused
    across calls (boto3 clients are thread-safe).
    """

    def __init__(self, region_name: Optional[str] = None) -> None:
        self._region = region_name or os.environ.get("AWS_REGION", "us-east-1")
        self._client: Optional[Any] = None
        self._s3: Optional[Any] = None

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

    def _get_s3_client(self) -> Any:
        if self._s3 is None:
            import boto3
            from botocore.config import Config as BotoConfig

            cfg = BotoConfig(
                retries={"max_attempts": 3, "mode": "standard"},
                read_timeout=120,
                connect_timeout=10,
            )
            self._s3 = boto3.client("s3", region_name=self._region, config=cfg)
            logger.info(
                "TextractService: S3 client initialised (region=%s)", self._region
            )
        return self._s3

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze_document_tables(self, file_path: str) -> Dict[str, Any]:
        """
        Route: synchronous AnalyzeDocument for single-page PDFs; asynchronous
        S3-based analysis for multi-page PDFs.

        Returns:
            {"tables": [...], "pages_analyzed": int, "tool": "aws_textract"}

        Raises:
            FileNotFoundError: if file_path does not exist.
            RuntimeError: if async Textract job fails or times out.
            botocore.exceptions.ClientError / BotoCoreError: propagate to runner.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {file_path}")

        import fitz

        doc = fitz.open(str(path))
        try:
            page_count = doc.page_count
        finally:
            doc.close()

        if page_count == 1:
            return self._analyze_sync(path)
        s3_bucket = os.environ.get("AWS_S3_BUCKET", "").strip()
        if s3_bucket:
            return self._analyze_async_s3(path, page_count)
        logger.warning(
            "TextractService: AWS_S3_BUCKET not set — using synchronous AnalyzeDocument "
            "per page for %d-page %s (async S3 path is preferred for production).",
            page_count,
            path.name,
        )
        return self._analyze_multipage_sync_per_page(path, page_count)

    def _analyze_sync(self, path: Path) -> Dict[str, Any]:
        client = self._get_client()
        logger.info(
            "TextractService: synchronous AnalyzeDocument for %s (%d bytes)",
            path.name,
            path.stat().st_size,
        )
        response = client.analyze_document(
            Document={"Bytes": path.read_bytes()},
            FeatureTypes=["TABLES"],
        )
        blocks = response.get("Blocks", [])
        return self._parse_blocks(blocks, path.name)

    def _analyze_multipage_sync_per_page(self, path: Path, page_count: int) -> Dict[str, Any]:
        """
        Multi-page PDF without S3: AWS only allows Bytes on sync AnalyzeDocument for
        a single page. Split with PyMuPDF and run one sync call per page, then merge.
        """
        import fitz

        client = self._get_client()
        all_tables: List[Dict[str, Any]] = []
        doc = fitz.open(str(path))
        try:
            for i in range(page_count):
                single = fitz.open()
                try:
                    single.insert_pdf(doc, from_page=i, to_page=i)
                    pdf_bytes = single.tobytes()
                finally:
                    single.close()
                logger.info(
                    "TextractService: sync AnalyzeDocument page %d/%d of %s",
                    i + 1,
                    page_count,
                    path.name,
                )
                response = client.analyze_document(
                    Document={"Bytes": pdf_bytes},
                    FeatureTypes=["TABLES"],
                )
                blocks = response.get("Blocks", [])
                parsed = self._parse_blocks(blocks, f"{path.name}#p{i + 1}")
                for t in parsed.get("tables", []):
                    t["page_number"] = i
                    t["table_index"] = len(all_tables)
                    all_tables.append(t)
        finally:
            doc.close()

        logger.info(
            "TextractService: %d tables from %d-page sync-per-page run on %s",
            len(all_tables),
            page_count,
            path.name,
        )
        return {
            "tables": all_tables,
            "pages_analyzed": page_count,
            "tool": "aws_textract",
        }

    def _analyze_async_s3(self, path: Path, page_count: int) -> Dict[str, Any]:
        s3_bucket = os.environ.get("AWS_S3_BUCKET", "").strip()
        if not s3_bucket:
            raise ValueError("AWS_S3_BUCKET is required for _analyze_async_s3")

        s3_key = f"textract-jobs/{uuid.uuid4().hex}/{path.name}"
        s3 = self._get_s3_client()

        logger.info(
            "TextractService: uploading %s (%d pages) to s3://%s/%s",
            path.name,
            page_count,
            s3_bucket,
            s3_key,
        )
        s3.upload_file(str(path), s3_bucket, s3_key)

        try:
            client = self._get_client()
            start = client.start_document_analysis(
                DocumentLocation={
                    "S3Object": {"Bucket": s3_bucket, "Name": s3_key}
                },
                FeatureTypes=["TABLES"],
            )
            job_id = start["JobId"]
            logger.info(
                "TextractService: async job %s started for %s", job_id, path.name
            )

            result = self._poll_async_job(client, job_id, path.name)
            all_blocks = self._collect_all_blocks(client, job_id, result)

            return self._parse_blocks(all_blocks, path.name)
        finally:
            try:
                s3.delete_object(Bucket=s3_bucket, Key=s3_key)
                logger.info(
                    "TextractService: cleaned up s3://%s/%s", s3_bucket, s3_key
                )
            except Exception as cleanup_err:
                logger.warning(
                    "TextractService: S3 cleanup failed: %s", cleanup_err
                )

    def _poll_async_job(self, client: Any, job_id: str, doc_name: str) -> Dict[str, Any]:
        """Poll GetDocumentAnalysis until SUCCEEDED or FAILED."""
        delay = 2.0
        max_attempts = 30
        last: Dict[str, Any] = {}

        for attempt in range(max_attempts):
            last = client.get_document_analysis(JobId=job_id)
            status = last.get("JobStatus")
            if status == "SUCCEEDED":
                return last
            if status == "FAILED":
                msg = last.get("StatusMessage", "unknown")
                raise RuntimeError(f"Textract job FAILED for {doc_name}: {msg}")
            time.sleep(min(delay, 32.0))
            delay = min(delay * 2.0, 32.0)

        raise RuntimeError(
            f"Textract job timed out for {doc_name} after {max_attempts} polls"
        )

    def _collect_all_blocks(
        self, client: Any, job_id: str, first: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Aggregate all Blocks using NextToken pagination (async API)."""
        all_blocks: List[Dict[str, Any]] = list(first.get("Blocks", []))
        next_token = first.get("NextToken")
        while next_token:
            page = client.get_document_analysis(
                JobId=job_id, NextToken=next_token
            )
            all_blocks.extend(page.get("Blocks", []))
            next_token = page.get("NextToken")
        return all_blocks

    def _parse_blocks(self, blocks: List[Dict[str, Any]], doc_name: str) -> Dict[str, Any]:
        blocks_by_id: Dict[str, Any] = {blk["Id"]: blk for blk in blocks}

        pages_analyzed = sum(1 for b in blocks if b.get("BlockType") == "PAGE")
        table_blocks = [b for b in blocks if b.get("BlockType") == "TABLE"]

        logger.info(
            "TextractService: %d TABLE blocks found in %s (%d pages)",
            len(table_blocks),
            doc_name,
            pages_analyzed,
        )

        tables: List[Dict[str, Any]] = []
        for table_block in table_blocks:
            result = self._extract_table(table_block, blocks_by_id)
            if result is None:
                continue
            result["page_number"] = self._get_page_number(
                table_block, blocks_by_id
            )
            result["table_index"] = len(tables)
            tables.append(result)

        logger.info(
            "TextractService: %d non-empty tables extracted from %s",
            len(tables),
            doc_name,
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
                    existing = cells[key]["text"]
                    if text and existing:
                        cells[key]["text"] = f"{existing} {text}".strip()
                    elif text:
                        cells[key]["text"] = text
                    cells[key]["is_header"] = cells[key]["is_header"] or is_header

        if max_row == 0 or max_col == 0:
            return None

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
            return None

        headers = [grid[header_row_idx][c].strip() for c in range(max_col)]

        while headers and all(
            not grid[r][len(headers) - 1] for r in range(max_row)
        ):
            headers.pop()

        if not headers:
            return None

        rows: List[List[str]] = []
        for r in range(header_row_idx + 1, max_row):
            row_vals = [grid[r][c].strip() for c in range(len(headers))]
            if any(row_vals):
                rows.append(row_vals)

        if not rows:
            return None

        confidences = [
            info["confidence"] for info in cells.values() if info["confidence"] > 0
        ]
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
        page_1based = table_block.get("Page")
        if page_1based is not None:
            return max(0, int(page_1based) - 1)
        return 0
