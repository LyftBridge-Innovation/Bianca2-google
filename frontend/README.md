# Bianca Frontend

Web chat interface for Bianca, the AI Chief of Staff.

## Features

- ✅ Google Sign-In authentication
- ✅ Real-time streaming responses (SSE)
- ✅ Tool call status indicators
- ✅ Session history with automatic titles
- ✅ Auto-scroll with smart pause/resume
- ✅ Clean, minimal UI inspired by Claude.ai

## Tech Stack

- **React 18** - UI library
- **Vite** - Build tool and dev server
- **@react-oauth/google** - Google authentication
- **Server-Sent Events** - Real-time streaming

## Prerequisites

1. Backend server running on `http://localhost:8000`
2. Google OAuth Client ID (see [GOOGLE_OAUTH_SETUP.md](./GOOGLE_OAUTH_SETUP.md))

## Setup

### 1. Install Dependencies

```bash
npm install
```

### 2. Configure Environment

Create a `.env` file (or edit the existing one):

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_GOOGLE_CLIENT_ID=your-google-client-id-here.apps.googleusercontent.com
```

See [GOOGLE_OAUTH_SETUP.md](./GOOGLE_OAUTH_SETUP.md) for detailed instructions on obtaining a Google Client ID.

### 3. Start Development Server

```bash
npm run dev
```

The app will be available at `http://localhost:5173`

## Project Structure

```
src/
├── api/              # API client and fetch wrappers
│   └── client.js
├── components/       # React components
│   ├── Auth/        # Login page
│   ├── Chat/        # Chat UI components
│   └── Layout/      # App layout and sidebar
├── context/         # React context providers
│   └── AuthContext.jsx
├── hooks/           # Custom React hooks
│   ├── useChat.js   # SSE streaming logic
│   └── useSessions.js
└── styles/          # Global CSS
    └── global.css
```

## How It Works

### Authentication Flow

1. User clicks "Sign in with Google"
2. Google OAuth popup appears
3. On success, JWT token is decoded client-side
4. User info (userId, name, email) stored in localStorage
5. App renders main chat interface

### Chat Streaming Flow

1. User sends message via ChatInput
2. POST request to `/chat/stream` with SSE
3. Events streamed in real-time:
   - `session`: New session ID
   - `tool_call`: Tool being executed
   - `token`: Individual response tokens
   - `done`: Stream complete
4. UI updates incrementally as tokens arrive

### Session Management

- Sessions auto-fetch on load
- Grouped by date (Today, Yesterday, etc.)
- Click session to load history
- "New Chat" button starts fresh session

## Development

### Available Scripts

```bash
npm run dev      # Start dev server (port 5173)
npm run build    # Build for production
npm run preview  # Preview production build
npm run lint     # Run ESLint
```

## Troubleshooting

### "Configuration Error" on startup
- Check that `VITE_GOOGLE_CLIENT_ID` is set in `.env`
- Restart dev server after changing `.env`

### Google Sign-In not working
- Verify Client ID is correct
- Check Google Cloud Console authorized origins include `http://localhost:5173`
- Make sure you're added as a test user (if using External consent screen)

### Streaming not working
- Ensure backend is running on `http://localhost:8000`
- Check browser console for CORS errors
- Verify `/chat/stream` endpoint returns `text/event-stream`

### Sessions not loading
- Check that user is authenticated (userId in localStorage)
- Verify `/chat/user/{userId}/sessions` endpoint works
- Open browser DevTools Network tab to see API calls

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

**Required features:**
- ES2020 support
- ReadableStream API
- CSS Grid and Flexbox
