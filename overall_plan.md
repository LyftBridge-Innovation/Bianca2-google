# AI Chief of Staff — Product Spec & Implementation Plan
> Version 1.0 · Phase 1 Ready for Build

---

## Product Overview

AI Chief of Staff is a multi-modal personal AI assistant built for busy business users who want the power of an AI agent without needing to know anything about LLMs or APIs. Users interact through the channels they already use — phone, chat, and email — and the AI handles scheduling, inbox management, and communication on their behalf.

The key differentiator is unified context across all modalities. Whether a user calls in, sends a message, or emails the agent, it remembers the full history of every interaction and responds intelligently with that context. It feels less like a tool and more like a real assistant that knows you.

| | |
|---|---|
| **Target User** | Business professionals who want a personal AI assistant without technical setup |
| **Core Problem** | Managing calendar, inbox, and communications is time-consuming and fragmented |
| **Solution** | A single AI agent accessible via phone, chat, and email that handles it all |
| **Differentiator** | Unified memory across modalities — the AI always knows what happened before |
| **MVP Scope** | Web chat UI + Google Calendar + Gmail tools. Voice and email channels in later phases |

---

## System Architecture

Two LLM pipelines sharing the same tools layer and memory store.

**Voice Pipeline (Gemini Live)**
Used for real-time phone/voice via Twilio. Streaming audio in/out. This pipeline is not modified — it connects to the shared tools and memory layer as-is.

**Chat Pipeline (Gemini / Configurable)**
Used for web chat, and later SMS and email. Standard request-response LLM calls with tool use. Model is swappable via LangChain abstraction.

**Shared Layer (Tools + Memory)**
Both pipelines call the same `tools/` module and Firestore memory store. This is what makes the AI feel consistent regardless of channel.

---

## Tech Stack

| | |
|---|---|
| **Backend** | Python + FastAPI |
| **LLM (Chat)** | Google Gemini via LangChain abstraction |
| **LLM (Voice)** | Google Gemini Live API (existing code, unchanged) |
| **Google Tools** | Gmail API + Calendar API via `google-auth` + `googleapiclient` |
| **Memory** | Firebase Firestore — per-user conversation summaries |
| **Auth (MVP)** | Hardcoded OAuth refresh token as env variable |
| **Auth (Later)** | Google Sign-In on onboarding page, tokens stored in Firestore |
| **Frontend** | React + Vite + Vanilla CSS |
| **Hosting** | Google Cloud Run (backend) + GitHub Pages (frontend) |
| **Voice Channel** | Twilio (Phase 5) |

---

## Phase Roadmap

| Phase | Description |
|---|---|
| **Phase 1** | Backend foundation + Google tools (Gmail + Calendar) ← **BUILD THIS FIRST** |
| **Phase 2** | Gemini chat pipeline — `/chat` endpoint with tool use + system prompt |
| **Phase 3** | Memory layer — Firestore conversation summaries injected into context |
| **Phase 4** | Web chat UI — React + Vite connected to `/chat` with streaming |
| **Phase 5** | Voice pipeline — connect existing Gemini Live code to shared tools + memory + Twilio |
| **Phase 6** | Hardening — error handling, prompt polish, rate limiting, prep for onboarding |

---

---

# Phase 1 — Backend Foundation + Google Tools

> **Goal:** A running FastAPI server where every Google tool works correctly and can be tested individually via curl or Postman. No LLM, no frontend, no memory. Just clean, tested tool functions.

---

## 1.1 Project Structure

```
ai-chief-of-staff/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── config.py                # Env vars, constants
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── gmail.py             # Gmail read + send + draft
│   │   ├── calendar.py          # Calendar read, create, decline
│   │   └── google_auth.py       # OAuth token manager
│   ├── routers/
│   │   └── tools_test.py        # Temporary test endpoints (remove in Phase 2)
│   └── requirements.txt
└── README.md
```

---

## 1.2 Getting Your Google OAuth Refresh Token

Do this before writing any code. Takes about 10 minutes.

**Step 1 — Create a Google Cloud project**

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (e.g. `ai-chief-of-staff`)
3. Enable these two APIs: **Gmail API** and **Google Calendar API**
4. Go to **APIs & Services → OAuth consent screen** → set to External → fill in app name → add your own email as a test user
5. Go to **APIs & Services → Credentials → Create Credentials → OAuth Client ID**
6. Choose **Desktop App** as the application type
7. Download the JSON — save it as `credentials.json` in your backend folder

**Step 2 — Run this one-time script to get your refresh token**

```python
# get_token.py — run once, then delete this file
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar",
]

flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
creds = flow.run_local_server(port=0)

print("REFRESH TOKEN:", creds.refresh_token)
print("CLIENT ID:", creds.client_id)
print("CLIENT SECRET:", creds.client_secret)
```

```bash
pip install google-auth-oauthlib
python get_token.py
```

A browser window opens, you sign in with your Google account, approve the scopes, and the script prints your tokens. Copy them into your `.env` file.

**Step 3 — .env file**

