"""Calendar tools — read, create, decline, and update events via gws CLI.

Function signatures are identical to the original google-api-python-client
implementation so langchain_tools.py and voice_pipeline/tool_dispatcher.py
work without any changes.
"""
import json
import logging
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
from tools.gws_client import execute, GWSError
from token_manager import get_access_token

logger = logging.getLogger(__name__)

# Calendar ID — matches the old config.GOOGLE_CALENDAR_ID default
CALENDAR_ID = "primary"


def list_events(user_id: str, days_ahead: int = 7) -> list[dict]:
    """Returns upcoming events for the next N days: id, title, start, end, attendees."""
    try:
        token = get_access_token(user_id)
        now = datetime.now(timezone.utc).isoformat()
        # Use end-of-day (23:59:59 UTC) so full calendar days are covered,
        # avoiding missed events due to rolling-window timezone edge cases.
        end_dt = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=days_ahead + 1)
        end = end_dt.isoformat()

        result = execute([
            "calendar", "events", "list",
            "--params", json.dumps({
                "calendarId": CALENDAR_ID,
                "timeMin": now,
                "timeMax": end,
                "singleEvents": True,
                "orderBy": "startTime",
            }),
        ], access_token=token)

        events = []
        for e in result.get("items", []):
            events.append({
                "id": e["id"],
                "title": e.get("summary", ""),
                "start": e["start"].get("dateTime", e["start"].get("date")),
                "end": e["end"].get("dateTime", e["end"].get("date")),
                "attendees": [a["email"] for a in e.get("attendees", [])],
            })
        return events
    except GWSError as e:
        logger.error("list_events failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


def get_event(user_id: str, event_id: str) -> dict:
    """Returns full event details including organizer and description."""
    try:
        token = get_access_token(user_id)
        e = execute([
            "calendar", "events", "get",
            "--params", json.dumps({
                "calendarId": CALENDAR_ID,
                "eventId": event_id,
            }),
        ], access_token=token)
        return {
            "id": e["id"],
            "title": e.get("summary", ""),
            "description": e.get("description", ""),
            "start": e["start"].get("dateTime", e["start"].get("date")),
            "end": e["end"].get("dateTime", e["end"].get("date")),
            "organizer": e.get("organizer", {}).get("email", ""),
            "attendees": [a["email"] for a in e.get("attendees", [])],
        }
    except GWSError as e:
        logger.error("get_event failed: %s", e)
        status = 404 if "not found" in str(e).lower() else 500
        raise HTTPException(status_code=status, detail=str(e))


def create_event(user_id: str, title: str, start: str, end: str,
                 attendees: list[str] = None, description: str = "") -> dict:
    """Creates a calendar event. start and end accept ISO 8601 strings."""
    try:
        token = get_access_token(user_id)
        event_body = {
            "summary": title,
            "description": description,
            "start": {"dateTime": datetime.fromisoformat(start).isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": datetime.fromisoformat(end).isoformat(), "timeZone": "UTC"},
            "attendees": [{"email": a} for a in (attendees or [])],
        }

        e = execute([
            "calendar", "events", "insert",
            "--params", json.dumps({"calendarId": CALENDAR_ID, "sendUpdates": "all"}),
            "--json", json.dumps(event_body),
        ], access_token=token)
        return {"id": e["id"], "status": "created", "link": e.get("htmlLink", "")}
    except GWSError as e:
        logger.error("create_event failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


def decline_event(user_id: str, event_id: str, message: str = None) -> dict:
    """Declines a calendar event and notifies the organizer."""
    try:
        token = get_access_token(user_id)
        # Get current user's email
        profile = execute([
            "calendar", "calendars", "get",
            "--params", json.dumps({"calendarId": "primary"}),
        ], access_token=token)
        user_email = profile["id"]

        # Get the event
        e = execute([
            "calendar", "events", "get",
            "--params", json.dumps({"calendarId": CALENDAR_ID, "eventId": event_id}),
        ], access_token=token)

        attendees = e.get("attendees", [])
        for a in attendees:
            if a["email"] == user_email:
                a["responseStatus"] = "declined"
                if message:
                    a["comment"] = message

        updated = execute([
            "calendar", "events", "patch",
            "--params", json.dumps({
                "calendarId": CALENDAR_ID,
                "eventId": event_id,
                "sendUpdates": "all",
            }),
            "--json", json.dumps({"attendees": attendees}),
        ], access_token=token)
        return {"id": updated["id"], "status": "declined"}
    except GWSError as e:
        logger.error("decline_event failed: %s", e)
        status = 404 if "not found" in str(e).lower() else 500
        raise HTTPException(status_code=status, detail=str(e))


def update_event(user_id: str, event_id: str, **kwargs) -> dict:
    """Updates fields on an existing event. Accepts title, start, end, description, attendees."""
    try:
        token = get_access_token(user_id)
        body = {}
        if "title" in kwargs:
            body["summary"] = kwargs["title"]
        if "description" in kwargs:
            body["description"] = kwargs["description"]
        if "start" in kwargs:
            body["start"] = {"dateTime": datetime.fromisoformat(kwargs["start"]).isoformat(), "timeZone": "UTC"}
        if "end" in kwargs:
            body["end"] = {"dateTime": datetime.fromisoformat(kwargs["end"]).isoformat(), "timeZone": "UTC"}
        if "attendees" in kwargs:
            body["attendees"] = [{"email": a} for a in kwargs["attendees"]]

        updated = execute([
            "calendar", "events", "patch",
            "--params", json.dumps({
                "calendarId": CALENDAR_ID,
                "eventId": event_id,
                "sendUpdates": "all",
            }),
            "--json", json.dumps(body),
        ], access_token=token)
        return {"id": updated["id"], "status": "updated"}
    except GWSError as e:
        logger.error("update_event failed: %s", e)
        status = 404 if "not found" in str(e).lower() else 500
        raise HTTPException(status_code=status, detail=str(e))
