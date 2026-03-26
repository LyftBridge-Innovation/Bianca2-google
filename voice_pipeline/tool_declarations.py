"""
Function declarations for Gemini Live tool calling.

All tool declarations are loaded from YAML skill configs via skills_loader.
Document creation tools are replaced with voice-friendly simplified versions
(title + description) because Gemini Live cannot generate full JS/Python code
as a function argument during a voice call.
Passed to the Gemini Live session at connect time.
"""
import sys
import os
from google.genai import types

# Ensure backend/ is on path for skills_loader import
_backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

# YAML document creation tool names that require generated code — replaced below
# with simpler voice-friendly declarations.
_CODE_BASED_TOOLS = {
    "create_docx_document",
    "create_xlsx_spreadsheet",
    "create_pptx_presentation",
    "create_pdf_document",
}

# Voice-friendly replacements: Gemini just says what it wants, Claude generates the code.
_VOICE_DOCUMENT_DECLARATIONS = [
    types.FunctionDeclaration(
        name="create_docx_document",
        description=(
            "Create a professionally formatted Word (.docx) document — report, memo, letter, "
            "brief, or contract — and upload it to Google Drive. Returns a shareable link."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "title": types.Schema(type=types.Type.STRING, description="Document title / filename"),
                "description": types.Schema(type=types.Type.STRING, description="Describe what the document should contain"),
            },
            required=["title", "description"],
        ),
    ),
    types.FunctionDeclaration(
        name="create_xlsx_spreadsheet",
        description=(
            "Create an Excel (.xlsx) spreadsheet — table, tracker, budget, or financial model — "
            "with formulas and upload it to Google Drive. Returns a shareable link."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "title": types.Schema(type=types.Type.STRING, description="Spreadsheet title / filename"),
                "description": types.Schema(type=types.Type.STRING, description="Describe what the spreadsheet should contain"),
            },
            required=["title", "description"],
        ),
    ),
    types.FunctionDeclaration(
        name="create_pptx_presentation",
        description=(
            "Create a PowerPoint (.pptx) presentation — pitch deck, slide deck, or report — "
            "with custom design and upload it to Google Drive. Returns a shareable link."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "title": types.Schema(type=types.Type.STRING, description="Presentation title / filename"),
                "description": types.Schema(type=types.Type.STRING, description="Describe what the presentation should contain"),
            },
            required=["title", "description"],
        ),
    ),
    types.FunctionDeclaration(
        name="create_pdf_document",
        description=(
            "Create a PDF document — report, invoice, or letter — with formatted layout "
            "and upload it to Google Drive. Returns a shareable link."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "title": types.Schema(type=types.Type.STRING, description="Document title / filename"),
                "description": types.Schema(type=types.Type.STRING, description="Describe what the PDF should contain"),
            },
            required=["title", "description"],
        ),
    ),
]


def get_function_declarations() -> list[types.FunctionDeclaration]:
    """
    Returns all FunctionDeclarations for the voice session.
    YAML skills provide all tools; code-based document creation tools are
    replaced with voice-friendly simplified versions.
    """
    try:
        from skills_loader import get_yaml_gemini_declarations
        yaml_decls = get_yaml_gemini_declarations()
    except Exception as e:
        print(f"Warning: Could not load YAML Gemini declarations: {e}")
        yaml_decls = []

    # Filter out code-based YAML document tools, then append voice-friendly versions
    filtered = [d for d in yaml_decls if d.name not in _CODE_BASED_TOOLS]
    return filtered + _VOICE_DOCUMENT_DECLARATIONS


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
