# PROJECT_CONTEXT.md

## 1. Project Overview

This project is a **Commission Tracker** — a full-stack web application that allows insurance brokers/agencies to upload commission statement documents (PDF and Excel files), automatically extract tabular data from them using multiple AI/ML extraction engines, map extracted fields to a standardised database schema, and track earned commissions per carrier, per client, over time. The system supports multi-tenant usage with OTP-based email authentication, role-based access control (admin/user/read_only), domain whitelisting, and per-user data isolation. The extraction pipeline is the core of the system: it employs Claude (Anthropic), Mistral AI (OCR + Pixtral Large), GPT-5/4o Vision (OpenAI), Google Document AI, and a local Docling/TableFormer/EasyOCR pipeline in a layered fallback architecture. The frontend is a Next.js 15 / React 19 dashboard with real-time WebSocket progress tracking, AI-assisted field mapping, editable table review, and commission analytics dashboards.

---

## 2. Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Frontend Framework | Next.js (App Router) | 15.3.4 |
| Frontend Library | React | 19.0.0 |
| Frontend Language | TypeScript | ^5 |
| CSS Framework | Tailwind CSS | ^4.1.11 |
| UI Component Library | Radix UI (dropdown, select, tabs, tooltip) | various |
| Charts | Chart.js + react-chartjs-2, Recharts | ^4.5.0 / ^3.1.2 |
| Animation | Framer Motion, @react-spring | ^12.23.12 / ^10.0.3 |
| PDF Viewing | @react-pdf-viewer, pdfjs-dist | ^3.12.0 / ^3.11.174 |
| Drag-and-Drop | @dnd-kit | ^6.3.1 / ^10.0.0 |
| Backend Framework | FastAPI | >=0.104.0 |
| Backend Language | Python | 3.11.13 |
| ASGI Server | Uvicorn | >=0.24.0 |
| Database | PostgreSQL (async via asyncpg) | — |
| ORM | SQLAlchemy (async) | >=2.0.0 |
| Database Providers | Local PostgreSQL / Render PostgreSQL / Supabase | — |
| AI: Primary Extraction | Anthropic Claude (claude-sonnet-4-20250514) | anthropic >=0.28.0 |
| AI: Fallback Extraction | Mistral AI (mistral-ocr-latest / Pixtral Large) | mistralai >=1.0.0 |
| AI: Vision Extraction | OpenAI GPT-5 / GPT-4o Vision | openai >=1.0.0 |
| AI: Field Mapping | Mistral AI (mistral-large-latest) | mistralai >=1.0.0 |
| Document AI | Google Document AI (Form Parser) | google-cloud-documentai >=2.25.0 |
| Local ML: Table Detection | Microsoft Table Transformer (HuggingFace) | transformers >=4.36.0 |
| Local ML: Document Processing | Docling | >=2.0.0 |
| OCR Engines | EasyOCR, Tesseract (pytesseract) | easyocr >=1.7.0 |
| Deep Learning Framework | PyTorch (CPU) | >=2.2.2 |
| PDF Processing | PyMuPDF, pdfplumber, pypdf, pdf2image | various |
| Image Processing | OpenCV (headless), Pillow, scikit-image | various |
| Cloud Storage | Google Cloud Storage | google-cloud-storage >=2.14.0 |
| Authentication | JWT (python-jose), OTP via email (aiosmtplib) | various |
| Caching (optional) | Redis | redis >=5.0.0 |
| Email | Gmail SMTP via aiosmtplib | aiosmtplib >=3.0.0 |
| Deployment | Render (Docker or native Python), Vercel (frontend) | — |
| Containerisation | Docker (python:3.11.13-slim) | — |

---

## 3. Installed Dependencies

### Backend Dependencies (`server/requirements.txt`)

| Package | Version Constraint |
|---------|--------------------|
| fastapi | >=0.104.0,<1.0.0 |
| uvicorn | >=0.24.0,<1.0.0 |
| websockets | >=12.0,<13.0 |
| sqlalchemy[asyncio] | >=2.0.0 |
| asyncpg | >=0.29.0 |
| psycopg2-binary | >=2.9.0 |
| google-cloud-documentai | >=2.25.0,<3.0.0 |
| google-cloud-storage | >=2.14.0,<3.0.0 |
| google-cloud-vision | >=3.4.0,<4.0.0 |
| google-auth | >=2.28.0,<3.0.0 |
| google-auth-oauthlib | >=1.1.0,<2.0.0 |
| google-auth-httplib2 | >=0.1.0,<1.0.0 |
| PyMuPDF | >=1.23.0,<2.0.0 |
| pdfplumber | >=0.11.0,<1.0.0 |
| pypdf | >=4.0.0,<5.0.0 |
| pdf2image | >=1.16.0,<2.0.0 |
| python-dotenv | >=1.0.0 |
| pydantic[email] | >=2.6.0,<3.0.0 |
| python-multipart | >=0.0.6,<1.0.0 |
| opencv-python-headless | >=4.8.0,<4.9.0 |
| Pillow | >=10.0.0 |
| numpy | >=1.24.0,<2.0.0 |
| scipy | >=1.10.0 |
| scikit-image | >=0.21.0 |
| scikit-learn | >=1.3.0,<2.0.0 |
| psutil | >=5.9.0,<6.0.0 |
| pandas | >=2.0.0,<3.0.0 |
| python-dateutil | >=2.8.0 |
| openpyxl | >=3.1.0,<4.0.0 |
| xlrd | >=2.0.0,<3.0.0 |
| openai | >=1.0.0,<2.0.0 |
| mistralai | >=1.0.0,<2.0.0 |
| anthropic | >=0.28.0,<1.0.0 |
| tiktoken | >=0.5.0,<1.0.0 |
| docling | >=2.0.0,<3.0.0 |
| torch | >=2.2.2,<3.0.0 (CPU-only via extra-index-url) |
| torchvision | >=0.17.0,<1.0.0 |
| transformers | >=4.36.0,<5.0.0 |
| huggingface-hub | >=0.23.0,<1.0.0 |
| easyocr | >=1.7.0,<2.0.0 |
| pytesseract | >=0.3.10,<1.0.0 |
| timm | >=0.9.0 |
| editdistance | >=0.8.0 |
| layoutparser | >=0.3.4,<1.0.0 |
| streamlit | >=1.28.0,<2.0.0 |
| tqdm | >=4.66.0,<5.0.0 |
| requests | >=2.32.0,<3.0.0 |
| loguru | >=0.7.0,<1.0.0 |
| pytest | >=7.4.0,<8.0.0 |
| pytest-cov | >=4.1.0,<5.0.0 |
| black | >=23.11.0,<24.0.0 |
| flake8 | >=6.1.0,<7.0.0 |
| mypy | >=1.7.0,<2.0.0 |
| python-jose[cryptography] | >=3.3.0,<4.0.0 |
| passlib[bcrypt] | >=1.7.4,<2.0.0 |
| redis | >=5.0.0,<6.0.0 |
| aiosmtplib | >=3.0.0,<4.0.0 |
| email-validator | >=2.1.0,<3.0.0 |

### Frontend Dependencies (`client/package.json`)

| Package | Version |
|---------|---------|
| next | 15.3.4 |
| react | ^19.0.0 |
| react-dom | ^19.0.0 |
| @dnd-kit/core | ^6.3.1 |
| @dnd-kit/sortable | ^10.0.0 |
| @dnd-kit/utilities | ^3.2.2 |
| @radix-ui/react-dropdown-menu | ^2.1.15 |
| @radix-ui/react-select | ^2.2.5 |
| @radix-ui/react-tabs | ^1.1.12 |
| @radix-ui/react-tooltip | ^1.2.7 |
| @react-pdf-viewer/core | ^3.12.0 |
| @react-pdf-viewer/default-layout | ^3.12.0 |
| @react-spring/parallax | ^10.0.3 |
| @react-spring/web | ^10.0.3 |
| @tailwindcss/postcss | ^4.1.11 |
| axios | ^1.6.0 |
| chart.js | ^4.5.0 |
| clsx | ^2.1.1 |
| formidable | ^3.5.4 |
| framer-motion | ^12.23.12 |
| js-cookie | ^3.0.5 |
| lucide-react | ^0.525.0 |
| pdf-lib | ^1.17.1 |
| pdf-parse | ^1.1.1 |
| pdfjs-dist | ^3.11.174 |
| postcss | ^8.5.6 |
| react-chartjs-2 | ^5.3.0 |
| react-dropzone | ^14.3.8 |
| react-hot-toast | ^2.5.2 |
| react-markdown | ^10.1.0 |
| react-select | ^5.10.1 |
| recharts | ^3.1.2 |
| tailwind-merge | ^3.3.1 |
| tailwindcss | ^4.1.11 |
| tailwindcss-animate | ^1.0.7 |
| xlsx | ^0.18.5 |

**Dev Dependencies:**
| Package | Version |
|---------|---------|
| @eslint/eslintrc | ^3 |
| @tailwindcss/typography | ^0.5.19 |
| @types/formidable | ^3.4.5 |
| @types/js-cookie | ^3.0.6 |
| @types/node | ^20 |
| @types/react | ^19 |
| @types/react-dom | ^19 |
| @types/xlsx | ^0.0.35 |
| eslint | ^9 |
| eslint-config-next | 15.3.4 |
| file-loader | ^6.2.0 |
| typescript | ^5 |

