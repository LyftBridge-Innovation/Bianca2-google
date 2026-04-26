/**
 * Login page — two-column asymmetric layout.
 * Left: brand story + CTA. Right: animated hero graphic.
 */
import { useGoogleLogin } from '@react-oauth/google';
import { useAuth } from '../../hooks/useAuth';
import { getRequiredScopes } from '../../api/client';
import { useState, useEffect } from 'react';
import { Footer } from '../Layout/Footer';
import './LoginPage.css';

const LOGO = import.meta.env.BASE_URL + 'lyftbridge.jpeg';

const FALLBACK_SCOPES = [
  'https://www.googleapis.com/auth/gmail.modify',
  'https://www.googleapis.com/auth/calendar',
  'https://www.googleapis.com/auth/drive.readonly',
  'https://www.googleapis.com/auth/drive.file',
  'https://www.googleapis.com/auth/tasks',
  'https://www.googleapis.com/auth/contacts.readonly',
  'https://www.googleapis.com/auth/spreadsheets.readonly',
  'https://www.googleapis.com/auth/documents.readonly',
  'https://www.googleapis.com/auth/presentations',
].join(' ');

const CalIcon = () => (
  <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
    <rect x="1.5" y="2.5" width="13" height="12" rx="1.5" stroke="currentColor" strokeWidth="1.4"/>
    <path d="M1.5 6.5h13M5 1.5v2M11 1.5v2" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
  </svg>
);
const MailIcon = () => (
  <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
    <rect x="1.5" y="3.5" width="13" height="9" rx="1.5" stroke="currentColor" strokeWidth="1.4"/>
    <path d="M1.5 5.5l6.5 4.5 6.5-4.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
  </svg>
);
const FolderIcon = () => (
  <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
    <path d="M1.5 4.5a1.5 1.5 0 0 1 1.5-1.5h3.5l1.5 2H13a1.5 1.5 0 0 1 1.5 1.5v5A1.5 1.5 0 0 1 13 13H3a1.5 1.5 0 0 1-1.5-1.5V4.5z" stroke="currentColor" strokeWidth="1.4"/>
  </svg>
);
const TaskIcon = () => (
  <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
    <path d="M3 8l3 3 7-7" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);

const FEATURES = [
  { icon: <CalIcon />,    label: 'Calendar & Scheduling' },
  { icon: <MailIcon />,   label: 'Gmail & Email' },
  { icon: <FolderIcon />, label: 'Drive & Documents' },
  { icon: <TaskIcon />,   label: 'Tasks & Contacts' },
];

export function LoginPage() {
  const { login } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [scopes, setScopes] = useState(null);

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
      {/* Background texture */}
      <div className="login-bg-dot-grid" aria-hidden="true" />
      <div className="login-bg-glow login-bg-glow--tl" aria-hidden="true" />
      <div className="login-bg-glow login-bg-glow--br" aria-hidden="true" />

      <div className="login-grid">

        {/* ── Left column — brand + CTA ──────────────────────────────────── */}
        <div className="login-left">
          <div className="login-left-inner">
            <img src={LOGO} alt="Lyftbridge" className="login-logo" />

            <div className="section-badge login-badge">
              <span className="section-badge__dot" />
              <span className="section-badge__label">AI Chief of Staff</span>
            </div>

            <h1 className="login-headline">
              Meet <span className="login-headline__gradient">Bianca</span>
            </h1>

            <p className="login-description">
              Your intelligent chief of staff — managing your calendar,
              inbox, documents, and more so you can focus on what matters.
            </p>

            <div className="login-features">
              {FEATURES.map(f => (
                <div key={f.label} className="login-feature-chip">
                  <span className="login-feature-chip__icon">{f.icon}</span>
                  <span className="login-feature-chip__label">{f.label}</span>
                </div>
              ))}
            </div>

            <button
              className="login-cta-btn"
              onClick={googleLogin}
              disabled={loading || !scopes}
            >
              <svg className="login-google-icon" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              {loading ? 'Signing in…' : !scopes ? 'Loading…' : 'Sign in with Google'}
              {!loading && scopes && (
                <svg className="login-cta-arrow" width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                  <path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              )}
            </button>

            {error && <p className="login-error">{error}</p>}

            <p className="login-permissions-note">
              Grants access to Gmail, Calendar, Drive, Tasks &amp; Contacts
            </p>

            <Footer className="login-footer" />
          </div>
        </div>

        {/* ── Right column — animated hero graphic ───────────────────────── */}
        <div className="login-right" aria-hidden="true">
          <div className="login-hero-wrap">
            {/* Radial glow */}
            <div className="login-hero-glow" />

            {/* Rotating outer ring */}
            <div className="login-hero-ring login-hero-ring--outer" />
            <div className="login-hero-ring login-hero-ring--inner" />

            {/* Central card */}
            <div className="login-hero-card login-hero-card--center">
              <div className="login-hero-card__avatar">B</div>
              <div className="login-hero-card__info">
                <span className="login-hero-card__name">Bianca</span>
                <span className="login-hero-card__role">Chief of Staff</span>
              </div>
              <div className="login-hero-card__dot" />
            </div>

            {/* Floating satellite cards */}
            <div className="login-hero-satellite login-hero-satellite--top">
              <span className="login-hero-satellite__icon">
                <svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                  <rect x="1.5" y="2.5" width="13" height="12" rx="1.5" stroke="currentColor" strokeWidth="1.4"/>
                  <path d="M1.5 6.5h13M5 1.5v2M11 1.5v2" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
                </svg>
              </span>
              <span>3 meetings today</span>
            </div>
            <div className="login-hero-satellite login-hero-satellite--bottom">
              <span className="login-hero-satellite__icon">
                <svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                  <rect x="1.5" y="3.5" width="13" height="9" rx="1.5" stroke="currentColor" strokeWidth="1.4"/>
                  <path d="M1.5 5.5l6.5 4.5 6.5-4.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
                </svg>
              </span>
              <span>12 emails triaged</span>
            </div>

            {/* Dot grid decoration */}
            <div className="login-hero-dots" />
          </div>
        </div>

      </div>
    </div>
  );
}
