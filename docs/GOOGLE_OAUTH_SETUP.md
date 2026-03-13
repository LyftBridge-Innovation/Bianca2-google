# Google OAuth Setup Guide

Before running the frontend, you need to create a Google OAuth Client ID.

## Steps

### 1. Go to Google Cloud Console
Visit [https://console.cloud.google.com](https://console.cloud.google.com)

### 2. Create or Select a Project
- If you haven't already, create a new project or select your existing project
- The project should be the same one you're using for your backend (Firestore, Vertex AI)

### 3. Enable Google+ API (if not already enabled)
- Go to "APIs & Services" → "Library"
- Search for "Google+ API"
- Click "Enable"

### 4. Configure OAuth Consent Screen
- Go to "APIs & Services" → "OAuth consent screen"
- Choose "External" (for testing) or "Internal" (if using Google Workspace)
- Fill in required fields:
  - App name: "Bianca" (or your preferred name)
  - User support email: Your email
  - Developer contact: Your email
- Click "Save and Continue"
- Skip scopes (we only need basic profile info)
- Add test users if using "External" type

### 5. Create OAuth Client ID
- Go to "APIs & Services" → "Credentials"
- Click "Create Credentials" → "OAuth client ID"
- Application type: "Web application"
- Name: "Bianca Web Client" (or your preferred name)
- Authorized JavaScript origins:
  - Add: `http://localhost:5173`
  - Add: `http://localhost:8000` (for backend CORS)
- Authorized redirect URIs: (Leave empty for now - not needed for Google Sign-In)
- Click "Create"

### 6. Copy Client ID
- After creation, you'll see your Client ID
- Copy the entire Client ID (it looks like: `123456789-abcdefg.apps.googleusercontent.com`)

### 7. Update Frontend Environment File
Open `frontend/.env` and replace the placeholder:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_GOOGLE_CLIENT_ID=YOUR_ACTUAL_CLIENT_ID_HERE
```

### 8. Start the Frontend
```bash
cd frontend
npm run dev
```

The app should now be accessible at `http://localhost:5173` with working Google Sign-In.

## Troubleshooting

**Error: "Invalid Client ID"**
- Make sure you copied the entire Client ID
- Check that there are no extra spaces
- Verify the Client ID is from a Web application type credential

**Error: "Not allowed origin"**
- Add `http://localhost:5173` to Authorized JavaScript origins in Google Cloud Console
- Wait a few minutes for changes to propagate

**Error: "Access blocked"**
- Make sure you added yourself as a test user in the OAuth consent screen
- Or change the consent screen to "Internal" if using Google Workspace
