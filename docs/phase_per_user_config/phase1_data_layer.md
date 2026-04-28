# Phase 1 — Per-user Config Data Layer

**Status:** Complete ✓  
**Completed:** Apr 27, 2026  
**Commits:** See `feat: per-user config data layer (Phase 1)` on `dev`

---

## What Was Built

A Firestore-backed per-user config data layer.  Every user's agent settings,
knowledge base, values, education, and resume are now independently stored and
retrievable.  No user shares another user's configuration.

---

## Firestore Schema Added

```
users/{user_id}
  # all existing fields unchanged
  agent_settings: {          ← EMBEDDED (small flat config, read with every auth lookup)
    ai_name: str             default "Bianca"
    ai_role: str             default "AI Chief of Staff"
    ai_voice: str            default "Aoede"
    primary_language: str    default "English"
    secondary_language: str  default ""
    model: str               default "claude-sonnet-4-6"
    temperature: float       default 0.7
    custom_prompt: str       default ""
    slides_template_id: str
    docs_template_id: str
    sheets_template_id: str
    voice_prompt: str
    voice_greeting: str
    email_polling_interval: int  default 15
    email_polling_days: str      default "weekdays"
    google_api_key: str          BYOK — never falls back to env var
    anthropic_api_key: str       BYOK — never falls back to env var
    perplexity_api_key: str      BYOK — never falls back to env var
  }
  onboarding_completed: bool   default false
  onboarding_step: int         default 0  (0=not started, 1–4=in progress, 5=done)

users/{user_id}/knowledge/     ← SUBCOLLECTION (text blobs, updated independently)
  persona             → { content: str, updated_at }
  education_text      → { content: str, updated_at }
  expertise           → { content: str, updated_at }
  company             → { content: str, updated_at }
  education_structured → { degrees: [...], courses: [...], updated_at }
  resume              → { experience: [...], updated_at }

users/{user_id}/values/        ← SUBCOLLECTION
  config              → { items: [...], updated_at }
```

**Why embed `agent_settings` in the user doc:**  
It is small (only strings/numbers) and is read on every chat request alongside
auth — embedding avoids a second Firestore round-trip.

**Why subcollections for knowledge and values:**  
Text content can be long.  Subcollections let each section be updated
independently without touching the user document.  They also allow targeted
Firestore security rules per section.

---

## BYOK (Bring Your Own Key) Policy

API keys (`google_api_key`, `anthropic_api_key`, `perplexity_api_key`) are
stored per-user.  There is **no fallback** to shared environment variables.  
If a user has not set a key, the system will not use a backend-level fallback.
This is enforced starting in Phase 2 when the prompt assembly and LLM selection
are wired to per-user settings.

---

## Files Changed / Created

| File | Change |
|------|--------|
| `backend/models.py` | Added `AgentSettings` Pydantic model; extended `User` with `agent_settings`, `onboarding_completed`, `onboarding_step`; added 12 new CRUD methods to `FirestoreCollections` |
| `backend/user_config_loader.py` | New — `load_user_settings()`, `build_user_knowledge_block()`, `build_user_values_block()`, and private format helpers |
| `backend/test_phase1.py` | New — 34-assertion test suite for the data layer |

---

## CRUD Methods Added to `FirestoreCollections`

| Method | Description |
|--------|-------------|
| `save_user_agent_settings(user_id, settings)` | Merge-write `agent_settings` into user doc |
| `update_onboarding_state(user_id, step, completed)` | Update onboarding progress |
| `save_user_knowledge_section(user_id, section_id, content)` | Write one text section |
| `get_user_knowledge_section(user_id, section_id)` | Read one text section |
| `save_user_education(user_id, data)` | Write structured education |
| `get_user_education(user_id)` | Read structured education |
| `save_user_resume(user_id, data)` | Write work experience |
| `get_user_resume(user_id)` | Read work experience |
| `get_all_user_knowledge_sections(user_id)` | Read all text sections in one call |
| `save_user_values(user_id, values)` | Write values list |
| `get_user_values(user_id)` | Read values list (returns `[]` if unset) |

---

## Test Results

```
34 passed  |  0 failed
```

Tests cover: model defaults, Firestore round-trips for all data types,
knowledge block assembly (header uses per-user `ai_name`), values block
assembly with custom values, onboarding state transitions, and backward
compatibility with legacy user documents that have no `agent_settings` field.

---

## Backward Compatibility

Existing `users/{user_id}` documents that lack the new fields will deserialize
cleanly via Pydantic defaults.  No migration is required for existing users —
they will get default `AgentSettings` until they complete onboarding.  The old
disk-based loaders (`settings_loader.py`, `knowledge_loader.py`, `values.py`)
are **unchanged** — Phase 2 will swap the prompt assembly to use the Firestore
loaders.

---

## What's Next — Phase 2

Wire `user_config_loader` into prompt assembly:

1. `prompts.py` — `get_system_prompt(user_id, ...)` — replace disk loader calls
   with `load_user_settings()`, `build_user_knowledge_block()`,
   `build_user_values_block()`.
2. `chat.py` — pass `user_id` to `get_system_prompt()` (already available).
3. `config.py` — all GET/PUT endpoints read/write Firestore per-user instead
   of shared disk files.  BYOK enforcement: API key endpoints never touch env
   vars.
