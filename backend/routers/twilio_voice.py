"""
Twilio Phone Voice Integration.

Endpoints
  POST /voice/twilio/incoming  — TwiML webhook; Twilio calls this on every inbound call.
                                  Looks up the caller's registered phone number in Firestore
                                  and returns a <Connect><Stream> TwiML to hand the call to
                                  our Gemini Live bridge.

  WS   /voice/twilio/stream    — Twilio Media Streams WebSocket.
                                  Bridges μ-law 8 kHz audio from Twilio ↔ PCM 16/24 kHz for
                                  Gemini Live, with full tool support (Gmail, Calendar, Drive, etc.)
                                  and Firestore transcript / memory persistence.

Audio format:
  Twilio → us   : base64-encoded μ-law 8 kHz in JSON  { "event": "media", "media": { "payload": "..." } }
  Gemini input  : raw PCM 16 kHz 16-bit (via ulaw8k_to_pcm16k)
  Gemini output : raw PCM 24 kHz 16-bit
  us → Twilio   : base64-encoded μ-law 8 kHz in JSON  { "event": "media", "streamSid": "...", ... }
"""
import asyncio
import base64
import json
import logging
import os
import sys

from fastapi import APIRouter, Request, Response, WebSocket, WebSocketDisconnect

# ── Voice-pipeline path ────────────────────────────────────────────────────────
_VOICE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "voice_pipeline")
)
if _VOICE_PATH not in sys.path:
    sys.path.insert(0, _VOICE_PATH)

from gemini_session import GeminiSession        # noqa: E402
from voice_prompts import INITIAL_GREETING      # noqa: E402

# ── Backend imports ────────────────────────────────────────────────────────────
from audio_bridge import TwilioAudioBridge, ulaw8k_to_pcm16k   # noqa: E402
from models import (                                             # noqa: E402
    FirestoreCollections, Session, Message, ToolCall, ToolActionLog,
)
from memory_utils import generate_human_readable                # noqa: E402
from summarization import summarize_session_sync                # noqa: E402

router = APIRouter(prefix="/voice/twilio", tags=["twilio-voice"])
_log = logging.getLogger(__name__)

_TWILIO_AUTH_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN", "")
_TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")


# ── TwiML builders ─────────────────────────────────────────────────────────────

def _twiml_stream(host: str, user_id: str) -> str:
    """TwiML that connects the call to our Media Stream WebSocket."""
    ws_url = f"wss://{host}/voice/twilio/stream?user_id={user_id}"
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        "<Connect>"
        f'<Stream url="{ws_url}" />'
        "</Connect>"
        "</Response>"
    )