---

## 4. Environment Variables

| Variable | Purpose | Required? |
|----------|---------|-----------|
| `OPENAI_API_KEY` | OpenAI API key for GPT-5/4o Vision extraction | Yes (for GPT extraction) |
| `MISTRAL_API_KEY` | Mistral AI API key for OCR and Pixtral Large extraction | Yes (for Mistral extraction) |
| `MISTRAL_API_BASE` | Mistral API base URL | No (defaults to https://api.mistral.ai/v1) |
| `ANTHROPIC_API_KEY` / `CLAUDE_API_KEY` | Anthropic API key for Claude Document AI | Yes (for Claude extraction) |
| `CLAUDE_MODEL_PRIMARY` | Primary Claude model name | No (defaults to claude-sonnet-4-20250514) |
| `CLAUDE_MODEL_FALLBACK` | Fallback Claude model name | No (defaults to claude-sonnet-4-20250514) |
| `CLAUDE_MAX_TOKENS` | Max tokens for Claude responses | No (defaults to 4000) |
| `CLAUDE_TIMEOUT` | Claude API timeout in seconds | No (defaults to 300) |
| `LOCAL_DB_KEY` | Local PostgreSQL connection string (preferred) | No |
| `RENDER_DB_KEY` | Render PostgreSQL connection string (fallback) | No |
| `SUPABASE_DB_KEY` | Supabase PostgreSQL connection string (last fallback) | No |
| `GCS_BUCKET_NAME` | Google Cloud Storage bucket name | Yes (pdf_extraction_files_saver) |
| `GOOGLE_CLOUD_PROJECT_ID` | GCP project ID | Yes (pdf-tables-extractor-465009) |
| `GOOGLE_DOCAI_PROCESSOR_ID` / `DOCAI_PROCESSOR_ID` | Google Document AI processor ID | Yes (521303e404fb7809) |
| `DOCAI_PROJECT_ID` | Google DocAI project ID | Yes |
| `DOCAI_REGION` | Google DocAI region | No (defaults to "us") |
| `JWT_SECRET_KEY` | Secret key for JWT token signing | Yes |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT access token expiry | No (defaults to 60) |
| `REFRESH_TOKEN_EXPIRE_DAYS` | JWT refresh token expiry | No (defaults to 7) |
| `INACTIVITY_TIMEOUT_MINUTES` | Session inactivity timeout | No (defaults to 120) |
| `SMTP_SERVER` | SMTP server for OTP emails | No (defaults to smtp.gmail.com) |
| `SMTP_PORT` | SMTP port | No (defaults to 587) |
| `EMAIL_USER` | SMTP email sender address | Yes (for OTP) |
| `EMAIL_PASSWORD` | SMTP email app password | Yes (for OTP) |
| `OTP_EXPIRY_MINUTES` | OTP code expiry time | No (defaults to 10) |
| `OTP_RATE_LIMIT_PER_HOUR` | Max OTP requests per hour | No (defaults to 10) |
| `OTP_MAX_ATTEMPTS` | Max OTP verification attempts | No (defaults to 3) |
| `REDIS_URL` | Redis connection URL (optional, for OTP caching) | No (defaults to redis://localhost:6379) |
| `CORS_ORIGINS` | Comma-separated allowed CORS origins | No (has defaults) |
| `ENVIRONMENT` | "development" or "production" | No (defaults to development) |
| `WEBSOCKET_TIMEOUT` | WebSocket connection timeout | No (defaults to 1800) |
| `WEBSOCKET_PING_INTERVAL` | WebSocket ping interval | No (defaults to 30) |
| `WEBSOCKET_KEEPALIVE` | WebSocket keepalive | No (defaults to 300) |
| `MISTRAL_TIMEOUT` | Mistral API timeout | No (defaults to 1800) |
| `GPT_TIMEOUT` | GPT API timeout | No (defaults to 300) |
| `EXTRACTION_TIMEOUT` | Total extraction timeout | No (defaults to 1800) |
| `DOCUMENT_PROCESSING_TIMEOUT` | Document processing timeout | No (defaults to 600) |
| `TABLE_EXTRACTION_TIMEOUT` | Table extraction timeout | No (defaults to 1200) |
| `METADATA_EXTRACTION_TIMEOUT` | Metadata extraction timeout | No (defaults to 300) |
| `POST_PROCESSING_TIMEOUT` | Post-processing timeout | No (defaults to 300) |
| `UVICORN_TIMEOUT_KEEP_ALIVE` | Uvicorn keep-alive timeout | No (defaults to 1800) |
| `UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN` | Uvicorn graceful shutdown timeout | No (defaults to 60) |
| `SMALL_DOC_TIMEOUT` | Timeout for small docs (<10 pages) | No (defaults to 300) |
| `MEDIUM_DOC_TIMEOUT` | Timeout for medium docs (10-50 pages) | No (defaults to 600) |
| `LARGE_DOC_TIMEOUT` | Timeout for large docs (50+ pages) | No (defaults to 1200) |
| `MAX_TIMEOUT` | Absolute maximum timeout | No (defaults to 1800) |
| `NEXT_PUBLIC_API_URL` | Frontend API base URL | Yes (client/.env, defaults to http://localhost:8000) |
| `EASYOCR_MODULE_PATH` | EasyOCR model cache directory | No |
| `DOCLING_CACHE_DIR` | Docling model cache directory | No |
| `HF_HOME` / `TRANSFORMERS_CACHE` | HuggingFace model cache directory | No |

---

## 5. Repository Structure

```
.
├── .dockerignore                    # Docker build exclusions (Python cache, venv, client/, docs, large models)
├── .gitattributes                   # Git LFS tracking for .safetensors files
├── .gitignore                       # Ignores node_modules, .next, venv, __pycache__, .env, model caches, credentials
├── Dockerfile                       # Python 3.11.13-slim, installs system deps + Python deps, pre-downloads ML models
├── docker-test.sh                   # Script to build and test Docker image locally
├── render.yaml                      # Render deployment config (native Python, Pro plan)
├── render-docker.yaml               # Render deployment config (Docker-based, Starter plan)
│
├── server/
│   ├── .env                         # Server environment variables (contains live API keys and DB credentials)
│   ├── .python-version              # Python version pinning (3.10.14 — inconsistent with Dockerfile's 3.11.13)
│   ├── README.md                    # Basic setup instructions
│   ├── requirements.txt             # All Python dependencies with version constraints
│   ├── runtime.txt                  # Python runtime version for Render (3.11.13)
│   ├── start.sh                     # Docker entrypoint: checks credentials, starts Uvicorn with configurable timeouts
│   ├── init_db.py                   # Database initialization script (creates all tables)
│   ├── logs.txt                     # Sample log output from model loading
│   ├── resp.json                    # Sample extraction API response (test data)
│   ├── pdf-tables-extractor-*.json  # Google Cloud service account credentials (should not be in repo)
│   │
│   ├── config/
│   │   └── timeouts.py              # Centralized timeout configuration (dataclass with env var loading)
│   │
│   ├── configs/
│   │   └── new_extraction_config.yaml  # Docling extraction pipeline configuration (models, processing, API settings)
│   │
│   └── app/
│       ├── main.py                  # FastAPI application entry point; registers all routers, middleware, health checks
│       ├── config.py                # Database connection config, JWT/email/OTP/Claude config, env var loading
│       ├── security_config.py       # Security headers, CORS, trusted hosts, rate limiting, session/token/password config
│       │
│       ├── api/                     # All API route handlers (24 files)
│       │   ├── admin.py             # Admin dashboard, user management, domain management
│       │   ├── ai_intelligent_mapping.py  # AI field mapping + plan type detection endpoints
│       │   ├── ai_table_mapping.py  # AI table suitability analysis and switching
│       │   ├── auth.py              # /auth/me and /auth/permissions endpoints
│       │   ├── company.py           # Company/carrier CRUD
│       │   ├── company_validation.py # Company name validation and detection in table data
│       │   ├── dashboard.py         # Dashboard stats, statement lists, earned commission data (largest API file)
│       │   ├── database_fields.py   # Database field definition CRUD
│       │   ├── date_extraction.py   # Date extraction from document first pages
│       │   ├── excel_extract.py     # Excel file extraction with multi-sheet support
│       │   ├── format_learning.py   # Carrier format learning, matching, and validation
│       │   ├── improve_extraction.py # GPT-based extraction improvement and row format correction
│       │   ├── mapping.py           # Field mapping configuration + commission processing
│       │   ├── new_extract.py       # Main extraction pipeline: smart/GPT/DocAI/Mistral/Claude endpoints
│       │   ├── otp_auth.py          # OTP authentication flow (request, verify, register, refresh, logout)
│       │   ├── pdf_proxy.py         # CORS-compliant proxy for GCS-stored PDFs
│       │   ├── pending.py           # Pending upload management, progress tracking, auto-save
│       │   ├── plan_types.py        # Plan type CRUD
│       │   ├── review.py            # Statement approve/reject
│       │   ├── statements.py        # Statement CRUD, PDF preview URL generation
│       │   ├── summary_rows.py      # Summary row pattern learning and detection
│       │   ├── table_editor.py      # Edited table save/retrieve/export, format pattern learning
│       │   ├── user_management.py   # User profile, stats, contributions, activity
│       │   └── websocket.py         # WebSocket endpoint for real-time extraction progress
│       │
│       ├── db/                      # Database layer
│       │   ├── database.py          # SQLAlchemy async engine setup, session factory, sync engine
│       │   ├── models.py            # All SQLAlchemy ORM models (16 tables)
│       │   ├── schemas.py           # Pydantic schemas for request/response validation
│       │   ├── otp_schemas.py       # Pydantic schemas for OTP authentication
│       │   ├── crud.py              # Backward-compat re-export from crud/ package
│       │   └── crud/                # Modular CRUD operations
│       │       ├── __init__.py      # Aggregates all CRUD exports
│       │       ├── company.py       # Company CRUD with cascade delete
│       │       ├── company_mapping.py # Field mapping and configuration CRUD
│       │       ├── statement_upload.py # Upload lifecycle management (largest CRUD file)
│       │       ├── extraction.py    # Extraction record creation
│       │       ├── database_fields.py # Database field CRUD with default seeding
│       │       ├── plan_types.py    # Plan type CRUD with default seeding
│       │       ├── carrier_format_learning.py # Format learning CRUD with fuzzy matching
│       │       ├── summary_row_patterns.py # Summary row pattern CRUD
│       │       └── earned_commission.py # Commission CRUD with bulk processing (most complex)
│       │
│       ├── dependencies/
│       │   └── auth_dependencies.py # FastAPI auth dependency injection (Bearer + cookie hybrid)
│       │
│       ├── utils/
│       │   ├── auth_utils.py        # JWT, password hashing, session management, role checks
│       │   └── db_retry.py          # Database retry logic with exponential backoff
│       │
│       └── services/                # Business logic and external service integrations
│           ├── ai/                  # AI-powered analysis services
│           │   ├── __init__.py
│           │   ├── ai_field_mapping_service.py    # Mistral-powered field mapping
│           │   ├── ai_plan_type_detection_service.py # Mistral-powered plan type detection
│           │   ├── gpt4o_vision_service.py         # GPT-5/4o Vision table extraction
│           │   └── table_suitability_service.py    # Heuristic table ranking (no AI)
│           │
│           ├── claude/              # Anthropic Claude integration
│           │   ├── __init__.py
│           │   ├── models.py        # Pydantic models for Claude responses
│           │   ├── prompts.py       # All Claude system/user prompts (7 prompts)
│           │   ├── service.py       # ClaudeDocumentAIService (primary extraction)
│           │   └── utils.py         # PDF processing, token estimation, response parsing, quality assessment
│           │
│           ├── mistral/             # Mistral AI integration
│           │   ├── __init__.py
│           │   ├── bracket_processor.py       # Accounting bracket → negative number conversion
│           │   ├── enhanced_summary_detector.py # Multi-strategy summary row detection
│           │   ├── enhancement_config.py      # Enhancement configuration and monitoring
│           │   ├── models.py                  # Pydantic models for Mistral responses
│           │   ├── prompts.py                 # All Mistral system prompts (4 prompts)
│           │   ├── service.py                 # MistralDocumentAIService (2500+ lines, fallback extraction)
│           │   └── utils.py                   # PDF processing, JSON parsing, quality assessment, carrier/date detection
│           │
│           ├── auth/                # Authentication services
│           │   ├── __init__.py
│           │   ├── jwt_service.py   # JWT token creation/verification/revocation
│           │   ├── otp_service.py   # OTP generation, email sending, verification
│           │   └── user_profile_service.py # User profile, statistics, contributions
│           │
│           ├── data_processing/     # Data processing utilities
│           │   ├── __init__.py
│           │   ├── company_name_service.py       # Company name detection and cleaning
│           │   ├── data_formatting_service.py     # Data format enforcement with LLM patterns
│           │   ├── duplicate_detection_service.py # SHA-256 file duplicate detection
│           │   ├── format_learning_service.py     # Carrier format learning and matching
│           │   └── quality_validation_service.py  # Extraction quality validation
│           │
│           ├── extraction/          # Extraction orchestration
│           │   ├── __init__.py
│           │   ├── date_extraction_service.py       # Date extraction from documents (OCR + text)
│           │   ├── enhanced_extraction_service.py   # Main extraction orchestrator with WebSocket progress
│           │   ├── excel_extraction_service.py      # Excel file extraction
│           │   ├── extraction_utils.py              # Table stitching, date normalisation, CSV/Excel export
│           │   └── new_extraction_service.py        # Docling-based extraction service
│           │
│           ├── google_docai/        # Google Document AI integration
│           │   ├── __init__.py
│           │   ├── config.py        # GCP project/processor/credential config
│           │   ├── extractor.py     # GoogleDocAIExtractor (main entry)
│           │   ├── post_processing.py # Text cleaning, OCR error fixing
│           │   ├── processing.py    # Document processing with retry and chunking
│           │   ├── table_extraction.py # Table extraction from DocAI response
│           │   └── utils.py         # DocAI tableBlock format adapters
│           │
│           ├── infrastructure/      # Infrastructure services
│           │   ├── __init__.py
│           │   ├── audit_logging_service.py   # Audit logging (partially implemented)
│           │   ├── gcs_utils.py               # Google Cloud Storage operations
│           │   ├── process_monitor.py         # Long-running process monitoring
│           │   └── websocket_service.py       # WebSocket connection manager + progress tracker
│           │
│           └── docling/             # Local Docling/TableFormer extraction pipeline
│               ├── __init__.py
│               ├── pipeline.py      # ExtractionPipeline orchestrator
│               ├── processors.py    # Financial document processing with adaptive patterns
│               ├── evaluation.py    # TEDS and GriTS evaluation metrics
│               ├── core/
│               │   ├── __init__.py
│               │   ├── document_processor.py  # Main document processor (routes by format)
│               │   ├── document_types.py      # DocumentFormat enum, ProcessedDocument dataclass
│               │   ├── docx_processor.py      # DOCX processing via Docling
│               │   ├── format_detector.py     # File format detection
│               │   ├── image_processor.py     # Image file processing
│               │   ├── multipage_handler.py   # Multi-page table linking (~2000 lines)
│               │   ├── pdf_processor.py       # PDF processing via Docling + pdfplumber
│               │   ├── table_extractor.py     # Table extraction from Docling documents (~1800 lines)
│               │   └── table_validator.py     # Table quality validation (~1000 lines)
│               ├── models/
│               │   ├── __init__.py
│               │   ├── advanced_ocr_engine.py    # Ensemble OCR (EasyOCR + Tesseract + PaddleOCR)
│               │   ├── advanced_tableformer.py   # Microsoft Table Transformer (HuggingFace)
│               │   └── tableformer.py            # Legacy TableFormer + EasyOCR OCR engine
│               └── utils/
│                   ├── __init__.py
│                   ├── compatibility.py   # PIL ANTIALIAS deprecation fix
│                   ├── config.py          # YAML/env-based configuration management
│                   ├── logging_utils.py   # Structured logging with loguru
│                   ├── metrics.py         # IoU-based extraction metrics
│                   └── validation.py      # Document and table data validators
│
└── client/
    ├── .env                         # Frontend env (NEXT_PUBLIC_API_URL=http://localhost:8000)
    ├── .gitignore                   # Standard Next.js ignores
    ├── README.md                    # Default create-next-app readme
    ├── components.json              # shadcn/ui configuration (new-york style)
    ├── eslint.config.mjs            # ESLint config (relaxed: no-explicit-any and no-unused-vars off)
    ├── next.config.ts               # Next.js config: PDF.js worker, API proxy, CSP headers, webpack customisation
    ├── next-env.d.ts                # Next.js TypeScript references
    ├── package.json                 # Frontend dependencies and scripts
    ├── package-lock.json            # Lockfile
    ├── postcss.config.mjs           # PostCSS with Tailwind plugin
    ├── tailwind.config.ts           # Tailwind with dark mode, custom colors, animations, shadcn integration
    ├── tsconfig.json                # TypeScript config with path aliases (@/*)
    │
    ├── public/
    │   └── images/
    │       ├── icon.svg             # Application icon
    │       ├── logo.svg             # Logo (light mode)
    │       └── logo-dark.svg        # Logo (dark mode)
    │
    └── src/
        ├── components/
        │   └── ProtectedRoute.tsx   # Route guard (auth + role + permission checks)
        │
        ├── context/
        │   ├── AuthContext.tsx       # Authentication context (OTP login, cookie-based tokens)
        │   ├── SubmissionContext.tsx  # Submission state context (dashboard refresh triggers)
        │   └── ThemeContext.tsx      # Theme context (light/dark/system)
        │
        ├── hooks/
        │   ├── README.md            # Documentation for useThemeHydration hook
        │   ├── useSectionVisibility.ts  # Intersection Observer for scroll visibility
        │   └── useThemeHydration.ts # Prevents SSR hydration mismatches with theme
        │
        ├── lib/
        │   └── utils.ts             # Tailwind cn() utility (clsx + tailwind-merge)
        │
        ├── pages/
        │   └── .gitkeep             # Empty directory placeholder for Next.js
        │
        ├── utils/
        │   └── emailValidation.ts   # Client-side email domain validation
        │
        └── app/
            ├── favicon.ico          # Application favicon
            ├── globals.css          # Global CSS with theme variables, premium UI classes
            ├── layout.tsx           # Root layout (ThemeProvider > AuthProvider > SubmissionProvider)
            ├── page.tsx             # Main dashboard (4 tabs: analytics, dashboard, commissions, carriers)
            ├── toast.tsx            # react-hot-toast Toaster configuration
            │
            ├── styles/
            │   └── animations.css   # Additional CSS animations
            │
            ├── auth/
            │   ├── page.tsx         # Login/signup page with OTP
            │   └── verify-otp/
            │       └── page.tsx     # OTP verification page
            │
            ├── admin/
            │   └── dashboard/
            │       └── page.tsx     # Admin dashboard (users, domains, stats)
            │
            ├── pending/
            │   └── page.tsx         # Pending uploads list
            │
            ├── statements/
            │   └── page.tsx         # Statement browser with carrier sidebar
            │
            ├── upload/
            │   ├── page.tsx         # Upload page wrapper
            │   ├── components/
            │   │   ├── BeautifulUploadZone.tsx   # Drag-and-drop upload with WebSocket progress
            │   │   ├── DashboardTable.tsx        # Paginated editable data table
            │   │   ├── ExtractedTable.tsx        # Multi-tab raw extracted data viewer
            │   │   ├── FieldMapper.tsx           # Drag-and-drop field mapping with @dnd-kit
            │   │   ├── Loader.tsx                # Loading spinner components
            │   │   ├── ProgressBar.tsx           # Step progress indicator
            │   │   └── UploadPageContent.tsx     # Upload page content with carrier routing
            │   └── services/
            │       └── dateExtractionService.ts  # Client-side date extraction service
            │
            ├── landing/
            │   ├── page.tsx                     # Marketing landing page
            │   ├── README.md                    # Landing page documentation
            │   └── components/
            │       ├── index.ts                 # Barrel export
            │       ├── BenefitsSection.tsx       # Benefits list with animations
            │       ├── CompanyCarousel.tsx       # Infinite carrier name carousel
            │       ├── FeatureGrid.tsx           # 3-column feature cards
            │       ├── Hero.tsx                  # Hero section with CTA
            │       ├── HeroScrollStorytelling.tsx # Parallax scroll animation
            │       ├── HeroScrollStorytelling_back.tsx # Backup version (light mode)
            │       ├── RegistrationForm.tsx      # Email registration form
            │       ├── StepScrollStorytelling.tsx # 3-step scroll storytelling
            │       └── UseCaseShowcase.tsx       # Use case cards + testimonials
            │
            ├── services/
            │   ├── aiIntelligentMappingService.ts # AI mapping analysis service
            │   └── authService.ts                # Auth service (OTP, tokens)
            │
            ├── hooks/
            │   ├── useCompanyNormalization.ts     # Company name normalisation hook
            │   ├── useDashboard.ts               # Dashboard data hooks
            │   └── useProgressWebSocket.ts       # WebSocket progress tracking hook
            │
            ├── utils/
            │   ├── CompanyNameNormalizer.ts       # Company name normalisation utility
            │   ├── analyticsUtils.ts             # Analytics calculation utilities
            │   └── insightsEngine.ts             # Business insights generation
            │
            └── components/
                ├── AIIntelligentMappingDisplay.tsx    # AI mapping suggestion display
                ├── CarrierUploadZone.tsx              # Carrier-specific upload zone
                ├── LoadingScreen.tsx                  # Full-screen loading component
                ├── Modal.tsx                          # Generic modal component
                ├── SummaryUploadZone.tsx              # Upload + Claude summarisation
                │
                ├── upload/
                │   ├── ActionBar.tsx                  # Context-sensitive action bar with validation
                │   ├── PDFViewer.tsx                  # PDF viewer (@react-pdf-viewer)
                │   ├── PremiumProgressLoader.tsx      # 5-step circular progress loader
                │   ├── SummaryProgressLoader .tsx     # 3-column progress with PDF preview + summary
                │   └── UnifiedTableEditor.tsx         # Two-phase table editor + field mapper (main workflow)
                │
                ├── ui/
                │   └── ProfessionalPagination.tsx     # Reusable pagination component
                │
                ├── carrierTab/
                │   ├── CarrierList.tsx                # Carrier list sidebar
                │   ├── CarrierStatementsTable.tsx     # Carrier statements table
                │   ├── CarrierTab.tsx                 # Carrier tab container
                │   ├── CompareModal.tsx               # Statement comparison modal
                │   ├── CompareModalEnhanced.tsx       # Enhanced comparison modal
                │   ├── DatabaseFieldsManager.tsx      # Database fields CRUD UI
                │   ├── EditMappingModal.tsx           # Field mapping editor modal
                │   ├── PlanTypesManager.tsx           # Plan types CRUD UI
                │   ├── StatementPreviewModal.tsx      # Statement preview with PDF + data
                │   └── TableViewerModal.tsx           # Raw table viewer modal
                │
                ├── dashboardTab/
                │   ├── CarriersModal.tsx              # Carrier selection modal
                │   ├── CompanyCarrierModal.tsx        # Company-carrier relationship modal
                │   ├── DashboardTab.tsx               # Main dashboard tab
                │   ├── EarnedCommissionTab.tsx        # Commission tracking tab
                │   ├── EditCommissionModal.tsx        # Commission record editor
                │   ├── MergeConfirmationModal.tsx     # Commission merge confirmation
                │   ├── PremiumAnalyticsTab.tsx        # Premium analytics with charts
                │   ├── PremiumCarrierPieChart.tsx     # Carrier distribution pie chart
                │   ├── StatCard.tsx                   # Statistics card component
                │   └── SystemCapabilitiesPanel.tsx    # System capabilities info panel
                │
                └── review-extracted-data/
                    ├── index.ts                      # Barrel export
                    ├── styles.css                    # Component-specific styles
                    ├── EnhancedAIMapper.tsx           # AI field mapping with table selector
                    ├── TableSelectorModal.tsx         # Table selection modal for AI mapping
                    ├── hooks/
                    │   ├── index.ts                   # Hooks barrel export
                    │   ├── useSummaryRowDetection.ts  # Summary row detection hook
                    │   ├── useTableOperations.ts      # Table CRUD operations hook
                    │   └── useTableSelection.ts       # Table selection state hook
                    ├── table/
                    │   ├── BulkActionsBar.tsx          # Bulk row actions toolbar
                    │   ├── EditableCell.tsx            # Inline-editable table cell
                    │   ├── ExtractedDataTable.tsx      # Main extracted data table component
                    │   ├── SummaryRowManager.tsx       # Summary row detection/removal UI
                    │   ├── TableRow.tsx                # Single table row component
                    │   └── TableRowSelector.tsx        # Row selection checkbox
                    ├── types/
                    │   ├── index.ts                    # Types barrel export
                    │   ├── documentTypes.ts            # Document-related type definitions
                    │   └── tableTypes.ts               # Table-related type definitions
                    └── utils/
                        ├── index.ts                    # Utils barrel export
                        ├── performanceUtils.ts         # Performance utility functions
                        ├── summaryDetection.ts         # Client-side summary row detection
                        └── tableUtils.ts               # Table manipulation utilities
```

---

## 6. Backend Architecture

### Module Overview

The backend is a FastAPI application (`server/app/main.py`) that registers 24 API routers, applies CORS/security/rate-limiting middleware, and runs background tasks for session cleanup and process monitoring.

**Configuration Layer:**
- `config.py` — Database connection (local → Render → Supabase fallback chain), JWT config, email config, Claude config
- `security_config.py` — CORS origins, trusted hosts, security headers, rate limit config, session config
- `config/timeouts.py` — Centralised timeout settings for all system components

**Database Layer:**
- `db/database.py` — Async SQLAlchemy engine with connection pooling (pool_size=10, max_overflow=20), sync engine for scripts
- `db/models.py` — 16 ORM models (see Section 8)
- `db/schemas.py` — Pydantic v2 schemas for all models
- `db/crud/` — 9 modular CRUD files with business logic

**API Layer (24 routers):**

| Method | Path | Purpose | Router |
|--------|------|---------|--------|
| GET | `/health` | Basic health check | main.py |
| GET | `/health/detailed` | Detailed health with resources | main.py |
| GET | `/security/status` | Security configuration status | main.py |
| GET | `/debug/cors` | Debug CORS configuration | main.py |
| GET | `/api/auth/me` | Get current user info | auth.py |
| GET | `/api/auth/permissions` | Get user permissions | auth.py |
| POST | `/api/auth/otp/request` | Request OTP code | otp_auth.py |
| POST | `/api/auth/otp/verify` | Verify OTP and authenticate | otp_auth.py |
| POST | `/api/auth/otp/register` | Register new user via OTP | otp_auth.py |
| POST | `/api/auth/otp/refresh` | Refresh access token | otp_auth.py |
| POST | `/api/auth/otp/logout` | Logout | otp_auth.py |
| POST | `/api/auth/otp/cleanup` | Clean up session on browser close | otp_auth.py |
| GET | `/api/auth/otp/status` | Check auth status | otp_auth.py |
| GET | `/api/auth/otp/profile` | Get user profile | otp_auth.py |
| POST | `/api/auth/otp/test-cookies` | Test cookie functionality | otp_auth.py |
| GET | `/api/admin/dashboard` | Admin dashboard stats | admin.py |
| GET | `/api/admin/users` | List all users | admin.py |
| GET | `/api/admin/users/{user_id}` | Get specific user | admin.py |
| PUT | `/api/admin/users/{user_id}/status` | Activate/deactivate user | admin.py |
| PUT | `/api/admin/users/{user_id}/role` | Change user role | admin.py |
| DELETE | `/api/admin/users/{user_id}` | Delete user | admin.py |
| POST | `/api/admin/users/{user_id}/reset-data` | Reset user data | admin.py |
| POST | `/api/admin/domains` | Add allowed domain | admin.py |
| GET | `/api/admin/domains` | List domains | admin.py |
| PUT | `/api/admin/domains/{domain_id}` | Update domain | admin.py |
| DELETE | `/api/admin/domains/{domain_id}` | Delete domain | admin.py |
| GET | `/api/user/profile` | Get user profile | user_management.py |
| GET | `/api/user/stats` | Get user statistics | user_management.py |
| GET | `/api/user/contributions` | Get contribution history | user_management.py |
| GET | `/api/user/activity` | Get activity summary | user_management.py |
| GET | `/api/user/duplicates` | Get duplicate history | user_management.py |
| GET | `/api/user/uploads` | Get user uploads | user_management.py |
| GET | `/api/user/admin/system-stats` | System stats (admin) | user_management.py |
| GET | `/api/user/admin/duplicate-stats` | Duplicate stats (admin) | user_management.py |
| GET | `/api/companies/` | List all companies | company.py |
| GET | `/api/companies/{company_id}` | Get company | company.py |
| POST | `/api/companies/` | Create company | company.py |
| DELETE | `/api/companies/{company_id}` | Delete company | company.py |
| DELETE | `/api/companies/` | Batch delete companies | company.py |
| PATCH | `/api/companies/{company_id}` | Update company name | company.py |
| GET | `/api/companies/user-specific` | User's carriers | dashboard.py |
| GET | `/api/companies/user-specific/{company_id}/statements` | User's carrier statements | dashboard.py |
| GET | `/api/companies/{company_id}/mapping/` | Get mapping config | mapping.py |
| POST | `/api/companies/{company_id}/mapping/` | Save mapping + process commissions | mapping.py |
| GET | `/api/companies/{company_id}/statements/` | Get carrier statements | statements.py |
| DELETE | `/api/companies/{company_id}/statements/{statement_id}` | Delete statement | statements.py |
| DELETE | `/api/companies/{company_id}/statements/` | Batch delete statements | statements.py |
| POST | `/api/companies/{company_id}/learn-format/` | Learn carrier format | format_learning.py |
| POST | `/api/companies/{company_id}/find-format-match/` | Find matching format | format_learning.py |
| POST | `/api/companies/{company_id}/validate-format/` | Validate against format | format_learning.py |
| GET | `/api/companies/{company_id}/learned-formats/` | Get learned formats | format_learning.py |
| POST | `/api/companies/{company_id}/get-table-editor-settings/` | Get editor settings | format_learning.py |
| POST | `/api/companies/{company_id}/get-learned-field-mapping/` | Get learned mapping | format_learning.py |
| DELETE | `/api/companies/{company_id}/learned-formats/{format_id}/` | Delete format | format_learning.py |
| GET | `/api/dashboard/stats` | Dashboard statistics | dashboard.py |
| GET | `/api/dashboard/statements` | All statements | dashboard.py |
| GET | `/api/dashboard/statements/{status}` | Statements by status | dashboard.py |
| GET | `/api/dashboard/carriers` | Carriers with counts | dashboard.py |
| GET | `/api/dashboard/carriers/{carrier_id}/statements` | Carrier statements | dashboard.py |
| GET | `/api/dashboard/carriers/{carrier_id}/statements/{status}` | Carrier status filter | dashboard.py |
| GET | `/api/dashboard/earned-commissions` | Earned commissions | dashboard.py |
| GET | `/api/dashboard/carriers/{carrier_id}/earned-commissions` | Carrier commissions | dashboard.py |
| GET | `/api/dashboard/earned-commissions/years` | Available years | dashboard.py |
| GET | `/api/dashboard/earned-commissions/summary` | Commission summary | dashboard.py |
| GET | `/api/earned-commission/stats` | Commission stats | dashboard.py |
| GET | `/api/earned-commission/global/stats` | Global stats | dashboard.py |
| GET | `/api/earned-commission/global/data` | Global data | dashboard.py |
| GET | `/api/earned-commission/carrier/{carrier_id}/stats` | Carrier stats | dashboard.py |
| GET | `/api/earned-commission/carrier/user-specific/{carrier_id}/stats` | User carrier stats | dashboard.py |
| GET | `/api/earned-commission/carriers` | Carriers with commissions | dashboard.py |
| GET | `/api/earned-commission/carriers-detailed` | Detailed carrier commissions | dashboard.py |
| GET | `/api/earned-commission/carrier/{carrier_id}/data` | Carrier commission data | dashboard.py |
| GET | `/api/earned-commission/all-data` | All commission data | dashboard.py |
| PUT | `/api/earned-commission/{commission_id}` | Update commission | dashboard.py |
| POST | `/api/earned-commission/merge` | Merge commissions | dashboard.py |
| GET | `/api/database-fields/` | List database fields | database_fields.py |
| GET | `/api/database-fields/{field_id}` | Get field | database_fields.py |
| POST | `/api/database-fields/` | Create field | database_fields.py |
| PUT | `/api/database-fields/{field_id}` | Update field | database_fields.py |
| DELETE | `/api/database-fields/{field_id}` | Soft-delete field | database_fields.py |
| POST | `/api/database-fields/initialize/` | Initialize defaults | database_fields.py |
| GET | `/api/plan-types/` | List plan types | plan_types.py |
| GET | `/api/plan-types/{plan_type_id}` | Get plan type | plan_types.py |
| POST | `/api/plan-types/` | Create plan type | plan_types.py |
| PUT | `/api/plan-types/{plan_type_id}` | Update plan type | plan_types.py |
| DELETE | `/api/plan-types/{plan_type_id}` | Soft-delete plan type | plan_types.py |
| POST | `/api/plan-types/initialize/` | Initialize defaults | plan_types.py |
| POST | `/api/extract-tables-smart/` | Smart extraction (auto-detect) | new_extract.py |
| POST | `/api/cancel-extraction/{upload_id}` | Cancel extraction | new_extract.py |
| POST | `/api/extract-tables-gpt/` | GPT-5 Vision extraction | new_extract.py |
| POST | `/api/extract-tables-google-docai/` | Google DocAI extraction | new_extract.py |
| POST | `/api/extract-intelligent/` | Mistral intelligent extraction | new_extract.py |
| POST | `/api/extract-tables-mistral-frontend/` | Mistral frontend format | new_extract.py |
| POST | `/api/extract-summarize-data-via-claude/` | Claude document summarisation | new_extract.py |
| POST | `/api/extract-dates/` | Extract dates from file | date_extraction.py |
| POST | `/api/extract-dates-bytes/` | Extract dates from bytes | date_extraction.py |
| GET | `/api/date-extraction-status/` | Date extraction status | date_extraction.py |
| POST | `/api/extract-tables-excel/` | Extract from Excel | excel_extract.py |
| POST | `/api/extract-tables-excel-bytes/` | Extract from Excel bytes | excel_extract.py |
| GET | `/api/excel-sheet-info/{company_id}` | Get Excel sheet info | excel_extract.py |
| POST | `/api/extract-tables-excel-s3/` | Extract from GCS Excel | excel_extract.py |
| POST | `/api/improve-extraction/fix-row-formats/` | GPT row format fix | improve_extraction.py |
| POST | `/api/improve-extraction/improve-current-extraction/` | GPT re-extraction | improve_extraction.py |
| POST | `/api/review/approve/` | Approve statement | review.py |
| POST | `/api/review/reject/` | Reject statement | review.py |
| GET | `/api/review/all/` | Get all reviews | review.py |
| GET | `/api/pending/files/{company_id}` | Pending files for company | pending.py |
| GET | `/api/pending/files/single/{upload_id}` | Single pending file | pending.py |
| GET | `/api/pending/resume/{upload_id}` | Resume upload session | pending.py |
| POST | `/api/pending/save-progress/{upload_id}` | Save step progress | pending.py |
| GET | `/api/pending/progress/{upload_id}/{step}` | Get step progress | pending.py |
| PUT | `/api/pending/update/{upload_id}` | Update upload data | pending.py |
| DELETE | `/api/pending/delete/{upload_id}` | Delete pending upload | pending.py |
| GET | `/api/pending/status/{upload_id}` | Get upload status | pending.py |
| POST | `/api/pending/auto-save/{upload_id}` | Auto-save progress | pending.py |
| POST | `/api/table-editor/save-tables/` | Save edited tables | table_editor.py |
| GET | `/api/table-editor/get-tables/{upload_id}` | Get edited tables | table_editor.py |
| DELETE | `/api/table-editor/delete-tables/{upload_id}` | Delete edited tables | table_editor.py |
| POST | `/api/table-editor/export-tables/{upload_id}` | Export tables | table_editor.py |
| POST | `/api/table-editor/update-extraction-metadata/` | Update carrier/date | table_editor.py |
| POST | `/api/table-editor/learn-format-patterns` | Learn format patterns | table_editor.py |
| GET | `/api/table-editor/health` | Health check | table_editor.py |
| POST | `/api/summary-rows/learn-pattern/` | Learn summary pattern | summary_rows.py |
| POST | `/api/summary-rows/detect-summary-rows/` | Detect summary rows | summary_rows.py |
| GET | `/api/summary-rows/patterns/{company_id}` | Get patterns | summary_rows.py |
| DELETE | `/api/summary-rows/patterns/{pattern_id}` | Delete pattern | summary_rows.py |
| GET | `/api/summary-rows/health` | Health check | summary_rows.py |
| POST | `/api/validate-company-name/` | Validate company name | company_validation.py |
| POST | `/api/detect-companies/` | Detect companies in table | company_validation.py |
| POST | `/api/create-company-transaction-mapping/` | Company transaction map | company_validation.py |
| POST | `/api/ai/map-fields` | AI field mapping | ai_intelligent_mapping.py |
| POST | `/api/ai/detect-plan-types` | AI plan type detection | ai_intelligent_mapping.py |
| POST | `/api/ai/enhanced-extraction-analysis` | Combined AI analysis | ai_intelligent_mapping.py |
| POST | `/api/ai/save-user-corrections` | Save AI corrections | ai_intelligent_mapping.py |
| GET | `/api/ai/service-status` | AI services status | ai_intelligent_mapping.py |
| POST | `/api/ai/switch-mapping-table` | Switch AI mapping table | ai_table_mapping.py |
| POST | `/api/ai/analyze-table-suitability` | Analyse table suitability | ai_table_mapping.py |
| GET | `/api/ai/table-selection-history/{upload_id}` | Table selection history | ai_table_mapping.py |
| GET | `/api/ai/table-mapping-status/{upload_id}` | Table mapping status | ai_table_mapping.py |
| GET | `/api/pdf-preview/` | Get PDF preview URL | statements.py |
| GET | `/api/statements/{statement_id}/formatted-tables` | Get formatted tables | statements.py |
| GET | `/api/pdf-proxy` | Proxy PDF from GCS | pdf_proxy.py |
| WS | `/api/ws/progress/{upload_id}` | WebSocket progress | websocket.py |
| GET | `/api/ws/status` | WebSocket status | websocket.py |
| GET | `/api/ws/connections/{upload_id}` | Upload connections | websocket.py |

---

## 7. Frontend Architecture

### Pages

- **`/` (Home)** — Main dashboard shell. Protected route. 4 tabs via URL param `?tab=`: `PremiumAnalyticsTab` (charts, analytics), `DashboardTab` (statement overview), `EarnedCommissionTab` (commission tracking), `CarrierTab` (carrier management). Sidebar navigation, user dropdown, theme toggle.

- **`/landing`** — Marketing landing page. Not authenticated. Parallax scroll storytelling, feature grid, benefits, use cases, carrier carousel, registration form.

- **`/auth`** — Login/signup page with split layout and animations. Email + OTP flow. Password strength meter for signup. Redirects to `/auth/verify-otp`.

- **`/auth/verify-otp`** — 6-digit OTP verification. Countdown timer, resend capability. On success, redirects to `/`.

- **`/admin/dashboard`** — Admin-only. User management (activate/deactivate, role change, delete), domain whitelist management, system statistics.

- **`/upload`** — File upload page. Drag-and-drop for PDF/Excel files. Real-time WebSocket progress. On success, navigates to carrier tab.

- **`/pending`** — Lists all incomplete/in-progress uploads across carriers. Resume, review, or delete actions.

- **`/statements`** — Full statement browser. Carrier sidebar, status tabs (all/approved/rejected/pending), statement previews.

### Key Component: UnifiedTableEditor

The central workflow component (`UnifiedTableEditor.tsx`, ~1769 lines). Two phases:
1. **Table Review** — PDF preview alongside editable extracted data table. Users can edit cells, delete rows, detect/remove summary rows, set carrier name, plan type, and statement date.
2. **Field Mapping** — AI-suggested mappings (via `EnhancedAIMapper`) with accept/reject per field. Drag-and-drop mapping via `@dnd-kit`. On submit: saves tables, learns format patterns, saves field mapping, processes commissions, and approves the statement.

### Data Flow (User Journey)

1. User lands on `/landing` → registers/logs in via OTP email
2. User uploads PDF/Excel on `/upload`
3. Backend extracts tables (Claude → Mistral → GPT fallback chain)
4. WebSocket sends real-time progress to frontend
5. On completion, user is taken to `UnifiedTableEditor` (Phase 1: table review)
6. User reviews/edits extracted data, sets metadata (carrier, date, plan type)
7. User proceeds to Phase 2: AI-suggested field mapping
8. User accepts/adjusts AI mappings, submits
9. Backend processes commission data, creates/updates `EarnedCommission` records
10. Statement is approved, visible in dashboard tabs and analytics

---

## 8. Database / Storage Schema

### PostgreSQL Tables (16 tables via SQLAlchemy ORM)

**`companies`**
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default uuid4 |
| name | String | UNIQUE, NOT NULL |
| created_at | DateTime | server_default now() |

**`company_field_mappings`**
| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK, autoincrement |
| company_id | UUID | FK → companies.id |
| display_name | String | NOT NULL |
| column_name | String | NOT NULL |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |
| | | UNIQUE(company_id, display_name) |

**`company_configurations`**
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| company_id | UUID | FK → companies.id, UNIQUE |
| field_config | JSON | |
| plan_types | JSON | |
| table_names | JSON | |
| created_at | DateTime | |
| updated_at | DateTime | |

**`carrier_format_learning`**
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| company_id | UUID | FK → companies.id |
| format_signature | String | NOT NULL |
| headers | JSON | NOT NULL |
| header_patterns | JSON | |
| column_types | JSON | |
| column_patterns | JSON | |
| sample_values | JSON | |
| table_structure | JSON | |
| data_quality_metrics | JSON | |
| field_mapping | JSON | |
| table_editor_settings | JSON | |
| confidence_score | Integer | default 0 |
| usage_count | Integer | default 1 |
| last_used | DateTime | |
| created_at | DateTime | |
| updated_at | DateTime | |
| | | UNIQUE(company_id, format_signature) |

**`statement_uploads`**
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| company_id | UUID | FK → companies.id (user's company) |
| carrier_id | UUID | FK → companies.id (nullable, carrier) |
| user_id | UUID | FK → users.id |
| file_name | Text | |
| file_hash | String | nullable (SHA-256) |
| file_size | Integer | nullable |
| uploaded_at | TIMESTAMP | |
| status | String | default 'pending' |
| current_step | String | default 'upload' |
| progress_data | JSON | |
| raw_data | JSON | |
| edited_tables | JSON | |
| field_mapping | JSON | |
| final_data | JSON | |
| mapping_used | JSON | |
| field_config | JSON | |
| rejection_reason | Text | |
| plan_types | JSON | |
| selected_statement_date | JSON | |
| ai_intelligence | JSON | |
| last_updated | DateTime | |
| completed_at | DateTime | |
| session_id | String | |
| auto_save_enabled | Integer | default 1 |

**`extractions`**
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| company_id | String | NOT NULL |
| user_id | UUID | FK → users.id, nullable |
| filename | String | NOT NULL |
| s3_url | String | NOT NULL |
| total_tables | Integer | NOT NULL |
| valid_tables | Integer | NOT NULL |
| quality_score | Integer | NOT NULL (0-100) |
| confidence | String | NOT NULL |
| extraction_metadata | JSON | |
| quality_metadata | JSON | |
| created_at | DateTime | |

**`database_fields`**
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| display_name | String | UNIQUE, NOT NULL |
| description | Text | |
| is_active | Integer | default 1 |
| created_at | DateTime | |
| updated_at | DateTime | |

Default fields: Company Name, Group Id, Policy Number, Commission Earned, Commission Rate, Total Commission Paid, Individual Commission.

**`plan_types`**
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| display_name | String | UNIQUE, NOT NULL |
| description | Text | |
| is_active | Integer | default 1 |
| created_at | DateTime | |
| updated_at | DateTime | |

Default types: Medical, Dental, Vision, Life, Disability, Supplemental.

**`earned_commissions`**
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| carrier_id | UUID | FK → companies.id |
| client_name | String | NOT NULL |
| invoice_total | Numeric(15,2) | default 0 |
| commission_earned | Numeric(15,2) | default 0 |
| statement_count | Integer | default 0 |
| upload_ids | JSON | nullable |
| user_id | UUID | FK → users.id, nullable |
| statement_date | DateTime | nullable |
| statement_month | Integer | nullable |
| statement_year | Integer | nullable |
| jan_commission..dec_commission | Numeric(15,2) | default 0 (12 columns) |
| last_updated | DateTime | |
| created_at | DateTime | |
| | | UNIQUE(carrier_id, client_name, statement_date, user_id) |

**`edited_tables`**
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| upload_id | UUID | FK → statement_uploads.id |
| company_id | UUID | FK → companies.id |
| name | String | NOT NULL |
| header | JSON | NOT NULL |
| rows | JSON | NOT NULL |
| created_at | DateTime | |
| updated_at | DateTime | |

**`summary_row_patterns`**
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| company_id | UUID | FK → companies.id |
| pattern_name | String | NOT NULL |
| table_signature | String | NOT NULL |
| column_patterns | JSON | NOT NULL |
| row_characteristics | JSON | NOT NULL |
| sample_rows | JSON | NOT NULL |
| confidence_score | Integer | default 80 |
| usage_count | Integer | default 1 |
| last_used | DateTime | |
| created_at | DateTime | |
| updated_at | DateTime | |
| | | UNIQUE(company_id, pattern_name) |

**`users`**
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| email | String | UNIQUE, NOT NULL, indexed |
| password_hash | String | nullable |
| first_name | String | nullable |
| last_name | String | nullable |
| role | String | NOT NULL, default 'user' |
| is_active | Integer | default 1 |
| is_verified | Integer | default 0 |
| company_id | UUID | FK → companies.id, nullable |
| last_login | DateTime | nullable |
| email_domain | String | nullable |
| is_email_verified | Integer | default 0 |
| auth_method | String | default 'password' |
| access_level | String | default 'basic' |
| created_at | DateTime | |
| updated_at | DateTime | |

**`allowed_domains`**
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| domain | String | UNIQUE, NOT NULL, indexed |
| company_id | UUID | FK → companies.id, nullable |
| is_active | Integer | default 1 |
| created_by | UUID | FK → users.id |
| created_at | DateTime | |
| updated_at | DateTime | |

**`user_sessions`**
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| user_id | UUID | FK → users.id |
| session_token | String | UNIQUE, NOT NULL, indexed |
| expires_at | DateTime | NOT NULL |
| is_active | Integer | default 1 |
| created_at | DateTime | |
| last_accessed | DateTime | |

**`file_duplicates`**
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| file_hash | String | NOT NULL, indexed |
| original_upload_id | UUID | FK → statement_uploads.id |
| duplicate_upload_id | UUID | FK → statement_uploads.id |
| detected_at | DateTime | |
| action_taken | String | default 'detected' |
| created_at | DateTime | |

**`user_data_contributions`**
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| user_id | UUID | FK → users.id |
| upload_id | UUID | FK → statement_uploads.id |
| contribution_type | String | NOT NULL |
| contribution_data | JSON | |
| created_at | DateTime | |

**`otp_requests`**
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| email | String | NOT NULL, indexed |
| otp_code | String | NOT NULL (hashed) |
| purpose | String | NOT NULL |
| expires_at | DateTime | NOT NULL |
| is_used | Integer | default 0 |
| attempts | Integer | default 0 |
| ip_address | String | nullable |
| user_agent | String | nullable |
| created_at | DateTime | |
| used_at | DateTime | nullable |

### Cloud Storage (Google Cloud Storage)

- **Bucket:** `pdf_extraction_files_saver`
- **Project:** `pdf-tables-extractor-465009`
- Uploaded PDF and Excel files are stored in GCS. Signed URLs (v4) are generated for frontend access. Files are proxied through the backend (`/api/pdf-proxy`) to avoid CORS issues.

---

## 9. Extraction Pipeline (Current State)

### Primary Entry Point

`POST /api/extract-tables-smart/` — The "smart" extraction endpoint. Orchestrated by `EnhancedExtractionService.extract_tables_with_progress()`.

### Step-by-Step Pipeline

**Step 1: File Upload & Validation**
- File uploaded via multipart form data
- File hash (SHA-256) calculated for duplicate detection
- File uploaded to Google Cloud Storage
- `StatementUpload` record created in database with status "pending"
- WebSocket connection established for real-time progress

**Step 2: File Type Detection**
- Excel files (`.xlsx`, `.xls`) → routed to `ExcelExtractionService`
- PDF files → proceed to extraction cascade

**Step 3: Metadata Extraction (Claude-first)**
- `ClaudeDocumentAIService.extract_metadata_only()` extracts carrier name, statement date, and broker from the first pages
- If Claude is unavailable, GPT-4o Vision extracts metadata from first-page image
- Metadata (carrier name, date, broker) passed to subsequent extraction steps

**Step 4: Table Extraction Cascade**

The system uses a cascade of extraction methods based on the `extraction_method` parameter:

1. **Claude Document AI** (`extraction_method="claude"`, primary for `smart`):
   - PDF encoded as base64
   - Sent to Claude Sonnet 4 via `messages.create()` with document content type
   - System prompt instructs structured JSON extraction of tables + metadata
   - For large documents (>100 pages): PDF chunked into 40-page segments, processed sequentially, tables merged
   - Response parsed for tables (headers + rows), metadata, quality metrics
   - Fallback to Mistral on failure

2. **Mistral Document AI** (`extraction_method="mistral"`, fallback):
   - Phase 1A: `mistral-ocr-latest` OCR processes document to markdown
   - Markdown parsed for pipe-delimited tables
   - If OCR finds tables, they're returned directly
   - If not, falls back to multi-phase approach:
     - Phase 1A: Document Intelligence Analysis (`chat.parse()` with `DocumentIntelligence` response format)
     - Phase 1B: Table Structure Intelligence (`chat.parse()` with `TableIntelligence` response format)
     - Phase 2: Cross-validation of carrier/date consistency
     - Phase 3: Response formatting
   - Enhanced with summary row detection and bracket processing

3. **GPT-5/4o Vision** (`extraction_method="gpt"`):
   - Detects PDF type (digital vs scanned)
   - Digital PDFs: text extracted via PyMuPDF, sent as text to GPT-5
   - Scanned PDFs: pages converted to optimised images (adaptive DPI 400-600), enhanced with PIL, sent as base64 to GPT-5 Vision
   - Intelligent page selection: scores pages by content (commission keywords), selects up to 20 representative pages
   - Hierarchical structure detection: identifies company header rows, adds "Company Name" column
   - Header validation: separate GPT call validates headers aren't AI-generated templates

4. **Google Document AI** (`extraction_method="docai"`):
   - PDF sent to Google DocAI Form Parser
   - Regular mode (≤15 pages), imageless mode (≤30 pages), or chunked mode (>30 pages)
   - Tables extracted from Form Parser response
   - Post-processed with text cleaning and OCR error fixing

5. **Docling Pipeline** (local, used internally by `NewExtractionService`):
   - Document processed by Docling `DocumentConverter`
   - Tables detected by Microsoft Table Transformer models
   - OCR via EasyOCR + Tesseract ensemble
   - Multi-page table linking
   - Financial document processing
   - Table merging and consolidation

**Step 5: Post-Processing**
- Summary row detection and removal (via `EnhancedSummaryRowDetector`)
- Accounting bracket conversion `(1,234.56)` → `-1234.56` (via `AccountingBracketProcessor`)
- Multi-page table stitching (via `stitch_multipage_tables()`)
- Company name detection and cleaning (via `CompanyNameDetectionService`)
- OCR error correction (O→0 in numeric contexts)
- Quality assessment

**Step 6: Response & Progress Completion**
- Tables, metadata, and quality metrics returned to frontend
- WebSocket sends completion event
- `StatementUpload` updated with `raw_data` and `current_step = 'table_editor'`

### Excel Extraction

- Uses pandas with openpyxl/xlrd
- Multi-sheet support with dynamic table region detection
- Three strategies: structured tables, data clusters, financial data regions
- Header detection with learned format matching

---

## 10. LLM Prompts

### Claude Prompts (in `server/app/services/claude/prompts.py`)

**Table Extraction Prompt** (`get_table_extraction_prompt()`):
Instructs Claude to extract ALL tables AND document metadata from insurance commission statement PDFs. Covers: table structure preservation, financial data accuracy, metadata extraction (carrier name from headers/logos NOT table data, statement date with date-range end-date rule, broker company), summary row detection, empty cell preservation. Output: JSON with tables array and document_metadata. ~90 lines.

**Metadata Extraction Prompt** (`get_metadata_extraction_prompt()`):
Focused extraction of carrier name, statement date (with date-range rules), broker/agent company, and document type. JSON output with confidence scores. ~45 lines.

**Quality Assessment Prompt** (`get_quality_assessment_prompt()`):
Assesses extraction quality: overall confidence, structure score, completeness, issues, quality grade A-F. JSON output. ~25 lines.

**Large Document Summary Prompt** (`get_large_document_summary_prompt(page_range)`):
Quick overview of page range for large docs: table count, layout type, complexity, carrier visibility, challenges. JSON output. ~15 lines.

**Chunk Extraction Prompt** (`get_chunk_extraction_prompt(chunk_info)`):
For processing chunks of large documents. Notes table continuation. ~10 lines.

**Summarize Extraction Prompt** (`get_summarize_extraction_prompt()`):
OCR agent for markdown extraction of invoice data. Returns structured markdown (not tables). ~10 lines. Contains Spanish text: "No debes envolver dentro de un bloque de código".

**System Prompt** (`get_system_prompt()`):
Sets context as expert AI for insurance commission statements. ~15 lines.

### Mistral Prompts (in `server/app/services/mistral/prompts.py`)

**Document Intelligence Prompt** (`get_document_intelligence_prompt()`):
Phase 1A analysis. Business entity intelligence (carriers vs brokers vs companies), context awareness, quality intelligence. Instructs to look at headers/logos/footers, NOT table data columns. ~85 lines.

**Table Intelligence Prompt** (`get_table_intelligence_prompt()`):
Phase 1B analysis. Table structure recognition, business logic understanding, data integrity, entity classification. JSON output with headers/rows/table_type/company_name/confidence. ~40 lines.

**Enhanced Extraction Prompt** (`get_enhanced_extraction_prompt(pdf_type, selected_pages, enable_advanced_features)`):
Pixtral Large-optimised prompt. References 124B model + 1B vision encoder + 128K context. Detailed carrier detection requirements (headers, logos, footers). Date extraction requirements. ~45 lines.

**Fallback Prompt** (`get_fallback_prompt()`):
Simple JSON extraction fallback. ~10 lines.

### Mistral Service System Prompt (in `server/app/services/mistral/service.py`)

**System Prompt** (`_create_system_prompt()`):
Comprehensive extraction specialist prompt covering document comprehension, business entity intelligence, table extraction excellence, quality intelligence. ~40 lines.

### GPT-5/4o Vision Prompts (in `server/app/services/ai/gpt4o_vision_service.py`)

**Digital PDF System Prompt** (`_create_digital_pdf_system_prompt()`):
Commission statement data extractor with hierarchical structure detection. 10-step extraction process. Column order preservation, company name integration. JSON output. ~75 lines.

**Vision System Prompt** (`_create_vision_system_prompt()`):
Nearly identical to digital prompt, adapted for image-based input. ~75 lines.

**Header Validation Prompt** (`_create_header_validation_prompt()`):
Determines if headers are legitimate business document headers or AI-generated templates. JSON output with is_template, confidence, legitimacy_score. ~35 lines.

**Document Context Analysis Prompt** (in `_analyze_document_context()`):
Analyses document excerpt for type, industry, expected terms, business context. JSON output. ~10 lines.

### AI Field Mapping Prompts (in `server/app/services/ai/ai_field_mapping_service.py`)

**System Prompt**: Expert in data field mapping for commission tracking. Provide confidence scores based on semantic similarity, data type compatibility, context alignment, business logic fit. JSON only. ~15 lines.

**User Prompt** (`_create_mapping_prompt()`): Maps extracted headers to database fields using context from sample data, learned mappings, and document context. JSON output with mappings array (extracted_field, mapped_to, confidence, reasoning, alternatives). ~40 lines.

### AI Plan Type Detection Prompts (in `server/app/services/ai/ai_plan_type_detection_service.py`)

**System Prompt**: Expert in insurance plan type classification. Analyse document metadata, table structure, sample data. Multiple plan types possible. Return confidence scores. JSON only. ~20 lines.

**User Prompt** (`_create_detection_prompt()`): 4-part analysis: semantic meaning, contextual clues, business logic (characteristics of each plan type), multiple plan detection. JSON output with detected_plan_types array. ~60 lines.

### Enhanced Extraction Service Metadata Prompt (in `server/app/services/extraction/enhanced_extraction_service.py`)

**Metadata Extraction via GPT** (`_extract_metadata_with_gpt()`): Extracts carrier name, statement date, broker/agent from first page image. JSON output with confidence scores. ~30 lines.

*(All prompt texts are preserved verbatim in the codebase in the files referenced above.)*

---

## 11. Current Limitations and TODOs

### Hardcoded Values
1. **GCS bucket name** hardcoded as `"pdf_extraction_files_saver"` in multiple places (gcs_utils.py, render.yaml, config files)
2. **Google DocAI processor ID** hardcoded as `"521303e404fb7809"` in config and render files
3. **Default database fields** hardcoded in `crud/database_fields.py`: Company Name, Group Id, Policy Number, Commission Earned, Commission Rate, Total Commission Paid, Individual Commission
4. **Default plan types** hardcoded in `crud/plan_types.py`: Medical, Dental, Vision, Life, Disability, Supplemental
5. **Carrier name regex patterns** hardcoded in `mistral/utils.py` (CarrierDetector) for only 8 carriers: Aetna, BCBS, Cigna, Humana, UHC, Highmark, Allied, AIA
6. **CORS origins** hardcoded for specific Render/Vercel URLs in `security_config.py`
7. **Claude model** hardcoded as `claude-sonnet-4-20250514` for both primary and fallback

### Security Issues
1. **`.env` file committed to repository** with live API keys, database credentials, JWT secrets, SMTP passwords — critical security vulnerability
2. **Google Cloud service account JSON** (`pdf-tables-extractor-*.json`) present in server directory (`.gitignore` rule exists but file is present)
3. **JWT secret in `.env`** is a production secret committed to source control
4. **Token revocation uses in-memory Set** (`jwt_service.py`) — lost on restart, not shared across workers. Comment says "use Redis in production"
5. **Rate limiting uses in-memory dict** (`main.py`) — lost on restart, not shared across workers
6. **`resp.json`** contains sample extraction response data committed to repo

### Incomplete Implementations
1. **Audit logging** (`audit_logging_service.py`) — `get_user_audit_logs()` and `get_security_violations()` return placeholder/dummy data. `check_suspicious_activity()` is a placeholder. Logs go to application logger, not a dedicated audit table.
2. **File malware scanning** (`security_config.py`) — `scan_for_malware: True` and `quarantine_suspicious_files: True` are configured but not implemented
3. **Intrusion detection** (`security_config.py`) — `enable_intrusion_detection: True` configured but not implemented
4. **Password authentication** — `password_hash` field exists on `User` model, `auth_utils.py` has password functions, but the primary auth flow is OTP-only. Password-based login appears incomplete or deprecated.
5. **PaddleOCR** — Referenced in `advanced_ocr_engine.py` but wrapped in try/except and silently skipped if not installed (not in requirements.txt)
6. **Streamlit** — Listed in `requirements.txt` but not used anywhere in the application
7. **spaCy** — Optional NER in `company_name_service.py` but not in requirements.txt
8. **Redis** — OTP service works without Redis (falls back to DB-only mode)

### Inconsistencies
1. **Python version**: `.python-version` says 3.10.14, `runtime.txt` says 3.11.13, Dockerfile uses 3.11.13
2. **AWS references**: `server/.env` contains AWS credentials (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) and S3 bucket name, but AWS/S3 has been replaced by GCS (commented out in requirements.txt: "AWS S3 SDK - REMOVED"). These are unused.
3. **`s3_url` field** on `Extraction` model references S3 but the system uses GCS
4. **Duplicate database setup**: Both `config.py` and `db/database.py` contain nearly identical database connection logic (engine creation, session factory)
5. **`SummaryProgressLoader .tsx`** — Filename contains a trailing space

### Architecture Concerns
1. **Single worker** — Uvicorn configured with `workers=1`, limiting concurrency for CPU-intensive ML model inference
2. **ML models loaded at startup** — EasyOCR, TableFormer, Docling models all loaded at import/init time, consuming significant memory
3. **No test files** — pytest is in requirements but no test files exist in the repository
4. **Large files** — `mistral/service.py` (2500+ lines), `multipage_handler.py` (~2000 lines), `table_extractor.py` (~1800 lines), `pipeline.py` (~1500+ lines), `UnifiedTableEditor.tsx` (~1769 lines) could benefit from decomposition

---

## 12. What Is NOT Yet Implemented

Based on code analysis, the following capabilities are described in config/comments but not built:

1. **Malware scanning of uploaded files** — Config exists (`FILE_UPLOAD_CONFIG.scan_for_malware`), no implementation
2. **File quarantine** — Config exists (`FILE_UPLOAD_CONFIG.quarantine_suspicious_files`), no implementation
3. **Intrusion detection system** — Config exists (`MONITORING_CONFIG.enable_intrusion_detection`), no implementation
4. **Suspicious activity detection** — Config exists (`MONITORING_CONFIG.suspicious_activity_threshold`), placeholder only
5. **Failed login lockout** — Config exists (`MONITORING_CONFIG.failed_login_threshold`), not enforced
6. **Privilege escalation alerting** — Config exists (`MONITORING_CONFIG.alert_on_privilege_escalation`), no implementation
7. **Dedicated audit log database table** — Audit events go to application logger only, no queryable DB storage
8. **Password-based authentication flow** — Models and utility functions exist but no API endpoint for password login
9. **Password aging/expiry** — Config exists (`PASSWORD_CONFIG.max_age_days: 90`), not enforced
10. **Max concurrent sessions enforcement** — Config exists (`SESSION_CONFIG.max_concurrent_sessions: 5`), not enforced at login
11. **Redis-based token revocation** — Comment in code says "use Redis in production", currently uses in-memory Set
12. **Redis-based rate limiting** — Rate limits use in-memory dict, not shared across processes
13. **Automated test suite** — pytest in dependencies, no test files
14. **PaddleOCR integration** — Code references it with try/except, not installed
15. **spaCy NER** — Optional import in company_name_service.py, not in requirements
16. **Adaptive pattern learning** (Docling OCR) — `AdaptivePatternLearner`, `SemanticContextAnalyzer`, `IntelligentConfidenceCalculator`, `AdaptiveValidationEnhancer` classes exist in `advanced_ocr_engine.py` as stub/placeholder implementations
17. **Batch extraction endpoint** — `extract_tables_batch` method exists on `ExtractionPipeline` but no API endpoint exposes it
18. **CSV import** — `.csv` listed in allowed extensions but no CSV extraction service exists
19. **DOCX extraction via API** — Docling DOCX processor exists but no API endpoint for DOCX uploads (only PDF and Excel exposed)
