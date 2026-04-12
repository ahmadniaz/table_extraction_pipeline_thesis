# Evaluation flow (as implemented)

**At a glance**

- **Upload** (`POST /api/documents/upload`) saves the PDF, sets `page_count` and `is_digital` via PyMuPDF text heuristics, and stores `complexity_tier` (UI default: `medium`). No extraction runs on upload.
- **Ground-truth seed** (`POST /api/documents/{id}/seed-ground-truth`) uses `DEFAULT_EXTRACTION_TOOL` (default `claude_sonnet`; only `claude_sonnet` and `pymupdf` are actually implemented—others fall back to `pymupdf` with a warning) and writes `GroundTruthTable` rows with `source` like `claude_sonnet_seed`, `confirmed=False`.
- **Benchmark extractions** are run per tool via `POST /api/extract/{doc_id}/{tool_name}` → `EvaluationRunner.run_tool`, which normalises output, applies `merge_similar_tables_global`, persists one `ExtractionResult` row per table (or one error row), then commits.
- **Scoring** happens when `POST /api/evaluate-tool/{doc_id}/{tool_name}` runs (per-tool, requires **confirmed** ground truth) or when `POST /api/evaluate/{doc_id}` / `POST /api/evaluate/batch` run (they score against **any** existing ground-truth rows, not only confirmed—see §2.5).
- **Metrics** (`metrics.py`): multiset cell **F1** (precision/recall), **TEDS** (token edit distance on HTML-like trees), **GriTS**-style **top/con/loc** from grid shape and greedy row/column matching—all **per matching `table_index`**, then stored on `EvaluationScore` linked to each `ExtractionResult`.
- **Batch evaluation UI** opens a WebSocket to `/api/ws/evaluation/{job_id}`, but **`/api/evaluate/batch` never emits progress events**—the progress panel will not advance from server pushes (see §2.6).

---

## 2.1 Entry points and orchestration

### Backend API surface (evaluation + extractions)

| Method | Path | Role |
|--------|------|------|
| `POST` | `/api/documents/upload` | Create `Document`; analyse PDF for `page_count`, `is_digital` (`documents.py`). |
| `POST` | `/api/documents/{doc_id}/seed-ground-truth` | Optional auto-seed of `GroundTruthTable` (`documents.py`). |
| `POST` | `/api/extract/{doc_id}/{tool_name}` | Run **one** tool; idempotent skip if results exist unless prior run had `is_transient_failure` (`evaluation.py`). |
| `POST` | `/api/evaluate/{doc_id}` | Body: `{ "tools": ["all"] \| [<tool names>] }`. Runs selected tools, writes `EvaluationScore` where GT exists (`evaluation.py`). |
| `POST` | `/api/evaluate/batch` | Body: `{ "tools", "tier": "all"\|"low"\|"medium"\|"high" }`. Loops all matching documents; skips docs with no GT (`evaluation.py`). |
| `POST` | `/api/evaluate-tool/{doc_id}/{tool_name}` | Score **existing** extractions for one tool vs **confirmed** GT only (`evaluation.py`). |
| `GET` | `/api/extractions/{doc_id}/{tool_name}` | List `ExtractionResult` rows for preview (`evaluation.py`). |
| `GET` | `/api/results/`, `/api/results/{doc_id}`, `/api/results/export/csv`, `/api/results/export/per-document-csv` | Aggregate and export scores (`evaluation.py`). |

`ALL_TOOLS` in `server/app/api/evaluation.py`:

```python
ALL_TOOLS = ["pymupdf", "docling", "aws_textract", "google_docai", "gpt5", "claude_sonnet", "mistral"]
```

`_resolve_tools(request.tools)`: if `"all"` ∈ `tools`, returns `ALL_TOOLS`; else validates each id against `ALL_TOOLS` or `400`.

### Frontend: where endpoints are called

