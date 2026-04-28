# Phase 3 — Onboarding Flow

**Status:** Complete ✓  
**Completed:** Apr 28, 2026  
**Depends on:** Phase 1, Phase 2

---

## What Was Built

New users who sign in for the first time are automatically redirected to a
4-step onboarding wizard that configures their agent from scratch.  On
completion, all config is saved to Firestore and the user lands directly in
the chat.

---

## User Flow

```
Google Sign-In
  ↓
/auth/google/callback  ← now returns onboarding_completed field
  ↓
onboarding_completed = false?
  ├── yes → show OnboardingFlow wizard
  └── no  → show AppLayout (chat)
```

**4 wizard steps:**

| Step | What the user does |
|------|--------------------|
| 1. Identity | Names the agent, sets role, language, picks a model |
| 2. API Key | Enters their own Anthropic or Google key (BYOK enforced) |
| 3. Persona | Writes persona bio + domain expertise + company context |
| 4. Values | Reviews and edits the default behavioral values |

On "Launch agent": `POST /onboarding/complete` — saves everything atomically,
sets `onboarding_completed=True`.

---

## Files Changed / Created

| File | Change |
|------|--------|
| `backend/routers/onboarding.py` | New — 3 endpoints: `GET /onboarding/state`, `POST /onboarding/step`, `POST /onboarding/complete` |
| `backend/main.py` | Register `onboarding_router` |
| `backend/routers/auth.py` | `GoogleCallbackResponse` now includes `onboarding_completed` field |
| `frontend/src/pages/OnboardingFlow.jsx` | New — 4-step wizard component |
| `frontend/src/pages/OnboardingFlow.css` | New — glassmorphism wizard styles using design system tokens |
| `frontend/src/context/AuthContext.jsx` | Store `onboardingCompleted` from auth response; add `markOnboardingComplete()` |
| `frontend/src/api/client.js` | Add `getOnboardingState`, `updateOnboardingStep`, `completeOnboarding` |
| `frontend/src/App.jsx` | Check `user.onboardingCompleted` after auth → route to wizard or chat |

---

## Backend API

### `GET /onboarding/state?user_id=`
```json
{ "completed": false, "step": 0 }
```

### `POST /onboarding/step`
```json
{ "user_id": "...", "step": 2 }
→ { "ok": true, "step": 2 }
```

### `POST /onboarding/complete`
```json
{
  "user_id": "...",
  "ai_name": "Aria",
  "ai_role": "Head of Strategy",
  "primary_language": "English",
  "model": "claude-sonnet-4-6",
  "anthropic_api_key": "sk-ant-...",
  "google_api_key": "",
  "persona": "Aria is a...",
  "expertise": "M&A, OKRs...",
  "company": "Lyftbridge...",
  "values": [...]       ← optional, defaults to BIANCA_VALUES
}
→ { "ok": true, "message": "Onboarding complete" }
```

**Validation:** Returns `400` if both `anthropic_api_key` and `google_api_key`
are empty — at least one BYOK key is required.

---

## Test Results

```
19 passed  |  0 failed
```

---

# Phase 4 — Migration Endpoint

**Status:** Complete ✓  
**Completed:** Apr 28, 2026

---

## What Was Built

Admin endpoint that copies the current global disk config (the old single-user
state) into Firestore for any specific user.  Allows existing users to be
onboarded without going through the wizard manually.

---

## Endpoint

### `POST /admin/migrate-config/{user_id}`

Copies from disk to Firestore:
- `backend/knowledge/settings.json` → `users/{user_id}.agent_settings`
- `backend/knowledge/01_persona/` → `users/{user_id}/knowledge/persona`
- `backend/knowledge/02_education/` → `users/{user_id}/knowledge/education_text`
- `backend/knowledge/03_expertise/` → `users/{user_id}/knowledge/expertise`
- `backend/knowledge/04_company/` → `users/{user_id}/knowledge/company`
- `backend/knowledge/education.json` → `users/{user_id}/knowledge/education_structured`
- `backend/knowledge/resume.json` → `users/{user_id}/knowledge/resume`
- `backend/knowledge/values_override.json` → `users/{user_id}/values/config`

Sets `onboarding_completed=True, step=5` — the user bypasses the wizard.

**API key preservation:** any API keys already stored in the user's Firestore
`agent_settings` are kept (not overwritten by the disk defaults, which are
typically blank).

Safe to run multiple times — idempotent.

---

## Migration Verification

```
Migration result: {
  "ok": true,
  "migrated": {
    "settings": true,
    "knowledge": { "persona": true, "education_text": true, "expertise": true, "company": true },
    "education": true,
    "onboarding_completed": true
  }
}
persona migrated: 3111 chars
```

---

## Overall Test Summary (Phases 1–3)

```
Phase 1: 34 passed | 0 failed
Phase 2: 25 passed | 0 failed
Phase 3: 19 passed | 0 failed
Total:   78 passed | 0 failed
```
