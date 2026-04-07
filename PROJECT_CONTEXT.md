# PROJECT_CONTEXT.md

> **Generated**: 2026-04-08 via exhaustive file-by-file audit of every file in the repository.
> **Purpose**: Authoritative source of truth for the thesis refactoring effort. Every claim below was verified directly from source code; uncertainties are stated explicitly.

---

## 1. Project Overview

This project is a **thesis research tool** for benchmarking the accuracy, speed, and cost of PDF table extraction across six different AI-powered and rule-based methods. Users upload PDF documents into a corpus, manually annotate ground truth tables, then run an automated evaluation pipeline that calls each extraction tool, scores the results against the ground truth using three complementary metrics (cell-level F1, TEDS, and GriTS), and visualises the results in a React dashboard. The project name in `client/package.json` is `table-extraction-evaluator`; the app title is "PDF Table Extraction Evaluator".

**Important note on legacy code**: The repository contains a large volume of dead code from a prior "commission tracker" SaaS product (carrier detection, format learning, OTP authentication, GCS upload, Excel extraction, smart extraction, etc.). That code is present in the `server/` directory but **none of it is wired into `server/app/main.py`**. Only the four thesis-specific routers (`documents`, `ground_truth`, `evaluation`, `eval_websocket`) are active. All legacy modules are documented in this file but clearly labelled as inactive.

---

## 2. Tech Stack

| Layer | Technology | Version |
|---|---|---|
| Frontend framework | Next.js | 15.3.4 |
| Frontend runtime | React | 19.0.0 |
| Frontend language | TypeScript | latest (via `@types/*`) |
| Styling | Tailwind CSS | ^4.x (via `@tailwindcss/postcss`) |
| UI primitives | Radix UI (dropdown-menu, select, tabs, tooltip) | latest |
| Icons | lucide-react | latest |
| Charts | Recharts | latest |
| File drag-drop | react-dropzone | latest |
| HTTP client | axios | latest |
| Toast notifications | react-hot-toast | latest |
| Animations | framer-motion | latest |
| PDF worker | pdfjs-dist | latest |
| Backend framework | FastAPI | ^0.115 |
| Backend runtime | Python | 3.11.13 |
| ASGI server | Uvicorn | ^0.34 |
| WebSockets | websockets | ^14 |
| ORM | SQLAlchemy (async) | ^2.0 |
| Database driver | asyncpg | ^0.30 |
| Database | PostgreSQL | (hosted: Supabase or local) |
| PDF library | PyMuPDF (fitz) | ^1.25 |
| PDF table extraction | pdfplumber | ^0.11 |
| OCR | EasyOCR | ^1.7 |
| OCR (alt) | PyTesseract | ^0.3 |
| OCR (Google) | Google Document AI | ^3.x |
| Table detection model | Docling (wraps TableFormer) | ^2.x |
| Table structure model | microsoft/table-transformer-structure-recognition-v1.1-all | — |
| ML framework | PyTorch | ^2.x |
| LLM - OpenAI | GPT-4o Vision (labelled "gpt5" in code) | gpt-4o (via openai SDK) |
| LLM - Anthropic | Claude (claude-sonnet-4-20250514) | ^0.52 |
| LLM - Mistral | Pixtral Large | ^1.x |
| Containerisation | Docker | — |
| Cloud deployment | Render | — |
| Cloud storage (legacy) | Google Cloud Storage | — |

---

## 3. Installed Dependencies

### Backend (`server/requirements.txt`)

| Package | Version constraint | Purpose |
|---|---|---|
| fastapi | ^0.115 | Web framework |
| uvicorn | ^0.34 | ASGI server |
| websockets | ^14 | WebSocket support |
| sqlalchemy | ^2.0 | Async ORM |
| asyncpg | ^0.30 | Async PostgreSQL driver |
| psycopg2-binary | ^2.9 | Sync PostgreSQL driver |
| google-cloud-documentai | ^3.0 | Google Document AI |
| google-auth | ^2.0 | Google authentication |
| PyMuPDF | ^1.25 | PDF processing |
| pdfplumber | ^0.11 | PDF table extraction |
| pypdf | ^5.0 | PDF utilities |
| pdf2image | ^1.17 | PDF→image conversion |
| python-dotenv | ^1.0 | Environment variable loading |
| pydantic | ^2.0 | Data validation |
| python-multipart | ^0.0.19 | Multipart form uploads |
| opencv-python-headless | ^4.10 | Image processing |
| Pillow | ^11.0 | Image processing |
| numpy | ^2.0 | Numerical arrays |
| scipy | ^1.14 | Scientific computing |
| scikit-image | ^0.24 | Image algorithms |
| scikit-learn | ^1.5 | ML utilities |
| psutil | ^6.0 | System monitoring |
| pandas | ^2.2 | Data manipulation |
| python-dateutil | ^2.9 | Date parsing |
| openpyxl | ^3.1 | Excel read/write |
| xlrd | ^2.0 | Legacy Excel read |
| openai | ^1.55 | OpenAI API client |
| mistralai | ^1.2 | Mistral API client |
| anthropic | ^0.52 | Anthropic API client |
| tiktoken | ^0.8 | Token counting (for cost estimation) |
| docling | ^2.0 | Document + table extraction pipeline |
| torch | ^2.5 | PyTorch ML framework |
| torchvision | ^0.20 | Vision models |
| transformers | ^4.47 | Hugging Face transformers |
| huggingface-hub | ^0.26 | Model downloading |
| easyocr | ^1.7 | OCR engine |
| pytesseract | ^0.3 | Tesseract OCR wrapper |
| timm | ^1.0 | Vision model zoo |
| editdistance | ^0.8 | Edit distance for metrics |
| tqdm | ^4.67 | Progress bars |
| requests | ^2.32 | HTTP client |
| loguru | ^0.7 | Structured logging |
| pytest | ^8.3 | Testing |
| pytest-cov | ^6.0 | Test coverage |
| black | ^24.0 | Code formatting |
| flake8 | ^7.1 | Linting |
| mypy | ^1.13 | Type checking |

### Frontend (`client/package.json`)

| Package | Version | Purpose |
|---|---|---|
| next | 15.3.4 | React framework |
| react | 19.0.0 | UI library |
| react-dom | 19.0.0 | DOM rendering |
| @radix-ui/react-dropdown-menu | latest | Dropdown components |
| @radix-ui/react-select | latest | Select components |
| @radix-ui/react-tabs | latest | Tab components |
| @radix-ui/react-tooltip | latest | Tooltip components |
| @tailwindcss/postcss | latest | Tailwind PostCSS integration |
| axios | latest | HTTP requests |
| clsx | latest | Class name utility |
| framer-motion | latest | Animations |
| lucide-react | latest | SVG icon library |
| pdfjs-dist | latest | PDF viewer in browser |
| postcss | latest | CSS processing |
| react-dropzone | latest | Drag-and-drop file upload |
| react-hot-toast | latest | Toast notifications |
| react-markdown | latest | Markdown rendering |
| react-select | latest | Advanced select inputs |
| recharts | latest | Chart components |
| tailwind-merge | latest | Merge Tailwind classes |
| tailwindcss | latest | Utility-first CSS |
| tailwindcss-animate | latest | Tailwind animation utilities |
| @eslint/eslintrc | dev | ESLint config |
| @tailwindcss/typography | dev | Tailwind prose plugin |
| @types/node | dev | Node type definitions |
| @types/react | dev | React type definitions |
| @types/react-dom | dev | React DOM type definitions |
| eslint | dev | Linter |
| eslint-config-next | dev | Next.js ESLint config |
| typescript | dev | TypeScript compiler |

