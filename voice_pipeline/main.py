"""
Voice Chat Application - Main Entry Point
A real-time voice chat application using Google's Gemini Live API.
"""
import asyncio
from audio_handler import AudioHandler
from gemini_session import GeminiSession
from prompts import INITIAL_GREETING


class VoiceChatApp:
    """Main application orchestrator for the voice chat system."""
    
    def __init__(self, gemini_session=None, audio_handler=None):
        self.audio_handler = audio_handler or AudioHandler()
        self.gemini_session = gemini_session or GeminiSession()
    
    async def start(self):
        """Start the voice chat application."""
        try:
            # Connect to Gemini
            await self.gemini_session.connect()
            
            print("Connected to Gemini.")
            print("🤖 Sending initial greeting to start the conversation...")
            
            # Send initial greeting to trigger AI to speak first
            await self.gemini_session.send_text(INITIAL_GREETING)
            
            print("👂 Listening for response and your speech...")
            
            # Start all tasks concurrently
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
        """Clean up resources."""
        await self.gemini_session.disconnect()
        self.audio_handler.cleanup()
        print("\nConnection closed.")


async def run():
    """Main function to run the voice chat application."""
    app = VoiceChatApp()
    await app.start()

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("Interrupted by user.")