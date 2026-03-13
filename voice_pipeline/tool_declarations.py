"""
Function declarations for Gemini Live tool calling.

All tool declarations are loaded from YAML skill configs via skills_loader.
Passed to the Gemini Live session at connect time.
"""
import sys
import os
from google.genai import types

# Ensure backend/ is on path for skills_loader import
_backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)


def get_function_declarations() -> list[types.FunctionDeclaration]:
    """Returns all FunctionDeclarations from YAML skill configs."""
    try:
        from skills_loader import get_yaml_gemini_declarations
        return get_yaml_gemini_declarations()
    except Exception as e:
        print(f"Warning: Could not load YAML Gemini declarations: {e}")
        return []


def build_tools_config(enable_google_search: bool = True) -> list:
    """
    Returns the full tools list for the Gemini Live session config.
    All declarations come from YAML skill configs + optionally Google Search.
    """
    declarations = get_function_declarations()
    custom_tool = types.Tool(function_declarations=declarations)

    if enable_google_search:
        google_search_tool = types.Tool(google_search=types.GoogleSearch())
        return [custom_tool, google_search_tool]

    return [custom_tool]
