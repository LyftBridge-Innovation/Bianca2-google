/**
 * Login page with Google Sign-In (auth-code flow with dynamic scopes).
 */
import { useGoogleLogin } from '@react-oauth/google';
import { useAuth } from '../../hooks/useAuth';
import { getRequiredScopes } from '../../api/client';
import { useState, useEffect } from 'react';
import { Footer } from '../Layout/Footer';
import './LoginPage.css';

const LOGO = import.meta.env.BASE_URL + 'lyftbridge.jpeg';

// Fallback scopes used when the backend is unreachable.
// Keep in sync with all YAML skill scopes in backend/skills/*.yaml.
const FALLBACK_SCOPES = [
  'https://www.googleapis.com/auth/gmail.modify',
  'https://www.googleapis.com/auth/calendar',
  // Drive — readonly for browsing + drive.file for uploading generated docs
  'https://www.googleapis.com/auth/drive.readonly',
  'https://www.googleapis.com/auth/drive.file',
  'https://www.googleapis.com/auth/tasks',
  'https://www.googleapis.com/auth/contacts.readonly',
  'https://www.googleapis.com/auth/spreadsheets.readonly',
  'https://www.googleapis.com/auth/documents.readonly',
  // Slides write scope needed for create_pptx_presentation upload
  'https://www.googleapis.com/auth/presentations',
].join(' ');

export function LoginPage() {
  const { login } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [scopes, setScopes] = useState(null);

  // Fetch required scopes from backend on mount
  useEffect(() => {
    getRequiredScopes()
      .then(data => setScopes(data.scopes.join(' ')))
      .catch(() => setScopes(FALLBACK_SCOPES));
  }, []);

  const googleLogin = useGoogleLogin({
    flow: 'auth-code',
    scope: scopes || FALLBACK_SCOPES,
    access_type: 'offline',
    prompt: 'consent',
    onSuccess: async (codeResponse) => {
      setLoading(true);
      setError(null);
      try {
        await login(codeResponse.code);
      } catch (err) {
        setError('Sign-in failed. Please try again.');
        console.error('Login failed:', err);
      } finally {
        setLoading(false);
      }
    },
    onError: () => {
      setError('Google Sign-In was cancelled.');
    },
  });

  return (
    <div className="login-page">
      <div className="login-ambient-gold" />
      <div className="login-content">
        <img src={LOGO} alt="Lyftbridge" className="login-logo" />
        <h1 className="login-title">Bianca</h1>
        <p className="login-subtitle">Your AI Chief of Staff</p>
        <p className="login-by">Developed by Lyftbridge</p>
        <div className="login-button-container">
          <button
            className="google-signin-btn"
            onClick={googleLogin}
            disabled={loading || !scopes}
          >
            <svg className="google-icon" viewBox="0 0 24 24" width="20" height="20">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            {loading ? 'Signing in...' : !scopes ? 'Loading...' : 'Sign in with Google'}
          </button>
        </div>
        {error && <p className="login-error">{error}</p>}
        <p className="login-permissions-note">
          Grants access to Gmail, Calendar, Drive, Tasks, Contacts &amp; more
        </p>
        <Footer className="login-footer" />
      </div>
    </div>
  );
}
