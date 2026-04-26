"""
System prompt assembly for Bianca.

The prompt is built in layers, each with a distinct responsibility:

  Layer 1 — Identity anchor    : who Bianca is + current date/time
  Layer 2 — Knowledge base     : persona, training, expertise, product context
  Layer 3 — Values             : non-negotiable behavioral rules (highest authority)
  Layer 4 — Capabilities       : tools available in this session
  [Runtime] Memory injection   : per-user memories, injected at request time in chat.py

This module owns layers 1–4. Memory is injected separately in the chat router.
"""

from datetime import datetime
from knowledge_loader import build_knowledge_block
from values import build_values_block
from settings_loader import load_settings


# ---------------------------------------------------------------------------
# Layer 1 — Identity anchor
# ---------------------------------------------------------------------------

def _build_identity_block() -> str:
    settings = load_settings()
    ai_name = settings.get("ai_name", "Bianca")
    ai_role = settings.get("ai_role", "AI Chief of Staff")
    now = datetime.now()
    date_str = now.strftime("%A, %B %d, %Y")   # e.g., "Friday, March 13, 2026"
    time_str = now.strftime("%I:%M %p")          # e.g., "02:45 PM"
    return (
        f"You are {ai_name}, an {ai_role}.\n\n"
        f"Today is {date_str}. Current time: {time_str}.\n"
        f"Use this as your reference for all time-based queries, scheduling, and calendar operations."
    )


# ---------------------------------------------------------------------------
# Layer 4 — Capabilities
# ---------------------------------------------------------------------------

_CAPABILITIES_BLOCK = """\
=== CAPABILITIES AVAILABLE IN THIS SESSION ===

**Gmail**
- list_emails   : retrieve recent emails from the inbox
- get_email     : read the full content of a specific email
- send_email    : send an email (only after explicit user confirmation)
- draft_email   : compose a draft without sending

**Google Calendar**
- list_events   : view upcoming events in a date range
- get_event     : read details of a specific event
- create_event  : create a new calendar event
- update_event  : modify an existing event's details or time
- decline_event : decline a meeting invitation with an optional message

**Document Creation** (files are uploaded to Google Drive; a shareable link is returned)
- create_docx_document     : Word (.docx) — reports, memos, letters, briefs, contracts.
  Write complete docx-js JavaScript as the `code` parameter.
- create_xlsx_spreadsheet  : Excel (.xlsx) — tables, budgets, financial models, trackers.
  Write complete openpyxl Python as the `code` parameter. Use formulas, not hardcoded values.
- create_pptx_presentation : PowerPoint (.pptx) — pitch decks, slide decks, presentations.
  Write complete pptxgenjs JavaScript as the `code` parameter.
- create_pdf_document      : PDF — fixed-format reports, invoices, formal letters.
  Write complete reportlab Python as the `code` parameter.

When a document creation tool is called, the system injects detailed generation
instructions for the chosen format. Follow them exactly — especially the critical
rules around hex colors, bullets, and file output path.

**Google Drive**
- list_drive_files   : list files in the user's Drive
- get_drive_file     : get metadata for a specific file
- search_drive_files : search Drive by name or content

**Google Search**
- Available automatically for any question that requires current information,
  recent news, live data, or facts beyond your training knowledge. Use it
  proactively whenever the user asks about real-world events, people, companies,
  or anything time-sensitive.

Use these tools proactively when the user's request clearly calls for them. \
Always prefer to draft emails rather than send them unless the user explicitly \
instructs you to send."""

_PERPLEXITY_BLOCK = """\
**Perplexity Web Search** (real-time, always up-to-date)
- perplexity_search        : live web search via Perplexity sonar — use for current events,
  recent news, stock prices, sports scores, company info, or any time-sensitive fact.
  Returns a concise 2-3 sentence answer with source links.
- perplexity_deep_research : in-depth research report via sonar-deep-research.
  Use only when the user explicitly requests a full analysis, research report, or
  deep investigation. Takes 30-90 seconds. Returns a complete markdown report with sources.

Prefer perplexity_search for quick lookups. Reserve perplexity_deep_research for requests
like "write me a research report on…" or "do a deep dive on…"."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _build_template_hints(settings: dict) -> str:
    """Return a capabilities note listing configured document template IDs, or empty string."""
    lines = []
    if settings.get("docs_template_id", "").strip():
        lines.append(f"- When creating Google Docs, use template ID: {settings['docs_template_id'].strip()}")
    if settings.get("slides_template_id", "").strip():
        lines.append(f"- When creating Google Slides, use template ID: {settings['slides_template_id'].strip()}")
    if settings.get("sheets_template_id", "").strip():
        lines.append(f"- When creating Google Sheets, use template ID: {settings['sheets_template_id'].strip()}")
    if not lines:
        return ""
    return "=== DOCUMENT TEMPLATE IDS ===\n" + "\n".join(lines)


def get_system_prompt(
    world_model: list | None = None,
    authorizations: list | None = None,
    constraints: list | None = None,
) -> str:
    """
    Assemble and return the full system prompt for a chat session.

    Called once per request. The identity block is generated fresh each call
    so the date/time is always accurate. Knowledge and values are fast
    (small text files + in-memory constants).

    Args:
        world_model:     List of world-model entries {category, title, content} to inject.
        authorizations:  List of authorization strings from Access Control tab.
        constraints:     List of constraint strings from Access Control tab.
    """
    settings = load_settings()
    custom_prompt = settings.get("custom_prompt", "").strip()

    blocks = [
        _build_identity_block(),
        build_knowledge_block(),
        build_values_block(),
        _CAPABILITIES_BLOCK,
    ]

    # Perplexity block — only injected when a key is configured
    _pplx_key = (
        settings.get("perplexity_api_key", "").strip()
        or __import__("os").getenv("PERPLEXITY_API_KEY", "")
    )
    if _pplx_key:
        blocks.append(_PERPLEXITY_BLOCK)

    template_hints = _build_template_hints(settings)
    if template_hints:
        blocks.append(template_hints)

    if world_model:
        blocks.append(_build_world_model_block(world_model))

    if authorizations or constraints:
        blocks.append(_build_access_control_block(authorizations or [], constraints or []))

    # Drop any empty blocks (e.g. if knowledge files are missing)
    assembled = "\n\n".join(block for block in blocks if block.strip())

    # Prepend custom prompt if set
    if custom_prompt:
        assembled = f"{custom_prompt}\n\n{assembled}"

    return assembled


def _build_world_model_block(entries: list) -> str:
    """Format world model entries as a context block for the system prompt."""
    if not entries:
        return ""
    lines = ["=== WORLD CONTEXT ==="]
    from itertools import groupby
    sorted_entries = sorted(entries, key=lambda e: e.get("category", ""))
    for category, group in groupby(sorted_entries, key=lambda e: e.get("category", "general")):
        lines.append(f"\n[{category.upper()}]")
        for entry in group:
            if not entry.get("enabled", True):
                continue
            title = entry.get("title", "")
            content = entry.get("content", "")
            if title and content:
                lines.append(f"- {title}: {content}")
            elif title:
                lines.append(f"- {title}")
    return "\n".join(lines)


def _build_access_control_block(authorizations: list, constraints: list) -> str:
    """Format access control rules as a behavioral block for the system prompt."""
    lines = ["=== ACCESS CONTROL ==="]
    if authorizations:
        lines.append("\nExplicitly permitted actions:")
        for a in authorizations:
            lines.append(f"- {a}")
    if constraints:
        lines.append("\nHard constraints — never violate these:")
        for c in constraints:
            lines.append(f"- {c}")
    return "\n".join(lines)
