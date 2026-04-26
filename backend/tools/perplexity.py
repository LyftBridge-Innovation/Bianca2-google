"""
Perplexity AI tools for Bianca.

Two tools available when PERPLEXITY_API_KEY is configured:
  - perplexity_quick_search    : sonar model — real-time 2-3 sentence answer
  - perplexity_deep_research   : sonar-deep-research — comprehensive report returned as markdown

Both are synchronous (httpx). quick_search is fast (~2s). deep_research is slow (30-90s)
and is expected to be run as a background task by the caller.
"""
import re
import os
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

_PPLX_URL = "https://api.perplexity.ai/chat/completions"


def _get_api_key() -> str:
    from settings_loader import load_settings
    settings = load_settings()
    return (
        settings.get("perplexity_api_key", "").strip()
        or os.getenv("PERPLEXITY_API_KEY", "")
    )


def _strip_think_blocks(text: str) -> str:
    """Remove <think>...</think> blocks that sonar-deep-research sometimes emits."""
    return re.sub(r"<think>.*?</think>\s*", "", text, flags=re.DOTALL | re.IGNORECASE)


def _call_perplexity(model: str, prompt: str, timeout: float = 120.0) -> tuple[str, list]:
    """
    Call the Perplexity chat completions API.

    Returns (content, search_results) where search_results is a list of
    {title, url} dicts (may be empty for sonar).
    """
    api_key = _get_api_key()
    if not api_key:
        raise ValueError(
            "Perplexity API key is not configured. "
            "Add it in Neural Config → Integrations or set PERPLEXITY_API_KEY env var."
        )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }

    response = httpx.post(_PPLX_URL, headers=headers, json=payload, timeout=timeout)
    response.raise_for_status()
    data = response.json()

    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    search_results = data.get("search_results", [])
    return content, search_results


def perplexity_quick_search(query: str) -> str:
    """
    Answer a real-time question using Perplexity's sonar model.

    Use this when the user asks about current events, live data, recent news,
    or any question requiring up-to-date web information. Returns a concise
    2-3 sentence answer with sources.

    Args:
        query: The question or search query to answer.
    """
    try:
        prompt = f"Answer concisely in 2-3 sentences: {query}"
        content, search_results = _call_perplexity("sonar", prompt, timeout=30.0)
        content = _strip_think_blocks(content).strip()

        if search_results:
            sources = [s.get("url") or s.get("title", "") for s in search_results[:3] if s]
            source_line = "  |  ".join(s for s in sources if s)
            if source_line:
                content += f"\n\nSources: {source_line}"

        logger.info("perplexity_quick_search: answered '%s'", query[:60])
        return content
    except Exception as exc:
        logger.error("perplexity_quick_search failed: %s", exc)
        return f"Perplexity search failed: {exc}"


def perplexity_deep_research(topic: str, title: str) -> str:
    """
    Conduct a comprehensive deep research report on a topic using Perplexity's
    sonar-deep-research model. Returns a full markdown report with sources.

    This call can take 30-90 seconds. Use this when the user asks for a full
    analysis, research report, or in-depth investigation of a topic — not for
    quick questions (use perplexity_quick_search for those).

    Args:
        topic: The research question or topic to investigate in depth.
        title: A short title for the research report (used as document heading).
    """
    try:
        content, search_results = _call_perplexity(
            "sonar-deep-research", topic, timeout=180.0
        )
        content = _strip_think_blocks(content).strip()

        # Build full document body
        doc = f"# {title}\n\n{content}\n"

        if search_results:
            doc += "\n\n---\n## Sources\n"
            for i, s in enumerate(search_results, 1):
                t = s.get("title") or s.get("url") or f"Source {i}"
                u = s.get("url", "")
                doc += f"{i}. {t}"
                if u:
                    doc += f" — {u}"
                doc += "\n"

        logger.info("perplexity_deep_research: completed '%s'", title)
        return doc
    except Exception as exc:
        logger.error("perplexity_deep_research failed: %s", exc)
        return f"Deep research failed: {exc}"


def build_perplexity_tools() -> list:
    """
    Return LangChain tool wrappers for the Perplexity functions.
    Returns an empty list if no API key is configured so the backend
    starts cleanly without one.
    """
    from langchain.tools import tool as langchain_tool

    api_key = _get_api_key()
    if not api_key:
        logger.info("Perplexity API key not set — skipping Perplexity tools")
        return []

    @langchain_tool
    def perplexity_search(query: str) -> str:
        """Answer a real-time question using Perplexity's live web search (sonar model).
        Use for current events, recent news, live data, or anything requiring up-to-date
        web information. Returns a concise 2-3 sentence answer with sources."""
        return perplexity_quick_search(query)

    @langchain_tool
    def perplexity_deep_research_tool(topic: str, title: str) -> str:
        """Conduct a comprehensive deep research report on a topic using Perplexity's
        sonar-deep-research model. Returns a full markdown report with sources.
        This takes 30-90 seconds — only use when the user explicitly asks for a
        research report or in-depth analysis, not for quick questions."""
        return perplexity_deep_research(topic, title)

    logger.info("Perplexity tools registered (quick_search + deep_research)")
    return [perplexity_search, perplexity_deep_research_tool]
