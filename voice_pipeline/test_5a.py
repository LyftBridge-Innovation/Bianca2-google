"""
Phase 5A — Static verification tests.
Run from the voice_pipeline directory with the project venv:
  ../venv/bin/python3 test_5a.py
"""
import sys
import os

# Backend path is handled by tool_dispatcher at import time (inserted at position 0).
# Do NOT insert it here — that would shadow voice_pipeline's own voice_config.py / voice_prompts.py.

PASS = "  PASS"
FAIL = "  FAIL"
results = []

def check(label, condition, detail=""):
    status = PASS if condition else FAIL
    line = f"{status}  {label}"
    if detail:
        line += f"  ({detail})"
    print(line)
    results.append(condition)
    return condition


print("=" * 60)
print("Phase 5A — Static checks")
print("=" * 60)

# ── Imports ───────────────────────────────────────────────────────────────────
print("\n[1] Imports")

try:
    from tool_declarations import build_tools_config, get_function_declarations
    check("tool_declarations imports", True)
except Exception as e:
    check("tool_declarations imports", False, str(e))

try:
    from tool_dispatcher import ToolDispatcher, FILLER_PHRASES
    check("tool_dispatcher imports", True)
except Exception as e:
    check("tool_dispatcher imports", False, str(e))

try:
    from audio_utils import (
        ulaw_to_pcm16k, pcm16k_to_ulaw,
        UlawToPcm16kStream, Pcm16kToUlawStream,
    )
    check("audio_utils imports", True)
except Exception as e:
    check("audio_utils imports", False, str(e))

try:
    from voice_prompts import SYSTEM_INSTRUCTION, INITIAL_GREETING
    check("voice_prompts imports", True)
except Exception as e:
    check("voice_prompts imports", False, str(e))

try:
    from voice_config import GEMINI_API_KEY, MODEL, DEFAULT_USER_ID, DEBUG_LOGGING
    check("config imports", True)
except Exception as e:
    check("config imports", False, str(e))

try:
    from gemini_session import GeminiSession
    check("gemini_session imports", True)
except Exception as e:
    check("gemini_session imports", False, str(e))

# ── Tool declarations ─────────────────────────────────────────────────────────
print("\n[2] Tool declarations")

try:
    decls = get_function_declarations()
    expected_tools = [
        "list_emails", "get_email", "send_email", "draft_email",
        "list_events", "get_event", "create_event", "update_event", "decline_event",
    ]
    declared_names = [d.name for d in decls]
    check("9 function declarations exist", len(decls) == 9, f"got {len(decls)}")
    for t in expected_tools:
        check(f"  {t} declared", t in declared_names)

    # Verify schemas are present (Gemini Live is strict about this)
    missing_schema = [d.name for d in decls if d.parameters is None]
    check("all declarations have parameter schemas", len(missing_schema) == 0,
          f"missing: {missing_schema}" if missing_schema else "")
except Exception as e:
    check("tool declarations structure", False, str(e))

try:
    tools_config = build_tools_config(enable_google_search=True)
    check("build_tools_config returns list", isinstance(tools_config, list))
    check("returns 2 tool objects (custom + google search)", len(tools_config) == 2,
          f"got {len(tools_config)}")
except Exception as e:
    check("build_tools_config", False, str(e))

try:
    tools_no_search = build_tools_config(enable_google_search=False)
    check("build_tools_config without search returns 1 object", len(tools_no_search) == 1,
          f"got {len(tools_no_search)}")
except Exception as e:
    check("build_tools_config no-search", False, str(e))

# ── Dispatcher ────────────────────────────────────────────────────────────────
print("\n[3] Dispatcher coverage")

try:
    dispatcher = ToolDispatcher("dev_user_1")
    expected_tools = [
        "list_emails", "get_email", "send_email", "draft_email",
        "list_events", "get_event", "create_event", "update_event", "decline_event",
    ]
    for t in expected_tools:
        check(f"  {t} registered", dispatcher.is_known_tool(t))

    check("unknown tool returns False", not dispatcher.is_known_tool("nonexistent_tool"))
except Exception as e:
    check("dispatcher init", False, str(e))

# ── Filler phrases ────────────────────────────────────────────────────────────
print("\n[4] Filler phrases")

try:
    for t in expected_tools:
        phrase = dispatcher.get_filler_phrase(t)
        check(f"  {t} has filler phrase", bool(phrase), repr(phrase))

    check("unknown tool returns fallback phrase",
          bool(dispatcher.get_filler_phrase("mystery_tool")))
except Exception as e:
    check("filler phrases", False, str(e))

# ── Audio utils ───────────────────────────────────────────────────────────────
print("\n[5] Audio utils")

