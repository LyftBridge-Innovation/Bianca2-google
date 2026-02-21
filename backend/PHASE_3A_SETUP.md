# Phase 3A Setup Guide

## Prerequisites

Before running Phase 3A, you need to set up Firebase/Firestore.

### 1. Create a Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com)
2. Click "Add project" (or use existing Google Cloud project)
3. Follow the setup wizard

### 2. Enable Firestore Database

1. In Firebase Console, go to **Build → Firestore Database**
2. Click "Create database"
3. Choose **Start in production mode**
4. Select a region (choose one close to your users)

### 3. Get Service Account Credentials

1. In Firebase Console, go to **Project Settings** (gear icon)
2. Go to **Service accounts** tab
3. Click **Generate new private key**
4. Save the downloaded JSON file as `firebase-credentials.json` in the `backend/` directory

**IMPORTANT:** Never commit this file to git! It's already in `.gitignore`.

### 4. Update .env File

Add these lines to `backend/.env`:

```env
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_CREDENTIALS_PATH=firebase-credentials.json
ASSISTANT_NAME=Bianca
```

Replace `your-project-id` with your actual Firebase project ID (found in Project Settings).

### 5. Install Dependencies

```bash
cd backend
pip install firebase-admin google-cloud-firestore
```

Or install from requirements.txt:

```bash
pip install -r requirements.txt
```

### 6. Initialize Test User

Start the server:

```bash
uvicorn main:app --reload
```

Initialize the test user in Firestore:

```bash
curl -X POST http://localhost:8000/admin/init-test-user
```

You should see:
```json
{
  "status": "created",
  "user_id": "dev_user_1",
  "message": "Test user initialized successfully"
}
```

## Phase 3A Testing

Now test all acceptance criteria:

### Test 1: Session Creation

```bash
curl -X POST http://localhost:8000/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello! What can you help me with?",
    "user_id": "dev_user_1"
  }'
```

Response includes a `session_id`. Copy it for next tests.

### Test 2: Message Persistence

Check the session in Firestore:

```bash
curl http://localhost:8000/chat/session/YOUR_SESSION_ID
```

You should see the messages array with both user and assistant messages.

### Test 3: Continue Existing Session

```bash
curl -X POST http://localhost:8000/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What meetings do I have coming up?",
    "session_id": "YOUR_SESSION_ID",
    "user_id": "dev_user_1"
  }'
```

### Test 4: Tool Call Logging

Ask Bianca to draft an email:

```bash
curl -X POST http://localhost:8000/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Draft an email to test@example.com saying hello",
    "session_id": "YOUR_SESSION_ID",
    "user_id": "dev_user_1"
  }'
```

Check tool action log:

```bash
curl http://localhost:8000/admin/tool-actions/dev_user_1
```

You should see a human-readable description like:
```
"Bianca drafted an email to test@example.com with subject Hello"
```

### Test 5: last_activity_at Updates

Send multiple messages and verify `last_activity_at` updates on each message:

```bash
curl http://localhost:8000/chat/session/YOUR_SESSION_ID
```

Check the `last_activity_at` field changes with each message.

### Test 6: Get Active Session

```bash
curl http://localhost:8000/chat/user/dev_user_1/sessions
```

Should return the most recent active session for the user.

## Verification Checklist

- [x] Firestore collections created: `users`, `sessions`, `tool_action_log`
- [ ] Session created with status: `active`
- [ ] Messages persisted to session
- [ ] Tool calls logged to both session and tool_action_log
- [ ] `human_readable` field generated correctly
- [ ] `last_activity_at` updates on every message
- [ ] User document exists with timezone
- [ ] New messages append to existing session when session_id provided

## Next Steps

Once all tests pass, Phase 3A is complete! Next:
- **Phase 3B:** Summarization pipeline
- **Phase 3C:** Memory injection with Vertex AI Search