---

## 4. Environment Variables

### Backend (`server/.env` — **COMMITTED TO REPO WITH REAL VALUES — SECURITY RISK**)

| Variable | Purpose | Required? |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI GPT-4o Vision API | Yes (for gpt5 tool) |
| `MISTRAL_API_KEY` | Mistral AI Pixtral Large API | Yes (for mistral tool) |
| `MISTRAL_API_BASE` | Mistral API base URL override | No |
| `CLAUDE_API_KEY` | Anthropic Claude API | Yes (for claude_sonnet tool) |
| `CLAUDE_MODEL_PRIMARY` | Primary Claude model ID | No (defaults to `claude-sonnet-4-20250514`) |
| `CLAUDE_MODEL_FALLBACK` | Fallback Claude model ID | No |
| `CLAUDE_MAX_TOKENS` | Max tokens for Claude responses | No |
| `CLAUDE_TIMEOUT` | Timeout for Claude API calls | No |
| `ANTHROPIC_API_KEY` | Alternative key name for Anthropic (checked after `CLAUDE_API_KEY`) | No |
| `LOCAL_DB_KEY` | Local PostgreSQL connection URL (checked first) | No |
| `RENDER_DB_KEY` | Render PostgreSQL connection URL (checked second) | No |
| `SUPABASE_DB_KEY` | Supabase PostgreSQL connection URL (checked third) | No |
| `DOCAI_PROJECT_ID` | Google Cloud project ID for Document AI | Yes (for google_docai tool) |
| `DOCAI_PROCESSOR_ID` | Google Document AI processor ID | Yes (for google_docai tool) |
| `DOCAI_REGION` | Document AI region (e.g. `us`) | No (defaults to `us`) |
| `GCS_BUCKET_NAME` | Google Cloud Storage bucket (legacy, inactive) | No |
| `JWT_SECRET_KEY` | JWT signing secret (legacy auth, inactive) | No |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT access token lifetime (legacy, inactive) | No |
| `REFRESH_TOKEN_EXPIRE_DAYS` | JWT refresh token lifetime (legacy, inactive) | No |
| `SMTP_SERVER` | SMTP host for email (legacy, inactive) | No |
| `SMTP_PORT` | SMTP port (legacy, inactive) | No |
| `EMAIL_USER` | Email sender address (legacy, inactive) | No |
| `EMAIL_PASSWORD` | Email sender password (legacy, inactive) | No |
| `OTP_EXPIRY_MINUTES` | OTP lifetime (legacy, inactive) | No |
| `OTP_RATE_LIMIT_PER_HOUR` | OTP rate limit (legacy, inactive) | No |
| `OTP_MAX_ATTEMPTS` | Max OTP attempts (legacy, inactive) | No |
| `REDIS_URL` | Redis connection URL (legacy, inactive) | No |
| `AWS_ACCESS_KEY_ID` | AWS credentials (legacy, inactive) | No |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key (legacy, inactive) | No |
| `AWS_REGION` | AWS region (legacy, inactive) | No |
| `S3_BUCKET_NAME` | S3 bucket (legacy, inactive) | No |
| `WEBSOCKET_TIMEOUT` | WebSocket connection timeout (seconds) | No (default 1800) |
| `MISTRAL_TIMEOUT` | Mistral API timeout (seconds) | No (default 1800) |
| `GPT_TIMEOUT` | GPT API timeout (seconds) | No (default 300) |
| `EXTRACTION_TIMEOUT` | Total extraction timeout (seconds) | No (default 1800) |
| `UVICORN_TIMEOUT_KEEP_ALIVE` | Uvicorn keep-alive timeout | No (default 1800) |
| `UVICORN_WORKERS` | Number of Uvicorn workers | No (default 1) |

### Frontend (`client/.env`)

| Variable | Purpose | Required? |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | Backend URL (e.g. `http://localhost:8000`) | Yes |

---

## 5. Repository Structure

