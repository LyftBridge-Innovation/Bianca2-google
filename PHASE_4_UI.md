# Phase 4 — Web Chat UI
> AI Chief of Staff · Ready for Implementation

---

## Overview

Phase 4 is split into two sub-phases:

| Sub-phase | What gets built |
|---|---|
| **4A** | Streaming — convert `/chat` endpoint to SSE, update response handling |
| **4B** | React frontend — Google Sign-In, chat UI, session sidebar |

Do not start 4B until 4A is tested and streaming is confirmed working end-to-end.

---

## Important Notes

- The most important thing in 4A is testing the SSE stream with curl before writing a single line of frontend code. The --no-buffer flag on curl is critical — without it curl batches the output and it looks like it's not streaming. Verify you actually see tokens arriving one by one before moving on.
- The trickiest frontend piece is the useChat hook — specifically the SSE-over-POST using fetch with ReadableStream. Make sure the agent doesn't reach for EventSource which only supports GET requests. The fetch-based reader is less familiar but it's the right approach here and there are good examples online.
- One thing I'd watch carefully — the auto-scroll behavior. It sounds trivial but getting it right (scroll to bottom on new messages, pause when user scrolls up, resume when they scroll back down) is surprisingly easy to get subtly wrong and it makes the product feel janky if it misbehaves. Tell the agent to treat this as a first-class feature, not an afterthought.

---

# Phase 4A — Streaming

## Overview

Convert the `/chat` endpoint from a blocking JSON response to a Server-Sent Events (SSE) stream. The frontend will receive tokens as they are generated rather than waiting for the full response. This is a backend-only change — no frontend work in this sub-phase.

---

## What Changes

Currently the endpoint waits for the full agentic loop (LLM → tool calls → final response) then returns a single `ChatResponse` object. After 4A it streams tokens as the final LLM response generates, but still waits for tool calls to complete before streaming begins. This is the simplest correct approach — tool calls happen silently, then the response streams in.

**The endpoint signature changes from:**
```
POST /chat/
Returns: ChatResponse { response, session_id, history }
```

**To:**
```
POST /chat/stream
Returns: text/event-stream
```

Keep the original `POST /chat/` endpoint alive and unchanged. The streaming endpoint is new and separate. This means nothing that already works breaks.

---

## SSE Event Format

The stream sends 4 event types. The frontend handles each differently.

**`session` event — sent first, before any tokens**
```
event: session
data: {"session_id": "abc-123"}
```
Frontend uses this to store the session ID for the current conversation.

**`token` event — sent for each text chunk**
```
event: token
data: {"token": "Sure, "}

event: token
data: {"token": "here are your "}

event: token
data: {"token": "upcoming meetings:"}
```

**`tool_call` event — sent when a tool executes (before streaming begins)**
```
event: tool_call
data: {"tool": "list_events", "status": "running"}
```
Frontend uses this to show a subtle status like "Checking your calendar..." during the tool call phase before tokens arrive.

**`done` event — sent when stream is complete**
```
event: done
data: {"session_id": "abc-123"}
```

---

## Backend Implementation Notes

FastAPI supports SSE via `StreamingResponse` with `media_type="text/event-stream"`. The generator function yields events as strings in the format above.

The agentic loop runs first (tool calls complete), then the final LLM response is streamed token by token using Gemini's streaming API. Firestore writes (session persistence, tool action log) happen after the stream completes — do not block the stream on Firestore writes.

CORS must allow the `text/event-stream` content type and the `Cache-Control` header. Update CORS middleware accordingly.

---

## Request Body

Same as the existing `/chat/` endpoint:

```json
{
  "message": "What is on my calendar today?",
  "user_id": "google_sub_id_here",
  "session_id": "abc-123"
}
```

`session_id` is optional. If omitted, a new session is created and the session ID is sent in the first `session` event.

---

## Phase 4A Acceptance Criteria

| Test | Pass Condition |
|---|---|
| SSE connection | `POST /chat/stream` returns `Content-Type: text/event-stream` |
| Session event | First event is always `session` with a valid session_id |
| Token streaming | Response arrives as multiple `token` events, not one block |
| Tool call event | Asking about calendar emits a `tool_call` event before tokens |
| Done event | Stream always terminates with a `done` event |
| Original endpoint | `POST /chat/` still works unchanged |
| Firestore persistence | Session and messages are persisted correctly after stream ends |
| CORS | Can connect to the stream from a browser on a different port |

Test all of these with `curl` before touching the frontend:
```bash
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"message": "What meetings do I have?", "user_id": "dev_user_1"}' \
  --no-buffer
```

---

---

# Phase 4B — React Frontend

## Stack

- React + Vite
- Vanilla CSS — no Tailwind, no component library
- Google Sign-In via `@react-oauth/google`
- No Redux — React state only (`useState`, `useContext`)

