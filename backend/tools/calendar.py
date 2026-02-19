"""Calendar tools — read, create, decline, and update events."""
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from tools.google_auth import GoogleAuthManager
from config import GOOGLE_CALENDAR_ID

auth_manager = GoogleAuthManager()


def _service(user_id: str):
    creds = auth_manager.get_credentials(user_id)
    return build("calendar", "v3", credentials=creds)


def list_events(user_id: str, days_ahead: int = 7) -> list[dict]:
    """Returns upcoming events for the next N days: id, title, start, end, attendees."""
    try:
        service = _service(user_id)
        now = datetime.now(timezone.utc).isoformat()
        end = (datetime.now(timezone.utc) + timedelta(days=days_ahead)).isoformat()
        result = service.events().list(
            calendarId=GOOGLE_CALENDAR_ID,
            timeMin=now,
            timeMax=end,
            singleEvents=True,
            orderBy="startTime",
        ).execute()

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
    except HttpError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


def get_event(user_id: str, event_id: str) -> dict:
    """Returns full event details including organizer and description."""
    try:
        service = _service(user_id)
        e = service.events().get(calendarId=GOOGLE_CALENDAR_ID, eventId=event_id).execute()
        return {
            "id": e["id"],
            "title": e.get("summary", ""),
            "description": e.get("description", ""),
            "start": e["start"].get("dateTime", e["start"].get("date")),
            "end": e["end"].get("dateTime", e["end"].get("date")),
            "organizer": e.get("organizer", {}).get("email", ""),
            "attendees": [a["email"] for a in e.get("attendees", [])],
        }
    except HttpError as e:
        if e.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Event {event_id} not found.")
        raise HTTPException(status_code=e.status_code, detail=str(e))


def create_event(user_id: str, title: str, start: str, end: str,
                 attendees: list[str] = None, description: str = "") -> dict:
    """Creates a calendar event. start and end accept ISO 8601 strings."""
    try:
        service = _service(user_id)
        body = {
            "summary": title,
            "description": description,
            "start": {"dateTime": datetime.fromisoformat(start).isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": datetime.fromisoformat(end).isoformat(), "timeZone": "UTC"},
            "attendees": [{"email": a} for a in (attendees or [])],
        }
        e = service.events().insert(calendarId=GOOGLE_CALENDAR_ID, body=body,
                                    sendUpdates="all").execute()
        return {"id": e["id"], "status": "created", "link": e.get("htmlLink", "")}
    except HttpError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


def decline_event(user_id: str, event_id: str, message: str = None) -> dict:
    """Declines a calendar event and notifies the organizer."""
    try:
        service = _service(user_id)
        # Get current user's email to identify their attendee entry
        profile = service.calendars().get(calendarId="primary").execute()
        user_email = profile["id"]

        e = service.events().get(calendarId=GOOGLE_CALENDAR_ID, eventId=event_id).execute()
        attendees = e.get("attendees", [])
        for a in attendees:
            if a["email"] == user_email:
                a["responseStatus"] = "declined"
                if message:
                    a["comment"] = message

        updated = service.events().patch(
            calendarId=GOOGLE_CALENDAR_ID,
            eventId=event_id,
            body={"attendees": attendees},
            sendUpdates="all",
        ).execute()
        return {"id": updated["id"], "status": "declined"}
    except HttpError as e:
        if e.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Event {event_id} not found.")
        raise HTTPException(status_code=e.status_code, detail=str(e))


def update_event(user_id: str, event_id: str, **kwargs) -> dict:
    """Updates fields on an existing event. Accepts title, start, end, description, attendees."""
    try:
        service = _service(user_id)
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

        updated = service.events().patch(
            calendarId=GOOGLE_CALENDAR_ID,
            eventId=event_id,
            body=body,
            sendUpdates="all",
        ).execute()
        return {"id": updated["id"], "status": "updated"}
    except HttpError as e:
        if e.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Event {event_id} not found.")
        raise HTTPException(status_code=e.status_code, detail=str(e))
