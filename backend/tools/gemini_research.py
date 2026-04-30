"""
Gemini Deep Research tool for Bianc.ai.

Uses the Gemini Interactions API (deep-research-preview-04-2026) to run
autonomous multi-step research tasks. Research runs in the background and
is polled until completion (typically 2–10 minutes, max 20 minutes).

Requires: google-genai>=1.0 and GOOGLE_API_KEY env var (or user-configured
google_api_key in Neural Config → Integrations).
"""
import os
import time
import logging

logger = logging.getLogger(__name__)

_AGENT = "deep-research-preview-04-2026"
_POLL_INTERVAL = 10   # seconds between status checks
_MAX_POLLS     = 120  # 120 × 10 s = 20 minutes hard limit


def _get_google_key() -> str:
    from settings_loader import load_settings
    settings = load_settings()
    return settings.get("google_api_key", "").strip() or os.getenv("GOOGLE_API_KEY", "")


def gemini_deep_research(topic: str, title: str) -> str:
    """
    Conduct comprehensive deep research on a topic using the Gemini Deep Research
    Agent (deep-research-preview-04-2026). Returns a full markdown report.

    This call blocks until the research completes (typically 2–10 minutes).
    Use only when the user explicitly requests a full analysis, research report,
    or in-depth investigation — not for quick factual questions.

    Args:
        topic: The research question or topic to investigate in depth.
        title: A short title for the report (used as the document heading).
    """
    from google import genai

    api_key = _get_google_key()
    if not api_key:
        return (
            "Google API key is not configured. "
            "Add it in Neural Config → Integrations to enable Deep Research."
        )

    try:
        client = genai.Client(api_key=api_key)

        interaction = client.interactions.create(
            input=topic,
            agent=_AGENT,
            background=True,
        )
        logger.info("gemini_deep_research: started interaction %s for '%s'", interaction.id, title)

        for attempt in range(_MAX_POLLS):
            time.sleep(_POLL_INTERVAL)
            result = client.interactions.get(interaction.id)
            if result.status == "completed":
                text = result.outputs[-1].text if result.outputs else "No output returned."
                logger.info(
                    "gemini_deep_research: completed '%s' after ~%ds",
                    title, (attempt + 1) * _POLL_INTERVAL,
                )
                return f"# {title}\n\n{text}"
            elif result.status == "failed":
                err = getattr(result, "error", "unknown error")
                logger.error("gemini_deep_research: failed for '%s': %s", title, err)
                return f"Deep research failed: {err}"

        return "Deep research timed out after 20 minutes. Try a more focused query."

    except Exception as exc:
        logger.error("gemini_deep_research: exception for '%s': %s", title, exc)
        return f"Deep research error: {exc}"


def build_gemini_research_tools() -> list:
    """
    Return a LangChain tool wrapper for Gemini Deep Research.
    Returns an empty list if no Google API key is available.
    """
    from langchain.tools import tool as langchain_tool

    if not _get_google_key():
        logger.info("Google API key not set — skipping Gemini Deep Research tool")
        return []

    @langchain_tool
    def gemini_deep_research_tool(topic: str, title: str) -> str:
        """Conduct a comprehensive deep research report using the Gemini Deep Research Agent.
        Autonomously plans, searches, reads, and synthesises information into a detailed
        markdown report with citations. Takes 2–10 minutes to complete.
        Use only when the user explicitly asks for a research report, full analysis,
        or deep investigation — not for quick questions."""
        return gemini_deep_research(topic, title)

    logger.info("Gemini Deep Research tool registered")
    return [gemini_deep_research_tool]
