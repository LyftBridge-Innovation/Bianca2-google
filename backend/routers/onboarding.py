"""Onboarding router — tracks new-user setup wizard progress."""

import json
import os
import re

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Any, Optional

from google import genai as _genai
import anthropic as _anthropic

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


# ── AI-guided onboarding chat ─────────────────────────────────────────────────

_ONBOARDING_SYSTEM_PROMPT = """
You are a friendly, concise AI assistant helping a user set up their personal AI agent on the Bianca platform.
Your job is to gather configuration information through natural, conversational questions — one topic at a time.

NOTE: The user has already provided their API key before starting this chat. Do NOT ask for an API key.

CONVERSATION FLOW (follow this order strictly):
1. Greet the user warmly and ask for the agent's name (e.g. "What would you like to name your AI agent?")
2. Ask for the agent's role/title (e.g. "What role should [name] play? e.g. AI Chief of Staff, Executive Assistant")
3. Ask for the primary language (offer English as default, mention a few other options)
4. Ask which AI model to use — present these five options clearly:
   a) Claude Sonnet 4.6 (Anthropic) — best balance of speed and intelligence
   b) Claude Opus 4.7 (Anthropic) — latest Opus, most powerful
   c) Claude Opus 4.6 (Anthropic) — most powerful, deepest reasoning
   d) Gemini 2.5 Flash (Google) — fast and cost-efficient
   e) Gemini 2.5 Pro (Google) — most capable Gemini model
   Map the user's choice to exactly one of these IDs: claude-sonnet-4-6, claude-opus-4-7, claude-opus-4-6, gemini-2.5-flash, gemini-2.5-pro
5. Ask the user to describe the agent's persona and personality in a few sentences (required)
6. Ask about domain expertise (optional — user can say "skip")
7. Ask about company/product context (optional — user can say "skip")
8. Ask about behavioral values — show the 5 defaults and ask if they want to keep them or customise:
   1. Draft Before Send — Never send an email without explicit confirmation. Always draft first.
   2. Confirm Before Irreversible Actions — Always confirm before taking actions that cannot be undone.
   3. Time Is the Scarcest Resource — Be concise. Do not repeat yourself. Move fast, act with confidence.
   4. One Clarifying Question at a Time — If something is ambiguous, ask one sharp question — not several.
   5. Close the Loop — After completing any action, confirm what was done in one clear sentence.
   If the user says keep defaults or similar, use those. If they describe custom values, parse them.
9. Once all required fields are collected (name, model, persona), tell the user everything is ready and their agent is about to launch.

RULES:
- Ask ONE topic per message. Keep replies short and friendly.
- Never use emojis. Use plain text and markdown only.
- Use markdown formatting where helpful (bold for options, bullet lists for choices).
- Never ask for information already provided in the conversation.
- For optional fields (expertise, company), make it clear the user can say "skip".
- Do not show the FIELDS block to the user — it is hidden metadata.

At the END of EVERY reply (including the very first greeting), append this exact block on a new line:
<!-- FIELDS: {"ai_name":"","ai_role":"","primary_language":"","model":"","persona":"","expertise":"","company":"","values":null,"is_complete":false} -->

Replace empty strings with values you have collected so far. Set is_complete to true ONLY when you have:
- ai_name (non-empty)
- model (one of the four IDs above)
- persona (non-empty)

Keep previously collected values in the JSON — never blank them out once set.
""".strip()

_REQUIRED_FIELDS = {"ai_name", "model", "persona"}
_VALID_MODELS = {"claude-sonnet-4-6", "claude-opus-4-7", "claude-opus-4-6", "gemini-2.5-flash", "gemini-2.5-pro"}
_FIELDS_RE = re.compile(r"<!--\s*FIELDS:\s*(\{.*?\})\s*-->", re.DOTALL)


def _extract_fields(text: str) -> dict:
    match = _FIELDS_RE.search(text)
    if not match:
        return {}
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return {}


def _strip_fields_block(text: str) -> str:
    return _FIELDS_RE.sub("", text).strip()


def _is_complete(fields: dict) -> bool:
    for f in _REQUIRED_FIELDS:
        if not fields.get(f, "").strip():
            return False
    if fields.get("model", "") not in _VALID_MODELS:
        return False
    return True


def _provider_from_key(api_key: str) -> str:
    """Detect provider from key prefix: sk-ant-* → anthropic, else → google."""
    return "anthropic" if api_key.strip().startswith("sk-ant-") or api_key.strip().startswith("sk-") else "google"


def _call_gemini(api_key: str, history: list, message: str) -> str:
    client = _genai.Client(api_key=api_key)
    contents = []
    for msg in history:
        role = "user" if msg.role == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg.text}]})
    contents.append({"role": "user", "parts": [{"text": message}]})
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
        config=_genai.types.GenerateContentConfig(
            system_instruction=_ONBOARDING_SYSTEM_PROMPT,
            temperature=0.7,
        ),
    )
    return response.text or ""


def _call_anthropic(api_key: str, history: list, message: str) -> str:
    client = _anthropic.Anthropic(api_key=api_key)
    messages = []
    for msg in history:
        role = "user" if msg.role == "user" else "assistant"
        messages.append({"role": role, "content": msg.text})
    messages.append({"role": "user", "content": message})
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=_ONBOARDING_SYSTEM_PROMPT,
        messages=messages,
    )
    return response.content[0].text if response.content else ""


class OnboardingChatMessage(BaseModel):
    role: str   # "user" or "model"
    text: str


class OnboardingChatRequest(BaseModel):
    user_id: str
    message: str
    api_key: str          # BYOK — user's own Gemini or Anthropic key
    history: list[OnboardingChatMessage] = []


@router.post("/chat")
def onboarding_chat(body: OnboardingChatRequest):
    """
    Stateless AI-guided onboarding chat — BYOK.
    Uses the user's own API key (Gemini or Anthropic, auto-detected from key prefix).
    Returns: { reply, extracted, is_complete, provider }
    """
    key = body.api_key.strip()
    if not key:
        raise HTTPException(status_code=400, detail="api_key is required.")

    provider = _provider_from_key(key)

    try:
        if provider == "anthropic":
            raw_reply = _call_anthropic(key, body.history, body.message)
        else:
            raw_reply = _call_gemini(key, body.history, body.message)
    except Exception as exc:
        err = str(exc)
        if any(x in err for x in ("401", "403", "invalid_api_key", "PERMISSION_DENIED", "authentication_error", "leaked")):
            raise HTTPException(status_code=401, detail="Invalid or revoked API key. Please check your key and try again.")
        raise HTTPException(status_code=503, detail=f"AI service error: {err[:240]}")

    extracted = _extract_fields(raw_reply)
    clean_reply = _strip_fields_block(raw_reply)
    complete = extracted.get("is_complete", False) or _is_complete(extracted)

    return {
        "reply": clean_reply,
        "extracted": extracted,
        "is_complete": complete,
        "provider": provider,
    }
