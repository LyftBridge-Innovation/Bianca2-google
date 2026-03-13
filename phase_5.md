# Phase 5 — Voice Pipeline
> AI Chief of Staff · Gemini Live + Twilio + Browser WebRTC

---

## Overview

Phase 5 wires the existing Gemini Live audio pipeline into the shared tools and memory layer, then exposes it via two surfaces — a browser-based WebRTC test UI and a Twilio phone number. The audio layer is reused almost entirely. The tool layer is built from scratch but reuses the same Gmail/Calendar functions from Phase 1.

Phase 5 is split into 4 sub-phases:

| Sub-phase | What gets built |
|---|---|
| **5A** | Gemini Live tool layer — function declarations, dispatcher, result injection |
| **5B** | Browser WebRTC test UI — mic → server → Gemini Live → browser |
| **5C** | Memory integration — voice sessions write to the same Firestore memory pool |
| **5D** | Twilio integration — phone number → Twilio WebSocket → Gemini Live |

Do not start 5B until 5A tool calling is verified in isolation. Do not start 5D until 5B is stable.

---

---

# Phase 5A — Gemini Live Tool Layer

## Overview

This is purely backend. No audio, no UI. The goal is to get Gemini Live making tool calls to Gmail and Calendar correctly, with filler phrases spoken before tool execution and results injected back into the session. Test everything with text input before touching audio.

---

## What Changes in gemini_session.py

Keep the WebSocket lifecycle, async streams, and audio queue management. Tear out the Google Search tool declaration and the console-print tool detection. Replace with the following:

**1. Function declarations**

Gemini Live requires `FunctionDeclaration` objects passed at session init. Declare all tools at startup — do not add them dynamically. The full set mirrors Phase 1 tools exactly:

| Function name | Description for Gemini |
|---|---|
| `list_emails` | List recent emails from the user's inbox |
| `get_email` | Get the full content of a specific email by ID |
| `send_email` | Send an email on behalf of the user |
| `draft_email` | Save an email draft without sending |
| `list_events` | List upcoming calendar events |
| `get_event` | Get full details of a specific calendar event |
| `create_event` | Create a new calendar event |
| `decline_event` | Decline a calendar event and notify the organizer |
| `update_event` | Update an existing calendar event |

Each declaration must include a proper JSON schema for parameters. Gemini Live is strict about this — missing or malformed schemas cause silent failures.

**2. Tool dispatcher**

When Gemini returns a `tool_call` part in the response stream, route it to the correct function:

```
On tool_call received from Gemini:
  1. Extract function_name and parameters
  2. Look up function_name in dispatcher map
  3. Speak filler phrase (see below) — send audio to output queue
  4. Execute the tool function (reuse Phase 1 tools directly)
  5. Send tool_response back to Gemini via send_tool_response()
  6. Gemini resumes speaking with the result
```

The dispatcher is a simple dictionary mapping function name strings to async callables. Keep it in a separate `tool_dispatcher.py` file.

**3. Filler phrases**

Fixed phrases per tool — spoken before execution. These are injected as text-to-speech into the audio output stream before the tool runs. Keep them short and natural:

| Tool group | Filler phrase |
|---|---|
| list_emails, get_email | "Let me check your inbox." |
| send_email, draft_email | "Give me a moment to handle that email." |
| list_events, get_event | "Let me pull up your calendar." |
| create_event, update_event | "Let me update your calendar." |
| decline_event | "Let me take care of that for you." |

Filler phrases are sent as a `send_message()` text input to Gemini Live before the tool executes, so Gemini speaks them naturally in its own voice rather than playing a separate audio clip. This keeps the voice consistent.

**4. Result injection**

After the tool executes, call `send_tool_response()` with the function name and result. Format results as clean strings — not raw Python dicts. Gemini will use the result to formulate its spoken response.

---

## Revised gemini_session.py Structure