---

## Project Structure

```
frontend/
├── index.html
├── vite.config.js
├── src/
│   ├── main.jsx
│   ├── App.jsx
│   ├── context/
│   │   └── AuthContext.jsx        # Google auth state
│   ├── components/
│   │   ├── Auth/
│   │   │   └── LoginPage.jsx      # Google Sign-In screen
│   │   ├── Layout/
│   │   │   ├── AppLayout.jsx      # Sidebar + main area wrapper
│   │   │   └── Sidebar.jsx        # Session list + new chat button
│   │   └── Chat/
│   │       ├── ChatWindow.jsx     # Main chat area
│   │       ├── MessageList.jsx    # Scrollable message history
│   │       ├── Message.jsx        # Individual message bubble
│   │       ├── TypingIndicator.jsx # Bianca is thinking... animation
│   │       ├── ToolCallStatus.jsx  # "Checking your calendar..."
│   │       └── ChatInput.jsx      # Input bar + send button
│   ├── hooks/
│   │   ├── useChat.js             # SSE connection, message state
│   │   └── useSessions.js         # Session list fetching
│   ├── api/
│   │   └── client.js              # API base URL, fetch helpers
│   └── styles/
│       ├── global.css
│       ├── layout.css
│       ├── chat.css
│       ├── sidebar.css
│       └── auth.css
```

---

## Design Language

The UI should feel like Claude.ai — clean, minimal, professional. No emojis anywhere in the UI. No gradients. No rounded-everything. The design should communicate that this is a serious tool for business users.

**Color palette:**
```
Background (main):     #0f0f0f  (near black, like Claude dark)
Background (sidebar):  #171717
Surface:               #1e1e1e  (message bubbles, inputs)
Border:                #2a2a2a
Text primary:          #ececec
Text secondary:        #8e8ea0
Accent:                #ffffff  (send button, active states)
User message bg:       #2a2a2a
Assistant message bg:  transparent (left-aligned, no bubble)
```

**Typography:**
- Font: System font stack — `-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`
- Base size: 15px
- Line height: 1.6
- No bold headings in chat messages — keep it conversational

**Spacing:**
- Sidebar width: 260px fixed
- Chat max width: 720px centered in main area
- Message padding: 12px 0 (top/bottom only, no left/right bubble padding on assistant)
- Input area: fixed bottom, blurs content behind it

---

## Screens

### 1. Login Page

Full screen, centered. No sidebar visible.

- Bianca wordmark top center (text only, no logo for now)
- One line subtitle: "Your AI Chief of Staff"
- Google Sign-In button below — use the official Google button from `@react-oauth/google`
- No other elements — keep it stark and clean

On successful sign-in, extract `sub` (user ID) and `name` from the Google JWT. Store in `AuthContext`. Redirect to chat.

---

### 2. App Layout

Two-column layout after login:

```
┌─────────────────────────────────────────────────────┐
│  Sidebar (260px)     │  Chat Area (flex: 1)          │
│                      │                               │
│  [+ New Chat]        │  MessageList                  │
│                      │                               │
│  Today               │                               │
│  > Session title 1   │                               │
│  > Session title 2   │                               │
│                      │                               │
│  Yesterday           │                               │
│  > Session title 3   │                               │
│                      │  ─────────────────────────── │
│                      │  ChatInput                    │
└─────────────────────────────────────────────────────┘
```

---

### 3. Sidebar

**New Chat button** — top of sidebar, full width. Clicking it:
1. Creates a new session (clears current chat window)
2. Triggers summarization of previous session on the backend (happens automatically via the existing logic)

**Session list** — grouped by recency: Today, Yesterday, Previous 7 days, Older. Each session shows its title (first message, truncated to ~40 characters). Active session is highlighted with a subtle left border accent. Clicking a session loads its message history.

**No user profile, no settings** — keep sidebar minimal for MVP. Just new chat + session list.

---

### 4. Chat Window

**Empty state** (new chat, no messages yet):
- Centered vertically in the chat area
- Large text: "Good morning, [first name]." (use time of day appropriately)
- Smaller text below: "What would you like to work on?"
- No suggested prompts — keep it clean

**Message list:**
- User messages: right-aligned, subtle dark bubble, no avatar
- Bianca messages: left-aligned, no bubble, no avatar, just text
- Timestamps: shown on hover only, secondary color, small
- Auto-scroll to bottom on new messages
- If user scrolls up, stop auto-scrolling. Resume when they scroll back to bottom.

**Typing indicator** (shown while waiting for response):
- Left-aligned, where Bianca's next message will appear
- Three dots animated sequentially — same as Claude's indicator
- CSS animation only, no JS required
- Appears immediately when user sends a message
- Replaced by streaming tokens as they arrive

