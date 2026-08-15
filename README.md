# 🎓 COE Automator — AI-Powered Academic Assistant

> **Autonomous AI tutor built for SSN College of Engineering students** — bridging the gap between institutional PDFs and intelligent, real-time academic assistance.

---

## 🌐 The Problem We Solved (Externals)

The **COE SSN website** hosts a wealth of academic resources — previous year question papers (QPs), unit-wise syllabi, curriculum PDFs, and regulation documents. The traditional student workflow looked like this:

```
Student visits COE portal
    → Finds the PDF (previous year QP / syllabus / curriculum)
    → Downloads it manually
    → Opens AI chatbot in another tab
    → Copy-pastes content or re-types questions
    → Gets a generic, context-free response
```

This is **slow, fragmented, and frustrating** — especially the night before an exam.

---

### ✅ What COE Automator Does Instead

We **bridged this gap** by directly ingesting the PDF content from official COE materials and piping it straight into an AI pipeline — no manual step in between:

```
Student opens COE Automator
    → Selects a subject or asks a question
    → AI reads the actual indexed PDF content internally
    → Returns context-aware, curriculum-aligned, exam-ready answers instantly
```

No downloading. No copy-pasting. No tab switching.

---

## 💡 Key External Features

| Feature | Description |
|---|---|
| 📄 **Live PDF Ingestion** | Automatically parses previous year QPs, syllabus, and curriculum PDFs from the COE SSN materials folder |
| 🔁 **Re-index on Demand** | Trigger a fresh scan of COE materials at any time with one click from the UI |
| 📚 **Syllabus Mode** | Ask natural language questions about curriculum, unit topics, and course objectives — answered directly from official PDF text |
| 🎯 **Course-Specific QP Analysis** | Select any subject to discover repeated questions, unit-wise trends, and high-weightage topics across past papers |
| 💬 **General Academic Chat** | Unconstrained AI tutoring for any engineering concept — no course filter required |
| 🏫 **Multi-Department Support** | Filter and browse courses by department (CSE, ECE, EEE, MECH, etc.) |

---

## ⚙️ How It Works Internally (Architecture)

The project is split into a **React frontend** and a **Python FastAPI backend**, deployed separately and connected via a REST proxy.

### Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 18 + Vite, Vanilla CSS (glassmorphism dark theme) |
| **Backend** | Python FastAPI + Uvicorn |
| **PDF Parsing** | `pypdf` — full-text extraction from COE material PDFs |
| **AI Engine** | Google Gemini (`google-generativeai`) with OpenAI as fallback |
| **Database** | Turso (libSQL) cloud DB for indexed question storage |
| **Deployment** | Frontend → Vercel · Backend → Render |

---

### Internal Data Flow

```
[ COE PDF Files — QPs / Syllabus / Curriculum ]
             ↓
       parser.py
  Extracts text, detects course codes,
  parses questions and unit info
             ↓
       database.py
  Stores structured Q&A + metadata
  in Turso libSQL cloud DB
             ↓
       agent.py
  Orchestrates AI context:
  picks relevant QP chunks, builds prompts
             ↓
       main.py  (FastAPI)
  REST API: /query, /courses, /ingest, /status
             ↓
  React Frontend
  Chat workspace — renders markdown responses,
  course picker, syllabus mode, preset chips
```

---

### Backend API Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/status` | GET | Indexing status + aggregate stats (courses, papers, questions) |
| `/api/courses` | GET | List all indexed courses with department metadata |
| `/api/ingest` | POST | Trigger PDF re-scan and full indexing pipeline |
| `/api/query` | POST | Submit a question → AI returns context-aware analysis |

---

### Frontend Architecture

- **Left Panel** — Query configuration: department filter, course search, mode selectors (General Chat / Syllabus Mode), active course chip
- **Right Panel** — Chat workspace: scrollable message stream with Markdown rendering, preset query chips, animated typing indicator
- **Status Polling** — Auto-polls `/api/status` every 2–3 seconds during indexing via `setInterval` with ref-based cleanup

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- A `.env` file in `/backend` with your API keys (see below)

### Backend Setup

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### Environment Variables — `backend/.env`

```env
GEMINI_API_KEY=your_google_gemini_key
OPENAI_API_KEY=your_openai_key
TURSO_DATABASE_URL=libsql://your-db.turso.io
TURSO_AUTH_TOKEN=your_turso_auth_token
```

---

## 📁 Project Structure

```
coeautomator/
├── backend/
│   ├── main.py              # FastAPI app & API route handlers
│   ├── agent.py             # AI orchestration, context building & prompt logic
│   ├── parser.py            # PDF text extraction & question/unit parsing
│   ├── database.py          # Turso libSQL schema, queries & data access
│   ├── config.py            # App-wide configuration constants
│   ├── build_cache.py       # Course code cache builder utility
│   ├── find_pdfs.py         # PDF discovery & verification tool
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── App.jsx          # Main single-page React workspace
│       └── index.css        # Full dark theme + glassmorphism design system
├── vercel.json              # Vercel frontend deployment + API proxy config
├── render.yaml              # Render backend deployment config
└── coe materials/           # Local PDF store — QPs, syllabus, curriculum
```

---

## 🎨 UI Design Highlights

- **Dark engineering lounge aesthetic** — deep navy/slate backgrounds, teal accent palette
- **Glassmorphism panels** — frosted glass cards for the config panel and chat workspace
- **Ambient floating particles** — subtle animated background with drifting dots and plus signs
- **Markdown-rendered AI responses** — rich formatting: tables, code blocks, bold, lists
- **Real-time typing indicator** — three pulsing dots during AI inference

---

## 🏫 Built For

**SSN College of Engineering, Chennai** — students across all departments dealing with exam prep, syllabus queries, and previous year QP analysis across regulations R2021, R2024, and beyond.

---

## 📜 License

MIT — open for contributions and forks.
