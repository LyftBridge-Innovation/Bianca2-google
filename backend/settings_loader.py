"""Shared settings loader — reads settings.json override file."""

import json
from pathlib import Path
from typing import Any

_SETTINGS_PATH = Path(__file__).parent / "knowledge" / "settings.json"

_DEFAULT_SETTINGS: dict[str, Any] = {
    "ai_name": "Bianca",
    "ai_role": "AI Chief of Staff",
    "ai_voice": "shimmer",
    "primary_language": "English",
    "secondary_language": "",
    # Default to Gemini 2.5 Flash on Vertex AI — works with ADC, no external key needed.
    # Switch to a Claude model in Neural Config → System Prompt tab.
    "model": "gemini-2.5-flash",
    "temperature": 0.7,
    "custom_prompt": "",
    "slides_template_id": "",
    "docs_template_id": "",
    "sheets_template_id": "",
    "voice_prompt": "",
    "voice_greeting": "",
    "email_polling_interval": 15,
    "email_polling_days": "weekdays",
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
