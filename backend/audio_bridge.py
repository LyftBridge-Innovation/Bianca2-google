"""
Audio format bridge between Twilio (μ-law 8 kHz) and Gemini Live (PCM 16 / 24 kHz).

Conversion chain
  Twilio → Gemini :  μ-law 8 kHz  →  audioop.ulaw2lin  →  PCM 8 kHz  →  ratecv(8→16k)  →  PCM 16 kHz
  Gemini → Twilio :  PCM 24 kHz   →  ratecv(24→8k)     →  PCM 8 kHz  →  lin2ulaw        →  μ-law 8 kHz

audioop is Python 3.11 stdlib (deprecated but not removed until 3.13).
"""
import asyncio
import base64
import json
import warnings

# Suppress the DeprecationWarning emitted by audioop in Python 3.11+
with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    import audioop


# ── Sample-rate constants ─────────────────────────────────────────────────────

_TWILIO_RATE    = 8_000   # μ-law, both inbound (caller) and outbound (Bianc.ai)
_GEMINI_IN_RATE = 16_000  # PCM expected by GeminiSession.send_audio
_GEMINI_OUT_RATE = 24_000 # PCM produced by Gemini Live receive_loop by default

_SW = 2  # sample width = 16-bit = 2 bytes


# ── Conversion helpers ────────────────────────────────────────────────────────

def ulaw8k_to_pcm16k(ulaw_bytes: bytes) -> bytes:
    """Convert μ-law 8 kHz bytes (from Twilio) to PCM 16 kHz 16-bit (for Gemini)."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        pcm8k = audioop.ulaw2lin(ulaw_bytes, _SW)
        pcm16k, _ = audioop.ratecv(pcm8k, _SW, 1, _TWILIO_RATE, _GEMINI_IN_RATE, None)
    return pcm16k


def pcm24k_to_ulaw8k(pcm24k_bytes: bytes) -> bytes:
    """Convert PCM 24 kHz 16-bit bytes (from Gemini) to μ-law 8 kHz (for Twilio)."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        pcm8k, _ = audioop.ratecv(pcm24k_bytes, _SW, 1, _GEMINI_OUT_RATE, _TWILIO_RATE, None)
        ulaw8k = audioop.lin2ulaw(pcm8k, _SW)
    return ulaw8k


# ── TwilioAudioBridge ─────────────────────────────────────────────────────────

class TwilioAudioBridge:
    """
    Bidirectional audio bridge wired between a Twilio Media Stream WebSocket
    and a GeminiSession.

    It implements the minimal "audio handler" interface expected by
    GeminiSession.receive_loop():

        audio_handler.queue_audio_for_playback(pcm_bytes: bytes) -> None

    Outgoing audio is queued and drained to Twilio by the companion drain_loop().

    Usage:
        bridge = TwilioAudioBridge(websocket, stream_sid)
        receive_task = asyncio.create_task(gemini.receive_loop(bridge))
        drain_task   = asyncio.create_task(bridge.drain_loop())
    """

    def __init__(self, ws, stream_sid: str):
        self._ws = ws
        self._stream_sid = stream_sid
        # Generous buffer — Gemini can burst audio chunks
        self._out_queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=600)

    # Called by GeminiSession.receive_loop on every audio output chunk
    def queue_audio_for_playback(self, pcm_bytes: bytes) -> None:
        try:
            ulaw = pcm24k_to_ulaw8k(pcm_bytes)
            self._out_queue.put_nowait(ulaw)
        except asyncio.QueueFull:
            pass   # Slow consumer — drop rather than block the receive loop
        except Exception:
            pass

    async def drain_loop(self) -> None:
        """Pull outgoing μ-law chunks from the queue and send them to Twilio."""
        while True:
            ulaw = await self._out_queue.get()
            payload = base64.b64encode(ulaw).decode()
            try:
                await self._ws.send_text(json.dumps({
                    "event": "media",
                    "streamSid": self._stream_sid,
                    "media": {"payload": payload},
                }))
            except Exception:
                break  # WebSocket closed — exit cleanly
