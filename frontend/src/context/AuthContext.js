import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const HEARTBEAT_INTERVAL = 30000; // 30 seconds

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('cap_token'));
  const [loading, setLoading] = useState(true);
  const [activeUsers, setActiveUsers] = useState({ count: 0, users: [] });
  const heartbeatIntervalRef = useRef(null);

  // Send heartbeat to server
  const sendHeartbeat = useCallback(async () => {
    if (!token) return;
    try {
      await axios.post(`${API}/presence/heartbeat`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
    } catch (error) {
      console.error('Heartbeat error:', error);
    }
  }, [token]);

  // Fetch active users
  const fetchActiveUsers = useCallback(async () => {
    if (!token) return;
    try {
      const response = await axios.get(`${API}/presence/active-users`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setActiveUsers(response.data);
    } catch (error) {
      console.error('Fetch active users error:', error);
    }
  }, [token]);

  // Start heartbeat when authenticated
  useEffect(() => {
    if (token && user) {
      // Send initial heartbeat
      sendHeartbeat();
      fetchActiveUsers();
      
      // Set up interval for heartbeat and active users refresh
      heartbeatIntervalRef.current = setInterval(() => {
        sendHeartbeat();
        fetchActiveUsers();
      }, HEARTBEAT_INTERVAL);

      // Cleanup on unmount or logout
      return () => {
        if (heartbeatIntervalRef.current) {
          clearInterval(heartbeatIntervalRef.current);
        }
      };
    }
  }, [token, user, sendHeartbeat, fetchActiveUsers]);

  // Handle page visibility change (mark offline when tab hidden for long)
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && token) {
        sendHeartbeat();
        fetchActiveUsers();
      }
    };

    const handleBeforeUnload = async () => {
      if (token) {
        // Try to send offline status (may not complete)
        navigator.sendBeacon && navigator.sendBeacon(
          `${API}/presence/offline`,
          JSON.stringify({})
        );
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [token, sendHeartbeat, fetchActiveUsers]);

  useEffect(() => {
    const initAuth = async () => {
      if (token) {
        try {
          const response = await axios.get(`${API}/auth/me`, {
            headers: { Authorization: `Bearer ${token}` }
          });
          setUser(response.data);
        } catch (error) {
          console.error('Auth init error:', error);
          logout();
        }
      }
      setLoading(false);
    };
    initAuth();
  }, [token]);

  const login = async (email, password) => {
    const response = await axios.post(`${API}/auth/login`, { email, password });
    const { access_token, user: userData } = response.data;
    localStorage.setItem('cap_token', access_token);
    setToken(access_token);
    setUser(userData);
    return userData;
  };

  const register = async (userData) => {
    const response = await axios.post(`${API}/auth/register`, userData);
    const { access_token, user: newUser } = response.data;
    localStorage.setItem('cap_token', access_token);
    setToken(access_token);
    setUser(newUser);
    return newUser;
  };

  const logout = async () => {
    // Try to mark offline before logging out
    if (token) {
      try {
        await axios.post(`${API}/presence/offline`, {}, {
          headers: { Authorization: `Bearer ${token}` }
        });
      } catch (e) {
        // Ignore errors
      }
    }
    
    // Clear heartbeat interval
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
    }
    
    localStorage.removeItem('cap_token');
    setToken(null);
    setUser(null);
    setActiveUsers({ count: 0, users: [] });
  };

  const hasRole = (roles) => {
    if (!user) return false;
    return roles.includes(user.role);
  };

  const canEdit = () => hasRole(['commander', 'executive_staff', 'staff']);
  
  const canAccessFinance = () => hasRole(['commander', 'executive_staff', 'finance']);
  
  const isCommander = () => hasRole(['commander', 'executive_staff']);

  return (
    <AuthContext.Provider value={{
      user,
      token,
      loading,
      login,
      register,
      logout,
      hasRole,
      canEdit,
      canAccessFinance,
      isCommander,
      isAuthenticated: !!user,
      activeUsers,
      refreshActiveUsers: fetchActiveUsers
    }}>
      {children}
    </AuthContext.Provider>
  );
};
