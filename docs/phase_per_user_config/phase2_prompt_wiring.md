# Phase 2 — Per-user Config Wired into Prompt Assembly

**Status:** Complete ✓  
**Completed:** Apr 28, 2026  
**Depends on:** Phase 1 (data layer)

---

## What Was Built

Every chat request now assembles its system prompt from the authenticated
user's own Firestore config instead of shared disk files.  The config API
endpoints (`/config/*`) are now per-user.  BYOK is enforced end-to-end: the
LLM is instantiated with the user's own API key — no fallback to shared
environment variables.

---

## Changes by File

### `backend/prompts.py`

| Before | After |
|--------|-------|
| `get_system_prompt(world_model, authorizations, constraints)` | `get_system_prompt(user_id, world_model, authorizations, constraints)` |
| `_build_identity_block()` called `load_settings()` internally | `_build_identity_block(settings)` takes the pre-loaded dict |
| Imported `load_settings`, `build_knowledge_block`, `build_values_block` (disk) | Imports `load_user_settings`, `build_user_knowledge_block`, `build_user_values_block` (Firestore) |
| Perplexity block triggered by `settings key OR env var PERPLEXITY_API_KEY` | Perplexity block triggered by **user's BYOK key only** |

### `backend/routers/chat.py`

| Before | After |
|--------|-------|
| `_get_llm()` — global singleton, reads `load_settings()` (disk) | `_get_llm(user_id)` — per-user settings, BYOK keys, cache keyed by config fingerprint |
| API key resolution: `settings key OR os.getenv(...)` | API key resolution: **user's Firestore key only**, no env var fallback |
| `get_system_prompt(world_model=..., ...)` | `get_system_prompt(user_id=..., world_model=..., ...)` — all 4 call sites updated |
| Document creation early intercept used `load_settings()` + `os.environ.get(ANTHROPIC_API_KEY)` | Uses `load_user_settings(user_id)` + user's BYOK `anthropic_api_key` only |

### `backend/routers/config.py`

Fully rewritten.  All endpoints now require `user_id`:

| Endpoint | GET | PUT/POST |
|----------|-----|---------|
| `/config/knowledge` | `?user_id=` | `user_id` in body |
| `/config/values` | `?user_id=` | `user_id` in body |
| `/config/settings` | `?user_id=` | `user_id` in body |
| `/config/education` | `?user_id=` | `user_id` in body |
| `/config/resume` | `?user_id=` | `user_id` in body |
| `/config/phone` | `?user_id=` | `user_id` in body (unchanged) |
| `/config/security-status` | `?user_id=` | — |
| `/config/system-prompt` | `?user_id=` | — |

**Security status is now BYOK-only** — `google_api_key`, `anthropic_api_key`,
`perplexity_api_key` fields reflect only the user's stored key, never env vars.

**Knowledge section IDs changed** from old disk path format (`01_persona`) to
flat Firestore keys (`persona`, `education_text`, `expertise`, `company`).

### `frontend/src/api/client.js`

All config functions updated to accept and pass `userId`:

| Old signature | New signature |
|--------------|--------------|
| `getKnowledge()` | `getKnowledge(userId)` |
| `saveKnowledgeFile(category, filename, content)` | `saveKnowledgeSection(userId, sectionId, content)` |
| `getValues()` | `getValues(userId)` |
| `saveValues(values)` | `saveValues(userId, values)` |
| `getSettings()` | `getSettings(userId)` |
| `updateSettings(settings)` | `updateSettings(userId, settings)` |
| `getSystemPrompt()` | `getSystemPrompt(userId)` |
| `getEducation()` | `getEducation(userId)` |
| `saveEducation(degrees, courses)` | `saveEducation(userId, degrees, courses)` |
| `getSecurityStatus()` | `getSecurityStatus(userId)` |
| `getResume()` | `getResume(userId)` |
| `saveResume(experience)` | `saveResume(userId, experience)` |

### `frontend/src/pages/NeuralConfig.jsx`

- All 13 config API call sites updated to pass `user.userId`.
- Knowledge section render updated: old shape was `{category, files: [{filename, content}]}`;
  new shape is `{section_id, label, content}` — flat, no nested files array.
- Empty knowledge section now shows `_No content yet. Click Edit to add._`
  instead of nothing.

---

## BYOK LLM Selection Logic

```
user calls /chat/stream
  ↓
load_user_settings(user_id)  ← Firestore only
  ↓
model starts with "claude"?
  ├── yes → ChatAnthropic(api_key=user.anthropic_api_key)
  │         raises ValueError if key is empty
  └── no
       ├── user.google_api_key set? → ChatGoogleGenerativeAI(google_api_key=...)
       └── no key → ChatVertexAI(ADC)  ← only valid in Cloud Run / local with gcloud auth
```

The LLM cache is keyed by `"{model}::{temperature}::{key_prefix12}"` — users
with the same model and key share one instance; users with different keys get
separate instances.

---

## Test Results

```
25 passed  |  0 failed
```

Tests cover: settings load for configured/unconfigured/unknown users, full
prompt assembly with per-user identity/knowledge/values, empty-user defaults,
world model injection, access control injection, Perplexity conditional on
BYOK key, and BYOK security-status (no env var fallback).

---

## What's Next — Phase 3

Onboarding flow so new users can configure their agent from scratch:

1. Backend `routers/onboarding.py` — `GET /onboarding/state`,
   `POST /onboarding/step`, `POST /onboarding/complete`
2. Frontend `OnboardingFlow.jsx` — 4-step wizard shown on first login:
   - Step 1: Agent identity (name, role, language, model)
   - Step 2: API key (BYOK — user enters their own Anthropic or Google key)
   - Step 3: Persona (bio text)
   - Step 4: Values (confirm/customize)
3. Check `onboarding_completed` after login → redirect to wizard if false
