"""
Knowledge base loader for Bianc.ai.

Reads the knowledge/ directory and assembles a structured system instruction
from persona, education, expertise, and company context files.

Directory layout:
  backend/knowledge/
    01_persona/      — who Bianc.ai is
    02_education/    — her training background
    03_expertise/    — domain knowledge
    04_company/      — product and mission context
    education.json   — user-configured degrees and courses
"""

import os
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"
_EDUCATION_PATH = _KNOWLEDGE_DIR / "education.json"
_RESUME_PATH = _KNOWLEDGE_DIR / "resume.json"

_SECTIONS = [
    ("01_persona",  "Persona & Identity"),
    ("02_education", "Training Background"),
    ("03_expertise", "Domain Expertise"),
    ("04_company",  "Product & Mission"),
]


def _load_section(dir_name: str, section_name: str) -> str:
    """Load all .txt and .md files from a knowledge subdirectory."""
    section_path = _KNOWLEDGE_DIR / dir_name
    if not section_path.exists():
        logger.warning(f"[KnowledgeLoader] Missing directory: {section_path}")
        return ""

    parts = [f"--- {section_name.upper()} ---"]
    loaded = 0

    for file_path in sorted(section_path.iterdir()):
        if file_path.suffix not in (".txt", ".md") or not file_path.is_file():
            continue
        try:
            content = file_path.read_text(encoding="utf-8").strip()
            if content:
                parts.append(content)
                loaded += 1
        except Exception as exc:
            logger.error(f"[KnowledgeLoader] Could not read {file_path.name}: {exc}")

    if loaded == 0:
        return ""

    return "\n\n".join(parts)


def _load_education_block() -> str:
    """Load configured education data and format as Bianc.ai's background."""
    if not _EDUCATION_PATH.exists():
        return ""

    try:
        data = json.loads(_EDUCATION_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.error(f"[KnowledgeLoader] Could not read education.json: {exc}")
        return ""

    degrees = data.get("degrees", [])
    courses = data.get("courses", [])

    if not degrees and not courses:
        return ""

    parts = ["--- YOUR EDUCATIONAL BACKGROUND ---"]
    parts.append("This is YOUR education — these are degrees YOU earned and courses YOU completed. When asked about your education, speak in first person about these credentials.")

    if degrees:
        parts.append("\n**Your Academic Credentials:**")
        for d in degrees:
            credential = f"- You hold a {d.get('level', 'degree')}: {d.get('name', 'Unnamed')}"
            if d.get('field'):
                credential += f" in {d['field']}"
            if d.get('institution'):
                credential += f" from {d['institution']}"
            parts.append(credential)

    if courses:
        parts.append("\n**Courses You Have Completed:**")
        for c in courses:
            course_line = f"- {c.get('code', '')}: {c.get('name', 'Unnamed')}"
            if c.get('description'):
                course_line += f" — {c['description']}"
            parts.append(course_line)

    parts.append("\nWhen discussing your education, refer to these as YOUR credentials. Say 'I studied...' or 'I have a degree in...' — this is your background.")

    return "\n".join(parts)


def _load_resume_block() -> str:
    """Load configured work experience and format as Bianc.ai's professional background."""
    if not _RESUME_PATH.exists():
        return ""

    try:
        data = json.loads(_RESUME_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.error(f"[KnowledgeLoader] Could not read resume.json: {exc}")
        return ""

    experience = data.get("experience", [])
    if not experience:
        return ""

    parts = ["--- YOUR PROFESSIONAL EXPERIENCE ---"]
    parts.append("This is YOUR work history. When asked about your background, speak in first person.")

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


def build_knowledge_block() -> str:
    """
    Assemble and return the full knowledge block for the system prompt.

    Returns an empty string if no knowledge files are found (safe fallback).
    """
    sections = []
    for dir_name, section_name in _SECTIONS:
        section_text = _load_section(dir_name, section_name)
        if section_text:
            sections.append(section_text)

    # Add user-configured education data
    education_block = _load_education_block()
    if education_block:
        sections.append(education_block)

    # Add user-configured work experience
    resume_block = _load_resume_block()
    if resume_block:
        sections.append(resume_block)

    if not sections:
        logger.warning("[KnowledgeLoader] No knowledge files found — skipping knowledge block.")
        return ""

    header = "=== BIANCA'S KNOWLEDGE BASE ==="
    footer = (
        "=== BEHAVIORAL GUIDELINES ===\n"
        "1. Stay fully in character as Bianc.ai at all times — confident, warm, direct.\n"
        "2. Use your domain expertise actively; do not hedge unnecessarily.\n"
        "3. Apply your knowledge of the user's work context when responding.\n"
        "4. Keep responses appropriately concise — say what needs to be said, no more.\n"
        "5. Reference information from earlier in the conversation to show continuity.\n"
        "6. When you are uncertain, say so plainly and offer to find out.\n"
        "7. Never repeat yourself — if you have already confirmed something, move on."
    )

    body = "\n\n".join(sections)
    logger.info(f"[KnowledgeLoader] Assembled knowledge block ({len(body):,} chars)")

    return f"{header}\n\n{body}\n\n{footer}"