```
table_extractor-thesis/
│
├── Dockerfile                      # Docker image for backend; pre-downloads EasyOCR, Docling, HF TableFormer models
├── docker-test.sh                  # Local Docker build + health-check test script
├── render.yaml                     # Render.com deployment config (Python env, pro plan)
├── render-docker.yaml              # Render.com deployment config (Docker env, starter plan)
├── .gitignore                      # Ignores node_modules, .next, .env, model caches, GCS credential files
│
├── client/                         # Next.js 15 frontend (thesis UI)
│   ├── package.json                # Frontend deps; project name: table-extraction-evaluator
│   ├── package-lock.json           # Lockfile
│   ├── next.config.ts              # Next.js config; API rewrites to localhost:8000; PDF.js worker bundling; CSP headers
│   ├── tailwind.config.ts          # Tailwind CSS; class-based dark mode; extended color palette
│   ├── tsconfig.json               # TypeScript config
│   ├── postcss.config.mjs          # PostCSS config
│   ├── .env                        # NEXT_PUBLIC_API_URL=http://localhost:8000
│   │
│   └── src/
│       ├── app/
│       │   ├── layout.tsx          # Root layout; wraps app in ThemeProvider + Toaster + Navbar
│       │   ├── page.tsx            # Entry point; redirects → /corpus
│       │   ├── globals.css         # Global Tailwind base styles + CSS variables
│       │   ├── toast.tsx           # Customised react-hot-toast Toaster (position top-center; themed)
│       │   │
│       │   ├── corpus/page.tsx     # Document corpus page; fetches documents + GT counts; hosts upload zone + document table
│       │   ├── evaluation/page.tsx # Evaluation configuration page; tool selector; tier filter; triggers batch eval
│       │   ├── results/page.tsx    # Results dashboard; aggregates metrics; renders 4 chart/table components
│       │   │
│       │   └── components/
│       │       ├── Navbar.tsx                              # Sticky navbar; links to Corpus/Evaluation/Results; dark mode toggle
│       │       ├── LoadingScreen.tsx                       # Full-screen loading spinner with FlaskConical icon
│       │       ├── Modal.tsx                               # Generic accessible modal with ESC + focus trap
│       │       │
│       │       ├── corpus/
│       │       │   ├── DocumentUploadZone.tsx              # Drag-and-drop PDF upload → POST /api/documents/upload; defaults to 'medium' tier
│       │       │   ├── DocumentTable.tsx                   # Tabular list of documents; inline tier editor; GT count badge; delete confirm; opens GT modal/editor
│       │       │   ├── GroundTruthModal.tsx                # Read-only modal showing saved GT tables for a document
│       │       │   ├── GroundTruthEditor.tsx               # Full editor for GT tables; add/remove rows and columns; multi-table tabs; save via PUT/POST
│       │       │   └── TierBadge.tsx                       # Coloured badge for complexity tier (low/medium/high)
│       │       │
│       │       ├── evaluation/
│       │       │   ├── ToolSelector.tsx                    # Checkbox grid for selecting extraction tools; defines ALL_TOOLS constant
│       │       │   ├── EvaluationProgressPanel.tsx         # WebSocket listener; shows overall % progress + per-tool status row
│       │       │   └── JobStatusRow.tsx                    # Single row showing tool name + status (waiting/running/done/failed)
│       │       │
│       │       ├── results/
│       │       │   ├── MetricsSummaryTable.tsx             # Sortable table of per-tool aggregate metrics (precision/recall/F1/TEDS/GriTS/cost/time)
│       │       │   ├── ComplexityBarChart.tsx              # Bar chart: F1 by complexity tier, one bar per tool (Recharts)
│       │       │   ├── TedsTrendChart.tsx                  # Line chart: TEDS by complexity tier, one line per tool (Recharts)
│       │       │   ├── DocumentDrillDown.tsx               # Document selector + per-result table with eye button → comparison modal
│       │       │   └── ExtractionComparisonModal.tsx       # Side-by-side view of extracted table vs. ground truth; shows F1 + TEDS badges
│       │       │
│       │       └── ui/
│       │           └── ProfessionalPagination.tsx          # Paginator with ellipsis; currently unused in the 3 active pages
│       │
│       ├── context/
│       │   └── ThemeContext.tsx     # React context for light/dark/system theme; persists to localStorage
│       │
│       ├── hooks/
│       │   ├── useSectionVisibility.ts   # IntersectionObserver + scroll hook (scroll progress calculation); NOT used in active pages
│       │   └── useThemeHydration.ts      # Prevents SSR hydration mismatch for theme-dependent rendering
│       │
│       └── lib/
│           └── utils.ts            # cn() helper: merges Tailwind classes via clsx + tailwind-merge
│
└── server/                         # FastAPI backend (thesis + legacy code)
    ├── requirements.txt            # All Python dependencies
    ├── runtime.txt                 # python-3.11.13
    ├── README.md                   # Outdated; describes old commission tracker, not thesis tool
    ├── start.sh                    # Uvicorn start script with configurable timeouts
    ├── init_db.py                  # Standalone script to create and verify the 4 DB tables
    ├── .env                        # All env vars (COMMITTED WITH REAL CREDENTIALS — SECURITY RISK)
    │
    ├── configs/
    │   └── new_extraction_config.yaml   # Config for legacy EnhancedExtractionService (TableFormer settings, OCR, processing params)
    │
    ├── config/
    │   └── timeouts.py             # Centralised timeout dataclass; reads from env vars with fallback defaults
    │
    └── app/
        ├── main.py                 # FastAPI app; CORS; startup DB creation; includes 4 active routers
        ├── config.py               # Loads API keys (OpenAI, Anthropic, Mistral, Google) from env
        │
        ├── db/
        │   ├── database.py         # Async SQLAlchemy engine + session factory; DB URL priority: LOCAL → RENDER → SUPABASE
        │   ├── models.py           # 4 active ORM models: Document, GroundTruthTable, ExtractionResult, EvaluationScore
        │   ├── schemas.py          # LEGACY: 25+ Pydantic schemas for old commission tracker (inactive)
        │   ├── otp_schemas.py      # LEGACY: OTP/auth schemas (inactive)
        │   ├── crud.py             # LEGACY: Central re-export of all CRUD functions (inactive)
        │   └── crud/               # LEGACY: Granular CRUD modules for old commission tracker (inactive)
        │       ├── __init__.py
        │       ├── database_fields.py
        │       ├── extraction.py
        │       └── plan_types.py
        │
        ├── api/                    # Route handlers
        │   ├── documents.py        # ACTIVE: PDF upload, list, get, delete, update-tier
        │   ├── ground_truth.py     # ACTIVE: GT annotation CRUD (create, list, update, delete)
        │   ├── evaluation.py       # ACTIVE: Run evaluation (single doc, batch); get results; export CSV
        │   ├── eval_websocket.py   # ACTIVE: WebSocket endpoint for live evaluation progress
        │   ├── new_extract.py      # LEGACY: Smart extraction with GCS, format learning, carrier detection (not in main.py)
        │   ├── excel_extract.py    # LEGACY: Excel extraction endpoints (not in main.py)
        │   ├── date_extraction.py  # LEGACY: Date extraction endpoints (not in main.py)
        │   └── table_editor.py     # LEGACY: Table editor save/load/export/learn-format (not in main.py)
        │
        ├── services/
        │   ├── evaluation/
        │   │   ├── runner.py       # ACTIVE: EvaluationRunner; dispatches to each tool; normalises output; persists ExtractionResult
        │   │   ├── metrics.py      # ACTIVE: compute_cell_f1, compute_teds, compute_grits
        │   │   └── cost_calculator.py  # ACTIVE: Estimates cost per tool (hardcoded token/page rates)
        │   │
        │   ├── claude/
        │   │   ├── service.py      # ACTIVE: ClaudeDocumentAIService; async Anthropic client; chunking for large PDFs; retry logic
        │   │   ├── prompts.py      # ACTIVE: All Claude prompt templates (table extraction, metadata, quality, chunk, summarize)
        │   │   ├── models.py       # ACTIVE: Pydantic models for Claude input/output
        │   │   └── utils.py        # ACTIVE: ClaudePDFProcessor, ClaudeTokenEstimator, ClaudeResponseParser, ClaudeQualityAssessor, ClaudeErrorHandler
        │   │
        │   ├── mistral/
        │   │   ├── service.py      # ACTIVE: MistralDocumentAIService; two-phase extraction (document + table intelligence); 1800s timeout
        │   │   ├── prompts.py      # ACTIVE: All Mistral prompt templates (4 prompts)
        │   │   ├── models.py       # ACTIVE: Pydantic models for Mistral input/output
        │   │   └── utils.py        # ACTIVE: PDF/image processing utilities for Mistral
        │   │
        │   ├── ai/
        │   │   ├── __init__.py
        │   │   └── gpt4o_vision_service.py  # ACTIVE: GPT4oVisionService; digital vs scanned PDF detection; renders pages to base64 images; OpenAI synchronous client
        │   │
        │   ├── google_docai/
        │   │   ├── extractor.py    # ACTIVE: GoogleDocAIExtractor; Form Parser; chunked processing; table stitching
        │   │   ├── config.py       # ACTIVE: DocAI client config
        │   │   ├── processing.py   # ACTIVE: DocumentProcessor wrapper
        │   │   ├── table_extraction.py  # ACTIVE: TableExtractor from DocAI response
        │   │   ├── post_processing.py   # ACTIVE: Stitching, cleaning, normalisation
        │   │   └── utils.py        # ACTIVE: Text cleaning, company name detection for DocAI
        │   │
        │   ├── docling/
        │   │   ├── pipeline.py     # ACTIVE: ExtractionPipeline; multi-stage table extraction; adaptive strategies; sequential table merging
        │   │   ├── core/           # ACTIVE: Sub-components (DocumentProcessor, TableFormerModel, MultiPageTableHandler, etc.)
        │   │   ├── ocr/            # ACTIVE: OCREngine, AdvancedOCREngine wrappers
        │   │   ├── evaluation.py   # ACTIVE: AdvancedEvaluationMetrics
        │   │   ├── financial.py    # ACTIVE: SmartFinancialDocumentProcessor
        │   │   └── utils/
        │   │       └── compatibility.py  # PIL ANTIALIAS deprecation fix applied at import time
        │   │
        │   ├── extraction/
        │   │   └── extraction_utils.py  # LEGACY (also used by active services): normalize_statement_date; header similarity; stitch_multipage_tables; ~1800 lines
        │   │
        │   └── data_processing/    # LEGACY (some used by active AI services):
        │       ├── data_formatting_service.py   # DataFormattingService used by GPT4oVisionService
        │       ├── company_name_service.py      # CompanyNameDetectionService used by GPT4oVisionService + DocAI
        │       └── ...             # Other data processing utilities (duplicate detection, format learning, etc.)
        │
        └── utils/
            └── db_retry.py         # retry_db_operation / with_db_retry: exponential backoff for transient DB errors
```

