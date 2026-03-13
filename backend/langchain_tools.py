"""LangChain tool registry — all tools loaded from YAML skill configs."""
import logging
from skills_loader import get_yaml_langchain_tools

logger = logging.getLogger(__name__)

ALL_TOOLS = get_yaml_langchain_tools()
logger.info("Loaded %d tools from YAML skill configs", len(ALL_TOOLS))
