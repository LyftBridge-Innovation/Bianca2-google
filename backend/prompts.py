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


# ---------------------------------------------------------------------------
# Layer 1 — Identity anchor
# ---------------------------------------------------------------------------

def _build_identity_block() -> str:
    now = datetime.now()
    date_str = now.strftime("%A, %B %d, %Y")   # e.g., "Friday, March 13, 2026"
    time_str = now.strftime("%I:%M %p")          # e.g., "02:45 PM"
    return (
        f"You are Bianca, an AI Chief of Staff.\n\n"
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
    blocks = [
        _build_identity_block(),
        build_knowledge_block(),
        build_values_block(),
        _CAPABILITIES_BLOCK,
    ]

    # Drop any empty blocks (e.g. if knowledge files are missing)
    return "\n\n".join(block for block in blocks if block.strip())