---

## 6. Backend Architecture

### Active Application Entry Point

**`server/app/main.py`**

- Creates `FastAPI` instance with CORS middleware (`allow_origins=["*"]`, all methods/headers, allow_credentials)
- On startup: calls `Base.metadata.create_all` to create all 4 tables if they don't exist
- Registers 4 routers (all under `/api/...`):
  - `documents` at prefix `/api`
  - `ground_truth` at prefix `/api`
  - `evaluation` at prefix `/api`
  - `eval_websocket` at prefix `/api/ws`
- Exposes `GET /health` → `{"status": "ok"}`

### Active API Endpoints

#### Documents (`server/app/api/documents.py`)

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/documents/upload` | Upload PDF; analyse with PyMuPDF (page count, digital/scanned); save to `data/pdfs/`; insert `Document` record |
| GET | `/api/documents/` | List all documents ordered by `uploaded_at` desc |
| GET | `/api/documents/{doc_id}` | Get single document by UUID |
| DELETE | `/api/documents/{doc_id}` | Cascading delete: evaluation scores → extraction results → ground truth → document; delete physical file |
| PATCH | `/api/documents/{doc_id}/tier` | Update `complexity_tier` (low / medium / high) |

#### Ground Truth (`server/app/api/ground_truth.py`)

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/ground-truth/{doc_id}` | Create ground truth table for a document (checks for duplicate `table_index`) |
| GET | `/api/ground-truth/{doc_id}` | List all GT tables for a document, ordered by `table_index` |
| PUT | `/api/ground-truth/{doc_id}/{table_index}` | Update existing GT table |
| DELETE | `/api/ground-truth/{doc_id}/{table_index}` | Delete specific GT table |

#### Evaluation (`server/app/api/evaluation.py`)

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/evaluate/{doc_id}` | Run specified tools on one document; compute metrics; persist `ExtractionResult` + `EvaluationScore` |
| POST | `/api/evaluate/batch` | Run evaluation across all docs (optionally filtered by tier); skips docs without GT |
| GET | `/api/results/` | Retrieve all evaluation results (joined: EvaluationScore + ExtractionResult + Document) |
| GET | `/api/results/{doc_id}` | Retrieve evaluation results for a specific document |
| GET | `/api/results/export/csv` | Stream all results as CSV download |

#### WebSocket (`server/app/api/eval_websocket.py`)

| Protocol | Path | Purpose |
|---|---|---|
| WebSocket | `/api/ws/evaluation/{job_id}` | Subscribe to evaluation progress events for a given `job_id` |

**WebSocket message types** (JSON objects broadcast by `EvalProgressManager.send_progress`):
- `{ "type": "tool_start", "tool": "<tool_id>" }`
- `{ "type": "tool_done", "tool": "<tool_id>" }`
- `{ "type": "tool_failed", "tool": "<tool_id>" }`
- `{ "type": "doc_start", "filename": "<name>" }`
- `{ "type": "doc_complete" }`
- `{ "type": "job_complete" }`

> **Limitation**: The evaluation routes do NOT currently call `eval_progress.send_progress()`. The WebSocket infrastructure exists but the evaluation API does not push messages to it. Real-time updates are not functional.

### Database Layer (`server/app/db/database.py`)

- Uses `create_async_engine` with PostgreSQL + asyncpg
- Connection URL priority: `LOCAL_DB_KEY` → `RENDER_DB_KEY` → `SUPABASE_DB_KEY` → `postgresql+asyncpg://localhost/commission_tracker`
- Pool settings: `pool_size=5`, `max_overflow=10`, `pool_timeout=30`, `pool_recycle=3600`, `pool_pre_ping=True`
- `connect_args`: `command_timeout=60`, `server_settings={"statement_timeout": "300000"}`
- `get_db()` — async dependency for FastAPI route handlers
- `get_sync_db()` — sync session generator for non-async contexts

### Evaluation Runner (`server/app/services/evaluation/runner.py`)

The `EvaluationRunner` class manages lazy-initialised instances of all tool services and dispatches `run_tool(pdf_path, doc_id, tool_name, db)` for each tool requested.

**Tool dispatch map:**
- `pymupdf` → `_extract_pymupdf`: uses `pdfplumber` to extract all tables; converts to `{headers, rows}` format
- `docling` → `_extract_docling`: calls `ExtractionPipeline.extract_tables` (async, wrapped in thread)
- `google_docai` → `_extract_google_docai`: calls `GoogleDocAIExtractor.extract_tables_async`
- `gpt5` → `_extract_gpt5`: calls `GPT4oVisionService.extract_commission_data` (sync, wrapped in thread)
- `claude_sonnet` → `_extract_claude`: calls `ClaudeDocumentAIService.extract_commission_data` (async)
- `mistral` → `_extract_mistral`: calls `MistralDocumentAIService.extract_commission_data_via_ocr` (async)

After each tool call, `run_tool` measures wall-clock time, estimates cost via `cost_calculator.calculate_cost()`, and persists one `ExtractionResult` row per extracted table.

### Metrics (`server/app/services/evaluation/metrics.py`)

**`compute_cell_f1(pred_headers, pred_rows, gt_headers, gt_rows)`**
- Flattens all cells from headers + rows into a multiset
- Normalises each cell: lowercase, strip, remove `$`, `,`
- Computes precision = |pred ∩ gt| / |pred|, recall = |pred ∩ gt| / |gt|, F1

**`compute_teds(pred, gt)`**
- Converts each table to minimal HTML (`<table><tr><th>/<td>`)
- Parses HTML into an element tree
- Computes Tree Edit Distance (TED) between trees
- TEDS = 1 − (TED / max(|pred_tree|, |gt_tree|))

**`compute_grits(pred, gt)`**
- Builds a grid from the table data
- Computes row and column similarity via best-match scoring
- Returns `grits_top` (topology), `grits_con` (content), `grits_loc` (location)

### Cost Calculator (`server/app/services/evaluation/cost_calculator.py`)

Hardcoded rates:
- `pymupdf`: $0.00 (rule-based, free)
- `google_docai`: $0.0015 per page (hardcoded `PRICE_PER_PAGE`)
- `gpt5` (GPT-4o): input $2.50 / 1M tokens, output $10.00 / 1M tokens
- `claude_sonnet`: input $3.00 / 1M tokens, output $15.00 / 1M tokens
- `mistral` (Pixtral Large): input $2.00 / 1M tokens, output $6.00 / 1M tokens
- `docling`: $0.00 (local model, free)
- Default tokens per page estimate: 500 input + 1000 output

### Legacy Inactive API Files

These files exist in `server/app/api/` but are NOT registered in `main.py`:

- **`new_extract.py`**: ~900 lines. Smart PDF extraction with GCS upload, duplicate detection (SHA256), carrier name detection, `FormatLearningService`, `TableSuitabilityService`, `AIPlanTypeDetectionService`. Imports from modules that may not fully exist in current state.
- **`excel_extract.py`**: Excel (.xlsx/.xls/.xlsm/.xlsb) extraction with multi-sheet support, GCS integration.
- **`date_extraction.py`**: Extracts document dates from first page of PDF/image/Excel.
- **`table_editor.py`**: Saves user-edited tables; triggers format learning; exports CSV/JSON.

