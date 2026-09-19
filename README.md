# AI Contract / Legal Document Simplifier

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![React 18](https://img.shields.io/badge/React-18.3-61dafb.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6-3178c6.svg)](https://www.typescriptlang.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-336791.svg)](https://www.postgresql.org/)

An enterprise-grade, document-grounded AI platform designed to transform complex legal contracts into plain-language explanations, perform automated clause-by-clause risk assessments (HIGH, MEDIUM, LOW), provide interactive source highlighting, offer document-scoped grounded AI Q&A, and generate downloadable executive PDF risk reports.

---

## 🌟 Key Features

### Phase 1: Core Document Ingestion & Storage
- **Multi-Format Upload**: Supports PDF (`pdfplumber`) and plain text (`.txt`) documents up to 25MB.
- **Strict Validation**: Validates file MIME types, file extensions, binary signatures, file sizes, and empty uploads.
- **Page-by-Page Extraction**: Extracted page text is stored with character offsets (`char_start`, `char_end`) for accurate document viewing.

### Phase 2: Clause Extraction & Plain-Language Simplification
- **Section & Clause Aware Breakdown**: Detects numbered sections, headings, and candidate contractual clauses verbatim.
- **Plain-Language Translations**: Translates dense legalese into clear explanations using cautious, non-binding phrasing.

### Phase 3: Risk Assessment & Interactive Navigation
- **Calculated Risk Scoring**: Assigns strict risk levels (`HIGH`, `MEDIUM`, `LOW`) with detailed legal rationale.
- **Executive Summary Dashboard**: Aggregates risk counts and displays overall contract health metrics.
- **Interactive Highlighting**: Clicking any risk finding scrolls and highlights the verbatim clause text in the interactive PDF/Document viewer.

### Phase 4: Document-Grounded AI Chat (RAG)
- **Strict Grounding Enforcement**: Answers user questions strictly using uploaded document excerpts. Rejects hallucinations and outside legal questions with *"I couldn't find this information in the uploaded document."*
- **Source Citation Navigation**: Clicking a citation badge (`Section 8.2 · Page 2 ↗`) instantly navigates the document viewer to the exact page and highlights the cited clause.
- **Isolated Document Scoping**: Vector retrieval is strictly isolated by `document_id`.

### 🚀 Stretch Features
- **Side-by-Side View (Feature A)**: Dual-column comparison view comparing original verbatim contract text side-by-side with plain-language explanations and flagged risk rationales.
- **Executive PDF Risk Report Download (Feature B)**: Generates and streams structured PDF executive summary reports built with ReportLab, including risk metrics, summary cards, clause breakdowns, and legal disclaimers.
- **Document-Type Aware Analysis (Feature C)**: Adapts risk assessment prompts based on contract categories (*Rental Agreements*, *Freelance Contracts*, *Terms of Service*, *Other*).

---

## 🏗️ System Architecture

```
                               ┌────────────────────────────────┐
                               │     React 18 + Vite Frontend   │
                               │  TypeScript / Vanilla CSS UI   │
                               └───────────────┬────────────────┘
                                               │ REST API Calls
                                               ▼
                               ┌────────────────────────────────┐
                               │       FastAPI Async Backend    │
                               │  (SQLAlchemy 2.0 / AsyncPG)    │
                               └───────┬───────────────┬────────┘
                                       │               │
                     ┌─────────────────┴─┐           ┌─┴────────────────┐
                     ▼                   ▼           ▼                  ▼
           ┌───────────────────┐ ┌──────────────┐ ┌───────────┐ ┌──────────────┐
           │ PostgreSQL DB     │ │ pdfplumber   │ │ LLM Engine│ │ ReportLab    │
           │ (pgvector schema) │ │ Text Extract │ │ (OpenAI/  │ │ PDF Report   │
           └───────────────────┘ └──────────────┘ │ Gemini/   │ │ Generator    │
                                                  │ Mock)     │ └──────────────┘
                                                  └───────────┘
```

---

## 🛠️ Technology Stack

- **Backend**: Python 3.11, FastAPI, AsyncPG, SQLAlchemy 2.0, Pydantic v2, pdfplumber, ReportLab, pytest
- **Frontend**: React 18, TypeScript, Vite, Axios, React Router v6
- **Database**: PostgreSQL 14+ / Supabase (with `pgcrypto` and `pgvector` compatible schema)
- **AI/LLM**: OpenAI GPT-4o-mini / Gemini 1.5 Flash / Intelligent Offline Mock Provider

---

## 📂 Project Structure

```
ai-contract-simplifier/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── analysis.py
│   │   │   │   ├── chat.py
│   │   │   │   ├── documents.py
│   │   │   │   └── health.py
│   │   │   └── router.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── database.py
│   │   ├── models/            # SQLAlchemy DB entities
│   │   ├── repositories/      # Data access layer
│   │   ├── schemas/           # Pydantic validation schemas
│   │   ├── services/          # RAG, LLM, Chunking, Extraction, PDF Report
│   │   └── tests/             # Unit and integration tests (50+ passing)
│   ├── uploads/               # Temporary stored uploads
│   ├── requirements.txt
│   └── pytest.ini
├── frontend/
│   ├── src/
│   │   ├── components/        # ClauseList, DocumentViewer, ContractChatPanel, etc.
│   │   ├── pages/             # DashboardPage, DocumentAnalysisPage, UploadPage
│   │   ├── services/          # Axios API client
│   │   └── types/             # TypeScript type definitions
│   ├── package.json
│   └── vite.config.ts
├── database/
│   └── schema.sql             # PostgreSQL schema definition
├── sample-contracts/          # Sample contracts (Rental, Freelance, Terms of Service)
├── docs/                      # Architectural documentation & diagrams
├── PROJECT_VALIDATION.md      # Detailed SRS requirements verification matrix
├── .env.example
└── README.md
```

---

## ⚙️ Environment Variables

Copy `.env.example` to `backend/.env`:

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/lexai_db

# Storage & Application
DEBUG=false
UPLOAD_DIR=uploads
MAX_FILE_SIZE_BYTES=26214400
CORS_ORIGINS=["http://localhost:5173","http://localhost:4173","http://localhost:3000"]

# AI / LLM Configuration (If blank, uses intelligent offline mock provider)
LLM_PROVIDER=openai
LLM_API_KEY=your_openai_or_gemini_api_key
LLM_MODEL=gpt-4o-mini
```

---

## 🚀 Running Locally

### 1. Database Setup
Ensure PostgreSQL is running and initialize the schema:
```bash
psql -U postgres -d lexai_db -f database/schema.sql
```

### 2. Backend Setup & Startup
```bash
cd backend
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Unix:
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
Backend API interactive docs: `http://localhost:8000/docs`

### 3. Frontend Setup & Startup
```bash
cd frontend
npm install
npm run dev
```
Access UI: `http://localhost:5173`

---

## 🧪 Testing

Run full backend test suite:
```bash
cd backend
pytest
```

Run frontend production build validation:
```bash
cd frontend
npm run build
```

---

## ⚠️ Known Limitations

1. **OCR Scanning**: Scanned PDF images without embedded text layers require OCR pre-processing.
2. **Tabular Data**: Highly complex nested multi-column financial tables default to paragraph chunking.

---

## ⚖️ Legal Disclaimer

*LexAI Legal Simplifier is an AI-powered educational and analytical tool designed to summarize contractual text. It does not provide formal legal advice, representation, or attorney-client privileges. Users should consult a qualified legal professional before signing or acting on legal agreements.*
