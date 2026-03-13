"""
Audio transcoding utilities for Twilio integration (Phase 5D).

Twilio sends 8 kHz mulaw (ulaw) audio; Gemini Live expects 16 kHz signed 16-bit PCM.
Both directions are handled here.

audioop was removed in Python 3.13 — we fall back to the audioop-lts drop-in replacement.
Install: pip install audioop-lts

Stateless helpers: ulaw_to_pcm16k / pcm16k_to_ulaw
  Use for one-shot conversions.

Stateful stream classes: UlawToPcm16kStream / Pcm16kToUlawStream
  Use for continuous Twilio streams to avoid click artifacts at chunk boundaries.
  The ratecv state is kept between calls.
"""
# audioop was removed in Python 3.13; audioop-lts is the drop-in replacement.
try:
    import audioop
except ModuleNotFoundError:
    import audioop_lts as audioop  # pip install audioop-lts


# ── Stateless one-shot helpers ────────────────────────────────────────────────

def ulaw_to_pcm16k(ulaw_bytes: bytes) -> bytes:
    """Convert 8 kHz mulaw bytes → 16 kHz signed 16-bit PCM bytes."""
    pcm_8k = audioop.ulaw2lin(ulaw_bytes, 2)
    pcm_16k, _ = audioop.ratecv(pcm_8k, 2, 1, 8000, 16000, None)
    return pcm_16k


def pcm16k_to_ulaw(pcm_bytes: bytes) -> bytes:
    """Convert 16 kHz signed 16-bit PCM bytes → 8 kHz mulaw bytes."""
    pcm_8k, _ = audioop.ratecv(pcm_bytes, 2, 1, 16000, 8000, None)
    return audioop.lin2ulaw(pcm_8k, 2)


# ── Stateful stream classes ───────────────────────────────────────────────────

class UlawToPcm16kStream:
    """
    Stateful mulaw → PCM 16 kHz converter for continuous Twilio inbound streams.
    Maintains ratecv state across chunks to prevent audio artifacts at boundaries.
    """

    def __init__(self):
        self._state = None

    def convert(self, ulaw_bytes: bytes) -> bytes:
        pcm_8k = audioop.ulaw2lin(ulaw_bytes, 2)
        pcm_16k, self._state = audioop.ratecv(pcm_8k, 2, 1, 8000, 16000, self._state)
        return pcm_16k

    def reset(self):
        """Call on call disconnect to clear state for next caller."""
        self._state = None


class Pcm16kToUlawStream:
    """
    Stateful PCM 16 kHz → mulaw converter for continuous Twilio outbound streams.
    Maintains ratecv state across chunks to prevent audio artifacts at boundaries.
    """

    def __init__(self):
        self._state = None

    def convert(self, pcm_bytes: bytes) -> bytes:
        pcm_8k, self._state = audioop.ratecv(pcm_bytes, 2, 1, 16000, 8000, self._state)
        return audioop.lin2ulaw(pcm_8k, 2)

    def reset(self):
        """Call on call disconnect to clear state for next caller."""
        self._state = None
