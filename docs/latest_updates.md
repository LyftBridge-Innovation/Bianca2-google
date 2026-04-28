# Latest Updates — Apr 26 2026

## Summary

This session diagnosed and fixed production Python errors on Cloud Run, then deployed the fixes.

---

## Bug Fixes

### 1. PDF generation crash — `KeyError: "Style 'Heading1' already defined in stylesheet"`

**Root cause:** The LLM was generating `reportlab` code that called `styles.add(ParagraphStyle('Heading1', ...))`. The `Heading1` style already exists in `getSampleStyleSheet()`, so `reportlab` throws a `KeyError` and the entire document script crashes.

**Fix:** `backend/document_skills/pdf_instructions.md` — added a hard rule listing all built-in style names (`Heading1`–`Heading6`, `Normal`, `Title`, `BodyText`, etc.) that must **never** be passed to `styles.add()`. Added correct code examples showing how to reference existing styles vs. create custom ones with unique names.

---

### 2. Document script timeout — Python subprocess killed after 120 s

**Root cause:** LLM-generated document code (pdf / xlsx) was likely making a network call (e.g. downloading an image or font) that silently hangs inside Cloud Run's sandbox, eventually hitting the 120 s subprocess timeout.

**Fix:** Added a `CRITICAL: No network calls` section to all four document instruction files:
- `backend/document_skills/pdf_instructions.md`
- `backend/document_skills/xlsx_instructions.md`
- `backend/document_skills/pptx_instructions.md`
- `backend/document_skills/docx_instructions.md`

Rule: scripts must be fully self-contained, no `urllib` / `requests` / `fetch` / `axios`, must complete in under 30 s.

---

### 3. Blank UI after long-running tasks (chat.py streaming fix)

**Root cause:** After `_get_llm().invoke(messages)` returned a full response with tool calls handled, the code called `_get_llm().stream(messages)` a second time — a redundant API call that could return empty or diverge from the already-processed response, causing the UI to render nothing.

**Fix:** `backend/routers/chat.py` — removed the second `stream()` call. The content from the existing `invoke()` response is now yielded directly as a single `token` SSE event.

---

### 4. Duplicate Claude Sonnet 4.6 model in Neural Config

**Root cause:** Two entries with `id: 'claude-sonnet-4-6'` existed in `MODEL_GROUPS` in `NeuralConfig.jsx`.

**Fix:** Removed the redundant entry — only one `Claude Sonnet 4.6` option remains.

---

## Deployment

All four fixes were committed to `dev`, merged to `main`, and deployed to Cloud Run via `gcloud builds submit`.

**Live revision:** `bianca-backend-00023-*` (build `f0d7fe5b`, deployed 2026-04-27T02:42 UTC)

---

## What Was Already Working (context)

| Revision | Status | Notes |
|---|---|---|
| `00018` | Replaced | Used `ChatAnthropicVertex` → 404 errors (model not in project's Vertex AI) |
| `00022` | Replaced | Reverted to direct Anthropic API (`ChatAnthropic`, 60 s timeout) — chat worked |
| `00023` | **Live** | Above fixes + no-network rules + streaming fix |

---

## Files Changed

| File | Change |
|---|---|
| `backend/document_skills/pdf_instructions.md` | Add style dedup rule + no-network rule |
| `backend/document_skills/xlsx_instructions.md` | Add no-network rule |
| `backend/document_skills/pptx_instructions.md` | Add no-network rule |
| `backend/document_skills/docx_instructions.md` | Add no-network rule |
| `backend/routers/chat.py` | Remove redundant `stream()` re-call after `invoke()` |
| `frontend/src/pages/NeuralConfig.jsx` | Remove duplicate Claude Sonnet 4.6 entry |
