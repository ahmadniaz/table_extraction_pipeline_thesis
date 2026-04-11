# Tool Implementation Summary

## Status Overview Table

| Tool | Status | Entry Point File | Runner Method | Frontend Key | Match? |
|------|--------|------------------|---------------|--------------|--------|
| PyMuPDF | PARTIALLY IMPLEMENTED (id `pymupdf`, code uses `pdfplumber`) | `server/app/services/evaluation/runner.py` | `_extract_pymupdf` | `pymupdf` | Yes |
| Docling | FULLY IMPLEMENTED (wired) | `server/app/services/evaluation/runner.py` → `docling/pipeline.py` | `_extract_docling` | `docling` | Yes |
| AWS Textract | NOT IMPLEMENTED | — | — | — | N/A |
| Google DocAI | FULLY IMPLEMENTED (wired) | `server/app/services/google_docai/extractor.py` | `_extract_google_docai` | `google_docai` | Yes |
| GPT-5 Vision | FULLY IMPLEMENTED (wired; OpenAI model id `gpt-5` in source) | `server/app/services/ai/gpt4o_vision_service.py` | `_extract_gpt5` | `gpt5` | Yes |
| Claude Sonnet | FULLY IMPLEMENTED (wired) | `server/app/services/claude/service.py` | `_extract_claude` | `claude_sonnet` | Yes |
| Mistral AI | FULLY IMPLEMENTED (wired; OCR `mistral-ocr-latest`, not Pixtral chat) | `server/app/services/mistral/service.py` | `_extract_mistral` | `mistral` | Yes |

## Critical Issues (action required before running evaluation)

1. **AWS Textract is not runnable** — `EvaluationRunner._DISPATCH` and `server/app/api/evaluation.py` `ALL_TOOLS` omit `aws_textract`; any thesis chapter that promises seven cloud/local tools including Textract cannot be satisfied without new code. Cost entry is dead: `server/app/services/evaluation/cost_calculator.py` line **11** (`PRICE_PER_PAGE["aws_textract"]`). Schema comment only: `server/app/db/models.py` line **41**.

2. **`pymupdf` tool does not use PyMuPDF for extraction** — Implementation is `pdfplumber` in `server/app/services/evaluation/runner.py` lines **180–193**. Thesis labelling must match implementation or results are misattributed.

3. **Cell-level F1 ignores header row** — `compute_cell_f1` (`server/app/services/evaluation/metrics.py` lines **35–51**) only multiset-matches **body cells**. `evaluation.py` passes **rows only** (lines **223**, **286**, **360**), not headers. TEDS/GriTS use headers via `ext_table` / `gt_table`, so metrics are **inconsistent** across scores.

4. **GPT tool naming vs implementation file** — Runner key `gpt5` and UI “GPT-5 Vision” align, but service lives in `gpt4o_vision_service.py` with class `GPT4oVisionService`. Model string in API calls is **`gpt-5`** (`server/app/services/ai/gpt4o_vision_service.py`, e.g. lines **133–136**, **625–628**). If the account does not expose that model id, evaluation fails at runtime.

5. **Mistral evaluation path cost is likely wrong** — `calculate_cost("mistral", page_count)` uses **chat token** rates (`cost_calculator.py` lines **21–22**, **38–42**), while the runner invokes **OCR** (`mistral/service.py` `extract_commission_data_via_ocr`, lines **546–576**). Reported USD cost will not match Mistral OCR pricing.

6. **Claude large-document chunks still upload the full PDF** — `server/app/services/claude/service.py` lines **536–538** (`_extract_chunk`): entire file base64-encoded per chunk call. Payload and cost do not scale down with “chunk index”; thesis claims about chunking should be checked against this behaviour.

## Warnings (should fix but not blocking)

1. **Google env var naming** — Extractor sets `GOOGLE_CLOUD_PROJECT_ID` / `GOOGLE_DOCAI_PROCESSOR_ID` (`google_docai/extractor.py` lines **94–101**); docs may say `DOCAI_PROJECT_ID` — deployment drift risk.

2. **Docling may return errors without raising** — `docling/pipeline.py` `extract_tables` exception path returns `TableExtractionResult` with `errors` list (lines **233–243**); runner may treat as empty tables rather than structured failure.

3. **GPT scanned path default `max_pages=30`** — `extract_commission_data` (`gpt4o_vision_service.py` line **1192**) limits vision pages; long PDFs are subsampled — thesis should document this.

4. **Intelligent GPT path may drop tables** — `_parse_extraction_response_intelligent` skips tables when header AI validation marks templates (`gpt4o_vision_service.py` lines **261–266**).

5. **Frontend tool descriptions** — e.g. Mistral described as “Pixtral Large” in `ToolSelector.tsx` line **11** while runner uses OCR markdown parsing, not Pixtral JSON prompts.

## Missing Tools

- **AWS Textract:** No extractor service, no `_DISPATCH` entry, no frontend checkbox, no `ALL_TOOLS` string. Only a placeholder per-page rate in `cost_calculator.py`.

## Prompt Consistency Check (LLM tools)

| Aspect | GPT-5 path (digital + vision) | Claude (standard) | Mistral (runner path) |
|--------|-------------------------------|---------------------|------------------------|
| Output shape | JSON `tables[].headers` / `rows`, optional `hierarchical_metadata` | JSON `tables` + `document_metadata` | **Markdown pipes** → parsed to `headers`/`rows` |
| System prompt | Long commission-specific instructions; digital also uses context-aware shorter template | Insurance commission + strict JSON schema | **None** (OCR API) |
| Company column | Explicit “Company Name” first column in GPT prompts | Not required in prompt schema | Depends on OCR markdown |
| Metadata | Optional in JSON | Required block in prompt template | Only `document_metadata` wrapper from service, not LLM JSON |

**Comparability:** GPT and Claude are closer (both JSON table arrays). Mistral’s OCR+markdown path is **not** asking for the same structure as the LLM tools; row/column errors and header detection differ materially. Metrics still compare multiset cells / tree/grid structure, but extraction biases differ.

## Cost Calculator Accuracy

- **Hardcoded values** (`cost_calculator.py`): `google_docai` **0.0065** USD/page; `aws_textract` **0.015** USD/page; GPT **5.00 / 15.00** per 1M input/output tokens; Claude **3.00 / 15.00**; Mistral **2.00 / 6.00** per 1M tokens; default **1500** input + **2000** output tokens per page when usage unknown.

- **Issues:** (1) **Google** — verify against current Document AI Form Parser pricing for your region/processor. (2) **AWS Textract** — unused entry; verify if ever wired. (3) **GPT / Claude** — token rates change frequently; April 2026 snapshot in comments may be stale. (4) **Mistral OCR** — token-based estimate is **unlikely** to match OCR product billing. (5) **Actual usage** — runner does not pass real token counts into `calculate_cost` for GPT/Claude/Mistral.

---

**Audit artefact:** Seven per-tool reports (`01`–`07`) plus this summary live under `tool_reports/` at the repository root.