```
GeminiSession
  __init__(user_id, enable_tools=True)
    - loads tool declarations
    - initialises dispatcher with user_id bound to each tool

  connect()
    - opens Gemini Live WebSocket
    - sends session config with function declarations + system prompt

  send_audio(pcm_bytes)
    - sends audio chunk to Gemini

  send_text(text)
    - sends text message (used for filler phrases + testing)

  receive_loop()
    - main async loop
    - routes: audio → output queue, tool_call → dispatcher, text → transcript

  _handle_tool_call(function_name, parameters)
    - speaks filler phrase
    - dispatches to tool
    - injects result back

  close()
    - graceful shutdown
```

---

## Updated System Prompt (prompts.py)

Rewrite `SYSTEM_INSTRUCTION` completely. The voice prompt needs to be different from the chat prompt — shorter sentences, no markdown, no bullet points, no lists. Gemini will speak whatever it generates so it must sound natural when read aloud.

Key directives to include:
- You are Bianca, an AI chief of staff speaking with the user over a phone call
- Keep responses concise — 1-3 sentences unless detail is explicitly requested
- Never use bullet points, headers, or markdown formatting
- When checking tools, you will naturally say what you are doing before doing it
- For calendar times, always confirm the timezone
- If you do not understand something, ask one short clarifying question

---

## Audio Transcoding Utilities (audio_utils.py)

New file. Twilio sends 8kHz mulaw (ulaw), Gemini Live expects 16kHz PCM. Both directions need transcoding.

```
ulaw_to_pcm16k(ulaw_bytes) -> pcm_bytes
  1. audioop.ulaw2lin(ulaw_bytes, 2)       # ulaw → 16-bit PCM at 8kHz
  2. audioop.ratecv(..., 8000, 16000, ...)  # 8kHz → 16kHz resample

pcm16k_to_ulaw(pcm_bytes) -> ulaw_bytes
  1. audioop.ratecv(..., 16000, 8000, ...)  # 16kHz → 8kHz resample
  2. audioop.lin2ulaw(pcm_bytes, 2)         # 16-bit PCM → ulaw
```

Both functions use Python's `audioop` from stdlib — no extra dependencies. Keep them fast and stateless. The ratecv state parameter should be handled by the caller if processing a continuous stream (Twilio connection) to avoid audio artifacts at chunk boundaries.

---

## Phase 5A Acceptance Criteria

Test everything via text input — no audio required yet.

| Test | Pass Condition |
|---|---|
| Session init | GeminiSession connects and sends function declarations without error |
| Text tool call | Send "what meetings do I have today?" as text, Gemini calls list_events |
| Filler phrase | Filler phrase is sent before tool execution |
| Tool result injection | Gemini receives tool result and responds with calendar content |
| Gmail tool call | Send "read my latest email", Gemini calls list_emails then get_email |
| Multi-tool | Ask something requiring 2 tool calls — both complete correctly |
| Error handling | Simulate tool failure — Gemini responds gracefully, does not crash |
| Dispatcher coverage | All 9 tools registered and reachable in dispatcher |

---

---

# Phase 5B — Browser WebRTC Test UI

## Overview

A minimal single-page test UI. User clicks a button, browser captures microphone audio, streams it to the FastAPI backend via WebSocket, backend forwards to Gemini Live, audio response streams back and plays in the browser. This is for development testing only — not a production feature.

---

## Architecture

```
Browser mic (WebRTC getUserMedia)
        ↓
Browser WebSocket → ws://localhost:8000/ws/voice/test
        ↓
FastAPI WebSocket handler
        ↓
GeminiSession.send_audio()
        ↓
Gemini Live (tool calls handled transparently)
        ↓
GeminiSession audio output queue
        ↓
FastAPI WebSocket handler
        ↓
Browser WebSocket → browser audio context → speaker
```

The browser sends raw PCM audio captured at 16kHz (set via AudioContext sample rate). The server forwards to Gemini as-is. Response audio from Gemini (PCM 16kHz) is sent back to the browser and played via Web Audio API.

No Twilio, no mulaw transcoding needed in this sub-phase — browser sends and receives PCM directly.

---

## New FastAPI Endpoint

```
WebSocket: /ws/voice/test?user_id=dev_user_1
```

