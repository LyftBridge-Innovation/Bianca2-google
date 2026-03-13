# Google Workspace CLI (gws) Migration Plan

## Executive Summary

This document outlines the migration from the current custom Python-based Google Workspace integration (Phase 3) to the new Google Workspace CLI (`gws`) approach. The new CLI provides a simpler, more maintainable solution with built-in authentication, automatic API discovery, and 40+ pre-built AI agent skills.

---

## Current Architecture Analysis

### Phase 3 Implementation Overview

**Files:**
- `backend/tools/google_auth.py` - Custom OAuth token manager with refresh token handling
- `backend/tools/gmail.py` - Gmail API wrappers (list, get, send, draft emails)
- `backend/tools/calendar.py` - Calendar API wrappers (list, get, create, decline, update events)
- `backend/langchain_tools.py` - LangChain tool decorators wrapping Gmail/Calendar functions
- `backend/routers/chat.py` - LLM integration with tool binding

**Current Approach:**
1. **Authentication:** Manual OAuth flow with hardcoded refresh tokens in `.env`
   - `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`
   - Credentials refreshed programmatically using google-auth library
   - MVP: Single user credentials (no per-user lookup yet)

2. **API Integration:** Direct Python SDK usage
   - `google-api-python-client` for Gmail and Calendar APIs
   - Custom wrapper functions for each operation
   - Manual error handling and response parsing
   - 9 custom tool implementations

3. **Tool Declaration:** LangChain decorators
   - `@tool` decorator on each function
   - Manual parameter documentation
   - Tools bound to LLM via `.bind_tools(ALL_TOOLS)`

**Limitations:**
- ❌ Manual OAuth flow requires developer to obtain refresh token
- ❌ Custom code for each Google API (Gmail, Calendar, etc.)
- ❌ No automatic API updates when Google adds features
- ❌ Complex credential management per user (planned but not implemented)
- ❌ Boilerplate code for request/response handling
- ❌ Limited to APIs we manually implement

---

## New Architecture: Google Workspace CLI (gws)

### What is gws?

