import { GoogleOAuthProvider } from '@react-oauth/google';
import { AuthProvider } from './context/AuthContext';
import { useAuth } from './hooks/useAuth';
import { LoginPage } from './components/Auth/LoginPage';
import { AppLayout } from './components/Layout/AppLayout';
import { OnboardingFlow } from './pages/OnboardingFlow';
import './styles/global.css';

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

function AppContent() {
  const { isAuthenticated, user } = useAuth();

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  // New users (or users who haven't completed onboarding) see the wizard first
  if (!user?.onboardingCompleted) {
    return <OnboardingFlow />;
  }

  return <AppLayout />;
}

function App() {
  if (!GOOGLE_CLIENT_ID) {
    return (
      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center', 
        height: '100vh',
        color: '#ececec',
        textAlign: 'center',
        padding: '20px'
      }}>
        <div>
          <h2>Configuration Error</h2>
          <p>Please set VITE_GOOGLE_CLIENT_ID in your .env file</p>
        </div>
      </div>
    );
  }

  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </GoogleOAuthProvider>
  );
}

export default App;