---

## 7. Frontend Architecture

### Application Shell (`client/src/app/layout.tsx`)

Wraps all pages with:
- `ThemeProvider` (light/dark/system with localStorage persistence)
- `Navbar` (sticky top bar)
- `Toaster` (react-hot-toast, top-center)
- Inter font via `next/font/google`

### Routing

Next.js App Router. All routes are under `src/app/`:

| Route | Component | Purpose |
|---|---|---|
| `/` | `page.tsx` | Redirect to `/corpus` |
| `/corpus` | `corpus/page.tsx` | Document management + GT annotation |
| `/evaluation` | `evaluation/page.tsx` | Benchmark configuration + execution |
| `/results` | `results/page.tsx` | Results visualisation |

### Page: `/corpus` (`client/src/app/corpus/page.tsx`)

**State**: `documents[]`, `gtCounts` (Record<docId, count>), `loading`

**Data fetching** (`fetchDocuments`):
1. `GET /api/documents/` → list of documents
2. For each document in parallel: `GET /api/ground-truth/{doc.id}` → count of GT tables

**Renders**:
- `DocumentUploadZone` — on successful upload calls `fetchDocuments`
- `DocumentTable` — shows all documents with tier editor, GT count badge, and actions (view GT, edit GT, delete)
- Refresh button

### Page: `/evaluation` (`client/src/app/evaluation/page.tsx`)

**State**: `selectedTools[]`, `tier` (low/medium/high/all), `documents[]`, `docFilter`, `docSearch`, `running`, `jobId`, `totalDocs`

**Data fetching**: `GET /api/documents/` on mount

**On "Run Evaluation"**: generates a UUID `jobId`, calls `POST /api/evaluate/batch` with `{ tools, complexity_tier, job_id }`, sets `running=true`

**Renders**:
- `ToolSelector` (checkbox grid for 6 tools)
- Complexity tier radio buttons
- Document search + filtered document list
- `EvaluationProgressPanel` (when running) — WebSocket subscriber

### Page: `/results` (`client/src/app/results/page.tsx`)

**State**: `rows[]` (raw evaluation results), `documents[]`, `loading`

**Data fetching**: `GET /api/results/` + `GET /api/documents/` on mount

**Helper functions**:
- `avg(arr)` — calculates mean, ignoring nulls
- `buildToolSummaries(rows)` — aggregates per-tool: avg precision/recall/F1/TEDS/GriTS-top/GriTS-con, cost per page, avg time
- `buildChartData(rows, documents)` — formats data for charts: rows indexed by complexity tier, columns by tool
- `buildResultsByDoc(rows)` — groups rows by `document_id`

**Renders**:
- `MetricsSummaryTable` — sortable aggregate metrics table
- `ComplexityBarChart` — F1 by complexity tier (bar chart)
- `TedsTrendChart` — TEDS by complexity tier (line chart)
- `DocumentDrillDown` — per-document drill-down + `ExtractionComparisonModal`
- Export CSV button → `GET /api/results/export/csv`

### Components

| Component | Props | API Calls | Notes |
|---|---|---|---|
| `Navbar` | — | — | Active link detection via `usePathname`; dark mode toggle |
| `DocumentUploadZone` | `onUploaded` | `POST /api/documents/upload` | Drag-and-drop; PDF only; defaults tier to 'medium' |
| `DocumentTable` | `documents`, `groundTruthCounts`, `onRefresh` | `PATCH /api/documents/{id}/tier`, `DELETE /api/documents/{id}` | Opens `GroundTruthModal` and `GroundTruthEditor` |
| `TierBadge` | `tier` | — | Colour-coded badge (green/amber/red) |
| `GroundTruthModal` | `docId`, `filename`, `onClose` | `GET /api/ground-truth/{docId}` | Read-only table viewer |
| `GroundTruthEditor` | `docId`, `filename`, `onClose`, `onSaved` | `GET`, `POST`, `PUT /api/ground-truth/...` | Full CRUD editor; multi-table tabs; add/remove rows + columns |
| `ToolSelector` | `selected`, `onChange` | — | Defines `ALL_TOOLS` constant (6 tools) |
| `EvaluationProgressPanel` | `jobId`, `selectedTools`, `totalDocs`, `onComplete` | WebSocket `/api/ws/evaluation/{jobId}` | Live progress; per-tool `JobStatusRow` |
| `JobStatusRow` | `toolName`, `status` | — | Displays waiting/running/done/failed with icons |
| `MetricsSummaryTable` | `data: ToolSummary[]` | — | Sortable by any column; F1 sorted desc by default |
| `ComplexityBarChart` | `data`, `tools` | — | Recharts BarChart; tier on X axis; score 0–1 on Y axis |
| `TedsTrendChart` | `data`, `tools` | — | Recharts LineChart; same axes |
| `DocumentDrillDown` | `documents`, `resultsByDoc` | — | Drop-down document selector; table of per-result metrics; opens comparison modal |
| `ExtractionComparisonModal` | `docId`, `filename`, `toolName`, `tableIndex`, `onClose` | `GET /api/results/{docId}`, `GET /api/ground-truth/{docId}` | Side-by-side extracted vs GT; F1 + TEDS badges |
| `LoadingScreen` | `message?`, `className?` | — | Full-screen spinner with animated FlaskConical icon |
| `Modal` | `children`, `onClose` | — | Generic accessible modal with ESC key + focus trap |
| `ProfessionalPagination` | `currentPage`, `totalPages`, `onPageChange` | — | Pagination with ellipsis — **currently unused in active pages** |

### Theme Context (`client/src/context/ThemeContext.tsx`)

- `ThemeProvider` wraps app; detects system preference
- Persists to `localStorage` key `commission-tracker-theme` (legacy name)
- Exposes `useTheme()` hook: `{ theme, setTheme, actualTheme }`

### Custom Hooks

- `useThemeHydration()` — prevents SSR hydration mismatch; returns `{ mounted, actualTheme, isDark, isLight, isSystem }`
- `useSectionVisibility()` — IntersectionObserver + scroll-based section visibility with `scrollProgress`; **not used in any active page**

### Utility (`client/src/lib/utils.ts`)

- `cn(...inputs)` — merges Tailwind class names via `clsx` + `tailwind-merge`

---

## 8. Database / Storage Schema

### Active Tables (defined in `server/app/db/models.py`)

#### `documents`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK, default `uuid4` | — |
| `filename` | String | NOT NULL | Original file name |
| `complexity_tier` | String | NOT NULL, default `'medium'` | `'low'` / `'medium'` / `'high'` |
| `page_count` | Integer | nullable | Detected by PyMuPDF on upload |
| `is_digital` | Boolean | nullable | True = text-based PDF, False = scanned |
| `uploaded_at` | DateTime | default `utcnow` | UTC timestamp |
| `file_path` | String | nullable | Relative path under `data/pdfs/` |

#### `ground_truth_tables`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK, default `uuid4` | — |
| `document_id` | UUID | FK → `documents.id` | — |
| `table_index` | Integer | NOT NULL | 0-based table index in document |
| `headers` | JSON | NOT NULL | `string[]` — column header names |
| `rows` | JSON | NOT NULL | `string[][]` — cell values |
| `annotated_at` | DateTime | default `utcnow` | UTC timestamp |
| `notes` | String | nullable | Annotator notes |

