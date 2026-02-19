"""
Temporary test endpoints for Phase 1 manual testing via curl/Postman.
Remove or gate behind a DEV flag before Phase 2 goes to production.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from config import TEST_USER_ID
from tools import gmail, calendar

router = APIRouter(prefix="/test", tags=["test"])


# ── Gmail ─────────────────────────────────────────────────────────────────────

@router.get("/gmail/list")
def test_list_emails():
    return gmail.list_emails(TEST_USER_ID)


@router.get("/gmail/{email_id}")
def test_get_email(email_id: str):
    return gmail.get_email(TEST_USER_ID, email_id)


class EmailBody(BaseModel):
    to: str
    subject: str
    body: str


@router.post("/gmail/send")
def test_send_email(payload: EmailBody):
    return gmail.send_email(TEST_USER_ID, payload.to, payload.subject, payload.body)


@router.post("/gmail/draft")
def test_draft_email(payload: EmailBody):
    return gmail.draft_email(TEST_USER_ID, payload.to, payload.subject, payload.body)


# ── Calendar ──────────────────────────────────────────────────────────────────

@router.get("/calendar/list")
def test_list_events():
    return calendar.list_events(TEST_USER_ID)


@router.get("/calendar/{event_id}")
def test_get_event(event_id: str):
    return calendar.get_event(TEST_USER_ID, event_id)


class CreateEventBody(BaseModel):
    title: str
    start: str
    end: str
    attendees: list[str] = []
    description: str = ""


@router.post("/calendar/create")
def test_create_event(payload: CreateEventBody):
    return calendar.create_event(
        TEST_USER_ID, payload.title, payload.start, payload.end,
        payload.attendees, payload.description
    )


class DeclineBody(BaseModel):
    message: str = None


@router.post("/calendar/decline/{event_id}")
def test_decline_event(event_id: str, payload: DeclineBody = None):
    msg = payload.message if payload else None
    return calendar.decline_event(TEST_USER_ID, event_id, msg)
