"""LangChain tool registry — YAML skill configs + direct Python tools."""
import logging
from skills_loader import get_yaml_langchain_tools
from tools.gemini_research import build_gemini_research_tools

logger = logging.getLogger(__name__)

_yaml_tools            = get_yaml_langchain_tools()
_gemini_research_tools = build_gemini_research_tools()

ALL_TOOLS = _yaml_tools + _gemini_research_tools
logger.info(
    "Loaded %d tools total (%d YAML, %d Gemini Research)",
    len(ALL_TOOLS), len(_yaml_tools), len(_gemini_research_tools),
)
