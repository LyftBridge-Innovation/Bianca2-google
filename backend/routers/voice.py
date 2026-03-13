"""
Phase 5B — Browser WebRTC test endpoint.

Architecture:
  Browser mic (PCM 16kHz Int16)
    → WebSocket /ws/voice/test
    → GeminiSession.send_audio()
    → Gemini Live (tools handled transparently)
    → GeminiSession audio output
    → WebSocket → browser speakers

JSON control messages (sent as strings over the same WebSocket):
  {"type": "transcript", "role": "user"|"assistant", "text": "..."}
  {"type": "tool_call", "tool": "list_events"}

Audio is sent/received as raw bytes (Int16 PCM). The browser checks
typeof event.data to distinguish JSON strings from audio bytes.
"""
import sys
import os
import asyncio
import json
from typing import List, Dict, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

# ── Voice pipeline path ───────────────────────────────────────────────────────
# GeminiSession and its dependencies live in voice_pipeline/.
# tool_dispatcher (imported by GeminiSession) will also add backend/ to sys.path
# at position 0, but backend/ is already present — no collision.
_voice_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'voice_pipeline')
)
if _voice_path not in sys.path:
    sys.path.insert(0, _voice_path)

from gemini_session import GeminiSession  # noqa: E402

# ── Backend imports (Firestore & memory utilities) ────────────────────────────
# The backend/ directory is already in sys.path via tool_dispatcher imports
from models import FirestoreCollections, Session, Message, ToolCall, ToolActionLog  # noqa: E402
from memory_utils import generate_human_readable  # noqa: E402
from summarization import summarize_session_sync  # noqa: E402
from memory_retrieval import retrieve_memories_for_message, format_memory_injection  # noqa: E402

router = APIRouter()

# ── Static test page ──────────────────────────────────────────────────────────

_HTML_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'voice_test.html'))


@router.get("/voice/test", include_in_schema=False)
async def voice_test_page():
    """Serve the single-file browser test UI."""
    return FileResponse(_HTML_PATH)


# ── Audio proxy ───────────────────────────────────────────────────────────────

class _AudioProxy:
    """
    Minimal stand-in for AudioHandler in the server context.
    receive_loop() calls queue_audio_for_playback() with each audio chunk;
    this proxy drops the bytes into an asyncio Queue so the forwarder task
    can pull them and send to the browser.
    """

    def __init__(self, queue: asyncio.Queue):
        self._queue = queue

    def queue_audio_for_playback(self, audio_bytes: bytes):
        try:
            self._queue.put_nowait(audio_bytes)
        except asyncio.QueueFull:
            pass  # Slow consumer — drop rather than block receive_loop


# ── WebSocket handler ─────────────────────────────────────────────────────────

