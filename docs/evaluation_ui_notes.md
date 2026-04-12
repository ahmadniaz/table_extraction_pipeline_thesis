# Evaluation UI — inventory, decisions, progress

## Phase 1 — Inventory (entry points & pages)

### Frontend routes

| Route | File | Purpose | Classification |
|-------|------|---------|----------------|
| `/` | `client/src/app/page.tsx` | Redirect to `/corpus` | **Canonical** entry. |
| `/corpus` | `client/src/app/corpus/page.tsx` | Upload PDFs, list docs, Ground Truth Editor, Evaluate link | **Primary** corpus hub. |
| `/evaluation/[doc_id]` | `client/src/app/evaluation/[doc_id]/page.tsx` | Per-tool extract/evaluate (no batch page) | **Primary** evaluation workspace. |
| `/results` | `client/src/app/results/page.tsx` | Aggregate results + CSV export links | **Primary**. |
| `/results/[doc_id]` | `client/src/app/results/[doc_id]/page.tsx` | Per-document scores | **Primary** (7 tools incl. AWS Textract). |

**Removed:** `client/src/app/evaluation/page.tsx` (batch hub), `ToolSelector`, `EvaluationProgressPanel`, `JobStatusRow`.

### Shared components

| Component | Used by | Classification |
|-----------|---------|----------------|
| `ExtractionPreviewModal` | `evaluation/[doc_id]` | **Shared** — keep. |
| `GroundTruthEditor` / `GroundTruthModal` | Corpus | **Shared** — keep. |
| `client/src/lib/evaluationTools.ts` | Per-doc evaluation + parity with server `ALL_TOOLS` | **Shared** |

### Backend routes (evaluation)

| Endpoint | Used by |
|----------|---------|
| `POST /api/documents/upload` | Upload zone — **now** also runs default-tool extraction + GT seed + `ExtractionResult` persistence. |
| `POST /api/documents/{id}/seed-ground-truth` | Corpus retry — **refactored** to reuse same extraction+GT path as upload (no double Claude call vs `run_tool`). |
| `POST /api/extract/{doc_id}/{tool}` | Per-doc evaluation page |
| `POST /api/evaluate-tool/{doc_id}/{tool}` | Per-doc evaluation page (confirmed GT) |
| `POST /api/evaluate/{doc_id}`, `POST /api/evaluate/batch` | **No UI** after batch page removal; **kept** for API/scripts/thesis reproducibility. |

---

## Phase 2 — Decisions

- **Canonical flow:** Corpus (upload) → Ground Truth Editor (confirm) → `/evaluation/[doc_id]` (extract other tools, evaluate) → `/results`.
- **Batch page:** Removed from nav and filesystem; home redirects to `/corpus`.
- **Claude:** No Extract button on per-doc page; included in “Evaluate all” and optional per-tool Evaluate; extraction comes from upload/seed via `EvaluationRunner.run_tool`.

---

## Phase 3–5 — Progress log

- [x] Phase 1 inventory (this doc)
- [x] Backend: upload + shared seed helper + seed endpoint refactor
- [x] Frontend: corpus upload without separate seed call; DocumentTable Evaluate link
- [x] Frontend: `evaluation/[doc_id]` — all tools including AWS Textract; hide Claude extract; evaluate-all + per-tool evaluate
- [x] Remove batch evaluation page + unused components
- [x] Navbar + home redirect
- [x] `results/[doc_id]`: add `aws_textract` to tool list
- [x] Fix GPT-5 `_parse_extraction_response` `result_json` NameError (extraction stability, not metrics)

### Remaining limitations

- `POST /api/evaluate/batch` is **not** linked from UI; use curl/Postman if needed.
- WebSocket `/api/ws/evaluation/{job_id}` has no producers — harmless if unused.

---

## What changed (summary)

- **Upload (`POST /api/documents/upload`)** calls `_apply_default_tool_extraction_and_gt`: one `EvaluationRunner.run_tool` for `DEFAULT_EXTRACTION_TOOL` (default `claude_sonnet`), then unconfirmed `GroundTruthTable` rows from those `ExtractionResult` rows (`table_index` aligned).
- **Corpus** no longer calls `seed-ground-truth` immediately after upload; it uses the `seed` object in the upload JSON. **Retry** still uses `POST .../seed-ground-truth`.
- **Per-document evaluation** (`/evaluation/[doc_id]`): all 7 tools listed; **no Extract** for Claude; **Score** per tool + **Score all**; optional link to `/results/[doc_id]`.
- **Navigation:** brand + home → **Corpus**; removed top-level **Evaluation** nav item (per-doc route is reached from Corpus).

---

## Checklist vs intended behaviour (§1)

| Item | Status |
|------|--------|
| 1.1 Upload runs Claude (or `DEFAULT_EXTRACTION_TOOL`), seeds GT, persists `ExtractionResult` | **Implemented** — `_apply_default_tool_extraction_and_gt` |
| 1.2 Per-tool table, no Extract for Claude, Evaluate all includes Claude | **Implemented** |
| 1.3 Scores/CSV unchanged; idempotent extract via `/api/extract` | **Unchanged** backend; seed path deletes prior tool ER+scores before re-run |