- **`client/src/app/components/corpus/DocumentUploadZone.tsx`** — `POST /api/documents/upload` (FormData: `file`, `complexity_tier` fixed to `"medium"`).
- **`client/src/app/corpus/page.tsx`** — After upload refresh, `POST /api/documents/{id}/seed-ground-truth`; opens `GroundTruthEditor` when seed returns tables.
- **`client/src/app/evaluation/page.tsx`** — `POST /api/evaluate/batch` with `{ tools: selectedTools, tier }` (`ToolSelector` multi-select; default tools: only `claude_sonnet` per `DEFAULT_SELECTED_TOOLS` in `ToolSelector.tsx`).
- **`client/src/app/evaluation/[doc_id]/page.tsx`** — Per-tool `POST /api/extract/{docId}/{tool}`; then **evaluate all** via sequential `POST /api/evaluate-tool/{docId}/{tool}`. Loads extractions with `GET /api/extractions/...` and scores with `GET /api/results/{docId}`. **Note:** this page’s `TOOLS` list omits `aws_textract` (UI limitation vs backend).
- **`client/src/app/components/evaluation/ExtractionPreviewModal.tsx`** — `GET /api/extractions/{docId}/{tool}` + `GET /api/ground-truth/{docId}`.
- **`client/src/app/results/page.tsx`**, **`results/[doc_id]/page.tsx`** — results and exports as above.

### `EvaluationRunner` construction and dispatch

- Instantiated with `EvaluationRunner()` (no constructor args) in `evaluation.py` for extract/evaluate routes.
- Lazy singletons per runner instance: `_get_pymupdf`, `_get_docling`, `_get_aws_textract`, `_get_google_docai`, `_get_gpt` (key `"gpt5"`), `_get_claude`, `_get_mistral` (`runner.py`).

`_DISPATCH` maps tool name → async method:

| Tool | Method | Executor / async |
|------|--------|-------------------|
| `pymupdf` | `_extract_pymupdf` | `run_in_executor(None, PyMuPDFService().extract_tables, file_path)` |
| `aws_textract` | `_extract_aws_textract` | `run_in_executor(None, TextractService().analyze_document_tables, file_path)` |
| `docling` | `_extract_docling` | `run_in_executor(None, DoclingService().extract_tables, file_path)` — **note:** `extract_tables` accepts `is_digital` but the runner does **not** pass it (defaults to `True` in the service signature). |
| `google_docai` | `_extract_google_docai` | `await GoogleDocAIExtractor().extract_tables_async(file_path)` (async wrapper; inner work in executor). |
| `gpt5` | `_extract_gpt5` | `run_in_executor(None, GPT4oVisionService().extract_commission_data, file_path)` |
| `claude_sonnet` | `_extract_claude` | `await ClaudeDocumentAIService().extract_commission_data(file_path)` (**native async**). |
| `mistral` | `_extract_mistral` | `await MistralDocumentAIService().extract_commission_data_via_ocr(file_path)` (**native async**). |

`run_all_tools` (not used by the API routes shown) loops `for tool_name in self._DISPATCH` in fixed dict order (Python 3.7+ insertion order).

---

## 2.2 Tool outputs → normalised tables → database

### Normalisation (`EvaluationRunner`)

1. **`_normalise_tables(raw)`** (`runner.py`):  
   - Reads `tables` from `dict["tables"]`, or treats `list` as table list, or `raw.tables`.  
   - Each table dict: `headers` from `headers` or `header`; `rows` from `rows` or `data`.  
   - Preserves optional keys if present: `page_number`, `table_index`, `strategy_used`, `bbox`, `row_count`, `col_count`, `textract_confidence`, `cell_matching_used`, `metadata`, `extractor`.

2. **`merge_similar_tables_global(tables)`** (`table_merging.py`): sorts by `(page_number, table_index)`, merges consecutive tables with identical normalised non-empty headers, same column count, at least one row each, and “adjacent” in reading order (same page + `table_index` +1, or cross-page rule with both `page_number` present). Merged output updates `row_count`, `col_count`, `metadata.merge_info`, `merged_from`, `merged_page_range`.

3. **`_empty_extracted_rows(tables)`**: `True` if no tables, or **every** table has `rows` not a non-empty list (empty list or missing → treated as empty).

### Per-tool raw outputs (representative)

- **PyMuPDF** — `PyMuPDFService.extract_tables` → `dict` with `"tables"` (each with `headers`, `rows`, `page_number`, `table_index`, `strategy_used`, `bbox`, counts), `total_pages`, `pages_with_tables`, `"tool": "pymupdf"` (`pymupdf/service.py` docstring).
- **AWS Textract** — `analyze_document_tables` → `{"tables": [...], "pages_analyzed": int, "tool": "aws_textract"}` (and parsed block metadata inside tables per `_parse_blocks`; single-page sync vs multi-page S3 async — `textract/service.py`).
- **Docling** — `extract_tables` → `{"tables": [...], "total_pages", "tool", "model"}`; tables include `cell_matching_used` (`docling_service.py`).
- **Google DocAI** — `extract_tables_async` returns `{"success": True, "tables": list, "extraction_metadata": {...}}` when inner `extract_tables` returns a list (`extractor.py`); tables after `_post_process_tables` include `docai_confidence`, `bbox`, `page_number`, `table_index`, etc.
- **GPT-5** — `extract_commission_data` → `dict` with `success`, `tables`, `usage` (`input_tokens`, `output_tokens`), optional `extraction_metadata` (`gpt4o_vision_service.py`).
- **Claude** — async `extract_commission_data` → dict with `tables`, `usage`, `success` semantics per internal parsing (`claude/service.py`).
- **Mistral** — `extract_commission_data_via_ocr` → dict including `usage` for token-based cost (`mistral/service.py`).

