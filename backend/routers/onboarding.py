"""Onboarding router — tracks new-user setup wizard progress."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Any, Optional

from models import AgentSettings, FirestoreCollections
from values import BIANCA_VALUES

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

_fs = FirestoreCollections()


# ── Request models ────────────────────────────────────────────────────────────

class StepUpdateRequest(BaseModel):
    user_id: str
    step: int  # 1–4


class OnboardingCompleteRequest(BaseModel):
    user_id: str
    # Step 1: identity
    ai_name: str
    ai_role: str
    primary_language: str
    model: str
    # Step 2: API key (at least one required)
    anthropic_api_key: str = ""
    google_api_key: str = ""
    # Step 3: persona / knowledge
    persona: str = ""
    expertise: str = ""
    company: str = ""
    # Step 4: values (optional — falls back to defaults)
    values: Optional[list[dict[str, Any]]] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/state")
def get_onboarding_state(user_id: str = Query(...)):
    """Return the current onboarding state for a user."""
    user = _fs.get_user(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    return {
        "completed": user.onboarding_completed,
        "step": user.onboarding_step,
    }


@router.post("/step")
def update_onboarding_step(body: StepUpdateRequest):
    """Update the current onboarding step (progress tracking)."""
    if not 1 <= body.step <= 4:
        raise HTTPException(status_code=400, detail="step must be between 1 and 4")
    user = _fs.get_user(body.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=f"User {body.user_id} not found")
    _fs.update_onboarding_state(body.user_id, step=body.step, completed=False)
    return {"ok": True, "step": body.step}


@router.post("/complete")
def complete_onboarding(body: OnboardingCompleteRequest):
    """
    Save all onboarding data and mark the user's onboarding as complete.

    Writes:
      - agent_settings (identity + BYOK API keys)
      - knowledge sections (persona, expertise, company)
      - values (custom or defaults)
      - onboarding_completed = True, onboarding_step = 5
    """
    if not body.anthropic_api_key.strip() and not body.google_api_key.strip():
        raise HTTPException(
            status_code=400,
            detail="At least one API key is required (Anthropic or Google).",
        )

    user = _fs.get_user(body.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=f"User {body.user_id} not found")

    # Build agent settings from step 1 + 2 data
    # Preserve any existing settings (e.g. temperature, template IDs) and overlay
    merged = user.agent_settings.model_dump()
    merged.update({
        "ai_name": body.ai_name.strip() or "Bianca",
        "ai_role": body.ai_role.strip() or "AI Chief of Staff",
        "primary_language": body.primary_language or "English",
        "model": body.model or "claude-sonnet-4-6",
        "anthropic_api_key": body.anthropic_api_key.strip(),
        "google_api_key": body.google_api_key.strip(),
    })
    _fs.save_user_agent_settings(body.user_id, AgentSettings(**merged))

    # Save knowledge sections (only non-empty values)
    if body.persona.strip():
        _fs.save_user_knowledge_section(body.user_id, "persona", body.persona.strip())
    if body.expertise.strip():
        _fs.save_user_knowledge_section(body.user_id, "expertise", body.expertise.strip())
    if body.company.strip():
        _fs.save_user_knowledge_section(body.user_id, "company", body.company.strip())

    # Save values (custom list or BIANCA_VALUES defaults)
    values_to_save = body.values if body.values else BIANCA_VALUES
    _fs.save_user_values(body.user_id, values_to_save)

    # Mark onboarding complete
    _fs.update_onboarding_state(body.user_id, step=5, completed=True)

    return {"ok": True, "message": "Onboarding complete"}
