"""Config router — per-user agent settings, knowledge, values, education, resume."""

import os
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from models import AgentSettings, FirestoreCollections
from prompts import get_system_prompt
from values import BIANCA_VALUES

router = APIRouter(prefix="/config", tags=["config"])

_fs = FirestoreCollections()

_VALID_KNOWLEDGE_SECTIONS = {"persona", "education_text", "expertise", "company"}
_SECTION_LABELS = {
    "persona": "Persona & Identity",
    "education_text": "Training Background",
    "expertise": "Domain Expertise",
    "company": "Product & Mission",
}

# ── Request / Response models ─────────────────────────────────────────────────

class KnowledgeSaveRequest(BaseModel):
    user_id: str
    content: str


class ValueItem(BaseModel):
    priority: int
    title: str
    rule: str


class SaveValuesRequest(BaseModel):
    user_id: str
    values: list[ValueItem]


class SettingsUpdate(BaseModel):
    user_id: str
    settings: dict[str, Any]


class DegreeItem(BaseModel):
    name: str
    level: str
    institution: str
    field: str


class CourseItem(BaseModel):
    code: str
    name: str
    description: Optional[str] = ""


class EducationData(BaseModel):
    user_id: str
    degrees: list[DegreeItem]
    courses: list[CourseItem]


class PhoneNumberRequest(BaseModel):
    user_id: str
    phone_number: str


class ExperienceItem(BaseModel):
    title: str
    organization: str
    startDate: str
    endDate: str = ""
    description: str = ""


class ResumeData(BaseModel):
    user_id: str
    experience: list[ExperienceItem]


# ── Knowledge endpoints ───────────────────────────────────────────────────────

@router.get("/knowledge")
def get_knowledge(user_id: str = Query(...)):
    """Return all knowledge sections for the given user from Firestore."""
    sections = []
    for section_id, label in _SECTION_LABELS.items():
        content = _fs.get_user_knowledge_section(user_id, section_id)
        sections.append({"section_id": section_id, "label": label, "content": content})
    return {"sections": sections}


@router.put("/knowledge/{section_id}")
def save_knowledge_section(section_id: str, body: KnowledgeSaveRequest):
    """Write a knowledge section for the given user to Firestore."""
    if section_id not in _VALID_KNOWLEDGE_SECTIONS:
        raise HTTPException(status_code=400, detail=f"Invalid section_id. Must be one of: {sorted(_VALID_KNOWLEDGE_SECTIONS)}")
    _fs.save_user_knowledge_section(body.user_id, section_id, body.content)
    return {"ok": True}


# ── Values endpoints ──────────────────────────────────────────────────────────

@router.get("/values")
def get_values(user_id: str = Query(...)):
    """Return the values list for the given user (custom or defaults)."""
    values = _fs.get_user_values(user_id)
    if values:
        return {"values": values, "source": "user"}
    return {"values": BIANCA_VALUES, "source": "default"}


@router.put("/values")
def save_values(body: SaveValuesRequest):
    """Persist an updated values list for the given user to Firestore."""
    if not body.values:
        raise HTTPException(status_code=400, detail="Values list cannot be empty")
    sorted_values = sorted(
        [v.model_dump() for v in body.values], key=lambda v: v["priority"]
    )
    _fs.save_user_values(body.user_id, sorted_values)
    return {"ok": True}


# ── Settings endpoints ────────────────────────────────────────────────────────

_ALLOWED_SETTING_KEYS = set(AgentSettings.model_fields.keys())


@router.get("/settings")
def get_settings(user_id: str = Query(...)):
    """Return all agent settings for the given user from Firestore."""
    user = _fs.get_user(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    return {"settings": user.agent_settings.model_dump()}


@router.put("/settings")
def update_settings(body: SettingsUpdate):
    """Merge a partial settings update for the given user into Firestore."""
    invalid = set(body.settings.keys()) - _ALLOWED_SETTING_KEYS
    if invalid:
        raise HTTPException(status_code=400, detail=f"Unknown setting keys: {sorted(invalid)}")

    user = _fs.get_user(body.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=f"User {body.user_id} not found")

    # Merge the incoming partial update onto the existing settings
    merged = user.agent_settings.model_dump()
    merged.update(body.settings)
    updated_settings = AgentSettings(**merged)

    _fs.save_user_agent_settings(body.user_id, updated_settings)
    return {"ok": True, "settings": updated_settings.model_dump()}


# ── Education endpoints ───────────────────────────────────────────────────────

@router.get("/education")
def get_education(user_id: str = Query(...)):
    """Return structured education data for the given user from Firestore."""
    return _fs.get_user_education(user_id)


@router.put("/education")
def save_education(body: EducationData):
    """Save structured education data for the given user to Firestore."""
    data = {
        "degrees": [d.model_dump() for d in body.degrees],
        "courses": [c.model_dump() for c in body.courses],
    }
    _fs.save_user_education(body.user_id, data)
    return {"ok": True}


# ── Resume endpoints ──────────────────────────────────────────────────────────

@router.get("/resume")
def get_resume(user_id: str = Query(...)):
    """Return resume / work experience data for the given user from Firestore."""
    return _fs.get_user_resume(user_id)


@router.put("/resume")
def save_resume(body: ResumeData):
    """Save resume data for the given user to Firestore."""
    data = {"experience": [e.model_dump() for e in body.experience]}
    _fs.save_user_resume(body.user_id, data)
    return {"ok": True}


# ── Phone number ──────────────────────────────────────────────────────────────

@router.get("/phone")
def get_phone_number(user_id: str = Query(...)):
    """Return the phone number registered for the given user."""
    try:
        from firestore_client import get_firestore_client
        db = get_firestore_client()
        doc = db.collection("users").document(user_id).get()
        if doc.exists:
            return {"phone_number": doc.to_dict().get("phone_number", "")}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"phone_number": ""}


@router.post("/phone")
def save_phone_number(body: PhoneNumberRequest):
    """Save (or clear) the phone number for a user in Firestore."""
    try:
        from firestore_client import get_firestore_client
        db = get_firestore_client()
        db.collection("users").document(body.user_id).set(
            {"phone_number": body.phone_number.strip()},
            merge=True,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"ok": True}


# ── Security / API key status ─────────────────────────────────────────────────

@router.get("/security-status")
def get_security_status(user_id: str = Query(...)):
    """
    Return boolean presence flags for configured API keys.

    BYOK: reflects the user's own stored keys only — no env var fallback.
    Values are never returned — only whether each key is set.
    """
    user = _fs.get_user(user_id)
    s = user.agent_settings if user else AgentSettings()
    return {
        "google_api_key": bool(s.google_api_key.strip()),
        "anthropic_api_key": bool(s.anthropic_api_key.strip()),
        "perplexity_api_key": bool(s.perplexity_api_key.strip()),
        "google_workspace_token": bool(os.getenv("GOOGLE_WORKSPACE_CLI_TOKEN", "")),
        "twilio": bool(
            os.getenv("TWILIO_ACCOUNT_SID", "")
            and os.getenv("TWILIO_AUTH_TOKEN", "")
        ),
    }


# ── System prompt preview ─────────────────────────────────────────────────────

@router.get("/system-prompt")
def get_system_prompt_preview(user_id: str = Query(...)):
    """Return the fully assembled system prompt for a user (preview only)."""
    prompt = get_system_prompt(user_id=user_id)
    return {"prompt": prompt, "length": len(prompt)}
