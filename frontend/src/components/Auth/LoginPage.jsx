/**
 * Login page with Google Sign-In.
 */
import { GoogleLogin } from '@react-oauth/google';
import { useAuth } from '../../hooks/useAuth';
import './LoginPage.css';

export function LoginPage() {
  const { login } = useAuth();

  const handleSuccess = (credentialResponse) => {
    try {
      login(credentialResponse);
    } catch (error) {
      console.error('Login failed:', error);
    }
  };

  const handleError = () => {
    console.error('Google Sign-In failed');
  };

  return (
    <div className="login-page">
      <div className="login-content">
        <h1 className="login-title">Bianca</h1>
        <p className="login-subtitle">Your AI Chief of Staff</p>
        <div className="login-button-container">
          <GoogleLogin
            onSuccess={handleSuccess}
            onError={handleError}
            theme="filled_black"
            size="large"
            text="signin_with"
          />
        </div>
      </div>
    </div>
  );
}
