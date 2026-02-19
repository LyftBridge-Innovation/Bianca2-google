"""Gemini API session handler for real-time voice communication."""
import asyncio
from google import genai
from typing import Optional
from config import GEMINI_API_KEY, MODEL, DEBUG_LOGGING, ENABLE_GOOGLE_SEARCH
from prompts import SYSTEM_INSTRUCTION


class GeminiSession:
    """Manages the Gemini Live API session for real-time audio communication."""
    
    def __init__(self, api_key: Optional[str] = None, enable_search: bool = ENABLE_GOOGLE_SEARCH):
        self.api_key = api_key or GEMINI_API_KEY
        self.client = genai.Client(api_key=self.api_key)
        self.session = None
        self._connection = None
        
        # Build config with optional Google Search tool
        self.config = {
            "response_modalities": ["AUDIO"],
            "system_instruction": SYSTEM_INSTRUCTION,
        }
        
        if enable_search:
            self.config["tools"] = [{'google_search': {}}]
            if DEBUG_LOGGING:
                print("🔍 Google Search tool enabled")
    
    async def connect(self):
        """Establish connection to Gemini Live API."""
        self._connection = self.client.aio.live.connect(
            model=MODEL,
            config=self.config
        )
        self.session = await self._connection.__aenter__()
        if DEBUG_LOGGING:
            print("🤖 Connected to Gemini Live API")
        return self.session
    
    async def disconnect(self):
        """Disconnect from Gemini Live API."""
        if self._connection:
            await self._connection.__aexit__(None, None, None)
            if DEBUG_LOGGING:
                print("🤖 Disconnected from Gemini")
    
    async def send_text(self, text: str, end_of_turn: bool = True):
        """Send a text message to Gemini."""
        if not self.session:
            raise RuntimeError("Session not connected. Call connect() first.")
        
        if DEBUG_LOGGING:
            print(f"📝 Sending text: {text[:50]}...")
        
        await self.session.send(input=text, end_of_turn=end_of_turn)
    
    async def send_audio_stream(self, audio_handler):
        """Continuously send audio from the audio handler to Gemini."""
        while True:
            audio_data = await audio_handler.get_mic_audio()
            if DEBUG_LOGGING:
                print("📤 Sending audio to Gemini...")
            await self.session.send_realtime_input(audio=audio_data)
    
    async def receive_audio_stream(self, audio_handler):
        """Continuously receive audio responses from Gemini."""
        while True:
            turn = self.session.receive()
            async for response in turn:
                if response.server_content and response.server_content.model_turn:
                    for part in response.server_content.model_turn.parts:
                        # Handle audio data
                        if part.inline_data and isinstance(part.inline_data.data, bytes):
                            audio_handler.queue_audio_for_playback(part.inline_data.data)
                        
                        # Handle code execution (for Google Search)
                        if part.executable_code is not None:
                            if DEBUG_LOGGING:
                                print(f"🔍 Executing search code:\n{part.executable_code.code}")
                        
                        if part.code_execution_result is not None:
                            if DEBUG_LOGGING:
                                print(f"🔍 Search result: {part.code_execution_result.output}")
                else:
                    if DEBUG_LOGGING:
                        print(f"📥 Received response: {response}")
            
            if DEBUG_LOGGING:
                print("✅ Turn complete")
