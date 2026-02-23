/**
 * Authentication context for Google Sign-In.
 */
import { createContext, useState } from 'react';
import { jwtDecode } from 'jwt-decode';

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

  const login = (credentialResponse) => {
    try {
      // Decode the JWT token from Google
      const decoded = jwtDecode(credentialResponse.credential);
      
      const userData = {
        userId: decoded.sub,  // Google user ID (use as user_id in API calls)
        name: decoded.name,
        email: decoded.email,
        picture: decoded.picture,
      };

      setUser(userData);
      localStorage.setItem('bianca_user', JSON.stringify(userData));
    } catch (error) {
      console.error('Failed to decode credential:', error);
      throw error;
    }
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem('bianca_user');
  };

  const value = {
    user,
    login,
    logout,
    isAuthenticated: !!user,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