### Failure and empty handling (`run_tool`)

- **`raw.get("success") is False`** (dict): sets `error_message`, classifies `failure_reason` from message substrings (`rate_limit`, `timeout`, `server_down`, else `api_error`); `is_transient` accordingly. **No tables** are parsed.
- **Exceptions**: `_classify_exception` → `(failure_reason, is_transient, error_message)` for OpenAI, Anthropic, Mistral, `requests`, `botocore` (`runner.py`).
- **`_empty_extracted_rows`**: single `ExtractionResult` with `failure_reason`: **`tool_limitation`** for `pymupdf` or `docling` when `not is_digital`; else **`empty_output`**. Message `"No tables extracted"`.
- **Success path**: one `ExtractionResult` per table index `0..n-1`.

### Database persistence (`ExtractionResult`)

- **One row per extracted table** for successful runs; **one row** for errors/empty (`table_index=0`).
- **First row only (`idx == 0`)** carries `processing_time_ms` (full run), **`cost_usd`** (full run cost), and **`raw_output`** (JSON-safe snapshot of entire raw tool output). Subsequent rows: `processing_time_ms=0`, `cost_usd=0`, `raw_output=None`.
- Fields: `document_id`, `tool_name`, `table_index`, `extracted_headers` / `extracted_rows` (or null on failure), `error_message`, `failure_reason`, `is_transient_failure`, `extracted_at` (server default).

### `Document` fields used by the runner

- Loaded in `run_tool`: `page_count` (default `1` if null), `is_digital` (default `True` if null) for **empty-output classification** and **cost** (`page_count`).
- **`complexity_tier`** is **not** read by `EvaluationRunner`; it filters **batch** evaluation (`Document.complexity_tier == body.tier`) and appears in exports/lists.
- Upload-time **`is_digital`**: `_analyse_pdf` marks digital if more than half of pages have `len(text.strip()) > 50` (`documents.py`). This differs from GPT-5’s internal `is_digital_pdf` heuristic (`gpt4o_vision_service.py`).

---

## 2.3 Cost calculation (`cost_calculator.py`)

- **`PRICE_PER_PAGE`**: `aws_textract` **0.015**, `google_docai` **0.01** USD/page; local/`gpt5`/`claude_sonnet`/`mistral`/`pymupdf`/`docling` **0.0** as base.
- **`calculate_cost(tool_name, page_count, input_tokens, output_tokens)`**:
  - `base = PRICE_PER_PAGE[tool] * page_count`.
  - For `tool_name in _TOKEN_PRICING` (`gpt5`, `claude_sonnet`, `mistral`):  
    `inp = input_tokens or (1500 * page_count)`, `out = output_tokens or (2000 * page_count)` using `_DEFAULT_TOKENS_PER_PAGE`.  
    Token cost = `inp * rate_in + out * rate_out`; return `round(base + token_cost, 6)`.
  - Else: return `round(base, 6)`.

**Token sourcing in `run_tool`**: `raw.get("usage", {})` with `input_tokens` / `output_tokens` (`runner.py`). Services are expected to populate these (GPT attaches `self._last_usage`; Claude/Mistral attach `usage` dicts).

---

## 2.4 Metric computation (`metrics.py`, `evaluation.py`)

### Functions

- **`normalise_cell`**: string cells → lowercase, strip, strip currency symbols, remove thousand commas between digits, collapse whitespace.
- **`compute_cell_f1(extracted_rows, ground_truth_rows)`**: multiset **cell** counts (all body rows only—headers are **not** included in F1), precision/recall/F1.
- **`compute_teds(extracted_table, ground_truth_table)`**: build HTML-like string via `_table_to_html` (headers + rows, cells passed through `normalise_cell`), tokenise tags/text, `editdistance.eval`, score `1 - dist/max_len`.
- **`compute_grits`**: builds grids with header row + body; **topology** from row/col count ratios; **content** via greedy best row–row Jaccard-like multiset similarity; **location** via greedy column–column similarity on full grids.

