"""
Gemini Live session handler — Phase 5A rebuild.

What changed from the original:
- Google Search is now declared alongside 9 custom FunctionDeclarations (Gmail + Calendar)
- receive_loop routes tool_call responses to the dispatcher
- _handle_tool_call sends a filler phrase, executes the tool, injects the result
- receive_audio_stream is kept as an alias so main.py / tests continue to work
- close() / disconnect() are both available (same thing)
"""
import asyncio
import os
from typing import Optional, Callable
from google import genai
from google.genai import types

from voice_config import GEMINI_API_KEY, MODEL, VERTEX_MODEL, DEBUG_LOGGING, DEFAULT_USER_ID
from voice_prompts import SYSTEM_INSTRUCTION
from tool_declarations import build_tools_config
from tool_dispatcher import ToolDispatcher


class GeminiSession:
    """
    Manages a Gemini Live WebSocket session with full tool calling support.

    Tools available per session:
      - list_emails, get_email, send_email, draft_email  (Gmail)
      - list_events, get_event, create_event, update_event, decline_event  (Calendar)
      - google_search  (built-in Gemini grounding tool)
    """

    def __init__(
        self,
        user_id: str = DEFAULT_USER_ID,
        enable_tools: bool = True,
        api_key: Optional[str] = None,
        on_transcript: Optional[Callable] = None,
        on_tool_call: Optional[Callable] = None,
        on_tool_call_complete: Optional[Callable] = None,
    ):
        """
        Args:
            user_id:       User whose Gmail/Calendar credentials are used.
            enable_tools:  If False, starts with no tools (useful for raw audio tests).
            api_key:       Override GEMINI_API_KEY from env.
            on_transcript: Optional async callback(role: str, text: str) for 5B/5C.
            on_tool_call:  Optional async callback(tool_name: str) for 5B UI panel.
            on_tool_call_complete: Optional async callback(tool_name: str, parameters: dict, result: str) for 5C Firestore logging.
        """
        self.user_id = user_id
        self.api_key = api_key or GEMINI_API_KEY

        # Prefer Vertex AI when GCP_PROJECT_ID is set (Cloud Run / server env).
        # Fall back to API key for local dev.
        vertex_project = os.getenv("GCP_PROJECT_ID") or os.getenv("VERTEX_PROJECT_ID", "")
        if vertex_project and not self.api_key:
            self.client = genai.Client(
                vertexai=True,
                project=vertex_project,
                location=os.getenv("VERTEX_LOCATION", "us-central1"),
            )
            self._model = VERTEX_MODEL
            if DEBUG_LOGGING:
                print(f"🔧 Using Vertex AI client (project={vertex_project})")
        else:
            self.client = genai.Client(api_key=self.api_key)
            self._model = MODEL
            if DEBUG_LOGGING:
                print(f"🔧 Using AI Studio client")

        self.session = None
        self._connection = None

        self.on_transcript = on_transcript
        self.on_tool_call = on_tool_call

        # Tool dispatcher bound to user_id
        self.dispatcher = ToolDispatcher(user_id, on_tool_call_complete) if enable_tools else None

        # Session config — tools are declared at connect time, not added dynamically
        self._config = {
            "response_modalities": ["AUDIO"],
            "system_instruction": SYSTEM_INSTRUCTION,
        }
        if enable_tools:
            self._config["tools"] = build_tools_config(enable_google_search=True)
            if DEBUG_LOGGING:
                print(f"🔧 Tools enabled for user_id={user_id} (9 custom + Google Search)")

    # ── Connection lifecycle ──────────────────────────────────────────────────

    async def connect(self):
        """Open the Gemini Live WebSocket session."""
        self._connection = self.client.aio.live.connect(
            model=self._model,
            config=self._config,
        )
        self.session = await self._connection.__aenter__()
        if DEBUG_LOGGING:
            print("🤖 Connected to Gemini Live")
        return self.session

    async def close(self):
        """Gracefully close the session."""
        if self._connection:
            try:
                await self._connection.__aexit__(None, None, None)
            except Exception:
                pass
        if DEBUG_LOGGING:
            print("🤖 Gemini session closed")

    async def disconnect(self):
        """Alias for close() — backward compatible."""
        await self.close()

    # ── Sending ───────────────────────────────────────────────────────────────

    async def send_text(self, text: str, end_of_turn: bool = True):
        """Send a text message to Gemini (used for filler phrases and text-mode tests)."""
        if not self.session:
            raise RuntimeError("Session not connected. Call connect() first.")
        if DEBUG_LOGGING:
            print(f"📝 send_text: {text[:60]}")
        await self.session.send(input=text, end_of_turn=end_of_turn)

    async def send_audio(self, audio_data: dict):
        """Send a single audio chunk dict {"data": bytes, "mime_type": "audio/pcm"} to Gemini."""
        if not self.session:
            raise RuntimeError("Session not connected.")
        await self.session.send_realtime_input(audio=audio_data)

    async def send_audio_stream(self, audio_handler):
        """Continuously pipe microphone audio chunks from AudioHandler to Gemini."""
        while True:
            audio_data = await audio_handler.get_mic_audio()
            try:
                await self.session.send_realtime_input(audio=audio_data)
                await asyncio.sleep(0.01)
            except Exception as e:
                if DEBUG_LOGGING:
                    print(f"⚠️ Audio send error: {e}")

    # ── Receive loop ──────────────────────────────────────────────────────────

    async def receive_loop(self, audio_handler):
        """
        Main receive loop — runs forever until cancelled.

        Routes:
          response.tool_call        → _handle_tool_call (awaited inline)
          response.server_content   → audio to speaker queue, text to transcript callback
          executable_code / result  → Google Search logging
        """
        import logging
        _log = logging.getLogger(__name__)
        try:
            while True:
                turn = self.session.receive()
                async for response in turn:

                    # ── Custom function call from Gemini ──────────────────────────
                    if response.tool_call:
                        for fc in response.tool_call.function_calls:
                            fname = fc.name
                            fparams = dict(fc.args) if fc.args else {}
                            fcall_id = getattr(fc, "id", None)
                            await self._handle_tool_call(fname, fparams, fcall_id)

                    # ── Audio / text from model turn ──────────────────────────────
                    if response.server_content:
                        sc = response.server_content

                        # Native audio preview: audio in model_turn parts
                        if sc.model_turn:
                            for part in sc.model_turn.parts:
                                if part.inline_data and isinstance(part.inline_data.data, bytes):
                                    audio_handler.queue_audio_for_playback(part.inline_data.data)
                                if part.text and self.on_transcript:
                                    await self.on_transcript("assistant", part.text)
                                if part.executable_code is not None and DEBUG_LOGGING:
                                    print(f"🔍 Search: {part.executable_code.code[:80]}")
                                if part.code_execution_result is not None and DEBUG_LOGGING:
                                    print(f"🔍 Search result: {part.code_execution_result.output[:80]}")

                        # Native audio preview: output_transcription (spoken text from model)
                        if hasattr(sc, "output_transcription") and sc.output_transcription:
                            t = sc.output_transcription
                            text = t.text if hasattr(t, "text") else str(t)
                            if text and self.on_transcript:
                                await self.on_transcript("assistant", text)

                        # Native audio preview: input_transcription (user speech → text)
                        if hasattr(sc, "input_transcription") and sc.input_transcription:
                            t = sc.input_transcription
                            text = t.text if hasattr(t, "text") else str(t)
                            if text and self.on_transcript:
                                await self.on_transcript("user", text)

                if DEBUG_LOGGING:
                    print("✅ Turn complete")

        except asyncio.CancelledError:
            pass  # Normal shutdown
        except Exception as e:
            _log.error("receive_loop crashed: %s", e, exc_info=True)
            if self.on_transcript:
                try:
                    await self.on_transcript("assistant", f"[Voice error: {e}]")
                except Exception:
                    pass

    async def receive_audio_stream(self, audio_handler):
        """Alias for receive_loop() — backward compatible with main.py."""
        await self.receive_loop(audio_handler)

    # ── Tool call handler ─────────────────────────────────────────────────────

    async def _handle_tool_call(self, function_name: str, parameters: dict, call_id: str = None):
        """
        Handle a single Gemini tool call:
          1. Execute the tool via dispatcher
          2. Inject result via send_tool_response (must include call_id) → Gemini speaks answer
        """
        import logging
        _log = logging.getLogger(__name__)
        _log.info("Tool call: %s  id=%s  params=%s", function_name, call_id, parameters)

        # Fire optional UI callback (Phase 5B tool call panel)
        if self.on_tool_call:
            try:
                await self.on_tool_call(function_name)
            except Exception:
                pass

        # ── Execute tool ──────────────────────────────────────────────────────
        result = ""
        try:
            if self.dispatcher and self.dispatcher.is_known_tool(function_name):
                result = await self.dispatcher.dispatch(function_name, parameters)
            else:
                result = f"Tool '{function_name}' is not available."
                _log.warning("Unknown tool requested: %s", function_name)
        except Exception as e:
            result = f"Error running {function_name}: {str(e)}"
            _log.error("Tool execution error (%s): %s", function_name, e, exc_info=True)

        _log.info("Tool result (%s): %s", function_name, str(result)[:200])

        # ── Inject result back to Gemini (call_id MUST be echoed) ────────────
        try:
            fr = types.FunctionResponse(
                name=function_name,
                response={"result": result},
            )
            if call_id:
                fr.id = call_id
            await self.session.send_tool_response(function_responses=[fr])
        except Exception as e:
            _log.error("send_tool_response failed (%s): %s", function_name, e, exc_info=True)
