/**
 * Authentication Context for DWC Admin Mobile App
 * Manages user authentication state
 */

import React, { createContext, useState, useContext, useEffect } from 'react';
import { login as apiLogin, logout as apiLogout, getToken } from '../services/api';
import websocketService from '../services/websocket';
import { registerForPushNotificationsAsync } from '../services/notifications';

const AuthContext = createContext({});

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Check if user is already logged in on app start
  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    try {
      const token = await getToken();
      if (token) {
        // User is logged in
        setUser({ token });

        // Connect to WebSocket
        websocketService.connect();

        // Register for push notifications
        registerForPushNotificationsAsync();
      }
    } catch (err) {
      console.error('Error checking auth status:', err);
    } finally {
      setLoading(false);
    }
  };

  const login = async (email, password) => {
    try {
      setLoading(true);
      setError(null);

      const tokenData = await apiLogin(email, password);
      setUser({ token: tokenData.access_token, email });

      // Connect to WebSocket after login
      websocketService.connect();

      // Register for push notifications
      await registerForPushNotificationsAsync();

      return true;
    } catch (err) {
      setError(err.message || 'Login failed');
      return false;
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    try {
      setLoading(true);

      // Disconnect WebSocket
      websocketService.disconnect();

      // Clear auth data
      await apiLogout();
      setUser(null);
    } catch (err) {
      console.error('Error during logout:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        error,
        login,
        logout,
        isAuthenticated: !!user,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
