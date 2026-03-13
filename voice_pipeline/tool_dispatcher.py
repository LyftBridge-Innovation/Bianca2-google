"""
Dispatcher for Gemini Live tool calls.

Maps function names → async callables that wrap the Phase 1 backend tools.
Also holds filler phrases and result formatters.

The backend directory is added to sys.path so calendar.py / gmail.py can be
imported directly — same code, no duplication.
"""
import sys
import os
import asyncio
from typing import Optional, Callable

# ── Backend path setup ────────────────────────────────────────────────────────
# Inserted at position 0 so backend tool modules resolve imports correctly.
# voice_pipeline uses voice_config.py exclusively — no naming collision.
_backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

# These imports resolve against backend/ once sys.path is updated
from tools.gmail import list_emails, get_email, send_email, draft_email          # noqa: E402
from tools.calendar import list_events, get_event, create_event, update_event, decline_event  # noqa: E402

# Import DEBUG_LOGGING from voice_config for error logging
from voice_config import DEBUG_LOGGING  # noqa: E402


# ── Filler phrases ────────────────────────────────────────────────────────────
# Sent as text to Gemini before tool execution so it speaks them in its own voice.

FILLER_PHRASES: dict[str, str] = {
    "list_emails":   "Let me check your inbox.",
    "get_email":     "Let me check your inbox.",
    "send_email":    "Give me a moment to handle that email.",
    "draft_email":   "Give me a moment to handle that email.",
    "list_events":   "Let me pull up your calendar.",
    "get_event":     "Let me pull up your calendar.",
    "create_event":  "Let me update your calendar.",
    "update_event":  "Let me update your calendar.",
    "decline_event": "Let me take care of that for you.",
}


# ── Result formatters ─────────────────────────────────────────────────────────
# Convert raw dicts to clean readable strings Gemini can speak naturally.

def _fmt_emails(emails: list[dict]) -> str:
    if not emails:
        return "No emails found."
    lines = [f"Found {len(emails)} email(s):"]
    for e in emails:
        lines.append(f"- [{e['id']}] From: {e['from']} | Subject: {e['subject']} | {e['date']}")
        if e.get("snippet"):
            lines.append(f"  Preview: {e['snippet'][:120]}")
    return "\n".join(lines)


def _fmt_email(email: dict) -> str:
    return (
        f"From: {email['from']}\n"
        f"To: {email['to']}\n"
        f"Date: {email['date']}\n"
        f"Subject: {email['subject']}\n"
        f"Body:\n{email['body'][:2000]}"
    )


def _fmt_events(events: list[dict]) -> str:
    if not events:
        return "No upcoming events found."
    lines = [f"Found {len(events)} event(s):"]
    for e in events:
        lines.append(f"- [{e['id']}] {e['title']} | Start: {e['start']} | End: {e['end']}")
        if e.get("attendees"):
            lines.append(f"  Attendees: {', '.join(e['attendees'])}")
    return "\n".join(lines)


def _fmt_event(event: dict) -> str:
    return (
        f"Title: {event['title']}\n"
        f"Start: {event['start']}\n"
        f"End: {event['end']}\n"
        f"Organizer: {event.get('organizer', 'N/A')}\n"
        f"Attendees: {', '.join(event.get('attendees', []))}\n"
        f"Description: {event.get('description', 'None')}"
    )


# ── Dispatcher ────────────────────────────────────────────────────────────────

class ToolDispatcher:
    """
    Async dispatcher bound to a specific user_id.
    Each instance maps function name strings → async handlers that call
    the synchronous backend tools via asyncio.to_thread().
    """

    def __init__(self, user_id: str, on_tool_call_complete: Optional[Callable] = None):
        self.user_id = user_id
        self.on_tool_call_complete = on_tool_call_complete
        self._map: dict = {
            "list_emails":   self._list_emails,
            "get_email":     self._get_email,
            "send_email":    self._send_email,
            "draft_email":   self._draft_email,
            "list_events":   self._list_events,
            "get_event":     self._get_event,
            "create_event":  self._create_event,
            "update_event":  self._update_event,
            "decline_event": self._decline_event,
        }

    def is_known_tool(self, function_name: str) -> bool:
        return function_name in self._map

    def get_filler_phrase(self, function_name: str) -> str:
        return FILLER_PHRASES.get(function_name, "Let me take care of that.")

    async def dispatch(self, function_name: str, parameters: dict) -> str:
        """
        Route a Gemini tool call to the correct backend function.
        Returns a clean formatted string result.
        Raises ValueError for unknown names.
        """
        handler = self._map.get(function_name)
        if not handler:
            raise ValueError(f"Unknown tool function: {function_name!r}")

        result = await handler(parameters)

        # Invoke tool completion callback for Firestore logging
        if self.on_tool_call_complete:
            try:
                await self.on_tool_call_complete(
                    tool_name=function_name,
                    parameters=parameters,
                    result=result
                )
            except Exception as e:
                # Don't fail tool execution if logging fails
                if DEBUG_LOGGING:
                    print(f"⚠️ Tool logging callback failed: {e}")

        return result

    # ── Gmail ─────────────────────────────────────────────────────────────────

    async def _list_emails(self, params: dict) -> str:
        max_results = int(params.get("max_results", 10))
        result = await asyncio.to_thread(list_emails, self.user_id, max_results)
        return _fmt_emails(result)

    async def _get_email(self, params: dict) -> str:
        result = await asyncio.to_thread(get_email, self.user_id, params["email_id"])
        return _fmt_email(result)

    async def _send_email(self, params: dict) -> str:
        result = await asyncio.to_thread(
            send_email, self.user_id, params["to"], params["subject"], params["body"]
        )
        return f"Email sent successfully. Message ID: {result['id']}"

    async def _draft_email(self, params: dict) -> str:
        result = await asyncio.to_thread(
            draft_email, self.user_id, params["to"], params["subject"], params["body"]
        )
        return f"Email saved as draft. Draft ID: {result['id']}"

    # ── Calendar ──────────────────────────────────────────────────────────────

    async def _list_events(self, params: dict) -> str:
        days_ahead = int(params.get("days_ahead", 7))
        result = await asyncio.to_thread(list_events, self.user_id, days_ahead)
        return _fmt_events(result)

    async def _get_event(self, params: dict) -> str:
        result = await asyncio.to_thread(get_event, self.user_id, params["event_id"])
        return _fmt_event(result)

    async def _create_event(self, params: dict) -> str:
        result = await asyncio.to_thread(
            create_event,
            self.user_id,
            params["title"],
            params["start"],
            params["end"],
            params.get("attendees", []),
            params.get("description", ""),
        )
        return f"Calendar event created. Event ID: {result['id']}. Link: {result.get('link', 'N/A')}"

    async def _update_event(self, params: dict) -> str:
        event_id = params.pop("event_id")
        result = await asyncio.to_thread(update_event, self.user_id, event_id, **params)
        return f"Calendar event updated. Event ID: {result['id']}"

    async def _decline_event(self, params: dict) -> str:
        result = await asyncio.to_thread(
            decline_event,
            self.user_id,
            params["event_id"],
            params.get("message", None),
        )
        return f"Event declined. Event ID: {result['id']}"