```env
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_REFRESH_TOKEN=your_refresh_token
GOOGLE_CALENDAR_ID=primary
TEST_USER_ID=dev_user_1
```

> Never commit `.env` or `credentials.json`. Add both to `.gitignore` immediately.

---

## 1.3 google_auth.py — Token Manager

This is the single place responsible for getting a valid access token. Built so that in a later phase, swapping hardcoded token → Firestore lookup requires changing only this file.

```python
class GoogleAuthManager:
    def get_credentials(self, user_id: str) -> Credentials:
        # MVP: returns credentials from env refresh token
        # Later: looks up user_id in Firestore for their token

    def refresh_if_expired(self, creds: Credentials) -> Credentials:
        # Silently refreshes access token if within 5 min of expiry
```

---

## 1.4 gmail.py — Gmail Tools

All functions take `user_id` as first argument. Auth is resolved internally.

| Function | Description |
|---|---|
| `list_emails(user_id, max_results=10)` | Returns recent emails: id, subject, sender, date, snippet |
| `get_email(user_id, email_id)` | Returns full email body + metadata |
| `send_email(user_id, to, subject, body)` | Sends an email on behalf of the user |
| `draft_email(user_id, to, subject, body)` | Saves a draft — does NOT send |

> **Note:** The AI defaults to `draft_email`. It only calls `send_email` when the user explicitly confirms. You cannot un-send an email to a client.

---

## 1.5 calendar.py — Calendar Tools

| Function | Description |
|---|---|
| `list_events(user_id, days_ahead=7)` | Returns upcoming events: id, title, start, end, attendees |
| `get_event(user_id, event_id)` | Returns full event detail including organizer and description |
| `create_event(user_id, title, start, end, attendees, description)` | Creates a calendar event |
| `decline_event(user_id, event_id, message=None)` | Sends decline + notifies organizer |
| `update_event(user_id, event_id, **kwargs)` | Updates an existing event's fields |

> **Note:** `decline_event` should call `events.patch` with attendee status `declined` AND set `sendUpdates="all"` so the organizer gets notified.

---

## 1.6 Test Endpoints

Temporary endpoints in `routers/tools_test.py` for manual testing. Remove or gate behind a dev flag in Phase 2.

```
GET  /test/gmail/list              # List recent emails
GET  /test/gmail/{email_id}        # Get specific email
POST /test/gmail/send              # Body: { to, subject, body }
POST /test/gmail/draft             # Body: { to, subject, body }
GET  /test/calendar/list           # List upcoming events
GET  /test/calendar/{event_id}     # Get event detail
POST /test/calendar/create         # Body: { title, start, end, attendees, description }
POST /test/calendar/decline/{id}   # Body: { message? }
```

---

## 1.7 requirements.txt

```
fastapi
uvicorn[standard]
python-dotenv
google-auth
google-auth-oauthlib
google-api-python-client
pydantic
```

---

## 1.8 Acceptance Criteria

Do not move to Phase 2 until every item passes.

| Test | Pass Condition |
|---|---|
| Gmail List | Returns at least 5 emails with correct fields |
| Gmail Get | Returns full body of a specific email by ID |
| Gmail Send | Email actually arrives in a real inbox |
| Gmail Draft | Draft is visible in Gmail drafts folder |
| Calendar List | Returns upcoming events with correct times |
| Calendar Get | Returns full event with attendees |
| Calendar Create | Event appears on Google Calendar |
| Calendar Decline | Organizer receives a decline notification |
| Token Refresh | Manually expire token — verify silent refresh works |
| Error Handling | Invalid email ID returns clean 404, not a raw Google API error |

---

## Instructions for Coding Agent

Build Phase 1 only. Do not implement LLM calls, memory, or any frontend.

- Each tool function must be independently testable via the test endpoints
- Use dependency injection for `GoogleAuthManager` so it can be swapped in later phases without touching tool code
- All Google API errors must be caught and re-raised as clean `HTTPException` with meaningful messages — never let raw Google errors bubble up
- Add docstrings to every public function
- All datetime inputs should accept ISO 8601 strings and be parsed internally
- Verify all 10 acceptance criteria before considering Phase 1 complete

---

## Future Phases — Summary

| Phase | What Gets Built |
|---|---|
| **Phase 2** | Wire Gemini into `/chat` endpoint via LangChain. Tool calling. Chief of staff system prompt. Test multi-turn conversations with calendar and gmail actions. |
| **Phase 3** | Firestore memory layer. Summarize conversations and store per user with timestamp. Inject last N summaries into system prompt. Test cross-session continuity. |
| **Phase 4** | React + Vite web chat UI. Hardcoded Google Sign-In for user ID only. SSE streaming. Connect to `/chat`. |
| **Phase 5** | Integrate existing Gemini Live voice code. Connect to shared tools and memory. Twilio webhook. Test with ngrok. |
| **Phase 6** | Prompt tuning for personality consistency across voice and chat. Error handling for tool failures. Rate limiting. Prep for proper Google OAuth onboarding. |