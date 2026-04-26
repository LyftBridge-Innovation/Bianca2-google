# Frontend UI Features Needing Backend Support

This document tracks which Neural Config UI elements are currently:
1. **Connected** — UI saves data via API and backend consumes it
2. **Saves only** — UI saves data via API but backend doesn't consume it yet
3. **Local state** — UI works but data is not persisted at all

---

## Fully Connected (Working End-to-End)

| Feature | Frontend | Backend | Notes |
|---------|----------|---------|-------|
| AI Name | Identity tab | `prompts.py` reads from settings.json | ✅ Wired |
| AI Role | Identity tab | `prompts.py` reads from settings.json | ✅ Wired |
| AI Voice | Identity tab | Saved to settings.json | Voice pipeline still hardcoded |
| Languages | Identity tab | Saved to settings.json | Not used by prompts yet |
| Knowledge Files | Persona > Knowledge | Saved to disk, `knowledge_loader.py` reads | ✅ Fully connected |
| Values | Values tab | Saved to values_override.json, `values.py` reads | ✅ Fully connected |
| Model | System Prompt tab | `chat.py` reads from settings.json | ✅ Wired |
| Temperature | System Prompt tab | `chat.py` reads from settings.json | ✅ Wired |
| Custom Prompt | System Prompt tab | `prompts.py` prepends to system prompt | ✅ Wired |
| System Prompt Preview | System Prompt tab | `GET /config/system-prompt` | ✅ Read-only preview |
| User Skills | Skills tab | Full CRUD via `/skills/` endpoints | ✅ Fully connected |
| Education > Degrees | Persona > Education | Saved to education.json, `knowledge_loader.py` injects | ✅ Fully connected |
| Education > Courses | Persona > Education | Saved to education.json, `knowledge_loader.py` injects | ✅ Fully connected |

---

## Saves to Settings but Backend Doesn't Consume

| Feature | Frontend | Saved To | Backend Gap |
|---------|----------|----------|-------------|
| Voice Greeting | Integrations tab | settings.json | `voice_pipeline/voice_prompts.py` hardcodes greeting |
| Voice Prompt | Integrations tab | settings.json | Voice pipeline doesn't read settings |
| Email Polling Interval | Integrations tab | settings.json | No email polling system exists |
| Email Polling Days | Integrations tab | settings.json | No email polling system exists |
| Slides Template ID | Integrations tab | settings.json | `tools/docs_writer.py` doesn't read it |
| Docs Template ID | Integrations tab | settings.json | `tools/docs_writer.py` doesn't read it |
| Sheets Template ID | Integrations tab | settings.json | `tools/sheets_writer.py` doesn't read it |

---

## Local State Only (No Backend)

| Feature | Frontend Tab | What It Does | Backend Needed |
|---------|--------------|--------------|----------------|
| **Resume > Experience** | Persona > Resume | Add/remove work experience | Firestore collection `users/{id}/experience` |
| **World Model** | World Model tab | Add/edit/delete entries per category | Firestore collection `world_model` |
| **Contacts** | Contacts tab | Add/edit/delete contacts | Firestore collection `users/{id}/contacts` |
| **Authorizations** | Access Control tab | Add/remove permission entries | Firestore or settings.json `authorizations` array |
| **Constraints** | Access Control tab | Add/remove constraint entries | Firestore or settings.json `constraints` array |
| **Security Keys Status** | Security tab | Shows configured/not configured badges | API endpoint to check env var presence |

---

## Priority Recommendations

### High Priority (Core Functionality)
1. **Templates** — Wire `slides_template_id`, `docs_template_id`, `sheets_template_id` into the GWS tool handlers so created docs use branded templates
2. **Voice Pipeline** — Make `voice_prompts.py` read from settings.json so voice greeting and prompt are configurable

### Medium Priority (Enhances UX)
3. **World Model** — Create backend CRUD endpoints + inject into prompt when skills activate
4. **Contacts** — Create backend CRUD + use for caller identification
5. **Access Control** — Persist authorizations/constraints + inject into system prompt

### Lower Priority (Nice to Have)
6. **Resume** — Persona flavor; could be injected into knowledge block like Education
7. **Security Keys Status** — Create an endpoint that checks which env vars are set (without revealing values)

---

## Implementation Notes

### For Template IDs
In `backend/tools/docs_writer.py` and `sheets_writer.py`:
```python
from settings_loader import load_settings

def create_document(...):
    settings = load_settings()
    template_id = settings.get('docs_template_id')
    if template_id:
        # Use gws copy command with template
    else:
        # Create blank document
```

### For Voice Pipeline
In `voice_pipeline/voice_prompts.py`, replace hardcoded `SYSTEM_INSTRUCTION` with a function:
```python
from settings_loader import load_settings

def get_voice_system_instruction():
    settings = load_settings()
    custom = settings.get('voice_prompt', '')
    greeting = settings.get('voice_greeting', 'Hello!')
    # Build instruction dynamically
```

### For Contacts/World Model/Access Control
Create new router `backend/routers/user_data.py` with:
- `GET/POST/DELETE /user-data/contacts`
- `GET/POST/DELETE /user-data/world-model`
- `GET/PUT /user-data/access-control`

Store in Firestore under `users/{user_id}/` subcollections.
