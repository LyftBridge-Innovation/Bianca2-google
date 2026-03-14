"""
Lightweight skill matcher — decides which user skills are relevant to a query.

No LLM call, no embeddings. Pure title-keyword matching:
  1. Parse H1 heading from each skill's markdown → skill "title"
  2. Extract trigger words from the title (lowered, stopwords removed)
  3. If any trigger word appears in the user's message → inject that skill

Returns an injectable prompt block or empty string.
"""

import re
from typing import List, Tuple

_STOPWORDS = frozenset({
    "a", "an", "the", "my", "your", "our", "their", "its", "this", "that",
    "is", "am", "are", "was", "were", "be", "been", "being",
    "in", "on", "at", "to", "for", "of", "with", "by", "from", "as",
    "and", "or", "but", "not", "no", "if", "so", "do", "does", "did",
    "will", "would", "should", "could", "can", "may", "might",
    "how", "what", "when", "where", "who", "which", "about",
    "all", "each", "every", "some", "any", "i", "me", "we", "you",
    "he", "she", "it", "they", "them",
})

_H1_PATTERN = re.compile(r"^#\s+(.+)", re.MULTILINE)
_WORD_PATTERN = re.compile(r"[a-z]+")


def extract_title(markdown: str) -> str:
    """Extract the first H1 heading from markdown, or return empty string."""
    match = _H1_PATTERN.search(markdown)
    return match.group(1).strip() if match else ""


_SCAN_LINES = 4  # number of non-empty lines to extract trigger words from


def _extract_trigger_words(content: str) -> set[str]:
    """
    Extract trigger words from the first few non-empty lines of a skill file.

    Scans the first 4 non-empty lines (which typically cover the H1 title and
    any keyword/description lines right below it), tokenizes them, and removes
    stopwords + short words.
    """
    lines_seen = 0
    text_parts = []

    for line in content.split("\n"):
        stripped = line.strip().lstrip("#").strip()
        if not stripped:
            continue
        text_parts.append(stripped)
        lines_seen += 1
        if lines_seen >= _SCAN_LINES:
            break

    words = set(_WORD_PATTERN.findall(" ".join(text_parts).lower()))
    return {w for w in words if w not in _STOPWORDS and len(w) > 2}


def match_skills(
    user_message: str,
    skills: List[Tuple[str, str, str]],
) -> List[Tuple[str, str]]:
    """
    Match user message against available skills.

    Args:
        user_message: the user's chat message
        skills: list of (skill_id, title, content) tuples

    Returns:
        list of (title, content) tuples for matched skills
    """
    if not skills:
        return []

    message_words = set(_WORD_PATTERN.findall(user_message.lower()))
    matched = []

    for _skill_id, title, content in skills:
        triggers = _extract_trigger_words(content)
        if triggers & message_words:
            matched.append((title, content))

    return matched


def build_skills_block(matched_skills: List[Tuple[str, str]]) -> str:
    """
    Format matched skills into an injectable prompt block.

    Args:
        matched_skills: list of (title, content) tuples

    Returns:
        formatted string or empty string if no matches
    """
    if not matched_skills:
        return ""

    parts = ["=== ACTIVE SKILLS ===\n"]
    for title, content in matched_skills:
        parts.append(f"[{title}]")
        parts.append(content.strip())
        parts.append("")

    return "\n".join(parts).rstrip()
