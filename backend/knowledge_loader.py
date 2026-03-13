"""
Knowledge base loader for Bianca.

Reads the knowledge/ directory and assembles a structured system instruction
from persona, education, expertise, and company context files.

Directory layout:
  backend/knowledge/
    01_persona/      — who Bianca is
    02_education/    — her training background
    03_expertise/    — domain knowledge
    04_company/      — product and mission context
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"

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

    if not sections:
        logger.warning("[KnowledgeLoader] No knowledge files found — skipping knowledge block.")
        return ""

    header = "=== BIANCA'S KNOWLEDGE BASE ==="
    footer = (
        "=== BEHAVIORAL GUIDELINES ===\n"
        "1. Stay fully in character as Bianca at all times — confident, warm, direct.\n"
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
