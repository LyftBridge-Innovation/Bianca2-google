"""
Phase 1 test — per-user config data layer.

Run from the backend/ directory with the venv active:
    python test_phase1.py

What this tests:
  1. User document: new AgentSettings and onboarding fields have correct defaults.
  2. AgentSettings write/read round-trip via Firestore.
  3. Knowledge section write/read round-trip.
  4. Education structured data write/read round-trip.
  5. Resume write/read round-trip.
  6. Values write/read round-trip.
  7. user_config_loader.load_user_settings() returns settings dict.
  8. user_config_loader.build_user_knowledge_block() assembles correct text.
  9. user_config_loader.build_user_values_block() assembles correct text.
 10. Existing User deserialization is backward-compatible (no agent_settings in doc).
"""

import sys
import os

# Allow running from backend/ directory
sys.path.insert(0, os.path.dirname(__file__))

from models import User, AgentSettings, FirestoreCollections
from user_config_loader import (
    load_user_settings,
    build_user_knowledge_block,
    build_user_values_block,
)

PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"

_results: list[tuple[bool, str]] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    symbol = PASS if condition else FAIL
    msg = f"  {symbol} {label}"
    if detail:
        msg += f"\n      {detail}"
    print(msg)
    _results.append((condition, label))


# ── Test constants ─────────────────────────────────────────────────────────────

TEST_USER_ID = "test_phase1_user_bianca"

SAMPLE_SETTINGS = AgentSettings(
    ai_name="Aria",
    ai_role="Head of Strategy",
    model="claude-sonnet-4-6",
    temperature=0.5,
    anthropic_api_key="sk-test-key-abc",
    google_api_key="",
    perplexity_api_key="pplx-test",
)

SAMPLE_KNOWLEDGE = {
    "persona": "Aria is a sharp, direct strategic advisor with a background in consulting.",
    "education_text": "Trained on executive strategy frameworks and operational research.",
    "expertise": "M&A advisory, OKR design, board communications, and fundraising.",
    "company": "Lyftbridge — a platform connecting AI agents with enterprise workflows.",
}

SAMPLE_EDUCATION = {
    "degrees": [
        {"level": "MBA", "name": "Master of Business Administration", "field": "Strategy", "institution": "Wharton"},
    ],
    "courses": [
        {"code": "STRAT-101", "name": "Corporate Strategy", "description": "Frameworks for competitive positioning."},
    ],
}

SAMPLE_RESUME = {
    "experience": [
        {"title": "Principal", "organization": "McKinsey & Co", "startDate": "2018", "endDate": "2022", "description": "Led transformation programs for F500 clients."},
        {"title": "Head of Strategy", "organization": "Lyftbridge", "startDate": "2022", "endDate": "", "description": ""},
    ]
}

SAMPLE_VALUES = [
    {"priority": 1, "title": "Clarity First", "rule": "Every communication must be clear and unambiguous."},
    {"priority": 2, "title": "No Surprises", "rule": "Always surface risks before they materialise."},
]


# ── Run tests ──────────────────────────────────────────────────────────────────