try:
    # Stateless helpers
    fake_ulaw = bytes([0x7F] * 160)  # 160 bytes of constant ulaw
    pcm = ulaw_to_pcm16k(fake_ulaw)
    check("ulaw_to_pcm16k returns bytes", isinstance(pcm, bytes))
    # 160 ulaw bytes at 8 kHz → upsampled 2x → 320 samples × 2 bytes = 640 bytes
    check("ulaw_to_pcm16k output size ~640 bytes", 600 <= len(pcm) <= 700, f"got {len(pcm)}")

    back = pcm16k_to_ulaw(pcm)
    check("pcm16k_to_ulaw returns bytes", isinstance(back, bytes))
    check("pcm16k_to_ulaw output size ~160 bytes", 140 <= len(back) <= 180, f"got {len(back)}")

    # Stateful stream classes
    inbound = UlawToPcm16kStream()
    chunk1 = inbound.convert(fake_ulaw[:80])
    chunk2 = inbound.convert(fake_ulaw[80:])
    check("UlawToPcm16kStream produces output", len(chunk1) > 0 and len(chunk2) > 0)
    inbound.reset()
    check("UlawToPcm16kStream.reset() works", inbound._state is None)

    outbound = Pcm16kToUlawStream()
    fake_pcm = bytes([0x00] * 640)
    converted = outbound.convert(fake_pcm)
    check("Pcm16kToUlawStream produces output", len(converted) > 0)
    outbound.reset()
    check("Pcm16kToUlawStream.reset() works", outbound._state is None)
except Exception as e:
    check("audio utils", False, str(e))

# ── Prompts ───────────────────────────────────────────────────────────────────
print("\n[6] Prompts")

try:
    check("SYSTEM_INSTRUCTION is non-empty", len(SYSTEM_INSTRUCTION) > 100,
          f"{len(SYSTEM_INSTRUCTION)} chars")
    check("no markdown bullets in SYSTEM_INSTRUCTION",
          "# " not in SYSTEM_INSTRUCTION and "**" not in SYSTEM_INSTRUCTION)
    check("mentions Gmail", "Gmail" in SYSTEM_INSTRUCTION or "email" in SYSTEM_INSTRUCTION.lower())
    check("mentions Calendar", "Calendar" in SYSTEM_INSTRUCTION or "calendar" in SYSTEM_INSTRUCTION.lower())
    check("mentions Google Search", "Google Search" in SYSTEM_INSTRUCTION or "search" in SYSTEM_INSTRUCTION.lower())
    check("INITIAL_GREETING is non-empty", len(INITIAL_GREETING) > 5)
except Exception as e:
    check("prompts", False, str(e))

# ── Config ────────────────────────────────────────────────────────────────────
print("\n[7] Config")

try:
    check("MODEL is set", bool(MODEL), MODEL)
    check("DEFAULT_USER_ID is set", bool(DEFAULT_USER_ID), DEFAULT_USER_ID)
    check("GEMINI_API_KEY loaded from env", bool(GEMINI_API_KEY),
          "set" if GEMINI_API_KEY else "MISSING — set GOOGLE_API_KEY in .env")
    check("DEBUG_LOGGING is bool", isinstance(DEBUG_LOGGING, bool))
except Exception as e:
    check("config", False, str(e))

# ── GeminiSession init (no network) ──────────────────────────────────────────
print("\n[8] GeminiSession init (no network call)")

try:
    session = GeminiSession(user_id="dev_user_1", enable_tools=True)
    check("GeminiSession instantiates", True)
    check("dispatcher attached", session.dispatcher is not None)
    check("user_id stored", session.user_id == "dev_user_1")
    check("tools in config", "tools" in session._config)
    check("response_modalities = AUDIO",
          session._config.get("response_modalities") == ["AUDIO"])
    check("system_instruction set", bool(session._config.get("system_instruction")))

    session_no_tools = GeminiSession(user_id="dev_user_1", enable_tools=False)
    check("GeminiSession with enable_tools=False has no dispatcher",
          session_no_tools.dispatcher is None)
    check("no tools in config when disabled", "tools" not in session_no_tools._config)
except Exception as e:
    check("GeminiSession init", False, str(e))

# ── Summary ───────────────────────────────────────────────────────────────────
print()
print("=" * 60)
passed = sum(results)
total  = len(results)
print(f"Results: {passed}/{total} passed")
if passed == total:
    print("All Phase 5A static checks PASSED — ready for live API testing.")
else:
    failed = total - passed
    print(f"{failed} check(s) FAILED — fix before connecting to Gemini Live.")
print("=" * 60)
