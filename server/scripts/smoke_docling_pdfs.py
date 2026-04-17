"""Minimal Docling smoke test — not part of the FastAPI app."""
from __future__ import annotations

import sys
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.document_converter import DocumentConverter, PdfFormatOption


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    pdf_dir = root / "data" / "pdfs"
    paths = sorted(pdf_dir.glob("*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)[:5]
    if not paths:
        print("No PDFs in", pdf_dir, file=sys.stderr)
        sys.exit(1)

    pipeline_options = PdfPipelineOptions(do_table_structure=True, do_ocr=True)
    pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE
    pipeline_options.table_structure_options.do_cell_matching = True

    conv = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )

    for pdf in paths:
        print("===", pdf.name, "===")
        try:
            conv_res = conv.convert(str(pdf))
            tables = conv_res.document.tables
            print("  tables len:", len(tables))
            for idx, t in enumerate(tables):
                df = t.export_to_dataframe()
                print("  table", idx, "dataframe rows:", len(df), "cols:", len(df.columns))
        except Exception as exc:
            print("  ERROR:", exc, file=sys.stderr)


if __name__ == "__main__":
    main()