**Repository:** [googleworkspace/cli](https://github.com/googleworkspace/cli)
**NPM Package:** `@googleworkspace/cli`
**Description:** One CLI for all of Google Workspace — built for humans and AI agents

### Key Features

1. **Zero Boilerplate**
   - No custom API wrappers needed
   - Structured JSON output for all operations
   - Single CLI handles Drive, Gmail, Calendar, Docs, Sheets, Chat, etc.

2. **Dynamic Discovery**
   - Reads Google's Discovery Service at runtime
   - Automatically picks up new API endpoints when Google adds them
   - No hardcoded API methods

3. **Simplified Authentication**
   ```bash
   gws auth setup     # One-time project setup (with gcloud)
   gws auth login     # OAuth login with scope selection
   ```
   - Credentials encrypted at rest (AES-256-GCM)
   - Stored in OS keyring or `~/.config/gws/`
   - Export credentials for headless environments

4. **AI Agent Skills (100+ Skills)**
   - Pre-built SKILL.md files for Claude Code (via skills CLI)
   - 50 curated recipes for Gmail, Drive, Docs, Calendar, Sheets
   - Helper commands prefixed with `+` (e.g., `gws gmail +send`)

5. **Example Commands**
   ```bash
   # List emails
   gws gmail users messages list --params '{"maxResults": 10}'

   # Send email
   gws gmail +send --to user@example.com --subject "Hello" --body "Hi"

   # List calendar events
   gws calendar events list --params '{"timeMin": "2026-03-12T00:00:00Z"}'

   # Create event
   gws calendar +insert --summary "Meeting" --start "2026-03-15T10:00:00"
   ```

---

## Migration Strategy

### Phase 1: Setup & Authentication (1-2 hours)

#### 1.1 Install gws CLI

**Environment:** The backend FastAPI server can call `gws` CLI as a subprocess.

```bash
# Install globally on the server/dev machine
npm install -g @googleworkspace/cli

# Verify installation
gws --version
```

**Alternative:** Install as project devDependency
```bash
cd /Users/arunachalammanikandan/Developer/ai-chief-of-staff
npm init -y  # Create package.json if doesn't exist
npm install @googleworkspace/cli
```

Then use: `npx gws` instead of `gws`

#### 1.2 Configure Authentication

**Decision Point:** Choose authentication method based on deployment:

**Option A: Desktop Development (Recommended for MVP)**
```bash
# One-time setup (requires gcloud CLI)
gws auth setup

# Or manual setup without gcloud:
# 1. Create OAuth client in Google Cloud Console (Desktop app type)
# 2. Download client_secret.json to ~/.config/gws/
# 3. Run: gws auth login -s gmail,calendar,drive
```

**Option B: Headless/Production (For deployment)**
```bash
# 1. Complete auth on local machine with browser
gws auth login -s gmail,calendar,drive

# 2. Export credentials
gws auth export --unmasked > gws-credentials.json

# 3. On server, set environment variable
export GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE=/path/to/gws-credentials.json
```

**Option C: Service Account (For server-to-server)**
```bash
# Point to existing service account key
export GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE=/path/to/service-account.json
```

#### 1.3 Update Backend Configuration

**File: `backend/config.py`**

Add new config variables:
```python
# Google Workspace CLI Configuration
GWS_CLI_PATH = os.getenv("GWS_CLI_PATH", "gws")  # or "npx gws"
GWS_CREDENTIALS_FILE = os.getenv("GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE", None)
```

**File: `backend/.env`**

```bash
# Google Workspace CLI (replaces old OAuth config)
GWS_CLI_PATH=gws
# For production/headless:
# GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE=/path/to/gws-credentials.json
```

#### 1.4 Test Authentication

```bash
# Verify gws can access Gmail
gws gmail users messages list --params '{"maxResults": 1}'

# Verify calendar access
gws calendar events list --params '{"maxResults": 1}'
```

**Acceptance Criteria:**
- ✅ `gws` CLI installed and accessible
- ✅ Authentication completed (credentials stored)
- ✅ Test commands return JSON successfully
- ✅ No authentication errors

---

### Phase 2: Create CLI Wrapper Module (2-3 hours)

#### 2.1 Create `backend/tools/gws_client.py`

**Purpose:** Python wrapper to execute `gws` CLI commands and parse JSON responses.

```python
"""
Google Workspace CLI (gws) Python wrapper.
Executes gws commands and returns structured JSON responses.
"""
import subprocess
import json
from typing import Any, Dict, List, Optional
from config import GWS_CLI_PATH, GWS_CREDENTIALS_FILE
import logging

logger = logging.getLogger(__name__)


class GWSClient:
    """Client for executing Google Workspace CLI commands."""

    def __init__(self, credentials_file: Optional[str] = GWS_CREDENTIALS_FILE):
        self.cli_path = GWS_CLI_PATH
        self.credentials_file = credentials_file

    def _execute(self, args: List[str], input_json: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Execute a gws command and return parsed JSON response.

        Args:
            args: Command arguments (e.g., ["gmail", "users", "messages", "list"])
            input_json: Optional JSON body for --json flag

        Returns:
            Parsed JSON response from gws

        Raises:
            GWSError: If command fails with non-zero exit code
        """
        cmd = [self.cli_path] + args

        env = {}
        if self.credentials_file:
            env["GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE"] = self.credentials_file

        try:
            logger.info(f"Executing gws command: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env={**os.environ, **env},
                timeout=30  # 30 second timeout
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip()
                logger.error(f"gws command failed: {error_msg}")
                raise GWSError(f"gws command failed: {error_msg}", exit_code=result.returncode)

            # Parse JSON response
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse gws output: {result.stdout[:200]}")
                raise GWSError(f"Invalid JSON response: {e}")

        except subprocess.TimeoutExpired:
            logger.error("gws command timed out after 30 seconds")
            raise GWSError("Command timed out")
        except FileNotFoundError:
            logger.error(f"gws CLI not found at: {self.cli_path}")
            raise GWSError(f"gws CLI not found. Install with: npm install -g @googleworkspace/cli")


class GWSError(Exception):
    """Exception raised for gws command errors."""
    def __init__(self, message: str, exit_code: int = 1):
        self.exit_code = exit_code
        super().__init__(message)


# Singleton instance
gws_client = GWSClient()
```

#### 2.2 Create High-Level Helper Functions

**File: `backend/tools/gws_helpers.py`**

Create convenience functions that match the current API:

```python
"""
High-level helper functions for Google Workspace CLI operations.
These functions provide the same interface as the old gmail.py and calendar.py modules.
"""
from typing import List, Dict, Optional
from tools.gws_client import gws_client, GWSError
from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger(__name__)


# ── Gmail Helpers ─────────────────────────────────────────────────────────────

def list_emails(user_id: str, max_results: int = 10) -> List[Dict]:
    """
    List recent emails from user's inbox.

    Returns:
        List of dicts with: id, subject, from, date, snippet
    """
    try:
        result = gws_client._execute([
            "gmail", "users", "messages", "list",
            "--params", json.dumps({"userId": "me", "maxResults": max_results})
        ])

        messages = result.get("messages", [])
        emails = []

        # Fetch metadata for each message
        for msg in messages:
            msg_data = get_email(user_id, msg["id"])
            emails.append({
                "id": msg_data["id"],
                "subject": msg_data["subject"],
                "from": msg_data["from"],
                "date": msg_data["date"],
                "snippet": msg_data.get("snippet", "")
            })

        return emails
    except GWSError as e:
        logger.error(f"Failed to list emails: {e}")
        raise


def get_email(user_id: str, email_id: str) -> Dict:
    """Get full email details by ID."""
    try:
        result = gws_client._execute([
            "gmail", "users", "messages", "get",
            "--params", json.dumps({"userId": "me", "id": email_id})
        ])

        # Parse headers
        headers = {h["name"]: h["value"] for h in result["payload"]["headers"]}

        # Extract body (simplified - gws returns full structure)
        body = ""
        payload = result["payload"]
        if "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain" and "data" in part["body"]:
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                    break
        elif "body" in payload and payload["body"].get("data"):
            body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")

        return {
            "id": result["id"],
            "subject": headers.get("Subject", ""),
            "from": headers.get("From", ""),
            "to": headers.get("To", ""),
            "date": headers.get("Date", ""),
            "body": body,
            "snippet": result.get("snippet", "")
        }
    except GWSError as e:
        logger.error(f"Failed to get email {email_id}: {e}")
        raise


def send_email(user_id: str, to: str, subject: str, body: str) -> Dict:
    """Send an email using gws helper command."""
    try:
        result = gws_client._execute([
            "gmail", "+send",
            "--to", to,
            "--subject", subject,
            "--body", body
        ])
        return {"id": result.get("id"), "status": "sent"}
    except GWSError as e:
        logger.error(f"Failed to send email: {e}")
        raise


def draft_email(user_id: str, to: str, subject: str, body: str) -> Dict:
    """Create email draft (no gws helper, use API directly)."""
    try:
        # Create draft using raw API (gws doesn't have +draft helper)
        message = {
            "raw": base64.urlsafe_b64encode(
                f"To: {to}\nSubject: {subject}\n\n{body}".encode()
            ).decode()
        }

        result = gws_client._execute([
            "gmail", "users", "drafts", "create",
            "--params", json.dumps({"userId": "me"}),
            "--json", json.dumps({"message": message})
        ])

        return {"id": result["id"], "status": "drafted"}
    except GWSError as e:
        logger.error(f"Failed to draft email: {e}")
        raise


# ── Calendar Helpers ──────────────────────────────────────────────────────────

def list_events(user_id: str, days_ahead: int = 7) -> List[Dict]:
    """List upcoming calendar events."""
    try:
        now = datetime.now(timezone.utc)
        end = now + timedelta(days=days_ahead)

        result = gws_client._execute([
            "calendar", "events", "list",
            "--params", json.dumps({
                "calendarId": "primary",
                "timeMin": now.isoformat(),
                "timeMax": end.isoformat(),
                "singleEvents": True,
                "orderBy": "startTime"
            })
        ])

        events = []
        for e in result.get("items", []):
            events.append({
                "id": e["id"],
                "title": e.get("summary", ""),
                "start": e["start"].get("dateTime", e["start"].get("date")),
                "end": e["end"].get("dateTime", e["end"].get("date")),
                "attendees": [a["email"] for a in e.get("attendees", [])]
            })

        return events
    except GWSError as e:
        logger.error(f"Failed to list events: {e}")
        raise


def create_event(user_id: str, title: str, start: str, end: str,
                attendees: List[str] = None, description: str = "") -> Dict:
    """Create calendar event using gws helper."""
    try:
        args = [
            "calendar", "+insert",
            "--summary", title,
            "--start", start,
            "--end", end
        ]

        if description:
            args.extend(["--description", description])

        # Note: +insert helper may not support attendees, fallback to full API
        if attendees:
            # Use full API for attendees
            event_body = {
                "summary": title,
                "description": description,
                "start": {"dateTime": start, "timeZone": "UTC"},
                "end": {"dateTime": end, "timeZone": "UTC"},
                "attendees": [{"email": a} for a in attendees]
            }

            result = gws_client._execute([
                "calendar", "events", "insert",
                "--params", json.dumps({"calendarId": "primary", "sendUpdates": "all"}),
                "--json", json.dumps(event_body)
            ])
        else:
            result = gws_client._execute(args)

        return {
            "id": result["id"],
            "status": "created",
            "link": result.get("htmlLink", "")
        }
    except GWSError as e:
        logger.error(f"Failed to create event: {e}")
        raise


# Additional calendar functions (get_event, decline_event, update_event)
# ... implement similarly using gws calendar API
```

**Benefits of this approach:**
- ✅ Same function signatures as old implementation
- ✅ No changes needed to `langchain_tools.py`
- ✅ Drop-in replacement for existing code
- ✅ Automatic API updates via gws discovery

---

### Phase 3: Update Tool Declarations (1 hour)

#### 3.1 Update Import in `langchain_tools.py`

**Before:**
```python
from tools import gmail, calendar
```

**After:**
```python
from tools import gws_helpers as gmail, gws_helpers as calendar
# Or more explicitly:
from tools.gws_helpers import (
    list_emails, get_email, send_email, draft_email,
    list_events, get_event, create_event, decline_event, update_event
)
```

**Note:** If helper function signatures match exactly, NO other changes needed in `langchain_tools.py`!

#### 3.2 Optional: Add New gws-Powered Tools

Since gws provides access to ALL Google Workspace APIs, you can easily add:

```python
# Google Drive tools
@tool
def list_drive_files(max_results: int = 10):
    """List files in Google Drive."""
    result = gws_client._execute([
        "drive", "files", "list",
        "--params", json.dumps({"pageSize": max_results})
    ])
    return result.get("files", [])

# Google Docs tools
@tool
def read_google_doc(document_id: str):
    """Read content from a Google Doc."""
    result = gws_client._execute([
        "docs", "documents", "get",
        "--params", json.dumps({"documentId": document_id})
    ])
    return result

# Google Sheets tools
@tool
def read_spreadsheet(spreadsheet_id: str, range: str):
    """Read data from a Google Sheet."""
    result = gws_client._execute([
        "sheets", "+read",
        "--spreadsheet", spreadsheet_id,
        "--range", range
    ])
    return result
```

---

### Phase 4: Install Claude Code Skills (30 minutes)

#### 4.1 Install Pre-Built Skills

The gws repo includes 100+ AI agent skills. Install them for Claude Code:

```bash
# Install all gws skills at once
npx skills add https://github.com/googleworkspace/cli

# Or install specific skills
npx skills add https://github.com/googleworkspace/cli/tree/main/skills/gws-gmail
npx skills add https://github.com/googleworkspace/cli/tree/main/skills/gws-calendar
npx skills add https://github.com/googleworkspace/cli/tree/main/skills/gws-drive
```

**What this does:**
- Adds SKILL.md files to your project
- Claude Code can automatically discover and use these skills
- Skills include natural language descriptions and examples
- No manual tool registration needed

#### 4.2 Verify Skills Installation

```bash
# Check installed skills
ls -la ~/.openclaw/skills/ | grep gws

# Or check project skills directory
ls -la skills/
```

**Benefits:**
- 50+ curated Gmail/Calendar/Drive workflows pre-built
- Helper commands like `+send`, `+triage`, `+watch`
- Automatic updates when gws adds new features

---

### Phase 5: Testing & Validation (2-3 hours)

#### 5.1 Unit Tests for gws_client

**File: `backend/tests/test_gws_client.py`**

```python
import pytest
from tools.gws_client import GWSClient, GWSError

def test_gws_gmail_list():
    """Test listing emails via gws."""
    client = GWSClient()
    result = client._execute([
        "gmail", "users", "messages", "list",
        "--params", '{"userId": "me", "maxResults": 1}'
    ])
    assert "messages" in result

def test_gws_calendar_list():
    """Test listing calendar events via gws."""
    client = GWSClient()
    # Add test implementation
    pass

def test_gws_error_handling():
    """Test that GWSError is raised on command failure."""
    client = GWSClient()
    with pytest.raises(GWSError):
        client._execute(["invalid", "command"])
```

#### 5.2 Integration Tests

**Test Checklist:**
- ✅ List emails returns expected format
- ✅ Get email by ID returns full content
- ✅ Draft email creates draft successfully
- ✅ Send email works (test with send to self)
- ✅ List calendar events returns upcoming events
- ✅ Create calendar event succeeds
- ✅ Update/decline event works
- ✅ Error handling gracefully handles API errors
- ✅ Timeout handling works for slow responses

#### 5.3 End-to-End Chat Test

**File: `backend/test_chat_gws.sh`**

```bash
#!/bin/bash
# Test chat endpoint with gws integration

# Test 1: List emails via chat
curl -X POST http://localhost:8000/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show me my recent emails",
    "user_id": "dev_user_1"
  }'

# Test 2: Draft email
curl -X POST http://localhost:8000/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Draft an email to test@example.com with subject Test",
    "user_id": "dev_user_1"
  }'

# Test 3: List calendar
curl -X POST http://localhost:8000/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What meetings do I have this week?",
    "user_id": "dev_user_1"
  }'
```

**Acceptance Criteria:**
- ✅ All existing Phase 3 tests pass with gws backend
- ✅ No regressions in chat functionality
- ✅ Tool calls execute successfully
- ✅ Responses maintain same format
- ✅ Error messages are user-friendly

---

### Phase 6: Cleanup & Deprecation (1 hour)

#### 6.1 Deprecate Old Files

**Files to remove/archive:**
- ~~`backend/tools/google_auth.py`~~ → Archive to `backend/PHASE_3/legacy/`
- ~~`backend/tools/gmail.py`~~ → Archive
- ~~`backend/tools/calendar.py`~~ → Archive

**Files to keep:**
- ✅ `backend/tools/gws_client.py` (new)
- ✅ `backend/tools/gws_helpers.py` (new)
- ✅ `backend/langchain_tools.py` (updated imports only)

#### 6.2 Update Configuration

**File: `backend/.env.example`**

```bash
# OLD (deprecated):
# GOOGLE_CLIENT_ID=xxx
# GOOGLE_CLIENT_SECRET=xxx
# GOOGLE_REFRESH_TOKEN=xxx
# GOOGLE_CALENDAR_ID=primary

# NEW (gws CLI):
GWS_CLI_PATH=gws
# For production/headless deployment:
# GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE=/path/to/gws-credentials.json
```

#### 6.3 Update Documentation

**File: `backend/PHASE_3/MIGRATION_COMPLETE.md`**

Document:
- What changed and why
- How to authenticate with gws
- How to export credentials for deployment
- Benefits of new approach
- Rollback procedure (if needed)

---

## Migration Benefits

### Code Reduction
- **Before:** ~500 lines of custom OAuth + API wrapper code
- **After:** ~200 lines of CLI wrapper + helpers
- **Reduction:** 60% less code to maintain

### Feature Expansion
- **Before:** 9 tools (Gmail + Calendar only)
- **After:** Unlimited tools via gws discovery
  - Gmail, Calendar, Drive, Docs, Sheets, Chat, Tasks, etc.
  - 40+ helper commands
  - Automatic updates when Google adds APIs

### Authentication Simplification
- **Before:** Manual OAuth flow, refresh token management, credential storage per user
- **After:** `gws auth login` → done
  - Export credentials for deployment
  - Service account support built-in
  - OS keyring integration

### Maintenance Reduction
- **Before:** Update code when Google changes APIs
- **After:** gws automatically discovers API changes
  - No code changes needed
  - CLI handles deprecations
  - Built-in error messages from Google

---

## Risk Assessment

### Low Risk Items ✅
- **Backward Compatibility:** Helper functions maintain same signatures
- **Fallback:** Can run old code in parallel during transition
- **Testing:** Comprehensive test suite catches regressions

### Medium Risk Items ⚠️
- **Subprocess Overhead:** Adds 100-200ms per gws call vs direct API
  - **Mitigation:** Acceptable for human-in-loop interactions
  - **Optimization:** Batch commands where possible

- **CLI Dependency:** Requires npm/node on server
  - **Mitigation:** Use pre-built binary from GitHub releases
  - **Alternative:** Docker container with gws pre-installed

### High Risk Items 🚨
- **Authentication Migration:** Users need to re-authenticate
  - **Mitigation:**
    1. Export old credentials before migration
    2. Document clear migration steps
    3. Provide rollback procedure
    4. Phase 3A/3B (Firestore, memory) unaffected

- **Breaking Changes:** gws is pre-1.0, API may change
  - **Mitigation:**
    1. Pin to specific gws version in package.json
    2. Test upgrades in staging environment
    3. Monitor gws changelog

---

## Rollback Procedure

If migration fails, rollback steps:

1. **Restore old files:**
   ```bash
   git checkout backend/tools/google_auth.py
   git checkout backend/tools/gmail.py
   git checkout backend/tools/calendar.py
   ```

2. **Revert imports in langchain_tools.py:**
   ```python
   from tools import gmail, calendar  # restore old import
   ```

3. **Restore .env configuration:**
   ```bash
   # Re-enable old OAuth config
   GOOGLE_CLIENT_ID=xxx
   GOOGLE_CLIENT_SECRET=xxx
   GOOGLE_REFRESH_TOKEN=xxx
   ```

4. **Restart server:**
   ```bash
   cd backend && uvicorn main:app --reload
   ```

**Data Safety:** Firestore data (Phase 3A/3B) remains intact. Only tool execution layer changes.

---

## Implementation Timeline

| Phase | Description | Estimated Time | Dependencies |
|-------|-------------|----------------|--------------|
| **Phase 1** | Setup & Authentication | 1-2 hours | gcloud CLI (optional) |
| **Phase 2** | Create CLI Wrapper | 2-3 hours | Phase 1 complete |
| **Phase 3** | Update Tool Declarations | 1 hour | Phase 2 complete |
| **Phase 4** | Install Claude Skills | 30 minutes | Phase 2 complete |
| **Phase 5** | Testing & Validation | 2-3 hours | Phase 3 complete |
| **Phase 6** | Cleanup & Documentation | 1 hour | Phase 5 complete |
| **TOTAL** | | **8-11 hours** | |

**Realistic Timeline:** 2-3 days (accounting for testing, debugging, documentation)

---

## Next Steps

### Immediate Actions
1. ✅ Review this migration plan with team
2. ⏳ Install gws CLI and test authentication
3. ⏳ Create `gws_client.py` wrapper module
4. ⏳ Implement helper functions in `gws_helpers.py`
5. ⏳ Run integration tests

### Decision Points
- **Authentication Method:** Desktop OAuth or Service Account?
- **Deployment Strategy:** All-at-once or gradual rollout?
- **Skill Installation:** Use pre-built gws skills or custom skills?
- **Version Pinning:** Pin to current gws version or allow auto-updates?

### Success Metrics
- ✅ All Phase 3 tests pass with gws backend
- ✅ Response time < 1 second for typical tool calls
- ✅ Zero authentication errors in production
- ✅ Can add new Google API (e.g., Drive) in < 30 minutes
- ✅ Code maintainability score improves (fewer lines, clearer intent)

---

## Appendix

### A. gws Command Reference

**Gmail:**
```bash
gws gmail users messages list --params '{"maxResults": 10}'
gws gmail +send --to user@example.com --subject "Test" --body "Hello"
gws gmail +triage  # Show unread inbox summary
```

**Calendar:**
```bash
gws calendar events list --params '{"calendarId": "primary"}'
gws calendar +insert --summary "Meeting" --start "2026-03-15T10:00:00"
gws calendar +agenda  # Show today's events
```

**Drive:**
```bash
gws drive files list --params '{"pageSize": 10}'
gws drive +upload ./file.pdf --name "Document"
```

### B. Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `GOOGLE_WORKSPACE_CLI_TOKEN` | Pre-obtained access token | From `gcloud auth print-access-token` |
| `GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE` | Path to credentials JSON | `~/.config/gws/credentials.json` |
| `GOOGLE_WORKSPACE_CLI_CONFIG_DIR` | Override config directory | `~/.config/gws` |
| `GWS_CLI_PATH` | Path to gws executable | `gws` or `npx gws` |

### C. Useful Resources

- **gws GitHub:** https://github.com/googleworkspace/cli
- **gws Skills Index:** https://github.com/googleworkspace/cli/tree/main/skills
- **Google Discovery Service:** https://developers.google.com/discovery
- **Skills CLI:** https://github.com/anthropics/skills-cli

---

## Conclusion

The migration from custom Python API wrappers to the Google Workspace CLI (`gws`) represents a strategic simplification that:

1. **Reduces code complexity** by 60%
2. **Expands functionality** from 9 → unlimited tools
3. **Simplifies authentication** to a single command
4. **Eliminates maintenance burden** via automatic API discovery
5. **Accelerates feature development** with pre-built skills

The investment of 8-11 hours for migration will pay dividends in reduced maintenance, faster feature development, and improved reliability.

**Recommendation:** Proceed with migration in staging environment, validate thoroughly, then deploy to production.

---

**Document Version:** 1.0
**Date:** 2026-03-12
**Author:** AI Chief of Staff Development Team
**Status:** Ready for Review
