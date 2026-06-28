# CensusDas.AI Staff Room

Try out the Demo:
https://censusdas-ai-staffroom--vaibhavshastri8.replit.app 

## 1. What This Product Is

**CensusDas.AI Staff Room** is a production-ready, multi-agent AI chat platform built specifically for Census of India field officers — Enumerators and Supervisors. It allows users to ask procedural, legal, and operational questions about census manuals and receive cited, contextually accurate answers in multiple Indian languages and communication styles.

The system is designed to replace or supplement printed instruction manuals in the field, acting as an always-available, language-aware expert assistant.

---

## 2. Architecture at a Glance

```
┌────────────────────────────────────┐
│          React Frontend (SPA)      │
│  Vite + Tailwind CSS v4 + React 19 │
└──────────────┬─────────────────────┘
               │ HTTP (same-origin REST)
               ▼
┌────────────────────────────────────────────────────────┐
│               FastAPI Backend (Python)                  │
│                                                        │
│  ┌──────────┐  ┌────────────┐  ┌────────────────────┐ │
│  │  Router  │  │   Expert   │  │    Assistant       │ │
│  │  Agent   │→ │   Agent    │→ │    Agent (Recap)   │ │
│  │ (hidden) │  │ GPT-4.1m   │  │    GPT-4.1-mini    │ │
│  └──────────┘  └─────┬──────┘  └────────────────────┘ │
│                       │                                │
│               ┌───────▼──────┐                         │
│               │  FAISS RAG   │                         │
│               │  Retriever   │                         │
│               │ (dual-index) │                         │
│               └──────────────┘                         │
└────────────────────────────────────────────────────────┘
```

**Deployment model:** The backend serves the compiled React build directly as static files — a single deployable unit (no separate frontend server needed).

---

## 3. Technology Stack

| Layer | Technology | Version / Notes |
|---|---|---|
| Frontend Framework | React | v19.1 |
| Frontend Build | Vite | v7.0.4 |
| CSS | Tailwind CSS | v4.1 (PostCSS) |
| Backend Framework | FastAPI + Uvicorn | Python 3.12 |
| AI Models | OpenAI GPT-4.1-mini, GPT-4o | Via OpenAI SDK |
| Embeddings | `text-embedding-3-large` | OpenAI |
| Vector Search | FAISS (FlatIP index) | Facebook AI |
| Data Serialization | Pickle + JSON | FAISS metadata |
| Config | YAML | Persona/agent definitions |
| Session Store | In-memory dict | `SESSION_STORE = {}` |
| Linting | ESLint v9 | React-hooks + react-refresh plugins |

---

## 4. Repository Structure

```
/
├── index.html                   # Vite SPA shell
├── vite.config.js               # Vite build config
├── package.json                 # Frontend deps (React, Tailwind, Vite)
├── postcss.config.js            # PostCSS / Tailwind setup
├── eslint.config.js             # ESLint rules
├── dist/                        # Compiled frontend (served by FastAPI)
│
├── src/                         # React frontend source
│   ├── App.jsx                  # Root layout, responsive logic, login state
│   ├── Sidebar.jsx              # Agent bios, login/logout, app info
│   ├── MainChat.jsx             # Chat UI, session management, flavor picker
│   ├── api.js                   # Centralized API fetch utility
│   └── index.css                # Global styles
│
└── backend/                     # Python FastAPI server
    ├── main.py                  # App entry; mounts routers + serves /dist
    └── app/
        ├── session_store.py     # In-memory session dictionary
        ├── routers/
        │   ├── chat.py          # POST /api/chat (main entry point)
        │   ├── flavors.py       # GET /api/flavors
        │   ├── corrections.py   # POST /api/corrections
        │   ├── session.py       # Session management endpoints
        │   ├── persona.py       # Persona info endpoints
        │   └── admin.py         # Admin utilities
        ├── orchestrator/
        │   └── conversation.py  # Multi-agent pipeline (core logic)
        ├── rag/
        │   ├── retriever.py     # FAISS embed + search
        │   └── data/
        │       ├── semantic_chunks_faiss_flatip.idx
        │       ├── semantic_chunks_meta.pkl
        │       ├── pages_faiss_flatip.idx
        │       ├── pages_meta.pkl
        │       └── corrections_log.json
        ├── config/
        │   ├── persona_loader.py
        │   └── persona_prompts/
        │       ├── assistant.yaml   # Assistant agent full config + knowledge base
        │       └── expert.yaml      # Expert agent config
        └── models/
            ├── session.py
            ├── message.py
            └── corrections.py
```

---

## 5. Core Engineering Components

### 5.1 Multi-Agent Orchestration Pipeline

Every user message flows through a deterministic 3-stage pipeline in `conversation.py`:

