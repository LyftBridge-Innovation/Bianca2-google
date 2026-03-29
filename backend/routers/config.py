"""Config router — knowledge base, values, identity, education, and system prompt."""

import json
import re
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from values import BIANCA_VALUES
from prompts import get_system_prompt
from settings_loader import load_settings, _DEFAULT_SETTINGS, _SETTINGS_PATH

router = APIRouter(prefix="/config", tags=["config"])

_KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"
_VALUES_OVERRIDE_PATH = _KNOWLEDGE_DIR / "values_override.json"
_EDUCATION_PATH = _KNOWLEDGE_DIR / "education.json"

_KNOWLEDGE_SECTIONS = [
    ("01_persona", "Persona & Identity"),
    ("02_education", "Training Background"),
    ("03_expertise", "Domain Expertise"),
    ("04_company", "Product & Mission"),
]
_VALID_CATEGORIES = {d for d, _ in _KNOWLEDGE_SECTIONS}


def _save_settings(settings: dict[str, Any]) -> None:
    _SETTINGS_PATH.write_text(
        json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8"
    )


# ── Models ────────────────────────────────────────────────────────────────────

class KnowledgeSaveRequest(BaseModel):
    content: str


class ValueItem(BaseModel):
    priority: int
    title: str
    rule: str


class SaveValuesRequest(BaseModel):
    values: list[ValueItem]


class SettingsUpdate(BaseModel):
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
    degrees: list[DegreeItem]
    courses: list[CourseItem]


class PhoneNumberRequest(BaseModel):
    user_id: str
    phone_number: str


# ── Knowledge endpoints ───────────────────────────────────────────────────────

@router.get("/knowledge")
def get_knowledge():
    """Return all knowledge categories with their file contents."""
    sections = []
    for category, label in _KNOWLEDGE_SECTIONS:
        dir_path = _KNOWLEDGE_DIR / category
        files = []
        if dir_path.exists():
            for file_path in sorted(dir_path.iterdir()):
                if file_path.is_file():
                    files.append({
                        "filename": file_path.name,
                        "content": file_path.read_text(encoding="utf-8"),
                    })
        sections.append({"category": category, "label": label, "files": files})
    return {"sections": sections}


@router.put("/knowledge/{category}/{filename}")
def save_knowledge_file(category: str, filename: str, body: KnowledgeSaveRequest):
    """Overwrite an existing knowledge file with new content."""
    if category not in _VALID_CATEGORIES:
        raise HTTPException(status_code=400, detail="Invalid category")
    if ".." in filename or "/" in filename or not re.match(r"^[\w\-. ]+$", filename):
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path = _KNOWLEDGE_DIR / category / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    file_path.write_text(body.content, encoding="utf-8")
    return {"ok": True}


# ── Values endpoints ──────────────────────────────────────────────────────────

@router.get("/values")
def get_values():
    """Return the current values list (override if present, else defaults)."""
    if _VALUES_OVERRIDE_PATH.exists():
        try:
            data = json.loads(_VALUES_OVERRIDE_PATH.read_text(encoding="utf-8"))
            return {"values": data, "source": "override"}
        except Exception:
            pass
    return {"values": BIANCA_VALUES, "source": "default"}


@router.put("/values")
def save_values(body: SaveValuesRequest):
    """Persist an updated values list to the override file."""
    if not body.values:
        raise HTTPException(status_code=400, detail="Values list cannot be empty")

    sorted_values = sorted(
        [v.model_dump() for v in body.values], key=lambda v: v["priority"]
    )
    _VALUES_OVERRIDE_PATH.write_text(
        json.dumps(sorted_values, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return {"ok": True}


# ── Settings endpoints (identity, model, integrations) ───────────────────────

@router.get("/settings")
def get_settings():
    """Return all config settings (identity, model, integrations)."""
    return {"settings": load_settings()}


@router.put("/settings")
def update_settings(body: SettingsUpdate):
    """Merge partial settings update into the persisted config."""
    allowed_keys = set(_DEFAULT_SETTINGS.keys())
    invalid = set(body.settings.keys()) - allowed_keys
    if invalid:
        raise HTTPException(status_code=400, detail=f"Unknown keys: {invalid}")

    current = load_settings()
    current.update(body.settings)
    _save_settings(current)
    return {"ok": True, "settings": current}


# ── Education endpoints (degrees + courses) ──────────────────────────────────

def _load_education() -> dict:
    """Load education data from JSON file."""
    if _EDUCATION_PATH.exists():
        try:
            return json.loads(_EDUCATION_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"degrees": [], "courses": []}


def _save_education(data: dict) -> None:
    """Save education data to JSON file."""
    _EDUCATION_PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


@router.get("/education")
def get_education():
    """Return the current education data (degrees and courses)."""
    return _load_education()


@router.put("/education")
def save_education(body: EducationData):
    """Save updated education data (degrees and courses)."""
    data = {
        "degrees": [d.model_dump() for d in body.degrees],
        "courses": [c.model_dump() for c in body.courses],
    }
    _save_education(data)
    return {"ok": True}


# ── Phone number registration ────────────────────────────────────────────────

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


# ── System prompt preview ────────────────────────────────────────────────────

@router.get("/system-prompt")
def get_system_prompt_preview():
    """Return the fully assembled system prompt for preview."""
    prompt = get_system_prompt()
    return {"prompt": prompt, "length": len(prompt)}
