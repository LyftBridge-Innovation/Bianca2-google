"""
Dispatcher for Gemini Live tool calls.

All tool handlers are loaded from YAML skill configs via skills_loader.
Filler phrases and result formatters provide voice-friendly output.
"""
import sys
import os
import asyncio
from typing import Optional, Callable

# ── Backend path setup ────────────────────────────────────────────────────────
_backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

from voice_config import DEBUG_LOGGING  # noqa: E402


# ── Filler phrases ────────────────────────────────────────────────────────────

FILLER_PHRASES: dict[str, str] = {
    "list_recent_emails":     "Let me check your inbox.",
    "get_email_by_id":        "Let me check your inbox.",
    "send_email_message":     "Give me a moment to handle that email.",
    "draft_email_message":    "Give me a moment to handle that email.",
    "list_upcoming_events":   "Let me pull up your calendar.",
    "get_event_details":      "Let me pull up your calendar.",
    "create_calendar_event":  "Let me update your calendar.",
    "update_calendar_event":  "Let me update your calendar.",
    "decline_calendar_event": "Let me take care of that for you.",
}

# Auto-generated filler mapping for YAML skill keywords
_SKILL_FILLERS = {
    "drive": "Let me check your Drive.",
    "task": "Let me check your Tasks.",
    "sheet": "Let me check your Sheets.",
    "doc": "Let me check your Docs.",
    "people": "Let me look up your Contacts.",
    "contact": "Let me look up your Contacts.",
    "slide": "Let me check your Slides.",
    "presentation": "Let me check your Slides.",
}


# ── Dispatcher ────────────────────────────────────────────────────────────────

class ToolDispatcher:
    """
    Async dispatcher bound to a specific user_id.
    All tools loaded from YAML skill configs via skills_loader.
    """

    def __init__(self, user_id: str, on_tool_call_complete: Optional[Callable] = None):
        self.user_id = user_id
        self.on_tool_call_complete = on_tool_call_complete
        self._map: dict = {}

        # Load all tool handlers from YAML skills
        try:
            from skills_loader import _load_all_skills, _make_tool_executor
            from request_context import current_user_id as _ctx
            _ctx.set(user_id)

            for skill in _load_all_skills():
                for tool_def in skill.tools:
                    executor = _make_tool_executor(tool_def)

                    def _bind(exec_fn, td):
                        async def handler(params: dict) -> str:
                            kwargs = {}
                            for p in td.get("parameters", []):
                                pname = p["name"]
                                if pname in params:
                                    kwargs[pname] = params[pname]
                                elif not p.get("required", False) and "default" in p:
                                    kwargs[pname] = p["default"]
                            result = await asyncio.to_thread(exec_fn, **kwargs)
                            return str(result)
                        return handler

                    self._map[tool_def["name"]] = _bind(executor, tool_def)

            if DEBUG_LOGGING:
                print(f"ToolDispatcher: loaded {len(self._map)} tools from YAML skills")
        except Exception as e:
            if DEBUG_LOGGING:
                print(f"Warning: Could not load YAML tool handlers: {e}")

    def is_known_tool(self, function_name: str) -> bool:
        return function_name in self._map

    def get_filler_phrase(self, function_name: str) -> str:
        if function_name in FILLER_PHRASES:
            return FILLER_PHRASES[function_name]
        fn_lower = function_name.lower()
        for keyword, phrase in _SKILL_FILLERS.items():
            if keyword in fn_lower:
                return phrase
        return "Let me take care of that."

    async def dispatch(self, function_name: str, parameters: dict) -> str:
        """
        Route a Gemini tool call to the correct backend function.
        Returns a clean formatted string result.
        """
        handler = self._map.get(function_name)
        if not handler:
            raise ValueError(f"Unknown tool function: {function_name!r}")

        result = await handler(parameters)

        # Invoke tool completion callback for Firestore logging
        if self.on_tool_call_complete:
            try:
                await self.on_tool_call_complete(
                    tool_name=function_name,
                    parameters=parameters,
                    result=result
                )
            except Exception as e:
                if DEBUG_LOGGING:
                    print(f"Tool logging callback failed: {e}")

        return result