**Tool call status** (shown between typing indicator and tokens):
- Small, secondary color text above where the response will appear
- Examples: "Checking your calendar...", "Reading your inbox...", "Sending email..."
- Map `tool_call` SSE events to human-readable strings
- Fades out when tokens start arriving

**Input bar:**
- Fixed to bottom of chat area
- Textarea (not input) — grows vertically up to 5 lines, then scrolls
- Send on Enter, newline on Shift+Enter
- Send button: right side of input, arrow icon (no text)
- Disabled and greyed out while response is streaming
- Subtle top border separating it from messages, slight blur on content behind

---

## useChat Hook

This is the most important piece of the frontend. It manages the SSE connection and all message state.

```
State:
  - messages: array of { role, content, timestamp }
  - sessionId: string | null
  - isStreaming: boolean
  - currentToolCall: string | null  (for tool call status display)
  - streamingContent: string        (accumulated tokens while streaming)

Actions:
  - sendMessage(text)
    1. Append user message to messages immediately
    2. Set isStreaming = true
    3. Open SSE connection to POST /chat/stream
    4. On "session" event → set sessionId
    5. On "tool_call" event → set currentToolCall to human-readable string
    6. On "token" event → append to streamingContent
    7. On "done" event → 
       - append final assembled message to messages
       - clear streamingContent
       - set isStreaming = false
       - set currentToolCall = null
    8. On error → set isStreaming = false, show error state
```

Note: SSE with POST requires using `fetch` with `ReadableStream`, not `EventSource` (which only supports GET). The hook should use `fetch` + response body reader directly.

---

## useSessions Hook

Fetches the session list for the sidebar.

```
- On mount: fetch GET /chat/user/{user_id}/sessions
- Returns: array of { session_id, title, created_at, status }
- Refreshes when a new session is created
- Groups sessions by date for sidebar display
```

---

## Google Sign-In Setup

1. Create OAuth Client ID in Google Cloud Console — type: **Web Application**
2. Add `http://localhost:5173` to authorized JavaScript origins (for dev)
3. Add production URL when deploying
4. Use `GoogleOAuthProvider` wrapping the whole app with the client ID
5. Use `useGoogleLogin` hook for the login button

The backend does not need a Google auth verification endpoint for MVP — the frontend just extracts `sub` and `name` from the decoded JWT client-side and passes `sub` as `user_id` in all API calls. Proper JWT verification on the backend is a Phase 6 security hardening task.

---

## API Client

Base URL from environment variable:
```
VITE_API_BASE_URL=http://localhost:8000
```

All requests pass `user_id` from `AuthContext`. The streaming endpoint uses `fetch` directly in `useChat`. All other endpoints use a thin wrapper around `fetch`.

---

## New Backend Endpoint Needed for Sidebar

The frontend needs to fetch session list with titles. Add to the backend:

```
GET /chat/user/{user_id}/sessions?limit=50
```

Returns:
```json
[
  {
    "session_id": "abc-123",
    "title": "What meetings do I have toda...",
    "created_at": "2026-02-22T14:30:00Z",
    "status": "summarized"
  }
]
```

Title is derived from the first user message in the session, truncated to 40 characters. This is computed at read time from the session document — no extra LLM call.

---

## Phase 4B Acceptance Criteria

| Test | Pass Condition |
|---|---|
| Login | Google Sign-In completes, user_id and name stored, redirected to chat |
| Empty state | New chat shows correct greeting with user's first name |
| Send message | User message appears immediately in the list |
| Typing indicator | Three-dot animation appears while waiting for response |
| Tool call status | "Checking your calendar..." appears when calendar tool fires |
| Streaming | Bianca's response streams in token by token |
| Session persistence | Refreshing the page and reopening a session shows full history |
| Sidebar sessions | Past sessions appear grouped by date with correct titles |
| Session switching | Clicking a past session loads its message history |
| New chat | New chat button clears window and creates a new session |
| Auto-scroll | Chat scrolls to bottom on new messages, pauses if user scrolls up |
| Input behavior | Enter sends, Shift+Enter adds newline, input disabled while streaming |
| Responsive | Layout works on screens down to 1024px wide |

---

## Build & Run

```bash
cd frontend
npm create vite@latest . -- --template react
npm install @react-oauth/google
npm run dev
```

---

## Things Deliberately Deferred

- JWT verification on the backend — Phase 6
- Gmail/Calendar OAuth scope capture during sign-in — Phase 6
- Auto-generated session titles via LLM — Phase 6
- Mobile responsive layout — Phase 6
- Markdown rendering in messages (bold, code blocks) — Phase 5 or 6
- Dark/light mode toggle — not planned
- User settings page — not planned for MVP