/**
 * Authentication context for Google Sign-In (backend-verified).
 */
import { createContext, useState } from 'react';
import { apiRequest } from '../api/client';

export const AuthContext = createContext(null);

// Initialize user from localStorage
const getInitialUser = () => {
  const storedUser = localStorage.getItem('bianca_user');
  if (storedUser) {
    try {
      return JSON.parse(storedUser);
    } catch {
      localStorage.removeItem('bianca_user');
      return null;
    }
  }
  return null;
};

export function AuthProvider({ children }) {
  const [user, setUser] = useState(getInitialUser);

  const login = async (authCode) => {
    // Exchange auth code for verified user info via backend
    const userData = await apiRequest('/auth/google/callback', {
      method: 'POST',
      body: JSON.stringify({ code: authCode }),
    });

    const userInfo = {
      userId: userData.user_id,
      name: userData.name,
      email: userData.email,
      picture: userData.picture,
      onboardingCompleted: userData.onboarding_completed ?? false,
    };

    setUser(userInfo);
    localStorage.setItem('bianca_user', JSON.stringify(userInfo));
  };

  const markOnboardingComplete = () => {
    setUser((prev) => {
      if (!prev) return prev;
      const updated = { ...prev, onboardingCompleted: true };
      localStorage.setItem('bianca_user', JSON.stringify(updated));
      return updated;
    });
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem('bianca_user');
  };

  const value = {
    user,
    login,
    logout,
    markOnboardingComplete,
    isAuthenticated: !!user,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