### Ground-truth matching

- **No** semantic/header matching across indices: predictions are paired by **`GroundTruthTable.table_index == ExtractionResult.table_index`**.
- **`POST /api/evaluate-tool/{doc_id}/{tool_name}`**: loads GT with **`confirmed.is_(True)`** only, ordered by `table_index`. For each GT, looks up extraction `by_index[gt.table_index]`. Missing extraction → GT skipped (no score).
- **`POST /api/evaluate/{doc_id}`** and **`/api/evaluate/batch`**: load **all** `GroundTruthTable` rows for the document (no `confirmed` filter). Match `gt_match` with `next((g for g in ground_truths if g.table_index == er.table_index), None)`.

### When scores are written

- **`evaluate_tool_for_document`**: Deletes existing `EvaluationScore` for each matched `extraction_result_id`, then inserts one score per matched table. If `failure_reason in ('tool_limitation','empty_output')`, writes **zeros** for all metrics and appends note to `error_message` (`_SCORE_ZERO_NOTE`).
- **`evaluate_document` / `evaluate_batch`**: if `gt_match` and **`not er.error_message`**, add `EvaluationScore`. (Failed extractions with non-empty `error_message` are skipped.)

### Aggregation

- **Per-table** scores in DB (`EvaluationScore` one-to-one with `ExtractionResult` for successful scoring paths).
- **API `GET /api/results/`**: flat list of score + extraction + document (no automatic macro average).
- **`export_per_document_summary_csv`**: for each document × **each tool in `ALL_TOOLS`**, averages F1/precision/recall/TEDS/GriTS **across that tool’s `ExtractionResult` rows** that have scores (`_avg_nums`).

### `EvaluationScore` model (`db/models.py`)

- `extraction_result_id` (FK), `precision`, `recall`, `f1_score`, `teds_score`, `grits_top`, `grits_con`, `grits_loc`, `computed_at`. No separate `metric_name` column—one row holds all metrics.

---

## 2.5 Ground truth creation and corrections

### Initial seed (`POST /api/documents/{doc_id}/seed-ground-truth`)

- Fails with **409** if any existing GT row has `confirmed=True`.
- Deletes prior auto-seed rows where `source in _AUTO_SEED_SOURCES` (e.g. `claude_sonnet_seed`, `pymupdf_seed`, …).
- Resolved tool from `_resolved_seed_tool()`: only **`claude_sonnet`** or **`pymupdf`**; others warn and behave as `pymupdf`.
- **Claude**: `await ClaudeDocumentAIService(config).extract_commission_data(...)`; **PyMuPDF**: executor `extract_tables`.
- Inserts `GroundTruthTable` rows with `table_index` 0..n-1, `source=f"{tool}_seed"`, `confirmed=False`, empty `correction_log`, `correction_count=0`.

### CRUD (`server/app/api/ground_truth.py`)

- `POST /api/ground-truth/{doc_id}` — create one table (409 if `table_index` exists).
- `PUT /api/ground-truth/{doc_id}/{table_index}` — update headers/rows/notes (does **not** auto-update `correction_log` / `correction_count`).
- `DELETE` — delete one table by index.
- `POST /api/ground-truth/{doc_id}/confirm` — **replaces all** GT for the document: each table `confirmed=True`, `source="manual"`, `correction_log` from payload, `correction_count=len(log)`.

### Merge (`POST /api/documents/{doc_id}/ground-truth/merge`)

- Appends secondary table’s rows onto primary (ordered by `table_index`); **headers from primary**; pads/truncates row width; appends one **correction_log** entry with `field`, `old_value`, `new_value`, `corrected_at`; increments **`correction_count` by 1** on primary; deletes secondary; **reindexes** remaining `table_index` values to `0..n-1`.

### Ground Truth Editor (frontend)

- **`GroundTruthEditor.tsx`**: loads via `sharedGetGroundTruth` → `GET /api/ground-truth/{docId}`; PDF from `GET /api/documents/{docId}/pdf`.
- **Operations**: edit header/cell, add/remove row/column, add/delete table, **merge** (calls document merge API), confirm (posts to `/confirm`).
- **`correction_count` display** in UI is a **client-side diff** vs initial snapshot (`originalsRef`) — count of header/cell changes vs loaded snapshot, **not** necessarily equal to DB `correction_count` until confirm.
- **On confirm**: `correction_log` = **existing server `correction_log`** + **`buildCorrectionLogForTable`** entries `{row, col, original, corrected}` (header edits use `row: -1`). Merge audit entries from API use `{field, old_value, new_value, corrected_at}`.

