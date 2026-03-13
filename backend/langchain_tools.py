"""LangChain tool wrappers for Gmail and Calendar functions."""
from langchain.tools import tool
from tools import gmail, calendar
from request_context import current_user_id


# ── Gmail Tools ───────────────────────────────────────────────────────────────

@tool
def list_recent_emails(max_results: int = 10):
    """List recent emails from the user's inbox. Returns email IDs, subjects, senders, dates, and snippets."""
    user_id = current_user_id.get()
    return gmail.list_emails(user_id, max_results)


@tool
def get_email_by_id(email_id: str):
    """Get the full content of a specific email by its ID. Returns subject, sender, recipient, date, and full body."""
    user_id = current_user_id.get()
    return gmail.get_email(user_id, email_id)


@tool
def draft_email_message(to: str, subject: str, body: str):
    """Create a draft email without sending it. Use this as the default action. Only use send_email after explicit user confirmation."""
    user_id = current_user_id.get()
    return gmail.draft_email(user_id, to, subject, body)


@tool
def send_email_message(to: str, subject: str, body: str):
    """Send an email immediately. ONLY use this after explicit user confirmation. Default to draft_email_message first."""
    user_id = current_user_id.get()
    return gmail.send_email(user_id, to, subject, body)


# ── Calendar Tools ────────────────────────────────────────────────────────────

@tool
def list_upcoming_events(days_ahead: int = 7):
    """List upcoming calendar events for the next N days. Returns event IDs, titles, start/end times, and attendees."""
    user_id = current_user_id.get()
    return calendar.list_events(user_id, days_ahead)


@tool
def get_event_details(event_id: str):
    """Get full details of a specific calendar event by its ID. Returns title, description, time, organizer, and attendees."""
    user_id = current_user_id.get()
    return calendar.get_event(user_id, event_id)


@tool
def create_calendar_event(title: str, start: str, end: str, attendees: list[str] = None, description: str = ""):
    """Create a new calendar event. Times must be in ISO 8601 format (e.g., '2026-02-20T10:00:00'). Attendees is a list of email addresses."""
    user_id = current_user_id.get()
    return calendar.create_event(user_id, title, start, end, attendees or [], description)


@tool
def decline_calendar_event(event_id: str, message: str = None):
    """Decline a calendar event and optionally send a message to the organizer."""
    user_id = current_user_id.get()
    return calendar.decline_event(user_id, event_id, message)


@tool
def update_calendar_event(event_id: str, title: str = None, start: str = None, end: str = None,
                         description: str = None, attendees: list[str] = None):
    """Update an existing calendar event. Only provide the fields you want to change."""
    user_id = current_user_id.get()
    kwargs = {}
    if title is not None:
        kwargs["title"] = title
    if start is not None:
        kwargs["start"] = start
    if end is not None:
        kwargs["end"] = end
    if description is not None:
        kwargs["description"] = description
    if attendees is not None:
        kwargs["attendees"] = attendees
    return calendar.update_event(user_id, event_id, **kwargs)


# All tools list for LangChain agent
ALL_TOOLS = [
    list_recent_emails,
    get_email_by_id,
    draft_email_message,
    send_email_message,
    list_upcoming_events,
    get_event_details,
    create_calendar_event,
    decline_calendar_event,
    update_calendar_event,
]
