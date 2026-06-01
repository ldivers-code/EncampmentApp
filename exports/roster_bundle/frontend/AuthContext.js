import React, { createContext, useContext, useState, useEffect, useCallback, useRef, useMemo } from 'react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const HEARTBEAT_INTERVAL = 30000; // 30 seconds

// All requests include credentials (httpOnly cookies)
axios.defaults.withCredentials = true;

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
  const [loading, setLoading] = useState(true);
  const [activeUsers, setActiveUsers] = useState({ count: 0, users: [] });
  const heartbeatIntervalRef = useRef(null);

  // Send heartbeat to server
  const sendHeartbeat = useCallback(async () => {
    if (!user) return;
    try {
      await axios.post(`${API}/presence/heartbeat`);
    } catch (error) {
      console.error('Heartbeat error:', error);
    }
  }, [user]);

  // Fetch active users
  const fetchActiveUsers = useCallback(async () => {
    if (!user) return;
    try {
      const response = await axios.get(`${API}/presence/active-users`);
      setActiveUsers(response.data);
    } catch (error) {
      console.error('Fetch active users error:', error);
    }
  }, [user]);

  // Start heartbeat when authenticated
  useEffect(() => {
    if (user) {
      sendHeartbeat();
      fetchActiveUsers();
      
      heartbeatIntervalRef.current = setInterval(() => {
        sendHeartbeat();
        fetchActiveUsers();
      }, HEARTBEAT_INTERVAL);

      return () => {
        if (heartbeatIntervalRef.current) {
          clearInterval(heartbeatIntervalRef.current);
        }
      };
    }
  }, [user, sendHeartbeat, fetchActiveUsers]);

  // Handle page visibility change
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && user) {
        sendHeartbeat();
        fetchActiveUsers();
      }
    };

    const handleBeforeUnload = () => {
      if (user) {
        // sendBeacon sends cookies automatically for same-origin
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
  }, [user, sendHeartbeat, fetchActiveUsers]);

  useEffect(() => {
    const initAuth = async () => {
      try {
        // Cookie is sent automatically — if valid, we get user data
        const response = await axios.get(`${API}/auth/me`);
        setUser(response.data);
      } catch (error) {
        // No valid session cookie
        setUser(null);
      }
      setLoading(false);
    };
    initAuth();
  }, []);

  const login = async (email, password) => {
    const response = await axios.post(`${API}/auth/login`, { email, password });
    const { user: userData } = response.data;
    setUser(userData);
    return userData;
  };

  const register = async (userData) => {
    const response = await axios.post(`${API}/auth/register`, userData);
    const { user: newUser } = response.data;
    setUser(newUser);
    return newUser;
  };

  const logout = async () => {
    // Clear heartbeat interval
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
    }
    
    // Call backend to clear httpOnly cookie + mark offline
    try {
      await axios.post(`${API}/presence/offline`);
    } catch (e) { /* ignore */ }
    try {
      await axios.post(`${API}/auth/logout`);
    } catch (e) { /* ignore */ }
    
    setUser(null);
    setActiveUsers({ count: 0, users: [] });
  };

  const hasRole = (roles) => {
    if (!user) return false;
    return roles.includes(user.role);
  };

  const canEdit = () => hasRole(['dcp', 'commander', 'executive_staff', 'staff']);
  
  const canUploadDocuments = () => hasRole([
    'dcp', 'commander', 'executive_staff', 'staff', 'exec_cadre',
    'training_officer', 'health_services', 'plans_programs', 'logistics', 'finance', 'dining_facility'
  ]);
  
  const canEditMealPlan = () => hasRole(['dcp', 'commander', 'executive_staff', 'plans_programs', 'dining_facility']);
  
  const canAccessFinance = () => hasRole(['dcp', 'commander', 'executive_staff', 'finance']);
  
  const isCommander = () => hasRole(['dcp', 'commander', 'executive_staff']);

  const refreshUser = async () => {
    try {
      const response = await axios.get(`${API}/auth/me`);
      setUser(response.data);
    } catch (e) { /* ignore */ }
  };

  const contextValue = useMemo(() => ({
    user,
    loading,
    login,
    register,
    logout,
    hasRole,
    canEdit,
    canUploadDocuments,
    canEditMealPlan,
    canAccessFinance,
    isCommander,
    isAuthenticated: !!user,
    activeUsers,
    refreshActiveUsers: fetchActiveUsers,
    refreshUser
  }), [user, loading, login, register, logout, hasRole, canEdit, canUploadDocuments, canEditMealPlan, canAccessFinance, isCommander, activeUsers, fetchActiveUsers, refreshUser]);

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
};
