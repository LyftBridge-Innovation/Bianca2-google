"""
Document skill context loader.

When a user asks to create a document, spreadsheet, presentation, or PDF,
the relevant instruction block is injected into the system prompt so that
Bianca knows exactly how to write the generation code.

Only one document type is matched per message — the first match wins.
"""
import os
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

SKILLS_DIR = os.path.join(os.path.dirname(__file__), "document_skills")

# Keywords that trigger each document type.
# Checked case-insensitively; first match wins.
DOCUMENT_SKILL_KEYWORDS: dict[str, list[str]] = {
    "pptx": [
        "slides", "slide deck", "deck", "presentation", "pitch deck",
        "powerpoint", ".pptx", "pptx", "slideshow",
    ],
    "docx": [
        "word doc", ".docx", "docx", "word document", "report", "memo",
        "letter", "brief", "contract", "proposal",
    ],
    "xlsx": [
        "excel", ".xlsx", "xlsx", "spreadsheet", "financial model",
        "workbook", "budget", "forecast", "tracker",
    ],
    "pdf": [
        ".pdf", "pdf document", "pdf report", "pdf file", "create a pdf",
        "generate a pdf",
    ],
}

# Header that wraps the instruction block in the system prompt
_BLOCK_HEADER = "=== DOCUMENT CREATION INSTRUCTIONS ({fmt}) ==="
_BLOCK_FOOTER = "=== END DOCUMENT CREATION INSTRUCTIONS ==="


@lru_cache(maxsize=4)
def _load_instructions(document_type: str) -> str:
    """Load and cache the instruction markdown for a given document type."""
    path = os.path.join(SKILLS_DIR, f"{document_type}_instructions.md")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.warning("Document skill instructions not found: %s", path)
        return ""


def detect_document_type(user_message: str) -> str | None:
    """
    Return the document type ("docx", "xlsx", "pptx", "pdf") if the message
    mentions document creation, or None if no match.
    """
    msg_lower = user_message.lower()
    for doc_type, keywords in DOCUMENT_SKILL_KEYWORDS.items():
        for kw in keywords:
            if kw in msg_lower:
                return doc_type
    return None


def get_document_skill_block(user_message: str) -> str | None:
    """
    Return a formatted instruction block to inject into the system prompt,
    or None if the message does not appear to request a document.
    """
    doc_type = detect_document_type(user_message)
    if not doc_type:
        return None

    instructions = _load_instructions(doc_type)
    if not instructions:
        return None

    header = _BLOCK_HEADER.format(fmt=doc_type.upper())
    block = f"{header}\n\n{instructions}\n\n{_BLOCK_FOOTER}"
    logger.info("Injecting document skill instructions for type: %s", doc_type)
    return block
