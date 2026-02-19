"""Configuration settings for the voice chat application."""
import os
import pyaudio

# --- API Configuration ---
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY", "AIzaSyAeox_cYO5XAFzdNHhE8dsEmVygDLB3JHw")
MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"

# --- Audio Configuration ---
FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000  # Microphone input sample rate
RECEIVE_SAMPLE_RATE = 24000  # Speaker output sample rate
CHUNK_SIZE = 1024

# --- Queue Configuration ---
MIC_QUEUE_MAX_SIZE = 5

# --- Tools Configuration ---
ENABLE_GOOGLE_SEARCH = True  # Enable Google Search tool for grounding

# --- Debug Configuration ---
DEBUG_LOGGING = True