#### `extraction_results`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK, default `uuid4` | — |
| `document_id` | UUID | FK → `documents.id` | — |
| `tool_name` | String | NOT NULL | `pymupdf`, `docling`, `google_docai`, `gpt5`, `claude_sonnet`, `mistral` |
| `table_index` | Integer | NOT NULL | Which table from the document |
| `extracted_headers` | JSON | nullable | `string[]` |
| `extracted_rows` | JSON | nullable | `string[][]` |
| `processing_time_ms` | Integer | nullable | Wall-clock ms |
| `cost_usd` | Float | nullable | Estimated cost |
| `error_message` | String | nullable | Error if extraction failed |
| `extracted_at` | DateTime | default `utcnow` | UTC timestamp |

#### `evaluation_scores`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK, default `uuid4` | — |
| `extraction_result_id` | UUID | FK → `extraction_results.id` | — |
| `precision` | Float | nullable | Cell-level precision |
| `recall` | Float | nullable | Cell-level recall |
| `f1_score` | Float | nullable | Cell-level F1 |
| `teds_score` | Float | nullable | Tree Edit Distance Similarity |
| `grits_top` | Float | nullable | GriTS topology |
| `grits_con` | Float | nullable | GriTS content |
| `grits_loc` | Float | nullable | GriTS location |
| `computed_at` | DateTime | default `utcnow` | UTC timestamp |

### Physical File Storage

Uploaded PDFs are stored locally at `server/data/pdfs/{filename}` (the `data/pdfs/` directory is created on demand by the upload endpoint). There is no cloud storage integration in the active code.

### Legacy Database Artifacts

`server/app/db/schemas.py` contains 25+ Pydantic schemas for the old commission tracker (`Company`, `CompanyFieldMapping`, `StatementUpload`, `EarnedCommission`, `UserProfile`, etc.) and `server/app/db/crud/` contains CRUD modules referencing models like `DatabaseField`, `PlanType`, `Extraction` that are **not present in the current `models.py`**. These are dead code and will fail at runtime if called.

---

## 9. Extraction Pipeline (Current State)

### Overview

```
PDF file (on disk)
    │
    ▼
EvaluationRunner.run_tool(pdf_path, tool_name)
    │
    ├─ pymupdf ──────────────────────────────────────────────────────────────────┐
    │       pdfplumber.open(pdf_path)                                            │
    │       .extract_tables() per page                                           │
    │       → [{headers, rows}, ...]                                             │
    │                                                                            │
    ├─ docling ──────────────────────────────────────────────────────────────────┤
    │       ExtractionPipeline.extract_tables(pdf_path)                          │
    │       → DoclingConverter → TableFormer model (microsoft/table-transformer) │
    │       → OCR (EasyOCR fallback) for scanned pages                           │
    │       → MultiPageTableHandler for cross-page merging                       │
    │       → SmartFinancialDocumentProcessor                                    │
    │       → [{headers, rows, confidence, ...}, ...]                           │
    │                                                                            │
    ├─ google_docai ─────────────────────────────────────────────────────────────┤
    │       GoogleDocAIExtractor.extract_tables_async(pdf_path)                  │
    │       Sends raw PDF bytes to Google Document AI Form Parser                │
    │       Processor: DOCAI_PROJECT_ID / DOCAI_PROCESSOR_ID (Form Parser)       │
    │       Chunks > N pages; stitches multi-page tables                         │
    │       → [{headers, rows}, ...]                                             │
    │                                                                            │
    ├─ gpt5 (GPT-4o Vision) ─────────────────────────────────────────────────────┤
    │       GPT4oVisionService.extract_commission_data(pdf_path)                 │
    │       Detects digital vs scanned (PyMuPDF text analysis)                   │
    │       Renders each page (up to 5) → base64 PNG images                      │
    │       Sends images + prompt to OpenAI chat.completions.create              │
    │       Model: gpt-4o (the service is labelled "gpt5" in the code)           │
    │       Response: JSON with tables array                                      │
    │       → [{headers, rows}, ...]                                             │
    │                                                                            │
    ├─ claude_sonnet ────────────────────────────────────────────────────────────┤
    │       ClaudeDocumentAIService.extract_commission_data(pdf_path)            │
    │       Reads PDF → base64                                                    │
    │       Large files (>10MB or >50 pages): split into chunks                  │
    │       Sends document (base64 PDF) + prompt via Anthropic messages API      │
    │       Model: claude-sonnet-4-20250514 (primary), fallback configurable     │
    │       Retries up to 3 times with exponential backoff                        │
    │       Parses JSON from response (with markdown fence cleanup)               │
    │       → [{headers, rows, confidence, ...}, ...]                            │
    │                                                                            │
    └─ mistral ──────────────────────────────────────────────────────────────────┘
            MistralDocumentAIService.extract_commission_data_via_ocr(pdf_path)
            Two-phase extraction:
              Phase 1A: Document Intelligence (carrier, date, broker)
              Phase 1B: Table Intelligence (table structure extraction)
            Renders pages → images → base64
            Sends to Mistral chat API (model: pixtral-large-latest or similar)
            1800s timeout; tenacity retry
            → [{headers, rows, confidence, ...}, ...]
                                │
                                ▼
                    _normalise_tables(raw_output, tool_name)
                    Standardises to [{headers: string[], rows: string[][]}, ...]
                                │
                                ▼
                    For each table vs each GT table at same index:
                        compute_cell_f1() → precision, recall, f1
                        compute_teds()    → teds_score
                        compute_grits()   → grits_top, grits_con, grits_loc
                                │
                                ▼
                    INSERT ExtractionResult (headers, rows, time_ms, cost_usd)
                    INSERT EvaluationScore (precision, recall, f1, teds, grits)
```

### PyMuPDF Tool Detail

- Library: `pdfplumber`
- Method: `pdf.pages[i].extract_tables()` for each page
- First row of each extracted table is treated as headers
- Remaining rows are data rows
- No AI model involved

### Docling Tool Detail

- Library: `docling` (wraps Microsoft TableFormer)
- Model: `microsoft/table-transformer-structure-recognition-v1.1-all`
- Layout model: `microsoft/layoutlmv3-base`
- OCR: EasyOCR (primary), Tesseract (fallback)
- Processing: document parsing → table detection → structure recognition → text extraction → post-processing → validation
- Multi-page table merging: header similarity check (>= 0.8 Jaccard similarity) + structural pattern matching
- Financial document processor for detecting summary rows

### Google Document AI Tool Detail

- API: `google.cloud.documentai_v1beta3`
- Processor type: Form Parser
- Authentication: service account JSON from `/etc/secrets/pdf-tables-extractor-*.json` or env var
- Input: raw PDF bytes
- Chunked processing for large documents
- Post-processing: text cleaning, company name detection, multi-page table stitching

### GPT-4o Vision Tool Detail

- Library: `openai` (synchronous `OpenAI` client)
- Model: `gpt-4o`
- Input format: base64-encoded PNG images of each page (max 5 pages)
- Rendering: PyMuPDF renders PDF pages at 144 DPI → PIL image → base64 PNG
- Prompt: see Section 10 (partial — file was 1317+ lines, prompt was not in first 80 lines read)

### Claude Tool Detail

- Library: `anthropic` (async `AsyncAnthropic`)
- Model: `claude-sonnet-4-20250514` (primary)
- Input format: base64-encoded raw PDF bytes sent as `{"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": ...}}`
- Max file: 10MB / 50 pages before chunking
- Retry: up to 3 attempts with exponential backoff; `asyncio.wait_for` timeout
- Prompt: see Section 10

