"""
System prompt assembly for Bianca.

The prompt is built in layers, each with a distinct responsibility:

  Layer 1 — Identity anchor    : who Bianca is + current date/time
  Layer 2 — Knowledge base     : persona, training, expertise, product context
  Layer 3 — Values             : non-negotiable behavioral rules (highest authority)
  Layer 4 — Capabilities       : tools available in this session
  [Runtime] Memory injection   : per-user memories, injected at request time in chat.py

This module owns layers 1–4. Memory is injected separately in the chat router.
"""

from datetime import datetime
from knowledge_loader import build_knowledge_block
from values import build_values_block
from settings_loader import load_settings


# ---------------------------------------------------------------------------
# Layer 1 — Identity anchor
# ---------------------------------------------------------------------------

def _build_identity_block() -> str:
    settings = load_settings()
    ai_name = settings.get("ai_name", "Bianca")
    ai_role = settings.get("ai_role", "AI Chief of Staff")
    now = datetime.now()
    date_str = now.strftime("%A, %B %d, %Y")   # e.g., "Friday, March 13, 2026"
    time_str = now.strftime("%I:%M %p")          # e.g., "02:45 PM"
    return (
        f"You are {ai_name}, an {ai_role}.\n\n"
        f"Today is {date_str}. Current time: {time_str}.\n"
        f"Use this as your reference for all time-based queries, scheduling, and calendar operations."
    )


# ---------------------------------------------------------------------------
# Layer 4 — Capabilities
# ---------------------------------------------------------------------------

_CAPABILITIES_BLOCK = """\
=== CAPABILITIES AVAILABLE IN THIS SESSION ===

**Gmail**
- list_emails   : retrieve recent emails from the inbox
- get_email     : read the full content of a specific email
- send_email    : send an email (only after explicit user confirmation)
- draft_email   : compose a draft without sending

**Google Calendar**
- list_events   : view upcoming events in a date range
- get_event     : read details of a specific event
- create_event  : create a new calendar event
- update_event  : modify an existing event's details or time
- decline_event : decline a meeting invitation with an optional message

**Google Search**
- Available automatically for any question that requires current information,
  recent news, live data, or facts beyond your training knowledge. Use it
  proactively whenever the user asks about real-world events, people, companies,
  or anything time-sensitive.

Use these tools proactively when the user's request clearly calls for them. \
Always prefer to draft emails rather than send them unless the user explicitly \
instructs you to send."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_system_prompt() -> str:
    """
    Assemble and return the full system prompt for a chat session.

    Called once per request. The identity block is generated fresh each call
    so the date/time is always accurate. Knowledge and values are fast
    (small text files + in-memory constants).
    """
    settings = load_settings()
    custom_prompt = settings.get("custom_prompt", "").strip()

    blocks = [
        _build_identity_block(),
        build_knowledge_block(),
        build_values_block(),
        _CAPABILITIES_BLOCK,
    ]

    # Drop any empty blocks (e.g. if knowledge files are missing)
    assembled = "\n\n".join(block for block in blocks if block.strip())

    # Prepend custom prompt if set
    if custom_prompt:
        assembled = f"{custom_prompt}\n\n{assembled}"

    return assembled