**Stage 1 — Hidden Router Agent** (`gpt-4.1-mini`, temp=0.1)  
Classifies the query as `general` (conversational) or `manual` (requires RAG). Also rewrites the query into English for better vector retrieval. Falls back to `manual` on ambiguity. , manual here refers to the Official Instruction Manuals issued by ORGI, Ministry of Home Affairs, for field staff in census 2011, available on the department website, this was built as a part of ongoing efforts to modernize the next Census of India.

**Stage 2 — Expert Agent** (`gpt-4.1-mini`, temp=0.2) — *manual route only*  
Receives the reframed query + top-6 retrieved pages from FAISS. Generates a scholarly English answer with explicit manual/section/page citations. Never exposes internal Manual_01/Manual_02 codes — uses full official manual names only.

**Stage 3 — Assistant Agent** (`gpt-4.1-mini`, temp=0.65)  
- On **general** route: answers directly in the user's chosen language and style.  
- On **manual** route: acts as interpreter — recaps the Expert's answer in simple terms in the user's language, then adds 2–3 contextual follow-up question suggestions.

All three reply objects (`PersonaReply`) are returned to the frontend in sequence and rendered as a multi-persona conversation.

---

### 5.2 RAG Retrieval System

**File:** `backend/app/rag/retriever.py`

- Embeds queries using `text-embedding-3-large` via OpenAI API
- Maintains **two separate FAISS FlatIP (inner product) indices** loaded at startup:
  - `semantic_chunks` — fine-grained chunks (top_k=25) for precise retrieval
  - `pages` — full-page units (top_k=6) for broader context
- The Expert currently uses `retrieve_pages` (top 6 pages); `retrieve_chunks` is available for future use
- **Live corrections:** `corrections_log.json` allows field-level metadata overrides per `chunk_id`/`page_id` without rebuilding the FAISS index — active corrections are applied at query time

**Knowledge base covers:** Census of India Instruction Manuals 01 and 02 (covering houselisting, housing census, population enumeration, legal framework, field procedures)

---

### 5.3 Flavor System (Language × Style)

Controlled entirely via `assistant.yaml` — not hardcoded. Each "flavor" is a combination of:
- **Language:** Hindi, Tamil, Telugu, English, and others
- **Style:** Warm, Technical, Concise, Friendly

On flavor change mid-session, the system emits a small bridge message and continues context — no session reset occurs. The `flags` dictionary on the session object tracks previous language/style to detect transitions.

---

### 5.4 Frontend Architecture

**`App.jsx`** — manages login state and responsive breakpoint (≤700px = mobile).  
On **mobile**: shows Sidebar (login) first, then swaps to MainChat after login.  
On **desktop**: renders both panels side-by-side simultaneously.

**`MainChat.jsx`** — generates a UUID per session, manages chat history in local state, renders the typed multi-persona conversation with per-agent typing indicators.

**`api.js`** — all backend calls go through a single fetch utility using relative URLs (same-origin, no CORS concerns in production).

---

### 5.5 Session Management

Sessions are stored in a plain **in-memory Python dictionary** (`SESSION_STORE = {}`).  
Each session carries:
- `uuid` — client-generated UUID
- `user_name`, `language`, `style`
- `history` — last 20 messages used for LLM context (full history preserved upstream)
- `last_topic` — used for topic continuity hints
- `flags` — dict for flavor-change tracking and feature flags

> ⚠️ **Note:** In-memory session storage, all sessions are lost on server restart. This is acceptable for stateless/demo deployments but would need an upgrade (Redis, DB) for production scale or persistence requirements.

---

## 6. API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/chat` | Main chat — accepts message, returns list of `PersonaReply` |
| `GET` | `/api/flavors` | Returns available language/style combinations |
| `POST` | `/api/corrections` | Adds a RAG metadata override to `corrections_log.json` |
| `GET` | `/api/session/{id}` | Retrieve session state |
| `GET` | `/api/persona` | Returns persona info (for sidebar bios) |
| `GET/POST` | `/api/admin` | Admin utilities |
| `GET` | `/*` | Serves React SPA (`dist/index.html`) with SPA fallback |

---

## 7. Configuration & Environment

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | Required. Used for both embeddings and all LLM calls |

Loaded via `python-dotenv` in `retriever.py` and `conversation.py`. No other external service dependencies.

Persona behavior is configured entirely through:
- `backend/app/config/persona_prompts/assistant.yaml` — Assistant role, full Census knowledge base (6 knowledge transfer parts), flavors, greetings
- `backend/app/config/persona_prompts/expert.yaml` — Expert role and citation behavior

---

## 8. Build & Run

### Frontend
```bash
npm install        # install dependencies
npm run build      # compiles to /dist (served by FastAPI)
npm run dev        # local dev server (Vite, port 5173)
```

### Backend
```bash
cd backend
pip install -r requirements.txt    # (if requirements.txt present)
uvicorn main:app --reload          # starts FastAPI on port 8000
```

In production, `dist/` must be built before starting the backend — FastAPI checks for its existence at startup and logs a clear message if missing.

---
