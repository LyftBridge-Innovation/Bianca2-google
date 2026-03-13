"""
YAML-based skill loader for Bianca AI assistant.

Reads skill YAML files from backend/skills/ and auto-generates:
  - LangChain @tool functions (for chat path)
  - Gemini FunctionDeclaration objects (for voice path)
  - A skill registry with scope/API mappings (for auth)
"""
import os
import json
import logging
import importlib
from typing import Any, Optional
from pathlib import Path

import yaml
from langchain.tools import tool as langchain_tool

from tools.gws_client import execute, GWSError
from token_manager import get_access_token
from request_context import current_user_id

logger = logging.getLogger(__name__)

SKILLS_DIR = os.path.join(os.path.dirname(__file__), "skills")

_PYTHON_TYPE_MAP = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "array": list,
}


# ── YAML loading ─────────────────────────────────────────────────────────────

class SkillDefinition:
    """Parsed representation of one skill YAML file."""

    def __init__(self, data: dict, filename: str):
        self.filename = filename
        skill = data["skill"]
        api = data["api"]
        self.name = skill["name"]
        self.display_name = skill.get("display_name", skill["name"])
        self.description = skill.get("description", "")
        self.icon = skill.get("icon", "")
        self.google_api = api["google_api"]
        self.scopes = api["scopes"]
        self.tools = data.get("tools", [])


def _load_all_skills() -> list[SkillDefinition]:
    """Load and validate all YAML files from SKILLS_DIR."""
    skills = []
    if not os.path.isdir(SKILLS_DIR):
        logger.warning("Skills directory not found: %s", SKILLS_DIR)
        return skills

    for filename in sorted(os.listdir(SKILLS_DIR)):
        if not filename.endswith((".yaml", ".yml")):
            continue
        if filename.startswith("_"):
            continue

        filepath = os.path.join(SKILLS_DIR, filename)
        try:
            with open(filepath, "r") as f:
                data = yaml.safe_load(f)

            assert "skill" in data, "Missing 'skill' key"
            assert "api" in data, "Missing 'api' key"
            assert "name" in data["skill"], "Missing skill.name"
            assert "scopes" in data["api"], "Missing api.scopes"

            skills.append(SkillDefinition(data, filename))
            logger.info(
                "Loaded skill: %s (%d tools) from %s",
                data["skill"]["name"],
                len(data.get("tools", [])),
                filename,
            )
        except Exception as e:
            logger.error("Failed to load skill from %s: %s", filename, e)

    return skills


# ── GWS arg building + response mapping ──────────────────────────────────────

def _build_gws_args(tool_def: dict, params: dict) -> tuple[list[str], Optional[dict]]:
    """Build gws CLI args and optional body from a tool def + actual params."""
    args = list(tool_def["gws_command"])

    params_map = tool_def.get("gws_params_map", {})
    if params_map:
        gws_params = {}
        for gws_key, template in params_map.items():
            if isinstance(template, str) and template.startswith("{") and template.endswith("}"):
                param_name = template[1:-1]
                value = params.get(param_name)
                if value is not None and value != "":
                    gws_params[gws_key] = value
            else:
                resolved = str(template)
                for pname, pval in params.items():
                    resolved = resolved.replace(f"{{{pname}}}", str(pval))
                gws_params[gws_key] = resolved
        if gws_params:
            args += ["--params", json.dumps(gws_params)]

    body_map = tool_def.get("gws_body_map", {})
    body = None
    if body_map:
        body = {}
        for body_key, template in body_map.items():
            if isinstance(template, str) and template.startswith("{") and template.endswith("}"):
                param_name = template[1:-1]
                value = params.get(param_name)
                if value is not None and value != "":
                    body[body_key] = value
            else:
                body[body_key] = template

    return args, body


def _resolve_path(obj: Any, path: str) -> Any:
    """Resolve a dotted/bracketed path like 'owners[0].displayName'."""
    parts = path.replace("[", ".[").split(".")
    current = obj
    for part in parts:
        if current is None:
            return None
        if part.startswith("[") and part.endswith("]"):
            idx = int(part[1:-1])
            if isinstance(current, list) and len(current) > idx:
                current = current[idx]
            else:
                return None
        elif isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def _extract_fields(item: dict, fields: list[dict]) -> dict:
    """Extract specified fields from a raw response dict."""
    result = {}
    for field in fields:
        value = _resolve_path(item, field["source"])
        result[field["target"]] = value if value is not None else ""
    return result


def _extract_response(raw: Any, mapping: dict) -> Any:
    """Reshape gws JSON response according to response_mapping."""
    if not mapping:
        return raw

    list_key = mapping.get("list_key")
    fields = mapping.get("fields", [])

    if list_key:
        items = raw.get(list_key, []) if isinstance(raw, dict) else []
        return [_extract_fields(item, fields) for item in items]
    return _extract_fields(raw, fields)


def _import_handler(handler_path: str):
    """Import a Python function from a dotted path like 'tools.gmail.list_emails'."""
    parts = handler_path.rsplit(".", 1)
    module_path, func_name = parts[0], parts[1]
    module = importlib.import_module(module_path)
    return getattr(module, func_name)


