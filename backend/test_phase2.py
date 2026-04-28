"""
Phase 2 test — per-user config wired into prompt assembly.

Run from the backend/ directory with the venv active:
    python test_phase2.py

What this tests:
  1. get_system_prompt(user_id) assembles a prompt using the test user's
     Firestore config (set up in Phase 1 tests).
  2. The identity block uses the per-user ai_name ("Aria") not the default ("Bianca").
  3. The knowledge block contains the user's custom persona text.
  4. The values block contains the user's custom values.
  5. A user with no knowledge configured gets an empty knowledge block (safe).
  6. A user with no values configured gets the default BIANCA_VALUES block.
  7. load_user_settings returns the correct model for the test user.
  8. The security-status endpoint correctly reflects BYOK keys (no env var fallback).
  9. get_system_prompt with world_model injects the world model block.
 10. get_system_prompt with authorizations/constraints injects access control.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from models import User, AgentSettings, FirestoreCollections
from prompts import get_system_prompt
from user_config_loader import load_user_settings, build_user_knowledge_block, build_user_values_block

PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"
_results: list[tuple[bool, str]] = []

TEST_USER_ID = "test_phase1_user_bianca"   # created in Phase 1 test
EMPTY_USER_ID = "test_phase2_empty_user"


def check(label: str, condition: bool, detail: str = "") -> None:
    symbol = PASS if condition else FAIL
    msg = f"  {symbol} {label}"
    if detail:
        msg += f"\n      {detail}"
    print(msg)
    _results.append((condition, label))


def main():
    print("\n=== Phase 2: Per-user Prompt Assembly ===\n")

    fs = FirestoreCollections()

    # Ensure a fresh "empty" user exists (no knowledge, no values, no custom settings)
    fs.create_or_update_user(
        User(user_id=EMPTY_USER_ID, email="empty@bianca.test", full_name="Empty User")
    )

    # ── 1. Settings round-trip via load_user_settings ─────────────────────────
    print("1. load_user_settings for test user (Aria)")
    s = load_user_settings(TEST_USER_ID)
    check("ai_name is 'Aria'", s["ai_name"] == "Aria", f"got: {s['ai_name']}")
    check("model is claude-sonnet-4-6", s["model"] == "claude-sonnet-4-6")
    check("anthropic_api_key present", bool(s["anthropic_api_key"]))

    # ── 2. load_user_settings for unknown user returns defaults ───────────────
    print("\n2. load_user_settings for unknown user → defaults")
    d = load_user_settings("definitely_nonexistent_user_xyz")
    check("defaults to ai_name 'Bianca'", d["ai_name"] == "Bianca")
    check("defaults to empty api keys", d["anthropic_api_key"] == "")

    # ── 3. System prompt for configured test user ─────────────────────────────
    print("\n3. get_system_prompt for test user 'Aria'")
    prompt = get_system_prompt(user_id=TEST_USER_ID)
    check("prompt is non-empty", len(prompt) > 100)
    check("identity uses 'Aria'", "You are Aria" in prompt, f"start: {prompt[:80]}")
    check("knowledge block present", "ARIA'S KNOWLEDGE BASE" in prompt)
    check("persona content in prompt", "sharp, direct strategic advisor" in prompt)
    check("expertise content in prompt", "DOMAIN EXPERTISE" in prompt)
    check("values block present", "CORE VALUES" in prompt)
    check("custom values in prompt", "Clarity First" in prompt)

    # ── 4. System prompt for empty user (no knowledge, no values) ─────────────
    print("\n4. get_system_prompt for empty user")
    ep = get_system_prompt(user_id=EMPTY_USER_ID)
    check("prompt still non-empty (identity + defaults)", len(ep) > 50)
    check("identity uses default name 'Bianca'", "You are Bianca" in ep)
    check("default BIANCA_VALUES injected", "Draft Before Send" in ep)
    check("no knowledge block (no files configured)", "KNOWLEDGE BASE" not in ep)

    # ── 5. World model injection ───────────────────────────────────────────────
    print("\n5. World model injection")
    wm = [{"category": "people", "title": "CEO", "content": "John Smith", "enabled": True}]
    p_wm = get_system_prompt(user_id=TEST_USER_ID, world_model=wm)
    check("WORLD CONTEXT block present", "WORLD CONTEXT" in p_wm)
    check("CEO entry present", "John Smith" in p_wm)

    # ── 6. Access control injection ───────────────────────────────────────────
    print("\n6. Access control injection")
    p_ac = get_system_prompt(
        user_id=TEST_USER_ID,
        authorizations=["Send emails on behalf of user"],
        constraints=["Never access financial data"],
    )
    check("ACCESS CONTROL block present", "ACCESS CONTROL" in p_ac)
    check("authorisation present", "Send emails on behalf of user" in p_ac)
    check("constraint present", "Never access financial data" in p_ac)

    # ── 7. Perplexity block only when key is set ──────────────────────────────
    print("\n7. Perplexity block conditional on BYOK key")
    p_no_pplx = get_system_prompt(user_id=EMPTY_USER_ID)  # no perplexity key
    check("no Perplexity block when key is absent", "Perplexity" not in p_no_pplx)

    # Set a perplexity key on the test user and check it appears
    from models import AgentSettings
    existing = load_user_settings(TEST_USER_ID)
    updated = AgentSettings(**{**existing, "perplexity_api_key": "pplx-testkey-123"})
    fs.save_user_agent_settings(TEST_USER_ID, updated)
    p_with_pplx = get_system_prompt(user_id=TEST_USER_ID)
    check("Perplexity block injected when BYOK key is set", "Perplexity" in p_with_pplx)
    # Clean up — remove the test perplexity key
    fs.save_user_agent_settings(TEST_USER_ID, AgentSettings(**{**existing, "perplexity_api_key": ""}))

    # ── 8. BYOK: security status reflects per-user keys, not env vars ─────────
    print("\n8. Security status is per-user BYOK")
    from routers.config import get_security_status
    status_configured = get_security_status(user_id=TEST_USER_ID)
    check("anthropic_api_key shows True for test user", status_configured["anthropic_api_key"] is True)

    status_empty = get_security_status(user_id=EMPTY_USER_ID)
    check("anthropic_api_key shows False for empty user (BYOK, no env fallback)", status_empty["anthropic_api_key"] is False)

    # ── Summary ───────────────────────────────────────────────────────────────
    passed = sum(1 for ok, _ in _results if ok)
    failed = sum(1 for ok, _ in _results if not ok)
    print(f"\n{'='*44}")
    print(f"  {passed} passed  |  {failed} failed")
    print(f"{'='*44}\n")

    if failed:
        print("FAILED tests:")
        for ok, label in _results:
            if not ok:
                print(f"  - {label}")
        sys.exit(1)
    else:
        print("All Phase 2 tests passed.")


if __name__ == "__main__":
    main()