Handler lifecycle:
```
on connect:
  - create GeminiSession(user_id)
  - start receive_loop() as background task
  - start audio_output_forwarder() — reads Gemini output queue, sends to browser

on message (bytes):
  - forward raw PCM to GeminiSession.send_audio()

on disconnect:
  - GeminiSession.close()
  - cancel background tasks
```

---

## Test UI (Single HTML File)

A single `voice_test.html` file served as a static file from FastAPI. No React, no build step. Plain HTML + JS only.

**Layout:**
```
┌─────────────────────────────────────┐
│  Bianca Voice Test                  │
│                                     │
│  [  Start Call  ]                   │
│                                     │
│  Status: Connected                  │
│                                     │
│  Tool calls:                        │
│  > list_events called               │
│  > get_email called                 │
│                                     │
│  Transcript:                        │
│  User: what's on my calendar?       │
│  Bianca: Let me pull up your...     │
└─────────────────────────────────────┘
```

**Behaviour:**
- Start Call button: requests mic permission, connects WebSocket, begins streaming
- Stop Call button: replaces Start Call while active, closes connection cleanly
- Status line: Connecting / Connected / Disconnected / Error
- Tool calls panel: appends each tool call event as it fires
- Transcript panel: scrollable, appends user and Bianca turns as they complete

The backend sends JSON control messages over the same WebSocket for transcript and tool call events:
```json
{"type": "transcript", "role": "user", "text": "what's on my calendar?"}
{"type": "transcript", "role": "assistant", "text": "Let me pull up your calendar."}
{"type": "tool_call", "tool": "list_events"}
```
Audio is sent as raw bytes. JSON messages are sent as strings. The browser differentiates by checking `typeof event.data`.

---

## Phase 5B Acceptance Criteria

| Test | Pass Condition |
|---|---|
| WebSocket connects | Browser connects to /ws/voice/test without error |
| Mic audio streams | Speaking into mic sends bytes to server (verify in server logs) |
| Voice response plays | Gemini's audio response plays through browser speakers |
| Tool call visible | Asking about calendar shows tool call in the UI panel |
| Transcript updates | Both user and Bianca turns appear in transcript |
| Clean disconnect | Stop Call closes connection without server errors |
| Concurrent safety | Starting a second call closes the previous one cleanly |

---

---

# Phase 5C — Memory Integration

## Overview

Voice sessions write to the same Firestore collections as chat sessions. After a call ends, the transcript is summarized into event and entity memories exactly like a chat session. The memory pool is shared — if a user calls and then chats, Bianca remembers the call.

---

## What Changes

**Session creation:** When a voice WebSocket connects, create a Firestore session document with `modality: "voice"`. Same schema as chat sessions.

