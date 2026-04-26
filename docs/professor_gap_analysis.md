# Professor Gap Analysis — Bianca v1 → Bianca (ai-chief-of-staff)

Reference project: `/Users/arunachalammanikandan/Developer/lyftbridge-bianca-v1.0`

---

## What Was Ported

### Perplexity AI Integration ✅

The professor's project used a FastMCP-hosted Perplexity tool via Replit. We ported the
**concept** (real-time search + deep research) and implemented it natively in our FastAPI stack:

| Component | File | Description |
|---|---|---|
| Tool implementations | `backend/tools/perplexity.py` | `perplexity_quick_search` (sonar) and `perplexity_deep_research` (sonar-deep-research) as Python functions |
| LangChain registration | `backend/langchain_tools.py` | `build_perplexity_tools()` called at startup; returns empty list if key not set |
| Settings key | `backend/settings_loader.py` | `perplexity_api_key` default added |
| Settings value | `backend/knowledge/settings.json` | Key stored here; loaded at runtime |
| System prompt | `backend/prompts.py` | `_PERPLEXITY_BLOCK` injected when key is present |
| UI — Integrations tab | `frontend/src/pages/NeuralConfig.jsx` | Password input + "Configured" badge |
| UI — Security tab | `frontend/src/pages/NeuralConfig.jsx` | Added to `SECURITY_KEYS` for status display |
| Security endpoint | `backend/routers/config.py` | `perplexity_api_key` added to `/config/security-status` |
| HTTP dependency | `backend/requirements.txt` | `httpx` added |

**Models used:**
- Quick search: `sonar` (~2s)
- Deep research: `sonar-deep-research` (30-90s)

**Routing decision:** Tools are only registered in the **chat model** (LangChain). The voice
pipeline was explicitly excluded per user instruction ("it has Google search connected").

---

## What Was Skipped

### Contact Lookup via Airtable ❌
**Reason:** User explicitly said "CONTACT LOOKUP DONT DO, WE HAVE GOOGLE CONNECTED FOR IT."
We already have People/Contacts via the `gws` CLI (Google Workspace).

### Google Sheets Contact Lookup ❌
**Reason:** User said "DONT DO ANYTHING WITH GOOGLE PLSSSS." The professor's project had
a Sheets-based contact store, but our system uses Firestore + Google Contacts via gws.

### MCP Server / FastMCP ❌
**Reason:** The professor's project ran tools as a FastMCP server on Replit. Our architecture
uses LangChain tools directly bound to the chat model — no intermediate MCP layer needed.

### Airtable CRM ❌
**Reason:** We use Firestore for user data. Airtable was the professor's persistence layer
on Replit; not applicable to our stack.

### Replit-specific configs ❌
**Reason:** Not applicable. We run on Cloud Run (backend) and GitHub Pages / Vite (frontend).

---

## Architecture Difference

| Aspect | Professor (Bianca v1) | Ours (ai-chief-of-staff) |
|---|---|---|
| Runtime | Replit | Cloud Run + local dev |
| Tool protocol | FastMCP | LangChain tools |
| Web search | Perplexity (via MCP) | Perplexity (native httpx) |
| Contacts | Airtable + Google Contacts | Firestore + gws Google Contacts |
| Auth | Replit secrets | Firestore + Firebase Auth |
| Voice | N/A | Twilio + Gemini Live |
