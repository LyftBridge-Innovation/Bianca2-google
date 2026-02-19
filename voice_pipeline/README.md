# Voice Pipeline (Phase 5)

This directory contains the Gemini Live voice chat implementation that will be integrated in Phase 5.

## Files

- `main.py` - Voice chat application entry point
- `audio_handler.py` - Audio input/output handling with PyAudio
- `gemini_session.py` - Gemini Live API session management
- `prompts.py` - System prompts for voice interaction
- `config.py` - Voice pipeline configuration
- `requirements.txt` - Dependencies for voice pipeline

## Running the Voice Pipeline

```bash
# Install dependencies
pip install -r requirements.txt

# Set your API key
export GOOGLE_API_KEY=your_key_here

# Run the voice chat
python main.py
```

## Integration Plan

In Phase 5, this voice pipeline will be connected to:
- Shared tools in `backend/tools/` (Gmail, Calendar)
- Shared memory layer (Firestore conversation history)
- Twilio for phone number integration

The voice pipeline will remain separate but call the same backend tools and memory as the chat pipeline.
