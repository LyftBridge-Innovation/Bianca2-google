"""
Voice pipeline — local mic/speaker entry point.

Runs the full voice pipeline on your machine:
  microphone → Gemini Live (Gmail + Calendar + Google Search tools) → speakers

Usage:
  python main.py
  DEBUG_LOGGING=true python main.py
  TEST_USER_ID=my_user python main.py
"""
import asyncio
from audio_handler import AudioHandler
from gemini_session import GeminiSession
from voice_config import DEFAULT_USER_ID
from voice_prompts import INITIAL_GREETING


class VoiceChatApp:
    """Orchestrates AudioHandler + GeminiSession for a local voice session."""

    def __init__(self, user_id: str = DEFAULT_USER_ID):
        self.audio_handler = AudioHandler()
        self.gemini_session = GeminiSession(user_id=user_id)

    async def start(self):
        """Connect, greet, then run all tasks concurrently."""
        try:
            await self.gemini_session.connect()
            print(f"Connected to Gemini (user_id={self.gemini_session.user_id})")
            print("Sending initial greeting...")

            await self.gemini_session.send_text(INITIAL_GREETING)
            print("Listening — speak now. Ctrl+C to quit.\n")

            async with asyncio.TaskGroup() as tg:
                tg.create_task(self.audio_handler.listen())
                tg.create_task(self.audio_handler.play())
                tg.create_task(self.gemini_session.send_audio_stream(self.audio_handler))
                tg.create_task(self.gemini_session.receive_audio_stream(self.audio_handler))

        except asyncio.CancelledError:
            pass
        finally:
            await self.cleanup()

    async def cleanup(self):
        await self.gemini_session.disconnect()
        self.audio_handler.cleanup()
        print("\nConnection closed.")


async def run():
    app = VoiceChatApp(user_id=DEFAULT_USER_ID)
    await app.start()


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("Interrupted.")
