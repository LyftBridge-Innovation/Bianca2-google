"""Shared settings loader — reads settings.json override file."""

import json
from pathlib import Path
from typing import Any

_SETTINGS_PATH = Path(__file__).parent / "knowledge" / "settings.json"

_DEFAULT_SETTINGS: dict[str, Any] = {
    "ai_name": "Bianc.ai",
    "ai_role": "AI Chief of Staff",
    "ai_voice": "Aoede",
    "primary_language": "English",
    "secondary_language": "",
    # Default to Claude Sonnet 4.6 — switch to Gemini in Neural Config → System Prompt tab.
    "model": "claude-sonnet-4-6",
    "temperature": 0.7,
    "custom_prompt": "",
    "slides_template_id": "",
    "docs_template_id": "",
    "sheets_template_id": "",
    "voice_prompt": "",
    "voice_greeting": "",
    "email_polling_interval": 15,
    "email_polling_days": "weekdays",
    # Google / Gemini API key (AI Studio) — falls back to GOOGLE_API_KEY env var if blank
    # Leave blank to use Vertex AI with Application Default Credentials instead.
    "google_api_key": "",
    # Anthropic key — falls back to ANTHROPIC_API_KEY env var if blank
    "anthropic_api_key": "",
}


def load_settings() -> dict[str, Any]:
    """Return merged settings (defaults + overrides from settings.json)."""
    settings = dict(_DEFAULT_SETTINGS)
    if _SETTINGS_PATH.exists():
        try:
            overrides = json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
            settings.update(overrides)
        except Exception:
            pass
    return settings