### **`GroundTruthModal.tsx`**

- Read-only view: same `GET /api/ground-truth/{docId}` for display.

---

## 2.6 Current limitations / quirks and implicit behaviour

- **Index alignment only**: metrics compare GT table `k` to extraction table `k`; no reordering or fuzzy matching.
- **Runner merge policy**: `merge_similar_tables_global` can **reduce** table count vs raw tool output; indices are **after** merge.
- **PyMuPDF + scanned PDFs**: empty tables → `tool_limitation` (not `empty_output`) when `Document.is_digital` is false (`runner.py`).
- **Docling**: `is_digital` from DB is **not** passed into `extract_tables` from `EvaluationRunner` (always default `True` in signature—logging only per service).
- **Docling**: automatic retry with `do_cell_matching=False` if column-count inconsistency detected (`docling_service.py`).
- **Textract**: single-page uses sync `AnalyzeDocument` with bytes; multi-page requires `AWS_S3_BUCKET` and async job + S3 upload (`textract/service.py`). Poll: max 30 attempts, exponential sleep capped at 32s.
- **Google DocAI**: `ENABLE_MULTIPAGE_STITCHING = False` (`extractor.py`) — no cross-page stitching in current config.
- **GPT-5**: scanned path **`max_pages` default 30** with `_select_representative_pages` when `total_pages > max_pages` (`extract_from_scanned_pdf`). Digital path sends up to **100_000** characters of extracted text in the prompt (`extract_from_digital_pdf_intelligent`).
- **GPT-5**: class `GPT4oVisionService` implements GPT-5 Responses API; **`merge_similar_tables`** on the service delegates to the same `merge_similar_tables_global` as the runner.
- **Document evaluation page** (`evaluation/[doc_id]/page.tsx`): **omits `aws_textract`** in the tool list—user cannot trigger Textract from that UI without API/other clients.
- **Batch evaluation WebSocket**: `EvaluationProgressPanel` listens for `tool_start`, `tool_done`, `doc_complete`, `job_complete`, etc., but **`eval_progress.send_progress` is never called** from `evaluation.py` or batch route—progress UI is effectively **disconnected** from server state.
- **Idempotent extract**: `POST /api/extract/...` skips reruns unless a prior run had **transient** failure; then deletes `EvaluationScore` + `ExtractionResult` for that tool and reruns.
- **`POST /api/evaluate/{doc_id}`** does **not** delete old extraction rows; repeated calls **append new** `ExtractionResult` rows (no unique constraint in `models.py`), which can **duplicate** `(document_id, tool_name, table_index)` rows and orphan older scores depending on query patterns—**operational risk** if used repeatedly.
- **Ground-truth confirmation vs scoring**: per-tool UI evaluation **requires confirmed GT**; batch/full-document evaluate endpoints do **not** filter to confirmed—can score against unconfirmed seed or draft GT.

---

## Open questions / ambiguities

1. **`gpt4o_vision_service.py` `_parse_extraction_response`**: After building the success `result` dict, the code references **`result_json`** (undefined) for `document_metadata` (lines 561–563). If execution reaches that line after a successful parse, Python would raise **`NameError`**, caught by the broad `except`, returning `success: False`. Verify whether successful GPT-5 extractions actually hit this in production or if another code path/version applies.

2. **Batch job WebSocket**: No server-side emission of progress events tied to `job_id`; UI expectations vs backend behaviour are **misaligned**.

3. **Duplicate extractions**: Unless using the idempotent `/api/extract` path, multiple evaluation runs may create **duplicate** `ExtractionResult` rows; API consumers may see **multiple scores** or ambiguous joins if not constrained—confirm intended operational procedure.

4. **`evaluate_document` vs `evaluate_tool`**: Different **confirmed** rules may cause the same document to be scored against **different GT sets** depending on which endpoint is used.

5. **`DocumentTable.tsx` / `GroundTruthModal`**: Not fully audited here; primary evaluation triggers are **`DocumentUploadZone`**, **`corpus/page`**, **`evaluation/page`**, **`evaluation/[doc_id]/page`**.

---

*Generated from codebase review; behaviour described reflects `server/app` and `client/src` as read during documentation.*
