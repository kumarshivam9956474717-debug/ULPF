import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import {
  UserProfile,
  loginApi,
  fetchCurrentUser,
  getAuthToken,
  setAuthSession,
  clearAuthSession
} from '../services/api';

interface AuthContextType {
  user: UserProfile | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  hasRole: (...roles: string[]) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Initialize session from localStorage
  useEffect(() => {
    const savedToken = getAuthToken();
    const savedUserRaw = localStorage.getItem('omnilogix_user');

    if (savedToken && savedUserRaw) {
      try {
        const parsedUser = JSON.parse(savedUserRaw) as UserProfile;
        setToken(savedToken);
        setUser(parsedUser);

        // Verify active status with backend
        fetchCurrentUser()
          .then((verifiedUser) => {
            setUser(verifiedUser);
            localStorage.setItem('omnilogix_user', JSON.stringify(verifiedUser));
          })
          .catch(() => {
            // If token is expired/invalid, clear session
            clearAuthSession();
            setToken(null);
            setUser(null);
          })
          .finally(() => {
            setIsLoading(false);
          });
        return;
      } catch {
        clearAuthSession();
      }
    }
    setIsLoading(false);
  }, []);

  // Listen for unauthorized events emitted by API interceptor
  useEffect(() => {
    const handleUnauthorized = () => {
      clearAuthSession();
      setToken(null);
      setUser(null);
    };

    window.addEventListener('omnilogix_auth_unauthorized', handleUnauthorized);
    return () => {
      window.removeEventListener('omnilogix_auth_unauthorized', handleUnauthorized);
    };
  }, []);

  const login = async (username: string, password: string) => {
    setIsLoading(true);
    try {
      const resp = await loginApi(username, password);
      setAuthSession(resp.access_token, resp.user);
      setToken(resp.access_token);
      setUser(resp.user);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    clearAuthSession();
    setToken(null);
    setUser(null);
    window.location.href = '/login';
  };

  const hasRole = (...roles: string[]): boolean => {
    if (!user) return false;
    return roles.includes(user.role);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        isAuthenticated: !!token && !!user,
        login,
        logout,
        hasRole
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