**Message persistence:** Each complete transcript turn (user speech recognized as text + Bianca's response text) is appended to the session `messages` array with role and timestamp. Tool calls are written to `tool_calls` array and `tool_action_log` as normal.

**Summarization trigger:** When the WebSocket disconnects (call ends), trigger `summarize_session()` as a background task. Same function used by chat — no changes needed.

**Memory injection:** At the start of each voice session (WebSocket connect), query Vertex AI Search for the top 5 relevant memories using the user's first message once it arrives. Inject into the GeminiSession system prompt mid-session via `send_message()` with a system role. If no first message yet, inject on the second turn.

---

## Phase 5C Acceptance Criteria

| Test | Pass Condition |
|---|---|
| Session created | Firestore session document created on voice WebSocket connect with modality: voice |
| Messages persisted | Transcript turns saved to session messages array |
| Tool actions logged | tool_action_log entries created during voice call |
| Summarization triggers | Ending call triggers background summarization |
| Memory created | event_memories and entity_memories documents exist after call ends |
| Cross-modal continuity | Start a chat after a voice call — Bianca references what was discussed on the call |

---

---

# Phase 5D — Twilio Integration

## Overview

Wire a real Twilio phone number to the backend. When someone calls the number, Twilio hits a webhook, the backend responds with TwiML to open a Media Stream WebSocket, and audio flows through the same GeminiSession used in the browser test. The only difference from 5B is audio format (mulaw 8kHz from Twilio vs PCM 16kHz from browser) and the WebSocket handshake protocol.

---

## New Endpoints

**TwiML webhook:**
```
POST /voice/incoming
```
Returns TwiML that tells Twilio to open a Media Stream to the backend:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="wss://your-domain.com/ws/voice/twilio"/>
  </Connect>
</Response>
```
This endpoint must be publicly accessible — use ngrok for local testing.

**Twilio Media Stream WebSocket:**
```
WebSocket: /ws/voice/twilio
```

Twilio connects here and sends JSON-wrapped audio messages. The format is different from a plain browser WebSocket:
```json
{"event": "media", "media": {"payload": "<base64-mulaw-audio>"}}
{"event": "start", "start": {"streamSid": "...", "callSid": "..."}}
{"event": "stop"}
```

Handler lifecycle:
```
on "start" event:
  - extract callSid as session identifier
  - create GeminiSession(user_id=hardcoded_dev_user)
  - start receive_loop and output forwarder

on "media" event:
  - base64 decode payload → ulaw bytes
  - ulaw_to_pcm16k() → PCM bytes
  - GeminiSession.send_audio(pcm_bytes)

on Gemini audio output:
  - pcm16k_to_ulaw() → ulaw bytes
  - base64 encode
  - send JSON: {"event": "media", "media": {"payload": "<base64>"}}

on "stop" event:
  - GeminiSession.close()
  - trigger summarization
```

---

## Twilio Setup Steps

Do these once manually before testing:

1. Log into your Twilio account and confirm your phone number has Voice capability enabled
2. In the phone number settings, set the webhook for incoming calls to `https://your-ngrok-url/voice/incoming` with HTTP POST
3. Enable Media Streams on your account (Twilio dashboard → Voice → Media Streams — may need to be enabled by Twilio support if not visible)
4. Install ngrok and run `ngrok http 8000` to get a public URL for local testing
5. Update the ngrok URL in Twilio webhook settings each time you restart ngrok (or use a paid ngrok account with a fixed domain)

Add to `.env`:
```env
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1xxxxxxxxxx
```

---

## Phase 5D Acceptance Criteria

| Test | Pass Condition |
|---|---|
| Webhook reachable | Twilio can POST to /voice/incoming via ngrok |
| TwiML valid | Twilio accepts the response and opens Media Stream WebSocket |
| Audio received | Server logs show media events arriving from Twilio |
| Transcoding correct | No audio artifacts or distortion in Gemini's response |
| Voice response | Caller hears Bianca speaking back |
| Tool call on call | Ask about calendar on the phone — Bianca responds with real data |
| Filler phrase audible | Caller hears "Let me pull up your calendar" before tool result |
| Memory after call | Firestore session summarized after call ends |
| End call cleanly | Hanging up triggers stop event and clean shutdown |

---

---

# Summary — What the Coding Agent Builds

| Phase | Deliverable |
|---|---|
| **5A** | Rebuilt gemini_session.py with function declarations, tool dispatcher, filler phrases, result injection. New tool_dispatcher.py. New audio_utils.py with ulaw/PCM transcoding. Rewritten system prompt. |
| **5B** | FastAPI WebSocket endpoint for browser testing. Single voice_test.html with start/stop, transcript panel, tool call panel. |
| **5C** | Voice sessions write to Firestore. Transcript persisted per turn. Summarization triggers on disconnect. Memory injected at session start. |
| **5D** | TwiML webhook endpoint. Twilio Media Stream WebSocket handler. Mulaw transcoding wired in. Twilio credentials in config. ngrok testing instructions. |

---

## Things Deliberately Deferred

- Phone number → user_id mapping (hardcoded dev_user_1 for all calls) — Phase 6
- WhatsApp integration — after Phase 5 is stable
- Production deployment with fixed domain — Phase 6
- Inactivity timer / APScheduler — Phase 6
- Mobile web UI for voice — not planned