@router.websocket("/ws/voice/test")
async def voice_websocket(websocket: WebSocket, user_id: str = "dev_user_1"):
    """
    Full-duplex voice WebSocket for the browser test UI.

    Query params:
      user_id  - whose Gmail/Calendar credentials to use (default: dev_user_1)
    """
    await websocket.accept()

    # ── Firestore session creation ────────────────────────────────────────────
    fs = FirestoreCollections()
    session_doc = Session(user_id=user_id, modality="voice")
    session_id = fs.create_session(session_doc)

    # ── State tracking ────────────────────────────────────────────────────────
    first_user_message: Optional[str] = None
    memory_injected: bool = False
    transcript_buffer: List[Dict[str, str]] = []  # {"role": ..., "text": ...}

    audio_out_queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=200)
    audio_proxy = _AudioProxy(audio_out_queue)

    # ── Callbacks for transcript and tool-call panel ──────────────────────────

    async def on_transcript(role: str, text: str):
        nonlocal first_user_message, memory_injected

        # Buffer transcript for persistence
        transcript_buffer.append({"role": role, "text": text})

        # Send to browser UI
        try:
            await websocket.send_text(
                json.dumps({"type": "transcript", "role": role, "text": text})
            )
        except Exception:
            pass

        # ── Memory injection on first user message ───────────────────────────
        if role == "user" and not memory_injected:
            first_user_message = text
            memory_injected = True

            try:
                # Query Vertex AI Search for relevant memories
                memory_data = retrieve_memories_for_message(
                    user_message=text,
                    user_id=user_id
                )

                if memory_data["total_count"] > 0:
                    memory_block = format_memory_injection(
                        event_memories=memory_data["event_memories"],
                        entity_memories=memory_data["entity_memories"]
                    )

                    # Inject as natural conversational context
                    # Gemini Live doesn't support system messages mid-session,
                    # so we frame it as background information
                    memory_injection = f"""I should mention—I have some relevant context about you from our previous conversations:

{memory_block}

I'll keep this in mind as we talk."""

                    await session.send_text(memory_injection, end_of_turn=True)
            except Exception as e:
                # Don't fail the call if memory injection fails
                pass

    async def on_tool_call(tool_name: str):
        try:
            await websocket.send_text(
                json.dumps({"type": "tool_call", "tool": tool_name})
            )
        except Exception:
            pass

    async def on_tool_call_complete(tool_name: str, parameters: dict, result: str):
        """Log tool execution to Firestore (session + global log)."""
        try:
            # 1. Append to session's tool_calls array
            tc = ToolCall(
                tool_name=tool_name,
                parameters=parameters,
                result=result
            )
            fs.append_tool_call(session_id, tc)

            # 2. Generate human-readable description
            human_readable = generate_human_readable(tool_name, parameters, result)

            # 3. Log to global tool_action_log collection
            action_log = ToolActionLog(
                user_id=user_id,
                session_id=session_id,
                tool_name=tool_name,
                human_readable=human_readable,
                parameters=parameters,
                result=result,
                modality="voice"  # Important: mark as voice
            )
            fs.log_tool_action(action_log)
        except Exception as e:
            # Don't fail tool execution if logging fails
            pass

    # ── Session setup ─────────────────────────────────────────────────────────

    session = GeminiSession(
        user_id=user_id,
        enable_tools=True,
        on_transcript=on_transcript,
        on_tool_call=on_tool_call,
        on_tool_call_complete=on_tool_call_complete,
    )

    connected = False
    receive_task: asyncio.Task | None = None
    forward_task: asyncio.Task | None = None

    try:
        await session.connect()
        connected = True

        # Tell the browser connection is live
        await websocket.send_text(
            json.dumps({"type": "transcript", "role": "assistant", "text": "Connected — speak now."})
        )

        # Task 1: Gemini → audio_out_queue → browser
        async def forward_audio():
            while True:
                chunk = await audio_out_queue.get()
                try:
                    await websocket.send_bytes(chunk)
                except Exception:
                    break

        # Task 2: Gemini receive loop (routes tool calls, fills audio_out_queue)
        receive_task = asyncio.create_task(session.receive_loop(audio_proxy))
        forward_task = asyncio.create_task(forward_audio())

        # Main loop: browser mic → Gemini
        while True:
            data = await websocket.receive_bytes()
            await session.send_audio({"data": data, "mime_type": "audio/pcm;rate=16000"})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_text(
                json.dumps({"type": "error", "message": str(e)})
            )
        except Exception:
            pass
    finally:
        # ── Persist transcripts ───────────────────────────────────────────────
        try:
            for t in transcript_buffer:
                msg = Message(role=t["role"], content=t["text"])
                fs.append_message(session_id, msg)
        except Exception as e:
            pass  # Don't fail cleanup

        # ── Trigger summarization ─────────────────────────────────────────────
        # Only summarize if we have at least 2 messages (one turn)
        if session_id and len(transcript_buffer) >= 2:
            try:
                # Run in thread pool since summarize_session_sync is blocking
                loop = asyncio.get_event_loop()
                loop.run_in_executor(
                    None,
                    summarize_session_sync,
                    user_id,
                    session_id
                )
            except Exception as e:
                pass  # Don't fail cleanup

        # ── Cleanup tasks ─────────────────────────────────────────────────────
        if receive_task:
            receive_task.cancel()
        if forward_task:
            forward_task.cancel()
        if connected:
            await session.close()
