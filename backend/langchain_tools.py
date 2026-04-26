"""LangChain tool registry — YAML skill configs + direct Python tools."""
import logging
from skills_loader import get_yaml_langchain_tools
from tools.perplexity import build_perplexity_tools

logger = logging.getLogger(__name__)

_yaml_tools = get_yaml_langchain_tools()
_perplexity_tools = build_perplexity_tools()

ALL_TOOLS = _yaml_tools + _perplexity_tools
logger.info(
    "Loaded %d tools total (%d YAML, %d Perplexity)",
    len(ALL_TOOLS), len(_yaml_tools), len(_perplexity_tools),
)
