"""
One-time setup script for existing users.

Discovers all real user accounts in Firestore (excluding test users),
runs the disk-to-Firestore config migration for each, and seeds their
API keys from the current .env file.

Run once after deploying Phase 1–3:
    cd backend && source ../venv/bin/activate && python setup_existing_users.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Load .env before anything else
from dotenv import load_dotenv
load_dotenv()

from models import User, AgentSettings, FirestoreCollections
from routers.admin import migrate_disk_config_to_firestore

_TEST_USER_PREFIXES = ("test_", "dev_user_", "legacy_")

ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
GOOGLE_KEY    = os.getenv("GOOGLE_API_KEY", "").strip()


def is_test_user(user_id: str) -> bool:
    return any(user_id.startswith(p) for p in _TEST_USER_PREFIXES)


def main():
    print("\n=== Existing-user setup: disk config → Firestore ===\n")

    fs = FirestoreCollections()

    # ── Discover all users in Firestore ───────────────────────────────────────
    all_users_docs = fs.db.collection("users").stream()
    users = []
    for doc in all_users_docs:
        data = doc.to_dict()
        try:
            users.append(User(**data))
        except Exception as e:
            print(f"  [skip] Could not deserialise user {doc.id}: {e}")

    real_users = [u for u in users if not is_test_user(u.user_id)]
    test_users = [u for u in users if is_test_user(u.user_id)]

    print(f"Found {len(users)} total users in Firestore")
    print(f"  Real users : {len(real_users)}")
    print(f"  Test users : {len(test_users)} (skipped)\n")

    if not real_users:
        print("No real users found. Nothing to migrate.")
        print("(If you haven't signed in yet, do that first, then re-run this script.)")
        return

    if not ANTHROPIC_KEY and not GOOGLE_KEY:
        print("WARNING: No API keys found in .env (ANTHROPIC_API_KEY / GOOGLE_API_KEY).")
        print("  Users will need to enter keys via Neural Config → Security tab.\n")

    # ── Process each real user ────────────────────────────────────────────────
    for user in real_users:
        print(f"── User: {user.email or user.user_id} ({user.user_id[:16]}…)")

        already_done = user.onboarding_completed
        if already_done:
            print(f"   onboarding already complete — re-running migration to refresh disk config\n")
        else:
            print(f"   onboarding NOT complete — running full migration")

        # Step 1: migrate disk config (knowledge, settings, values, education, resume)
        try:
            result = migrate_disk_config_to_firestore(user.user_id)
            migrated = result.get("migrated", {})
            knowledge_sections = list(migrated.get("knowledge", {}).keys())
            print(f"   ✓ settings migrated")
            print(f"   ✓ knowledge sections: {knowledge_sections}")
            if migrated.get("education"):
                print(f"   ✓ education migrated")
            if migrated.get("resume"):
                print(f"   ✓ resume migrated")
            if migrated.get("values"):
                print(f"   ✓ values migrated")
            print(f"   ✓ onboarding_completed = True")
        except Exception as e:
            print(f"   ✗ migration failed: {e}")
            continue

        # Step 2: seed API keys from .env (BYOK — env vars no longer used at runtime)
        if ANTHROPIC_KEY or GOOGLE_KEY:
            reloaded = fs.get_user(user.user_id)
            current = reloaded.agent_settings.model_dump() if reloaded else {}
            patched = False

            if ANTHROPIC_KEY and not current.get("anthropic_api_key", "").strip():
                current["anthropic_api_key"] = ANTHROPIC_KEY
                patched = True
                print(f"   ✓ ANTHROPIC_API_KEY seeded from .env")
            elif current.get("anthropic_api_key", ""):
                print(f"   ✓ ANTHROPIC_API_KEY already set in Firestore — kept")

            if GOOGLE_KEY and not current.get("google_api_key", "").strip():
                current["google_api_key"] = GOOGLE_KEY
                patched = True
                print(f"   ✓ GOOGLE_API_KEY seeded from .env")
            elif current.get("google_api_key", ""):
                print(f"   ✓ GOOGLE_API_KEY already set in Firestore — kept")

            if patched:
                fs.save_user_agent_settings(user.user_id, AgentSettings(**current))

        print()

    # ── Summary ───────────────────────────────────────────────────────────────
    print("=" * 52)
    print(f"  Done. {len(real_users)} user(s) migrated and ready.")
    print("=" * 52)
    print()
    print("Next steps:")
    print("  1. Deploy the updated backend to Cloud Run.")
    print("  2. Sign in — you'll land directly in chat (no wizard).")
    print("  3. New users who sign in for the first time will see the 4-step wizard.")
    print()


if __name__ == "__main__":
    main()
