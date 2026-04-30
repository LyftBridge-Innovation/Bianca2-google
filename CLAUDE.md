# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Bianc.ai** — an AI Chief of Staff with a chat interface and Google Workspace integration. FastAPI backend + React frontend + a standalone Gemini Live voice pipeline.

## Development Commands

### Backend (FastAPI)
```bash
cd backend
source ../venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
# or: python main.py
```
Runs on `http://localhost:8000`. Health check: `GET /`

### Frontend (React + Vite)
```bash
cd frontend
npm run dev        # http://localhost:5173
npm run lint       # ESLint
npm run build      # Production build
```

### Voice Pipeline (standalone)
```bash
cd voice_pipeline
source ../venv/bin/activate
python main.py
```

### Environment Setup
- Backend: `backend/.env` (see `.env.example` for required vars)
- Frontend: `frontend/.env` with `VITE_API_BASE_URL` and `VITE_GOOGLE_CLIENT_ID`

## Architecture

### Request Flow
1. Frontend POSTs to `/chat/stream` → returns SSE stream
2. `routers/chat.py` builds system prompt (identity + knowledge + values + capabilities + memory)
3. Invokes LangChain with `ChatVertexAI` (gemini-2.5-flash) and bound tools from `skills_loader.py`
4. Long-running tool calls (create_doc, send_email) are offloaded to **Google Cloud Tasks** via `task_service.py`
5. Results stream back as SSE events: `token`, `tool_call`, `tool_result`, `done`

### Prompt Layers (in order)
1. Identity + date/time — `backend/prompts.py::_build_identity_block()`
2. Knowledge base — `backend/knowledge_loader.py` reads `backend/knowledge/` (01_persona, 02_education, 03_expertise, 04_company)
3. Values — `backend/values.py::build_values_block()`
4. Capabilities — static block in `backend/prompts.py`
5. Memory — injected at request time in `backend/routers/chat.py` from Vertex AI Search

### Skills / Tools System
- 8 skills defined as YAML in `backend/skills/` (calendar, gmail, docs, sheets, slides, drive, tasks, people)
- `backend/skills_loader.py` reads YAMLs and binds them as LangChain tools
- `backend/skill_matcher.py` scans first 4 lines of skill YAML to match intent
- Each skill has dynamic OAuth scopes; user tokens stored in Firestore
- `backend/tools/gws_client.py` wraps the `gws` CLI — must pass `GOOGLE_WORKSPACE_CLI_TOKEN` via `env=env` in `subprocess.run`

### Google Workspace Integration
- All GWS operations go through `gws` CLI (external binary)
- Error details from `gws` are in stdout JSON, not stderr
- OAuth tokens: `access_type: 'offline'` + `prompt: 'consent'` required for refresh token re-issuance with new scopes

### Memory & Storage
- **Firestore**: user auth, sessions, task queue state, user-uploaded skills
- **Vertex AI Search** (datastore): semantic memory retrieval, injected into every prompt
- Firestore collections: `users`, `sessions`, `memories_events`, `memories_entities`, `tasks`, `skills`

### Background Task Queue
- `backend/task_service.py` enqueues long-running tasks to Google Cloud Tasks
- `backend/routers/tasks.py` handles task status/polling endpoints
- SSE keepalive loop in `routers/chat.py` keeps the connection alive while tasks run
- Task queue uses thread-safe queues for push operations

### Voice Pipeline (Gemini Live)
- Entirely separate process in `voice_pipeline/` — not imported by backend
- `gemini_session.py` manages Gemini Live API websocket session
- After a `tool_call` event, ONLY `send_tool_response` is valid — no `send_text` in between
- `FunctionResponse.id` must echo back the `FunctionCall.id`
- `Type.ARRAY` params require `items=Schema(type=...)` in declarations
- Voice system prompt is self-contained in `voice_pipeline/voice_prompts.py` (no backend imports)

### Frontend
- React 19 + Vite; CSS modules (no Tailwind)
- Auth via Google Sign-In → backend validates → issues session cookie
- `useChat.js` hook manages SSE connection and streaming state
- `api/client.js` is the fetch wrapper for all API calls
- `NeuralConfig.jsx` — settings page for skill management and education/persona config

## UI Design System
Single source of truth: `frontend/src/styles/global.css`
- Accent colors: violet `#7c6af7`, gold `#e8b86d`, cyan `#4dc8f5`
- Glassmorphism: `backdrop-filter: blur(16px) saturate(180%)` + semi-transparent bg + subtle border
- Gradient text: `background-clip: text` + `-webkit-text-fill-color: transparent`
- JetBrains Mono for code blocks
- Always reference CSS custom properties from `global.css`; never hardcode colors

## Git Conventions
- Active development on `dev` branch; PRs target `main`
- Commit messages: 2 lines max (subject + one body line)
- No "Co-Authored-By" lines
