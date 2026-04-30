# Bianc.ai — Your AI MBA Agent

**Bianc.ai** is a personalised AI MBA Agent built by Lyftbridge. Each user signs in with their Google account, configures their own agent (name, persona, model, values), and gets a private AI that can manage their Gmail, Google Calendar, Drive, Docs, Sheets, Slides, Tasks, and Contacts — plus conduct deep research using Gemini.

---

## Table of Contents

1. [Live Deployments & URLs](#live-deployments--urls)
2. [Google Cloud Account & Services](#google-cloud-account--services)
3. [Repository Structure](#repository-structure)
4. [Architecture Overview](#architecture-overview)
5. [Local Development Setup](#local-development-setup)
6. [Environment Variables Reference](#environment-variables-reference)
7. [Git Workflow — dev → main → deploy](#git-workflow--dev--main--deploy)
8. [How Deployment Works (Cloud Build)](#how-deployment-works-cloud-build)
9. [For Claude Code Users (Quick Start Guide)](#for-claude-code-users-quick-start-guide)

---

## Live Deployments & URLs

| Service | URL | Notes |
|---------|-----|-------|
| **Backend API (Cloud Run)** | `https://bianca-backend-<hash>-uc.a.run.app` | FastAPI — check exact URL in Cloud Run console |
| **Frontend (GitHub Pages)** | `https://lyftbridge-innovation.github.io/Bianca2-google/` | React SPA served statically |
| **GitHub Repository** | `https://github.com/LyftBridge-Innovation/Bianca2-google` | `main` = production, `dev` = development |
| **Google Cloud Console** | `https://console.cloud.google.com/home/dashboard?project=bianca2-73d98` | GCP project `bianca2-73d98` |
| **Cloud Build History** | `https://console.cloud.google.com/cloud-build/builds?project=bianca2-73d98` | See all build runs |
| **Cloud Run Service** | `https://console.cloud.google.com/run/detail/us-central1/bianca-backend?project=bianca2-73d98` | Live backend |
| **Firestore Database** | `https://console.firebase.google.com/project/bianca2-73d98/firestore` | Per-user data |
| **Artifact Registry** | `us-central1-docker.pkg.dev/bianca2-73d98/bianca/bianca-backend` | Docker images |

---

## Google Cloud Account & Services

**GCP Project ID:** `bianca2-73d98`
**GCP Project Number:** `1068648751681`
**Region:** `us-central1` (backend), `global` (Vertex AI Search)

### Services in Use

| GCP Service | What it Does |
|-------------|--------------|
| **Cloud Run** | Hosts the FastAPI backend (`bianca-backend` service). Scales to zero when idle, scales up on traffic. |
| **Cloud Build** | CI/CD pipeline. Triggered manually via `gcloud builds submit .`. Builds Docker image, pushes to Artifact Registry, deploys to Cloud Run. |
| **Artifact Registry** | Stores Docker images at `us-central1-docker.pkg.dev/bianca2-73d98/bianca/bianca-backend`. |
| **Firebase / Firestore** | Database. Stores all per-user data: agent settings, memories, sessions, tasks, skills. Database name: `bianca2`. |
| **Vertex AI Search** | Semantic memory retrieval. Datastore ID: `bianca-memories_1771699589953`. Injected into every chat prompt as context. |
| **Secret Manager** | Stores API keys securely: `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `GOOGLE_WEB_CLIENT_SECRET`, `TWILIO_AUTH_TOKEN`. Never stored in code. |
| **Google OAuth 2.0** | User authentication via Gmail login. Client ID: `1068648751681-l8q67075qjac041gjsgbd5mlpqdd2ftc.apps.googleusercontent.com` |
| **Pub/Sub** | Gmail push notifications. Topic: `projects/bianca2-73d98/topics/gmail-push`. Triggers real-time email processing. |
| **Vertex AI (Gemini)** | Default LLM via Application Default Credentials. Used for chat, memory summarisation, email drafting. |
| **Gemini Deep Research** | Agent `deep-research-preview-04-2026` via the Interactions API. Runs autonomous multi-step research tasks. |

### Firebase Collections (Firestore)

| Collection | What's Stored |
|------------|---------------|
| `users` | User profile + `agent_settings` (name, model, API keys, etc.) |
| `users/{uid}/knowledge` | Per-user knowledge base (persona, education, expertise, company) |
| `users/{uid}/values` | Per-user behavioral values |
| `users/{uid}/skills` | User-uploaded custom skills (YAML) |
| `sessions` | Chat session history |
| `memories_events` | Event-based memories (e.g. "user had a meeting on Tuesday") |
| `memories_entities` | Entity memories (people, companies, facts) |
| `tasks` | Background task queue state |
| `tool_action_log` | Log of every tool call made |

---

## Repository Structure

```
ai-chief-of-staff/
│
├── backend/                    # FastAPI Python backend
│   ├── main.py                 # App entry point — registers all routers
│   ├── config.py               # GCP project IDs, LLM defaults, rate-limit config
│   ├── models.py               # Pydantic data models (User, AgentSettings, etc.)
│   ├── prompts.py              # System prompt assembly (identity + knowledge + values + capabilities)
│   ├── settings_loader.py      # Reads legacy disk settings.json (backward compat)
│   ├── values.py               # Builds the values block for the system prompt
│   ├── knowledge_loader.py     # Reads per-user knowledge from Firestore
│   ├── langchain_tools.py      # Registers all LangChain tools (YAML skills + Python tools)
│   ├── skills_loader.py        # Loads YAML skill files and wraps them as LangChain tools
│   ├── skill_matcher.py        # Matches user intent to skill from YAML metadata
│   ├── memory_utils.py         # Writes memories to Firestore + Vertex AI Search
│   ├── summarization.py        # Summarises long content using Gemini
│   ├── task_service.py         # Google Cloud Tasks integration for background jobs
│   ├── requirements.txt        # All Python dependencies
│   ├── firebase-credentials.json  # Service account key (NOT committed — add manually)
│   ├── .env                    # Local dev secrets (NOT committed to git)
│   │
│   ├── routers/                # FastAPI route handlers
│   │   ├── auth.py             # Google OAuth login, session cookie, logout
│   │   ├── chat.py             # Main SSE chat endpoint (/chat/stream)
│   │   ├── config.py           # Agent settings CRUD (read/save Neural Config data)
│   │   ├── admin.py            # Admin endpoints (migrate users, delete user data)
│   │   ├── onboarding.py       # Onboarding wizard + AI-guided setup chat endpoint
│   │   ├── tasks.py            # Background task status polling
│   │   ├── skills.py           # User skill marketplace endpoints
│   │   ├── email_agent.py      # Gmail auto-reply agent (Pub/Sub triggered)
│   │   ├── twilio_voice.py     # Twilio phone call webhooks
│   │   ├── voice.py            # WebSocket voice endpoint
│   │   └── user_data.py        # User data read endpoints
│   │
│   ├── skills/                 # YAML skill definitions (8 built-in Google Workspace skills)
│   │   ├── calendar.yaml       # Create, list, update, delete calendar events
│   │   ├── gmail.yaml          # Read, draft, send, search emails
│   │   ├── docs.yaml           # Create and edit Google Docs
│   │   ├── sheets.yaml         # Create and edit Google Sheets
│   │   ├── slides.yaml         # Create Google Slides presentations
│   │   ├── drive.yaml          # Upload, search, manage Drive files
│   │   ├── tasks.yaml          # Manage Google Tasks
│   │   └── people.yaml         # Search Google Contacts
│   │
│   ├── tools/                  # Python tool implementations
│   │   ├── gws_client.py       # Wraps the `gws` CLI for all Google Workspace operations
│   │   ├── calendar.py         # Calendar tool logic
│   │   ├── gmail.py            # Gmail tool logic
│   │   ├── gemini_research.py  # Gemini Deep Research Agent tool (replaces Perplexity)
│   │   ├── document_engine.py  # Generates .docx and .pptx files via Node.js
│   │   ├── drive_uploader.py   # Uploads generated files to Google Drive
│   │   └── email_agent_engine.py  # Core email drafting/reply logic
│   │
│   └── knowledge/              # Global fallback config (per-user config is in Firestore)
│       └── settings.json       # Disk-based settings override (legacy/admin only)
│
├── frontend/                   # React 19 + Vite frontend
│   ├── index.html              # Entry HTML — sets page title and favicon
│   ├── vite.config.js          # Vite config — base path for GitHub Pages
│   ├── package.json            # npm dependencies
│   ├── .env                    # Local dev env vars (VITE_API_BASE_URL, VITE_GOOGLE_CLIENT_ID)
│   │
│   ├── public/                 # Static assets served at root
│   │   ├── lyftbridge-wordmark-dark.png   # Full Lyftbridge logo (dark bg)
│   │   ├── lyftbridge-favicon.png         # Circular Lyftbridge favicon
│   │   └── lyftbridge.jpeg                # Legacy small logo (kept for reference)
│   │
│   └── src/
│       ├── main.jsx            # React app bootstrap
│       ├── App.jsx             # Root component — routing + auth gate + onboarding gate
│       │
│       ├── styles/
│       │   └── global.css      # Design system: CSS custom properties, colors, typography
│       │
│       ├── context/
│       │   └── AuthContext.jsx # Google login state shared across the whole app
│       │
│       ├── hooks/
│       │   └── useChat.js      # SSE streaming hook — manages chat state and tool events
│       │
│       ├── api/
│       │   └── client.js       # All fetch calls to the backend (one place for all API calls)
│       │
│       ├── components/
│       │   ├── Auth/
│       │   │   ├── LoginPage.jsx     # Google Sign-In page
│       │   │   └── LoginPage.css
│       │   ├── Chat/
│       │   │   ├── ChatInput.jsx     # Message input bar
│       │   │   ├── ChatMessages.jsx  # Message list with SSE token streaming
│       │   │   ├── EmptyState.jsx    # Shown when no messages yet
│       │   │   └── ToolCallCard.jsx  # Visual card for tool invocations in chat
│       │   └── Layout/
│       │       ├── AppLayout.jsx     # Main app shell (sidebar + content area)
│       │       ├── Sidebar.jsx       # Navigation sidebar with chat history
│       │       ├── Footer.jsx        # Lyftbridge footer (used on all pages)
│       │       └── *.css             # Component styles
│       │
│       └── pages/
│           ├── NeuralConfig.jsx      # Agent settings UI (persona, model, API keys, values, skills)
│           ├── NeuralConfig.css
│           ├── OnboardingFlow.jsx    # First-time setup wizard (manual or AI-guided)
│           ├── OnboardingFlow.css
│           ├── Marketplace.jsx       # Skill marketplace
│           └── Marketplace.css
│
├── voice_pipeline/             # Standalone Gemini Live voice agent (separate process)
│   ├── main.py                 # Entry point — runs the voice app
│   ├── gemini_session.py       # Gemini Live API WebSocket session management
│   ├── audio_handler.py        # Microphone input + speaker output
│   ├── audio_utils.py          # Audio format utilities
│   ├── voice_config.py         # Voice model, audio settings
│   ├── voice_prompts.py        # Self-contained system prompt (no backend imports)
│   ├── tool_declarations.py    # Function declarations for Gemini Live tool calls
│   ├── tool_dispatcher.py      # Executes tool calls received from Gemini Live
│   └── requirements.txt        # Voice pipeline Python deps
│
├── logo/                       # Brand assets
│   ├── Lyftbridge on Transparent for Black Backgrounds Large.png  # Dark bg wordmark
│   ├── Lyftbridge on Transparent for white backgrounds Large.png  # Light bg wordmark
│   └── 3-23-26 Lyftbridge Favicon.png                            # Circular favicon icon
│
├── docs/                       # Project documentation and planning notes
├── Dockerfile                  # Multi-stage build: Python 3.11 + Node 20 + gws CLI
├── cloudbuild.yaml             # Cloud Build CI/CD pipeline definition
├── CLAUDE.md                   # Instructions for Claude Code (AI coding agent)
└── README.md                   # This file
```

---

## Architecture Overview

### How a Chat Message Flows

```
User types message
       ↓
Frontend (React) → POST /chat/stream  (with session cookie + user_id)
       ↓
backend/routers/chat.py
  1. Loads per-user settings from Firestore
  2. Assembles system prompt:
       • Identity (name, role, language, model)
       • Knowledge base (persona, education, expertise, company)
       • Values (behavioral rules)
       • Capabilities (Google Workspace tool list)
       • Gemini Deep Research capability (if Google key is set)
       • Semantic memories from Vertex AI Search
  3. Selects LLM:
       • Claude → Anthropic API (user's own key via BYOK)
       • Gemini → Vertex AI (Application Default Credentials)
  4. Binds LangChain tools (YAML skills + Python tools)
  5. Streams response as SSE events:
       token        → a chunk of text
       tool_call    → agent is using a tool
       tool_result  → tool returned a result
       done         → stream finished
       ↓
Frontend renders tokens live, shows tool call cards
```

### Key Design Decisions

- **Per-user everything**: All agent config (name, persona, model, API keys, knowledge, values) is stored in Firestore under `users/{uid}`. Nothing is shared between users.
- **BYOK (Bring Your Own Key)**: Users supply their own Anthropic or Google API keys. The backend never falls back to a shared key.
- **Google Workspace via `gws` CLI**: All Gmail/Calendar/Drive operations go through the `gws` npm package (a CLI wrapper around the Google APIs). The CLI token is stored per-user in Firestore.
- **Long tasks via Cloud Tasks**: Slow operations (creating documents, sending emails) are offloaded to Google Cloud Tasks so the SSE stream stays alive.
- **Gemini Deep Research**: Uses the `deep-research-preview-04-2026` Interactions API agent, which autonomously plans, searches, reads, and synthesises research reports. Takes 2–10 minutes per request.

---

## Local Development Setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- `gcloud` CLI authenticated with project `bianca2-73d98`
- A `firebase-credentials.json` service account key (download from Firebase Console → Project Settings → Service Accounts)

---

### 1. Clone the Repository

```bash
git clone https://github.com/LyftBridge-Innovation/Bianca2-google.git
cd Bianca2-google
```

---

### 2. Python Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

---

### 3. Backend Setup

```bash
cd backend
pip install -r requirements.txt
```

Create `backend/.env` by copying the example below (fill in your values):

```env
GOOGLE_API_KEY=<your-google-ai-studio-key>
ANTHROPIC_API_KEY=<your-anthropic-key>

GOOGLE_CLIENT_ID=1068648751681-l8q67075qjac041gjsgbd5mlpqdd2ftc.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=<from-google-cloud-console>
GOOGLE_WEB_CLIENT_ID=1068648751681-l8q67075qjac041gjsgbd5mlpqdd2ftc.apps.googleusercontent.com
GOOGLE_WEB_CLIENT_SECRET=<from-google-cloud-console>

FIREBASE_PROJECT_ID=bianca2-73d98
FIREBASE_CREDENTIALS_PATH=firebase-credentials.json
FIREBASE_DATABASE_NAME=bianca2
GOOGLE_APPLICATION_CREDENTIALS=firebase-credentials.json

ASSISTANT_NAME=Bianc.ai

VERTEX_DATASTORE_ID=bianca-memories_1771699589953
VERTEX_LOCATION=global
VERTEX_PROJECT_ID=bianca2-73d98
```

Also place `firebase-credentials.json` inside the `backend/` directory. Download it from:
> Firebase Console → `bianca2-73d98` → Project Settings → Service Accounts → Generate new private key

Run the backend:

```bash
cd backend
source ../venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Backend is now live at `http://localhost:8000`. Test with `GET http://localhost:8000/` — should return `{"status": "ok"}`.

---

### 4. Frontend Setup

```bash
cd frontend
npm install
```

Create `frontend/.env`:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_GOOGLE_CLIENT_ID=1068648751681-l8q67075qjac041gjsgbd5mlpqdd2ftc.apps.googleusercontent.com
```

Run the frontend dev server:

```bash
npm run dev
```

Frontend is now live at `http://localhost:5173`.

---

### 5. Voice Pipeline (Optional — Standalone)

The voice pipeline runs as a completely separate process. It does NOT import anything from the backend.

```bash
cd voice_pipeline
source ../venv/bin/activate
pip install -r requirements.txt
python main.py
```

This opens a microphone session with Gemini Live. Press `Ctrl+C` to stop.

---

## Environment Variables Reference

### Backend (`backend/.env`)

| Variable | Description | Where to Get It |
|----------|-------------|-----------------|
| `GOOGLE_API_KEY` | Google AI Studio API key (used by Gemini models + Deep Research) | [aistudio.google.com](https://aistudio.google.com) → Get API key |
| `ANTHROPIC_API_KEY` | Anthropic API key (used when user picks a Claude model) | [console.anthropic.com](https://console.anthropic.com) |
| `GOOGLE_CLIENT_ID` | OAuth 2.0 client ID for user login | Cloud Console → APIs & Services → Credentials |
| `GOOGLE_CLIENT_SECRET` | OAuth 2.0 client secret | Same as above |
| `GOOGLE_WEB_CLIENT_ID` | Same as `GOOGLE_CLIENT_ID` (both needed by different parts of the app) | Same as above |
| `GOOGLE_WEB_CLIENT_SECRET` | Same as `GOOGLE_CLIENT_SECRET` | Same as above |
| `FIREBASE_PROJECT_ID` | Firebase project ID | `bianca2-73d98` |
| `FIREBASE_CREDENTIALS_PATH` | Path to service account JSON file | `firebase-credentials.json` |
| `FIREBASE_DATABASE_NAME` | Firestore database name | `bianca2` |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account key (used by Google SDKs) | Same file as `firebase-credentials.json` |
| `ASSISTANT_NAME` | Default name for the assistant | `Bianc.ai` |
| `VERTEX_DATASTORE_ID` | Vertex AI Search datastore for memory retrieval | `bianca-memories_1771699589953` |
| `VERTEX_LOCATION` | Vertex AI Search location | `global` |
| `VERTEX_PROJECT_ID` | GCP project for Vertex AI | `bianca2-73d98` |
| `TWILIO_ACCOUNT_SID` | Twilio account SID (optional — enables phone calls) | [console.twilio.com](https://console.twilio.com) |
| `TWILIO_AUTH_TOKEN` | Twilio auth token (optional) | Same as above |

### Frontend (`frontend/.env`)

| Variable | Description |
|----------|-------------|
| `VITE_API_BASE_URL` | URL of the running backend. Use `http://localhost:8000` for local dev, or the Cloud Run URL for staging. |
| `VITE_GOOGLE_CLIENT_ID` | Google OAuth client ID — same value as the backend's `GOOGLE_CLIENT_ID`. |

---

## Git Workflow — dev → main → deploy

This project uses a two-branch workflow. **All development work goes into `dev` first, then gets merged into `main`, and `main` is what gets deployed.**

### Branch Rules

| Branch | Purpose |
|--------|---------|
| `dev` | Active development. Make all changes here. Test locally. Push here first. |
| `main` | Production. Only updated by merging from `dev`. Triggers deployment. |

### Step-by-Step Workflow

**1. Switch to the dev branch and make sure it's up to date:**

```bash
git checkout dev
git pull origin dev
```

**2. Make your changes to any files.**

**3. Stage and commit your changes:**

```bash
git add .
git commit -m "feat: describe what you changed"
```

Commit message format (keep to 2 lines max):
- `feat:` — new feature
- `fix:` — bug fix
- `refactor:` — code restructure with no behavior change
- `docs:` — documentation only

**4. Push dev to GitHub:**

```bash
git push origin dev
```

**5. Merge dev into main:**

```bash
git checkout main
git merge dev --no-ff -m "Merge branch 'dev': short description of changes"
git push origin main
```

**6. Deploy to Google Cloud (see next section).**

---

## How Deployment Works (Cloud Build)

### What `cloudbuild.yaml` Does

The CI/CD pipeline has three steps:

1. **Build** — Builds a Docker image from `Dockerfile`. The image contains Python 3.11, Node.js 20, the `gws` CLI, all Python dependencies from `requirements.txt`, and all backend source code.
2. **Push** — Pushes the Docker image to Google Artifact Registry at:
   `us-central1-docker.pkg.dev/bianca2-73d98/bianca/bianca-backend:latest`
3. **Deploy** — Deploys the new image to Cloud Run (`bianca-backend` service in `us-central1`). Injects environment variables and secrets from Google Secret Manager.

### How to Trigger a Deployment

```bash
# From the repo root (not backend/ or frontend/)
gcloud builds submit .
```

This uploads your source to Google Cloud Storage, runs the three-step pipeline, and deploys the new backend. A typical build takes **5–7 minutes**.

You can watch the build live at:
`https://console.cloud.google.com/cloud-build/builds?project=bianca2-73d98`

### What Gets Deployed

Only the **backend** is deployed to Cloud Run. The **frontend** is a static site hosted on GitHub Pages — it does not need a separate deployment step. GitHub Pages automatically serves from the `main` branch's built output (or can be set to serve the `public/` folder, depending on GitHub Pages settings).

### Secrets in Production

Sensitive values are stored in Google Secret Manager and injected into Cloud Run at runtime. They are **never** in `cloudbuild.yaml` as plaintext. The secrets currently configured are:

- `ANTHROPIC_API_KEY`
- `GOOGLE_API_KEY`
- `GOOGLE_WEB_CLIENT_SECRET`
- `TWILIO_AUTH_TOKEN`

To update a secret value (e.g. rotate an API key):

```bash
echo -n "new-key-value" | gcloud secrets versions add SECRET_NAME --data-file=-
```

---

## For Claude Code Users (Quick Start Guide)

This section is for your AI coding agent (Claude Code / Cursor). Read `CLAUDE.md` first — it contains project-specific instructions for the AI.

### What Claude Code Needs to Know

1. **The backend is Python (FastAPI)**. It lives in `backend/`. All Python changes go there.
2. **The frontend is React (Vite)**. It lives in `frontend/src/`. All UI changes go there.
3. **Never commit `backend/.env` or `backend/firebase-credentials.json`** — these contain secrets.
4. **Always run `npm run build` in `frontend/` after any frontend change** to verify the build is clean before committing.
5. **All API calls from the frontend go through `frontend/src/api/client.js`** — never add fetch calls directly in components.
6. **CSS lives next to each component** — do not use Tailwind. Use CSS modules/files and pull colours from `frontend/src/styles/global.css` custom properties.

### Getting Started from Scratch

```bash
# 1. Clone
git clone https://github.com/LyftBridge-Innovation/Bianca2-google.git
cd Bianca2-google

# 2. Python environment
python3 -m venv venv
source venv/bin/activate

# 3. Backend deps
cd backend && pip install -r requirements.txt && cd ..

# 4. Copy secrets (get these from the project owner)
#    • backend/.env         — paste the .env contents
#    • backend/firebase-credentials.json — paste the service account JSON

# 5. Frontend deps
cd frontend && npm install && cd ..

# 6. Run both (two separate terminals)
# Terminal 1 — backend
cd backend && source ../venv/bin/activate && uvicorn main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend && npm run dev
```

Open `http://localhost:5173` in your browser. Sign in with a Google account.

### Common Tasks for Claude Code

| Task | Files to Edit |
|------|--------------|
| Change the system prompt | `backend/prompts.py` |
| Add a new backend route | `backend/routers/` (new file) + register in `backend/main.py` |
| Add a new frontend page | `frontend/src/pages/` (new file) + add to `frontend/src/App.jsx` |
| Add a new Google Workspace tool | `backend/skills/` (new YAML file) |
| Add a new Python tool | `backend/tools/` (new file) + import in `backend/langchain_tools.py` |
| Change agent settings fields | `backend/models.py` (AgentSettings) + `frontend/src/pages/NeuralConfig.jsx` |
| Change available LLM models | `frontend/src/pages/NeuralConfig.jsx` (MODEL_GROUPS) + `frontend/src/pages/OnboardingFlow.jsx` (MODEL_OPTIONS) + `backend/routers/onboarding.py` (_VALID_MODELS) |
| Deploy a new version | `git add . && git commit -m "..." && git push origin dev` then merge to main and run `gcloud builds submit .` |

### Running Checks Before Committing

```bash
# Frontend build (must pass with no errors)
cd frontend && npm run build

# Frontend lint
cd frontend && npm run lint

# Backend syntax check
cd backend && python -m py_compile main.py routers/chat.py prompts.py models.py
```

---

*Last updated: April 2026. Maintained by Lyftbridge Innovation.*
