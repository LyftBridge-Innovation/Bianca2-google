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


def extract_doc_title(user_message: str, document_type: str) -> str:
    """
    Best-effort extraction of a document title from the user's message.
    Falls back to a sensible default based on document_type.
    """
    import re
    msg = user_message.strip()

    # Look for quoted titles first: "make me a 'Q3 Report'" or "titled X"
    for pattern in [
        r'(?:called|named|titled?|for)\s+["\u201c\u2018]([^"\u201d\u2019]{3,60})["\u201d\u2019]',
        r'["\u201c\u2018]([^"\u201d\u2019]{3,60})["\u201d\u2019]',
    ]:
        m = re.search(pattern, msg, re.IGNORECASE)
        if m:
            return m.group(1).strip()

    # Use first sentence fragment, truncated
    first_line = re.split(r'[.\n]', msg)[0].strip()
    if 10 < len(first_line) < 80:
        # Strip leading verb phrases like "create a", "make me a", "build me a"
        cleaned = re.sub(
            r'^(?:create|make|build|write|generate|draft|give me|can you make|i need)\s+(?:me\s+)?(?:a\s+|an\s+)?',
            '', first_line, flags=re.IGNORECASE,
        ).strip()
        if len(cleaned) > 5:
            return cleaned[:70]

    defaults = {
        "docx": "Document",
        "xlsx": "Spreadsheet",
        "pptx": "Presentation",
        "pdf": "Report",
    }
    return defaults.get(document_type, "Document")


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
