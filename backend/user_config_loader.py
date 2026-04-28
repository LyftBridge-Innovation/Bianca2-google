"""
Per-user config loader — reads agent settings, knowledge, and values from
Firestore.

Design principles:
- All config is keyed by user_id.  There is no global fallback for API keys
  (strict BYOK — the user must supply their own keys).
- Knowledge and values default to empty / hardcoded defaults when a user has
  not configured them yet (safe for new accounts before onboarding is done).
- This module is intentionally separate from the legacy disk-based loaders
  (settings_loader.py, knowledge_loader.py, values.py) so Phase 1 introduces
  no breaking changes.  Phase 2 will swap the prompt assembly to call these
  functions instead of the disk ones.
"""

import logging
from typing import Any

from models import AgentSettings, FirestoreCollections
from values import BIANCA_VALUES

logger = logging.getLogger(__name__)

_fs: FirestoreCollections | None = None


def _get_fs() -> FirestoreCollections:
    global _fs
    if _fs is None:
        _fs = FirestoreCollections()
    return _fs


# ── Settings ──────────────────────────────────────────────────────────────────

def load_user_settings(user_id: str) -> dict[str, Any]:
    """
    Return the agent settings for a user as a plain dict.

    If the user document has no agent_settings yet (e.g. new account before
    onboarding) this returns the AgentSettings defaults.  API keys will be
    empty strings — the caller must handle missing keys.
    """
    user = _get_fs().get_user(user_id)
    if user is not None:
        return user.agent_settings.model_dump()
    logger.warning("[UserConfigLoader] user %s not found — using default settings", user_id)
    return AgentSettings().model_dump()


# ── Knowledge block ───────────────────────────────────────────────────────────

_TEXT_SECTIONS = [
    ("persona",        "Persona & Identity"),
    ("education_text", "Training Background"),
    ("expertise",      "Domain Expertise"),
    ("company",        "Product & Mission"),
]


def build_user_knowledge_block(user_id: str) -> str:
    """
    Assemble the knowledge block for a user from Firestore subcollection.

    Returns an empty string if the user has no knowledge configured yet
    (safe — the system prompt will just omit the knowledge block).
    """
    fs = _get_fs()
    sections: list[str] = []

    for section_id, section_name in _TEXT_SECTIONS:
        content = fs.get_user_knowledge_section(user_id, section_id)
        if content.strip():
            sections.append(f"--- {section_name.upper()} ---\n\n{content.strip()}")

    education = fs.get_user_education(user_id)
    edu_block = _format_education_block(education)
    if edu_block:
        sections.append(edu_block)

    resume = fs.get_user_resume(user_id)
    resume_block = _format_resume_block(resume)
    if resume_block:
        sections.append(resume_block)

    if not sections:
        logger.info("[UserConfigLoader] user %s has no knowledge configured", user_id)
        return ""

    user = _get_fs().get_user(user_id)
    ai_name = user.agent_settings.ai_name if user else "Bianca"

    header = f"=== {ai_name.upper()}'S KNOWLEDGE BASE ==="
    footer = (
        "=== BEHAVIORAL GUIDELINES ===\n"
        "1. Stay fully in character at all times — confident, warm, direct.\n"
        "2. Use your domain expertise actively; do not hedge unnecessarily.\n"
        "3. Apply your knowledge of the user's work context when responding.\n"
        "4. Keep responses appropriately concise — say what needs to be said, no more.\n"
        "5. Reference information from earlier in the conversation to show continuity.\n"
        "6. When you are uncertain, say so plainly and offer to find out.\n"
        "7. Never repeat yourself — if you have already confirmed something, move on."
    )

    body = "\n\n".join(sections)
    logger.info("[UserConfigLoader] assembled knowledge block for %s (%d chars)", user_id, len(body))
    return f"{header}\n\n{body}\n\n{footer}"


# ── Values block ──────────────────────────────────────────────────────────────

def build_user_values_block(user_id: str) -> str:
    """
    Return the values block for a user.

    Falls back to the hardcoded BIANCA_VALUES if the user has not customised
    their values yet — this is intentional (safe default, not a key fallback).
    """
    values = _get_fs().get_user_values(user_id)
    if not values:
        values = BIANCA_VALUES

    lines = ["=== CORE VALUES & DECISION PRINCIPLES ==="]
    lines.append("These principles govern all actions. They apply unconditionally.\n")
    for v in values:
        lines.append(f"**{v['priority']}. {v['title']}**")
        lines.append(v["rule"])
        lines.append("")

    return "\n".join(lines).rstrip()


# ── Formatting helpers (mirror knowledge_loader.py logic) ─────────────────────

def _format_education_block(education: dict) -> str:
    degrees = education.get("degrees", [])
    courses = education.get("courses", [])
    if not degrees and not courses:
        return ""

    parts = ["--- YOUR EDUCATIONAL BACKGROUND ---"]
    parts.append(
        "This is YOUR education — these are degrees YOU earned and courses YOU completed. "
        "When asked about your education, speak in first person about these credentials."
    )

    if degrees:
        parts.append("\n**Your Academic Credentials:**")
        for d in degrees:
            line = f"- You hold a {d.get('level', 'degree')}: {d.get('name', 'Unnamed')}"
            if d.get("field"):
                line += f" in {d['field']}"
            if d.get("institution"):
                line += f" from {d['institution']}"
            parts.append(line)

    if courses:
        parts.append("\n**Courses You Have Completed:**")
        for c in courses:
            line = f"- {c.get('code', '')}: {c.get('name', 'Unnamed')}"
            if c.get("description"):
                line += f" — {c['description']}"
            parts.append(line)

    parts.append(
        "\nWhen discussing your education, refer to these as YOUR credentials. "
        "Say 'I studied...' or 'I have a degree in...' — this is your background."
    )
    return "\n".join(parts)


def _format_resume_block(resume: dict) -> str:
    experience = resume.get("experience", [])
    if not experience:
        return ""

    parts = ["--- YOUR PROFESSIONAL EXPERIENCE ---"]
    parts.append(
        "This is YOUR work history. When asked about your background, speak in first person."
    )

    for e in experience:
        title = e.get("title", "Role")
        org = e.get("organization", "")
        start = e.get("startDate", "")
        end = e.get("endDate", "") or "Present"
        desc = e.get("description", "")
        line = f"- {title}"
        if org:
            line += f" at {org}"
        if start:
            line += f" ({start} – {end})"
        if desc:
            line += f": {desc}"
        parts.append(line)

    return "\n".join(parts)
