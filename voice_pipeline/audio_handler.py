"""Audio input/output handler for the voice chat application."""
import asyncio
import pyaudio
from typing import Optional
from config import (
    FORMAT, CHANNELS, SEND_SAMPLE_RATE, RECEIVE_SAMPLE_RATE,
    CHUNK_SIZE, MIC_QUEUE_MAX_SIZE, DEBUG_LOGGING
)


class AudioHandler:
    """Manages audio input from microphone and output to speakers."""
    
    def __init__(self):
        self.pya = pyaudio.PyAudio()
        self.mic_stream: Optional[object] = None
        self.speaker_stream: Optional[object] = None
        self.mic_queue = asyncio.Queue(maxsize=MIC_QUEUE_MAX_SIZE)
        self.speaker_queue = asyncio.Queue()
        
    async def start_microphone(self):
        """Start capturing audio from the microphone."""
        mic_info = self.pya.get_default_input_device_info()
        self.mic_stream = await asyncio.to_thread(
            self.pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=SEND_SAMPLE_RATE,
            input=True,
            input_device_index=mic_info["index"],
            frames_per_buffer=CHUNK_SIZE,
        )
        if DEBUG_LOGGING:
            print(f"🎤 Microphone started: {mic_info['name']}")
    
    async def start_speaker(self):
        """Start speaker output stream."""
        self.speaker_stream = await asyncio.to_thread(
            self.pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=RECEIVE_SAMPLE_RATE,
            output=True,
        )
        if DEBUG_LOGGING:
            print("🔊 Speaker output initialized")
    
    async def listen(self):
        """Continuously capture audio from microphone and queue it."""
        if not self.mic_stream:
            await self.start_microphone()
        
        kwargs = {"exception_on_overflow": False} if __debug__ else {}
        while True:
            data = await asyncio.to_thread(
                self.mic_stream.read, CHUNK_SIZE, **kwargs
            )
            audio_data = {"data": data, "mime_type": "audio/pcm"}
            
            # Use try_put to avoid blocking - drop frames if queue is full
            try:
                self.mic_queue.put_nowait(audio_data)
            except asyncio.QueueFull:
                # Queue is full - drop the oldest frame and add this one
                try:
                    self.mic_queue.get_nowait()
                    self.mic_queue.put_nowait(audio_data)
                except:
                    pass  # Silently drop if we can't manage the queue
    
    async def play(self):
        """Continuously play audio from the speaker queue."""
        if not self.speaker_stream:
            await self.start_speaker()
        
        while True:
            audio_bytes = await self.speaker_queue.get()
            if DEBUG_LOGGING:
                print(f"🔉 Playing audio: {len(audio_bytes)} bytes")
            await asyncio.to_thread(self.speaker_stream.write, audio_bytes)
    
    def queue_audio_for_playback(self, audio_bytes: bytes):
        """Add audio data to the playback queue."""
        self.speaker_queue.put_nowait(audio_bytes)
        if DEBUG_LOGGING:
            print(f"🔊 Queued audio chunk: {len(audio_bytes)} bytes")
    
    async def get_mic_audio(self):
        """Get the next audio chunk from the microphone queue."""
        return await self.mic_queue.get()
    
    def cleanup(self):
        """Close audio streams and terminate PyAudio."""
        if self.mic_stream:
            self.mic_stream.close()
        if self.speaker_stream:
            self.speaker_stream.close()
        self.pya.terminate()
        if DEBUG_LOGGING:
            print("🔇 Audio streams closed")
