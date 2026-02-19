# Voice Chat Application

A real-time voice chat application powered by Google's Gemini Live API with native audio support.

## Features

- **Real-time voice conversation** with Gemini AI
- **Google Search integration** for up-to-date information
- **Modular architecture** for easy customization and scaling
- **Debug logging** to monitor audio flow and search queries
- **Configurable settings** for audio, API, and tools

## Project Structure

```
voice-chat/
├── main.py                 # Application entry point and orchestrator
├── audio_handler.py        # Audio input/output management
├── gemini_session.py       # Gemini API session handling
├── config.py              # Configuration settings
├── prompts.py             # AI system instructions and prompts
└── requirements.txt       # Python dependencies
```

## Module Overview

### `main.py`
- Application orchestrator
- Manages the lifecycle of the voice chat app
- Coordinates between audio handler and Gemini session

### `audio_handler.py`
- `AudioHandler` class for managing audio I/O
- Handles microphone input and speaker output
- Manages audio queues for streaming

### `gemini_session.py`
- `GeminiSession` class for Gemini API communication
- Manages real-time audio streaming to/from Gemini
- Handles text input for initial prompts

### `config.py`
- Audio configuration (sample rates, formats, etc.)
- API settings (model name, API key)
- Tools configuration (enable/disable Google Search)
- Debug and queue settings

### `prompts.py`
- System instructions that define AI behavior
- Initial greeting and conversation starters
- Easily customizable prompts for different use cases

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set your API key (optional if using environment variable):
```bash
export GOOGLE_API_KEY="your-api-key-here"
```

Or edit `config.py` directly.

3. Run the application:
```bash
python3 main.py
```

## Usage

1. The AI will introduce itself when you start the app
2. Speak naturally into your microphone
3. The AI will respond when it detects you've finished speaking
4. **Ask questions about current events** - the AI will use Google Search automatically
5. Press Ctrl+C to exit

### Example Questions with Google Search
- "When did the last Brazil vs. Argentina soccer match happen?"
- "Who won the Euro 2024?"
- "What's the latest news about AI?"
- "What's the current weather in New York?"

When Google Search is triggered, you'll see:
- 🔍 The search code being executed
- 🔍 The search results obtained

## Customization

### Enable/Disable Google Search
Edit `config.py`:
```python
ENABLE_GOOGLE_SEARCH = True  # or False to disable
```

Or in code:
```python
from gemini_session import GeminiSession
from main import VoiceChatApp

session = GeminiSession(enable_search=False)
app = VoiceChatApp(gemini_session=session)
```

### Change AI Personality
Edit `prompts.py` to modify `SYSTEM_INSTRUCTION`:
```python
SYSTEM_INSTRUCTION = "You are a [your custom personality]"
```

### Adjust Audio Settings
Edit `config.py` to change sample rates, buffer sizes, etc.

### Add New Features
- Add new methods to `AudioHandler` for audio processing
- Extend `GeminiSession` for additional API features
- Modify `VoiceChatApp` to add new behaviors

## Debug Mode

Debug logging is enabled by default in `config.py`:
```python
DEBUG_LOGGING = True
```

This shows:
- 📤 Audio being sent to Gemini
- 🔊 Audio chunks received
- 🔉 Audio being played
- ✅ Conversation turn completions

## Requirements

- Python 3.11+
- PyAudio
- Google Generative AI SDK