def _twiml_say(message: str) -> str:
    """TwiML that speaks a message then hangs up."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f'<Say voice="alice">{message}</Say>'
        "<Hangup />"
        "</Response>"
    )


# ── Twilio signature validation ───────────────────────────────────────────────

def _validate_twilio_signature(request: Request, form_data: dict) -> bool:
    """Return True if the request is legitimately from Twilio (or if dev-mode).

    Cloud Run terminates TLS before uvicorn, so request.url uses http://.
    Twilio signs with https://, so we must reconstruct the canonical public URL
    from the X-Forwarded-Proto / host headers that Cloud Run injects.
    """
    if not _TWILIO_AUTH_TOKEN:
        return True  # Dev / local — skip validation
    try:
        from twilio.request_validator import RequestValidator
        validator = RequestValidator(_TWILIO_AUTH_TOKEN)
        sig = request.headers.get("X-Twilio-Signature", "")

        # Reconstruct the public HTTPS URL (Cloud Run strips TLS before uvicorn)
        proto = request.headers.get("x-forwarded-proto") or "https"
        host  = request.headers.get("x-forwarded-host") or request.headers.get("host", "")
        url   = f"{proto}://{host}{request.url.path}"
        if request.url.query:
            url += f"?{request.url.query}"

        _log.debug("Twilio sig validation — url=%s sig=%s", url, sig[:8] + "...")
        return validator.validate(url, form_data, sig)
    except Exception as exc:
        _log.warning("Twilio signature validation error: %s — failing open", exc)
        return True  # Fail open; prevents outage if twilio lib has issues


# ── Firestore phone-number lookup ─────────────────────────────────────────────

def _lookup_user_by_phone(phone_number: str) -> tuple[str | None, str | None]:
    """
    Look up a Bianca user by their registered phone_number field in Firestore.
    Returns (user_id, None) on success or (None, error_message) on failure.
    """
    try:
        from firestore_client import get_firestore_client
        db = get_firestore_client()
        docs = list(
            db.collection("users")
            .where("phone_number", "==", phone_number)
            .limit(1)
            .stream()
        )
        if docs:
            return docs[0].id, None
        return None, (
            "Sorry, this number is not registered with Bianca. "
            "Please sign in to Bianca and add your phone number under Neural Config, Integrations."
        )
    except Exception as exc:
        _log.error("Firestore phone lookup error: %s", exc)
        return None, "Service temporarily unavailable. Please try again shortly."


# ── Incoming call — TwiML webhook ─────────────────────────────────────────────

@router.post("/incoming")
async def incoming_call(request: Request):
    """
    Twilio calls this endpoint (HTTP POST) when someone dials the Twilio number.
    Returns TwiML to connect the call to the Gemini Live WebSocket bridge.
    """
    form_data = dict(await request.form())

    # ── Status-change callbacks from Twilio (not new inbound calls) ──────────
    # When "Call Status Changes" webhook fires it includes CallStatus but no
    # meaningful TwiML action is needed — return 204 immediately.
    call_status = form_data.get("CallStatus", "")
    if call_status and call_status not in ("", "ringing"):
        _log.info("Twilio status callback — CallStatus=%s, ignoring", call_status)
        return Response(status_code=204)

    if not _validate_twilio_signature(request, form_data):
        _log.warning("Twilio signature validation failed")
        return Response(
            content=_twiml_say("This call could not be authenticated."),
            media_type="application/xml",
            status_code=403,
        )

    from_number = form_data.get("From", "").strip()
    _log.info(
        "Incoming Twilio call — From=%s CallStatus=%s", from_number, call_status
    )

    if not from_number:
        return Response(
            content=_twiml_say("Sorry, we could not identify your number."),
            media_type="application/xml",
        )

    user_id, error_msg = _lookup_user_by_phone(from_number)
    if error_msg:
        _log.warning("Phone lookup failed for %s: %s", from_number, error_msg)
        return Response(
            content=_twiml_say(error_msg),
            media_type="application/xml",
        )

    # Derive the host from the incoming request so this works on any deployment
    host = request.headers.get("host") or request.url.netloc
    stream_url = f"wss://{host}/voice/twilio/stream?user_id={user_id}"
    _log.info(
        "Routing call from %s → user_id=%s stream_url=%s",
        from_number, user_id, stream_url,
    )

    return Response(
        content=_twiml_stream(host, user_id),
        media_type="application/xml",
    )


# ── Media stream — WebSocket bridge ──────────────────────────────────────────

@router.websocket("/stream")
async def media_stream(websocket: WebSocket, user_id: str = ""):
    """
    Twilio Media Streams WebSocket.

    Message protocol (Twilio → us):
      { "event": "connected" }
      { "event": "start",  "streamSid": "MZ...", "start": { "streamSid": "MZ...", ... } }
      { "event": "media",  "streamSid": "MZ...", "media": { "payload": "<base64_ulaw>" } }
      { "event": "stop",   "streamSid": "MZ...", "stop": { ... } }

    Message protocol (us → Twilio):
      { "event": "media", "streamSid": "MZ...", "media": { "payload": "<base64_ulaw>" } }
    """
    await websocket.accept()
    _log.info("Twilio media stream WebSocket accepted — user_id=%r", user_id)

    if not user_id:
        _log.warning("Media stream opened without user_id — closing 1008")
        await websocket.close(code=1008, reason="user_id query parameter is required")
        return

    # ── Firestore session ─────────────────────────────────────────────────────
    fs = FirestoreCollections()
    session_doc = Session(user_id=user_id, modality="voice")
    session_id = fs.create_session(session_doc)
    _log.info("Firestore session created — session_id=%s user_id=%s", session_id, user_id)

    # ── Mutable call state ────────────────────────────────────────────────────
    transcript_buffer: list[dict] = []
    memory_injected = False
    gemini = None  # declared here so finally block can reference it

    receive_task: asyncio.Task | None = None
    drain_task:   asyncio.Task | None = None
    bridge:       TwilioAudioBridge | None = None
    connected = False

    try:
        # ── GeminiSession callbacks ───────────────────────────────────────────

        async def on_transcript(role: str, text: str) -> None:
            nonlocal memory_injected
            transcript_buffer.append({"role": role, "text": text})
            _log.debug("[%s] transcript %s: %s", session_id[:8], role, text[:80])

            if role == "user" and not memory_injected:
                memory_injected = True
                try:
                    from memory_retrieval import (
                        retrieve_memories_for_message,
                        format_memory_injection,
                    )
                    mem = retrieve_memories_for_message(user_message=text, user_id=user_id)
                    if mem["total_count"] > 0:
                        block = format_memory_injection(
                            event_memories=mem["event_memories"],
                            entity_memories=mem["entity_memories"],
                        )
                        await gemini.send_text(
                            f"Background context from previous sessions:\n{block}",
                            end_of_turn=True,
                        )
                except Exception as exc:
                    _log.debug("Memory injection skipped: %s", exc)

        async def on_tool_call(tool_name: str) -> None:
            _log.info("Tool call: %s (user=%s)", tool_name, user_id)

        async def on_tool_call_complete(
            tool_name: str, parameters: dict, result: str
        ) -> None:
            try:
                fs.append_tool_call(
                    session_id, ToolCall(tool_name=tool_name, parameters=parameters, result=result)
                )
                readable = generate_human_readable(tool_name, parameters, result)
                fs.log_tool_action(
                    ToolActionLog(
                        user_id=user_id,
                        session_id=session_id,
                        tool_name=tool_name,
                        human_readable=readable,
                        parameters=parameters,
                        result=result,
                        modality="voice",
                    )
                )
            except Exception as exc:
                _log.debug("Tool log error: %s", exc)

        # ── Build GeminiSession (inside try so constructor errors are caught) ─
        _log.info("Building GeminiSession for user_id=%s …", user_id)
        gemini = GeminiSession(
            user_id=user_id,
            enable_tools=True,
            on_transcript=on_transcript,
            on_tool_call=on_tool_call,
            on_tool_call_complete=on_tool_call_complete,
        )
        _log.info("GeminiSession built — connecting to Gemini Live …")

        await gemini.connect()
        connected = True
        _log.info("Gemini Live connected — user_id=%s", user_id)

        # Main Twilio message loop
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            event = msg.get("event", "")

            if event == "connected":
                _log.debug("Twilio protocol 'connected'")

            elif event == "start":
                # streamSid appears at the top level and/or inside msg["start"]
                stream_sid = (
                    msg.get("streamSid")
                    or msg.get("start", {}).get("streamSid", "")
                )
                _log.info("Stream started — streamSid=%s", stream_sid)

                bridge = TwilioAudioBridge(websocket, stream_sid)
                receive_task = asyncio.create_task(gemini.receive_loop(bridge))
                drain_task   = asyncio.create_task(bridge.drain_loop())

                # Kick off Bianca's opening greeting
                await gemini.send_text(INITIAL_GREETING)

            elif event == "media":
                if bridge is None:
                    continue  # Audio arrived before 'start' — ignore
                payload_b64 = msg.get("media", {}).get("payload", "")
                if payload_b64:
                    ulaw_bytes = base64.b64decode(payload_b64)
                    pcm16k = ulaw8k_to_pcm16k(ulaw_bytes)
                    await gemini.send_audio({"data": pcm16k, "mime_type": "audio/pcm;rate=16000"})

            elif event == "stop":
                _log.info("Twilio 'stop' event — ending call for user_id=%s", user_id)
                break

    except WebSocketDisconnect:
        _log.info("Twilio WebSocket disconnected — user_id=%s", user_id)
    except Exception as exc:
        _log.error(
            "Media stream FATAL error (user=%s): %s",
            user_id, exc, exc_info=True,
        )

    finally:
        # ── Persist transcript to Firestore ───────────────────────────────────
        try:
            for entry in transcript_buffer:
                fs.append_message(
                    session_id, Message(role=entry["role"], content=entry["text"])
                )
        except Exception as exc:
            _log.debug("Transcript save error: %s", exc)

        # ── Trigger async summarization ───────────────────────────────────────
        if len(transcript_buffer) >= 2:
            try:
                loop = asyncio.get_event_loop()
                loop.run_in_executor(None, summarize_session_sync, user_id, session_id)
            except Exception as exc:
                _log.debug("Summarise error: %s", exc)

        # ── Cancel background tasks ───────────────────────────────────────────
        for task in (receive_task, drain_task):
            if task:
                task.cancel()

        if connected and gemini:
            await gemini.close()

        _log.info("Media stream cleanup complete — user_id=%s session=%s", user_id, session_id)
