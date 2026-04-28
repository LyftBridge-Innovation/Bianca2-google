"""
Phase 3 test — onboarding backend router.

Run from the backend/ directory with the venv active:
    python test_phase3.py

What this tests:
  1. GET /onboarding/state returns completed=False for a fresh user.
  2. POST /onboarding/step updates the step counter.
  3. POST /onboarding/complete with valid data:
     a. Saves agent_settings (ai_name, model, api_key).
     b. Saves knowledge sections (persona, expertise, company).
     c. Saves values list.
     d. Sets onboarding_completed=True, step=5.
  4. GET /onboarding/state now returns completed=True.
  5. POST /onboarding/complete without an API key returns 422/400.
  6. Auth callback response includes onboarding_completed field.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from models import User, FirestoreCollections
from routers.onboarding import (
    get_onboarding_state,
    update_onboarding_step,
    complete_onboarding,
    StepUpdateRequest,
    OnboardingCompleteRequest,
)
from fastapi import HTTPException

PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"
_results: list[tuple[bool, str]] = []

TEST_USER_ID = "test_phase3_onboard_user"


def check(label: str, condition: bool, detail: str = "") -> None:
    symbol = PASS if condition else FAIL
    msg = f"  {symbol} {label}"
    if detail:
        msg += f"\n      {detail}"
    print(msg)
    _results.append((condition, label))


def main():
    print("\n=== Phase 3: Onboarding Router ===\n")

    fs = FirestoreCollections()

    # Create a fresh test user
    fs.create_or_update_user(
        User(user_id=TEST_USER_ID, email="onboard@bianca.test", full_name="Onboard Tester")
    )

    # ── 1. Initial state: not completed ───────────────────────────────────────
    print("1. Initial onboarding state")
    state = get_onboarding_state(user_id=TEST_USER_ID)
    check("completed is False", state["completed"] is False)
    check("step is 0", state["step"] == 0)

    # ── 2. Step update ────────────────────────────────────────────────────────
    print("\n2. Step update")
    result = update_onboarding_step(StepUpdateRequest(user_id=TEST_USER_ID, step=2))
    check("step updated to 2", result["step"] == 2)
    state = get_onboarding_state(user_id=TEST_USER_ID)
    check("Firestore reflects step=2", state["step"] == 2)

    # ── 3. complete_onboarding with valid data ────────────────────────────────
    print("\n3. complete_onboarding with full data")
    result = complete_onboarding(OnboardingCompleteRequest(
        user_id=TEST_USER_ID,
        ai_name="TestAgent",
        ai_role="Chief Tester",
        primary_language="English",
        model="claude-sonnet-4-6",
        anthropic_api_key="sk-test-onboarding-key",
        persona="TestAgent is a meticulous QA engineer who leaves no bug unfound.",
        expertise="Automated testing, CI/CD, and code coverage tooling.",
        company="Bianca Labs — building AI agents that test themselves.",
    ))
    check("complete returns ok=True", result.get("ok") is True)

    # ── 4. Verify all data was saved ─────────────────────────────────────────
    print("\n4. Verify saved data")
    user = fs.get_user(TEST_USER_ID)
    check("onboarding_completed=True", user.onboarding_completed is True)
    check("onboarding_step=5", user.onboarding_step == 5)
    check("ai_name saved", user.agent_settings.ai_name == "TestAgent")
    check("ai_role saved", user.agent_settings.ai_role == "Chief Tester")
    check("anthropic_api_key saved", user.agent_settings.anthropic_api_key == "sk-test-onboarding-key")

    persona = fs.get_user_knowledge_section(TEST_USER_ID, "persona")
    check("persona section saved", "meticulous QA engineer" in persona)

    expertise = fs.get_user_knowledge_section(TEST_USER_ID, "expertise")
    check("expertise section saved", "Automated testing" in expertise)

    company = fs.get_user_knowledge_section(TEST_USER_ID, "company")
    check("company section saved", "Bianca Labs" in company)

    values = fs.get_user_values(TEST_USER_ID)
    check("values saved (defaults)", len(values) > 0)

    # ── 5. GET state now returns completed=True ───────────────────────────────
    print("\n5. State after completion")
    state = get_onboarding_state(user_id=TEST_USER_ID)
    check("completed is True", state["completed"] is True)
    check("step is 5", state["step"] == 5)

    # ── 6. Missing API key raises 400 ─────────────────────────────────────────
    print("\n6. Missing API key → 400 error")
    fs.create_or_update_user(
        User(user_id="test_nokey_user", email="nokey@bianca.test", full_name="No Key")
    )
    raised = False
    try:
        complete_onboarding(OnboardingCompleteRequest(
            user_id="test_nokey_user",
            ai_name="NobodyBot",
            ai_role="Nobody",
            primary_language="English",
            model="claude-sonnet-4-6",
            anthropic_api_key="",   # <-- empty
            google_api_key="",      # <-- empty
            persona="Test persona",
        ))
    except HTTPException as e:
        raised = e.status_code == 400
    check("missing API key raises 400", raised)

    # ── 7. Auth response includes onboarding_completed ────────────────────────
    print("\n7. Auth response model includes onboarding_completed")
    from routers.auth import GoogleCallbackResponse
    resp = GoogleCallbackResponse(
        user_id="x", name="X", email="x@x.com", picture="", onboarding_completed=True
    )
    check("response has onboarding_completed field", resp.onboarding_completed is True)
    resp_false = GoogleCallbackResponse(
        user_id="x", name="X", email="x@x.com", picture=""
    )
    check("default is False", resp_false.onboarding_completed is False)

    # ── Summary ───────────────────────────────────────────────────────────────
    passed = sum(1 for ok, _ in _results if ok)
    failed = sum(1 for ok, _ in _results if not ok)
    print(f"\n{'='*44}")
    print(f"  {passed} passed  |  {failed} failed")
    print(f"{'='*44}\n")

    if failed:
        for ok, label in _results:
            if not ok:
                print(f"  FAIL: {label}")
        sys.exit(1)
    else:
        print("All Phase 3 tests passed.")


if __name__ == "__main__":
    main()