def _make_tool_executor(tool_def: dict):
    """
    Create a closure that executes a tool.

    If the tool has a 'handler' field, imports and wraps the Python function.
    Otherwise, uses the generic gws CLI executor built from gws_command/gws_params_map.
    """
    handler_path = tool_def.get("handler")

    if handler_path:
        # Import the Python handler function (e.g. tools.gmail.list_emails)
        handler_fn = _import_handler(handler_path)

        def handler_executor(**kwargs) -> Any:
            user_id = current_user_id.get()
            if not user_id:
                return {"error": "No user context available"}
            return handler_fn(user_id, **kwargs)

        return handler_executor

    # Generic gws CLI executor
    def gws_executor(**kwargs) -> Any:
        user_id = current_user_id.get()
        if not user_id:
            return {"error": "No user context available"}

        token = get_access_token(user_id)
        args, body = _build_gws_args(tool_def, kwargs)

        try:
            raw = execute(args, body_json=body, access_token=token)
            return _extract_response(raw, tool_def.get("response_mapping", {}))
        except GWSError as e:
            logger.error("Tool %s failed: %s", tool_def["name"], e)
            return {"error": str(e)}

    return gws_executor


# ── LangChain tool generation ────────────────────────────────────────────────

def _build_langchain_tool(tool_def: dict):
    """Dynamically create a LangChain @tool from a YAML tool definition."""
    executor = _make_tool_executor(tool_def)
    func_name = tool_def["name"]
    description = tool_def["description"].strip()
    params = tool_def.get("parameters", [])
    has_handler = "handler" in tool_def

    # Build function parameter string
    param_parts = []
    for p in params:
        ptype = _PYTHON_TYPE_MAP.get(p["type"], str).__name__
        if p.get("required", False):
            param_parts.append(f"{p['name']}: {ptype}")
        else:
            default_repr = repr(p.get("default"))
            param_parts.append(f"{p['name']}: {ptype} = {default_repr}")

    params_str = ", ".join(param_parts)

    # For handler-based tools: skip empty optional params so the Python
    # handler receives only what the LLM actually provided.
    # For gws-based tools: pass everything and let the gws builder filter.
    if has_handler:
        kwarg_lines = []
        for p in params:
            if p.get("required", False):
                kwarg_lines.append(f'    kwargs["{p["name"]}"] = {p["name"]}')
            else:
                kwarg_lines.append(
                    f'    if {p["name"]} is not None and {p["name"]} != "" and {p["name"]} != []:'
                    f'\n        kwargs["{p["name"]}"] = {p["name"]}'
                )
        kwarg_block = "\n".join(kwarg_lines)
    else:
        kwarg_block = "\n".join(f'    kwargs["{p["name"]}"] = {p["name"]}' for p in params)

    func_code = f'''def {func_name}({params_str}):
    """{description}"""
    kwargs = {{}}
{kwarg_block}
    return _executor(**kwargs)
'''

    local_ns = {"_executor": executor}
    exec(func_code, local_ns)
    return langchain_tool(local_ns[func_name])


# ── Gemini FunctionDeclaration generation ────────────────────────────────────

def _build_gemini_declaration(tool_def: dict):
    """Build a Gemini FunctionDeclaration from a YAML tool definition."""
    try:
        from google.genai import types as gemini_types
    except ImportError:
        return None

    _gemini_type_map = {
        "string": gemini_types.Type.STRING,
        "integer": gemini_types.Type.INTEGER,
        "number": gemini_types.Type.NUMBER,
        "boolean": gemini_types.Type.BOOLEAN,
        "array": gemini_types.Type.ARRAY,
    }

    params = tool_def.get("parameters", [])
    properties = {}
    required = []

    for p in params:
        ptype = _gemini_type_map.get(p["type"], gemini_types.Type.STRING)
        schema_kwargs = {
            "type": ptype,
            "description": p.get("description", ""),
        }
        # Gemini requires 'items' for array types
        if ptype == gemini_types.Type.ARRAY:
            items_type = _gemini_type_map.get(p.get("items_type", "string"), gemini_types.Type.STRING)
            schema_kwargs["items"] = gemini_types.Schema(type=items_type)
        properties[p["name"]] = gemini_types.Schema(**schema_kwargs)
        if p.get("required", False):
            required.append(p["name"])

    return gemini_types.FunctionDeclaration(
        name=tool_def["name"],
        description=tool_def["description"].strip(),
        parameters=gemini_types.Schema(
            type=gemini_types.Type.OBJECT,
            properties=properties,
            required=required if required else None,
        ),
    )


# ── Public API (lazy-loaded) ─────────────────────────────────────────────────

_skills: list[SkillDefinition] | None = None
_langchain_tools: list | None = None
_gemini_declarations: list | None = None
_skill_registry: dict | None = None


def _ensure_loaded():
    global _skills, _langchain_tools, _gemini_declarations, _skill_registry
    if _skills is not None:
        return

    _skills = _load_all_skills()
    _langchain_tools = []
    _gemini_declarations = []
    _skill_registry = {}

    for skill in _skills:
        tool_names = []
        for tool_def in skill.tools:
            lc_tool = _build_langchain_tool(tool_def)
            _langchain_tools.append(lc_tool)

            gd = _build_gemini_declaration(tool_def)
            if gd:
                _gemini_declarations.append(gd)

            tool_names.append(tool_def["name"])

        _skill_registry[skill.name] = {
            "display_name": skill.display_name,
            "description": skill.description,
            "google_api": skill.google_api,
            "scopes": skill.scopes,
            "tools": tool_names,
            "icon": skill.icon,
        }

    logger.info(
        "Skills loaded: %d skills, %d tools",
        len(_skill_registry),
        len(_langchain_tools),
    )


def get_yaml_langchain_tools() -> list:
    _ensure_loaded()
    return _langchain_tools


def get_yaml_gemini_declarations() -> list:
    _ensure_loaded()
    return _gemini_declarations


def get_skill_registry() -> dict:
    _ensure_loaded()
    return _skill_registry


def get_all_scopes() -> list[str]:
    _ensure_loaded()
    scopes = set()
    for info in _skill_registry.values():
        scopes.update(info["scopes"])
    return sorted(scopes)