def main():
    print("\n=== Phase 1: Per-user Config Data Layer ===\n")

    fs = FirestoreCollections()

    # ── 1. Default AgentSettings values ───────────────────────────────────────
    print("1. AgentSettings defaults")
    defaults = AgentSettings()
    check("ai_name defaults to 'Bianca'", defaults.ai_name == "Bianca")
    check("model defaults to 'claude-sonnet-4-6'", defaults.model == "claude-sonnet-4-6")
    check("API keys default to empty string", defaults.anthropic_api_key == "" and defaults.google_api_key == "")
    check("onboarding fields on User", User(user_id="x", email="x@x.com").onboarding_completed is False)

    # ── 2. AgentSettings write / read round-trip ──────────────────────────────
    print("\n2. AgentSettings Firestore round-trip")
    # Simulate what auth does: create the user document first.
    seed_user = User(user_id=TEST_USER_ID, email="test_phase1@bianca.test", full_name="Phase1 Tester")
    fs.create_or_update_user(seed_user)
    fs.save_user_agent_settings(TEST_USER_ID, SAMPLE_SETTINGS)
    loaded = load_user_settings(TEST_USER_ID)
    check("ai_name saved and loaded", loaded["ai_name"] == "Aria", f"got: {loaded['ai_name']}")
    check("ai_role saved and loaded", loaded["ai_role"] == "Head of Strategy")
    check("anthropic_api_key saved and loaded", loaded["anthropic_api_key"] == "sk-test-key-abc")
    check("temperature saved and loaded", loaded["temperature"] == 0.5)

    # ── 3. Knowledge text sections ────────────────────────────────────────────
    print("\n3. Knowledge text sections")
    for section_id, content in SAMPLE_KNOWLEDGE.items():
        fs.save_user_knowledge_section(TEST_USER_ID, section_id, content)
    for section_id, expected in SAMPLE_KNOWLEDGE.items():
        got = fs.get_user_knowledge_section(TEST_USER_ID, section_id)
        check(f"section '{section_id}' round-trip", got == expected)

    # ── 4. Education structured ───────────────────────────────────────────────
    print("\n4. Education structured data")
    fs.save_user_education(TEST_USER_ID, SAMPLE_EDUCATION)
    edu = fs.get_user_education(TEST_USER_ID)
    check("degree saved", len(edu["degrees"]) == 1)
    check("degree institution", edu["degrees"][0]["institution"] == "Wharton")
    check("course saved", len(edu["courses"]) == 1)
    check("course name", edu["courses"][0]["name"] == "Corporate Strategy")

    # ── 5. Resume ─────────────────────────────────────────────────────────────
    print("\n5. Resume / work experience")
    fs.save_user_resume(TEST_USER_ID, SAMPLE_RESUME)
    resume = fs.get_user_resume(TEST_USER_ID)
    check("two experiences saved", len(resume["experience"]) == 2)
    check("first role title", resume["experience"][0]["title"] == "Principal")

    # ── 6. Values ─────────────────────────────────────────────────────────────
    print("\n6. Values")
    fs.save_user_values(TEST_USER_ID, SAMPLE_VALUES)
    vals = fs.get_user_values(TEST_USER_ID)
    check("two values saved", len(vals) == 2)
    check("first value title", vals[0]["title"] == "Clarity First")

    # ── 7. Knowledge block assembly ───────────────────────────────────────────
    print("\n7. Knowledge block assembly")
    kb = build_user_knowledge_block(TEST_USER_ID)
    check("knowledge block is non-empty", len(kb) > 0)
    check("header uses ai_name 'ARIA'", "ARIA'S KNOWLEDGE BASE" in kb, f"header: {kb[:60]}")
    check("persona section present", "PERSONA & IDENTITY" in kb)
    check("expertise section present", "DOMAIN EXPERTISE" in kb)
    check("education structured block present", "EDUCATIONAL BACKGROUND" in kb)
    check("resume block present", "PROFESSIONAL EXPERIENCE" in kb)

    # ── 8. Values block assembly ──────────────────────────────────────────────
    print("\n8. Values block assembly")
    vb = build_user_values_block(TEST_USER_ID)
    check("values block is non-empty", len(vb) > 0)
    check("custom value 'Clarity First' present", "Clarity First" in vb)
    check("custom value 'No Surprises' present", "No Surprises" in vb)

    # ── 9. Onboarding state update ────────────────────────────────────────────
    print("\n9. Onboarding state")
    fs.update_onboarding_state(TEST_USER_ID, step=2)
    user = fs.get_user(TEST_USER_ID)
    check("onboarding_step updated to 2", user is not None and user.onboarding_step == 2)
    check("onboarding_completed still False", user is not None and user.onboarding_completed is False)
    fs.update_onboarding_state(TEST_USER_ID, step=5, completed=True)
    user = fs.get_user(TEST_USER_ID)
    check("onboarding_completed set to True", user is not None and user.onboarding_completed is True)

    # ── 10. Backward compat: User model with no agent_settings in raw doc ──────
    print("\n10. Backward compatibility")
    raw = {"user_id": "legacy_user", "email": "old@example.com"}
    legacy_user = User(**raw)
    check("legacy user gets default AgentSettings", legacy_user.agent_settings.ai_name == "Bianca")
    check("legacy user onboarding_completed=False", legacy_user.onboarding_completed is False)

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
        print("All Phase 1 tests passed.")


if __name__ == "__main__":
    main()