### Mistral Tool Detail

- Library: `mistralai`
- Model: `pixtral-large-latest` (or similar Pixtral Large)
- Input format: base64-encoded page images
- Two-phase: Phase 1A (document intelligence) + Phase 1B (table intelligence)
- Timeout: 1800 seconds (30 minutes)
- Retry: `tenacity` retry decorator
- Prompts: see Section 10

---

## 10. LLM Prompts

### Claude — System Prompt (`server/app/services/claude/prompts.py → get_system_prompt()`)

```
You are an expert AI assistant specializing in document analysis and data extraction, 
with deep expertise in insurance commission statements. You excel at accurately 
extracting structured data from complex financial documents while maintaining 
data integrity and handling edge cases gracefully.
```

### Claude — Table Extraction Prompt (`get_table_extraction_prompt()`)

```
Extract ALL tables and document metadata from this insurance commission statement PDF.

CRITICAL REQUIREMENTS:
1. Extract EVERY table in the document - do not skip any tables
2. Preserve exact table structure with all columns and rows
3. Include ALL data rows - do not truncate or summarize
4. Maintain financial data accuracy - preserve exact numbers, percentages, amounts
5. Handle complex table structures: merged cells, multi-line headers, nested tables

CARRIER EXTRACTION RULES (CRITICAL):
- Look for carrier/insurance company name in document HEADER or FOOTER or LETTERHEAD
- The carrier is typically the company sending the commission statement
- Do NOT extract carrier from table data (individual policy records)
- Carrier name appears at top of document, in logos, or in "From:" fields
- Examples: "Anthem Blue Cross", "UnitedHealthcare", "Aetna", "Cigna"

STATEMENT DATE RULES (CRITICAL):
- Extract the STATEMENT/PERIOD date, not individual policy dates
- If date range is shown (e.g., "March 1-31, 2024"), extract as range
- Statement date is typically in header, title, or near carrier name
- Do NOT extract individual policy effective dates as the statement date

BROKER COMPANY RULES:
- Look for the agent/broker company name (the recipient of commissions)
- Usually appears as "Agency:", "Agent:", "Broker:", "To:", or in address block
- Different from carrier name

EXTRACT THIS METADATA:
- carrier_name: Insurance company sending the statement
- statement_date: Period or date of the statement
- broker_company: Agency/broker receiving commissions

RETURN FORMAT - Respond with ONLY valid JSON, no markdown:
{
  "tables": [
    {
      "headers": ["col1", "col2", "col3"],
      "rows": [["val1", "val2", "val3"], ...],
      "table_type": "commission_detail|summary|other",
      "page_number": 1,
      "confidence_score": 0.95
    }
  ],
  "metadata": {
    "carrier_name": "...",
    "statement_date": "...",
    "broker_company": "...",
    "document_type": "commission_statement"
  }
}
```

### Claude — Metadata Extraction Prompt (`get_metadata_extraction_prompt()`)

```
Extract ONLY the key document metadata from this insurance commission statement.

CARRIER NAME RULES (CRITICAL):
- Look in document HEADER, FOOTER, LETTERHEAD
- The carrier is the INSURANCE COMPANY sending commissions
- Do NOT use carrier names from table data/policy records
- Look for company logos, "From:", letterhead

STATEMENT DATE RULES (CRITICAL):
- Extract the STATEMENT PERIOD date range if shown
- Format: "YYYY-MM-DD" or "Month DD, YYYY - Month DD, YYYY" for ranges
- Look in header/title area, near carrier name
- Do NOT extract individual policy dates

BROKER COMPANY:
- The agent/broker RECEIVING commissions
- Look for "Agency:", "Agent:", "To:", address block

Return ONLY valid JSON:
{
  "carrier_name": "...",
  "statement_date": "...",
  "broker_company": "...",
  "document_type": "commission_statement|invoice|other"
}
```

### Claude — Quality Assessment Prompt (`get_quality_assessment_prompt()`)

```
You are a quality assurance expert. Review this extraction result and provide a quality assessment.

Evaluate:
1. Overall confidence in the extraction accuracy (0.0-1.0)
2. Table structure correctness (headers properly identified, rows aligned)
3. Data completeness (all tables extracted, no truncation)
4. Potential issues or anomalies

Return ONLY valid JSON:
{
  "overall_confidence": 0.95,
  "table_structure_score": 0.90,
  "data_completeness": 0.85,
  "extraction_accuracy": 0.90,
  "issues_detected": ["list of any issues found"],
  "quality_grade": "A|B|C|D|F"
}
```

### Claude — Large Document Summary Prompt (`get_large_document_summary_prompt()`)

Template that asks Claude to summarise document structure for large files before chunked extraction. (Full text in `server/app/services/claude/prompts.py`.)

### Claude — Chunk Extraction Prompt (`get_chunk_extraction_prompt()`)

Template for extracting tables from a specific chunk of a large document, with context about which chunk this is. (Full text in `server/app/services/claude/prompts.py`.)

### Claude — Summarize Extraction Prompt (`get_summarize_extraction_prompt()`)

```
You are an OCR agent. Extract structured data from this invoice/document.

Important:
- Extract all text content in a structured format
- Do NOT create or extract tables - return plain text only
- Focus on key fields: dates, amounts, parties, line items
- Format as clean Markdown without tables

Return the extracted data as formatted Markdown text.
```

---

### Mistral — Document Intelligence Prompt (`server/app/services/mistral/prompts.py → get_document_intelligence_prompt()`)

```
You are an expert business document analyst with 20+ years of experience processing 
insurance commission statements, financial reports, and business documents.

PHASE 1A: DOCUMENT INTELLIGENCE ANALYSIS

Your task is to perform a comprehensive document intelligence analysis:

1. DOCUMENT COMPREHENSION
   - Understand the overall document structure and purpose
   - Identify the primary document type and business context
   - Analyze layout patterns and information hierarchy

2. CARRIER/INSURANCE COMPANY IDENTIFICATION (CRITICAL)
   IMPORTANT RULES:
   - The CARRIER is the insurance company sending the commission statement
   - Look for carrier name in: document HEADER, LETTERHEAD, LOGO TEXT, FOOTER
   - The carrier name is typically printed prominently at the TOP of the document
   - Look for phrases like "From:", "Prepared by:", company logos with text
   - DO NOT extract carrier from table data (individual policy or group records)
   - DO NOT use broker/agent names as carrier
   
3. STATEMENT DATE IDENTIFICATION (CRITICAL)
   IMPORTANT RULES:
   - Extract the STATEMENT PERIOD date, not individual policy dates
   - If a date RANGE is shown (e.g., "March 1-31, 2024"), extract the FULL RANGE
   - Format single dates as: "YYYY-MM-DD"
   - Format date ranges as: "YYYY-MM-DD to YYYY-MM-DD"
   - Look for: "Statement Period:", "For the period:", "Commission Period:", date in header
   
4. BROKER/AGENT ENTITY IDENTIFICATION
   - Identify the broker, agency, or agent RECEIVING the commissions
   - Look for: "To:", "Agency:", "Agent:", "Broker:", address blocks
   
5. DOCUMENT CLASSIFICATION
   - Classify document type with confidence scores

Return a comprehensive JSON analysis with confidence scores and evidence.
```

### Mistral — Table Intelligence Prompt (`get_table_intelligence_prompt()`)

```
You are an expert data extraction specialist with deep expertise in financial 
table structures and insurance commission data.

PHASE 1B: TABLE STRUCTURE INTELLIGENCE

Extract ALL tables from this document with business logic understanding:

EXTRACTION REQUIREMENTS:
1. Extract EVERY table - do not skip any
2. Preserve EXACT column structure and ALL data rows
3. Identify table purpose: commission_detail, summary, payment, other
4. Detect summary/total rows (last rows, rows with "Total", "Grand Total", etc.)
5. Handle merged cells by duplicating content

CRITICAL: structured_tables format:
{
  "structured_tables": [
    {
      "headers": ["exact", "column", "names"],
      "rows": [["row1col1", "row1col2"], ["row2col1", "row2col2"]],
      "table_type": "commission_detail|summary|payment|other",
      "confidence": 0.95
    }
  ]
}

Return ONLY the JSON object above, no additional text.
```

### Mistral — Enhanced Extraction Prompt (`get_enhanced_extraction_prompt()`)

Full prompt for Pixtral Large's advanced vision capabilities, emphasizing:
- 99%+ extraction completeness requirement
- All previous CARRIER/DATE rules
- Specific handling for accounting brackets `(amount)` as negative values
- Multi-page table continuation detection
- Returns combined metadata + tables JSON

(Full text in `server/app/services/mistral/prompts.py`)

### Mistral — Fallback Prompt (`get_fallback_prompt()`)

```
Extract all tables from this document. Return JSON with:
{
  "tables": [
    {
      "headers": ["col1", "col2"],
      "rows": [["val1", "val2"]]
    }
  ]
}
```

### GPT-4o Vision Prompt

The `GPT4oVisionService` prompt is in `server/app/services/ai/gpt4o_vision_service.py`. Only the first 80 lines of that 1317-line file were read during this audit. The full prompt text was not captured. Based on the service description, it sends page images with a prompt requesting extraction of commission tables in JSON format. **The exact prompt text requires reading lines 80+ of `gpt4o_vision_service.py`.**

---

## 11. Current Limitations and TODOs

### Critical Security Issue
- `server/.env` is **committed to the repository with real API keys and database credentials**. This includes `OPENAI_API_KEY`, `MISTRAL_API_KEY`, `CLAUDE_API_KEY`, `SUPABASE_DB_KEY`, `RENDER_DB_KEY`, `DOCAI_PROCESSOR_ID`. These should be rotated immediately.

### WebSocket Progress Not Wired
- `EvaluationProgressPanel` connects to the WebSocket endpoint and displays progress UI
- The evaluation router (`evaluation.py`) **never calls `eval_progress.send_progress()`**
- Real-time progress display is non-functional; the UI shows loading but receives no messages from backend

### PyMuPDF Tool Incorrectly Labelled
- The tool registered as `pymupdf` in `runner.py` actually uses `pdfplumber`, not PyMuPDF directly
- PyMuPDF (fitz) is used in the `documents` upload endpoint for page count / digital detection
- The `ToolSelector` component labels it "Rule-based PDF text extraction" which is correct

### GPT Labelling Mismatch
- The tool ID is `gpt5` throughout the codebase (runner, frontend constants, DB records)
- The actual model called is `gpt-4o` (OpenAI's GPT-4 Vision), not GPT-5
- This will cause confusion in results and published thesis data

### Missing GT Enforcement in Evaluation
- Batch evaluation skips documents without ground truth (correct)
- Single-document evaluation (`POST /api/evaluate/{doc_id}`) does NOT check for GT before running tools — it will run all tools and insert ExtractionResult rows, but EvaluationScore computation will fail/return zero if no GT exists

### Cost Estimates Are Rough
- `cost_calculator.py` uses hardcoded `_DEFAULT_TOKENS_PER_PAGE = {"input": 500, "output": 1000}` when actual token counts are unavailable
- Claude's `ClaudeTokenEstimator` uses `tiktoken` if available, otherwise character-based estimation
- Actual per-call token counts are not currently passed back to the runner for precise cost calculation

### Dead Code Volume
- Approximately 60-70% of the `server/` codebase is legacy commission tracker code that is completely inactive
- Key inactive modules: `new_extract.py`, `excel_extract.py`, `date_extraction.py`, `table_editor.py`, all `crud/` modules, `schemas.py`, `otp_schemas.py`, `server/app/services/extraction/`, `server/app/services/data_processing/` (partially)
- These modules contain imports from non-existent or partially-existent modules and would fail at import time if loaded

### Model Cache Directories
- Dockerfile pre-downloads EasyOCR + Docling + HF TableFormer models to persistent directories
- Local development requires internet access on first run for model downloads
- `configs/new_extraction_config.yaml` uses `/tmp/model_cache` which is ephemeral in containers

### Docling Pipeline Complexity vs Evaluation Use
- `ExtractionPipeline` in `docling/pipeline.py` is extremely complex (~1000+ lines) with adaptive strategies, financial processing, semantic similarity checks, and HOTFIX merge logic
- For evaluation purposes, a simpler/more reproducible Docling call might be preferable

### `server/README.md` Is Outdated
- Documents the old commission tracker API endpoints, not the thesis tool
- Should be replaced

### No Test Coverage for Active Code
- `pytest` is listed as a dev dependency
- No test files for the 4 active routers or evaluation runner were found in the repository

### `useSectionVisibility` and `ProfessionalPagination` Are Unused
- These frontend components/hooks exist but are not imported by any active page

---

## 12. What Is NOT Yet Implemented

### In the Active Thesis System

1. **Real-time WebSocket progress**: The WebSocket endpoint and client are fully implemented but the server never sends messages during evaluation. Wiring `eval_progress.send_progress()` into the evaluation runner loop is required.

2. **Per-document single evaluation trigger**: The UI only exposes batch evaluation. There is no button to run a single document through a single tool from the UI (though the API endpoint exists).

3. **Table index alignment for multi-table documents**: When a document has multiple tables, the evaluation matches `extraction_result.table_index` to `ground_truth_table.table_index`. If an extractor returns tables in a different order than the GT, scores will be computed against wrong GT tables. No alignment/matching logic exists.

4. **PDF viewer in corpus**: Users cannot preview the PDF they uploaded to verify page content while annotating ground truth. `pdfjs-dist` is installed but not used.

5. **GT import/export**: Ground truth tables can only be entered via the web editor. There is no CSV/JSON import or export for GT data.

6. **Authentication**: JWT/OTP infrastructure exists in the legacy code but is completely inactive. The API has no authentication — anyone with the URL can upload, delete, and run evaluations.

7. **Automatic table extraction to assist GT annotation**: When annotating ground truth, users type every cell manually. There is no "pre-fill from PyMuPDF" or similar assisted annotation.

8. **Statistical significance testing**: Results are displayed as averages but there is no confidence interval, p-value, or significance test between tool scores.

9. **Per-tool error analysis**: When a tool fails (error_message set), the UI shows "Error" status but does not display the error message text.

10. **Docling and Google DocAI credentials validation**: The system will silently fail if `DOCAI_PROJECT_ID`/`DOCAI_PROCESSOR_ID` are absent or if Google credentials file is missing — there is no pre-flight check at startup.

11. **Pagination in results**: `ProfessionalPagination` component is built but the results page loads all evaluation records at once with no pagination.

12. **Cost tracking for Docling**: `cost_calculator.py` returns $0.00 for Docling. If a cloud-hosted version of TableFormer were used, cost tracking would not exist.
