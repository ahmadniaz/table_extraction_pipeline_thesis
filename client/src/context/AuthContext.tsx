'use client';

import React, { createContext, useContext, useState, useEffect, useCallback, useRef, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
// Using browser's built-in cookie handling instead of js-cookie
import axios from 'axios';
import { authService } from '../app/services/authService';

// Token refresh manager to prevent race conditions
class TokenRefreshManager {
  private static instance: TokenRefreshManager;
  private refreshPromise: Promise<void> | null = null;
  private pendingRequests: Array<{ resolve: () => void, reject: (error: any) => void }> = [];

  static getInstance(): TokenRefreshManager {
    if (!TokenRefreshManager.instance) {
      TokenRefreshManager.instance = new TokenRefreshManager();
    }
    return TokenRefreshManager.instance;
  }

  async refreshToken(): Promise<void> {
    if (this.refreshPromise) {
      // Return existing promise instead of creating new one
      return this.refreshPromise;
    }

    this.refreshPromise = this.performRefresh();
    
    try {
      await this.refreshPromise;
      // Resolve all pending requests
      this.pendingRequests.forEach(({ resolve }) => resolve());
      this.pendingRequests = [];
    } catch (error) {
      // Reject all pending requests
      this.pendingRequests.forEach(({ reject }) => reject(error));
      this.pendingRequests = [];
      throw error;
    } finally {
      this.refreshPromise = null;
    }
  }

  private async performRefresh(): Promise<void> {
      const response = await axios.post('/api/auth/otp/refresh', {}, {
      withCredentials: true
    });
    
    if (response.status !== 200) {
      throw new Error('Refresh failed');
    }
  }
}

// Cookie utility functions
const getCookie = (name: string): string | null => {
  if (typeof document === 'undefined') return null;
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop()?.split(';').shift() || null;
  return null;
};

const setCookie = (name: string, value: string, days: number) => {
  if (typeof document === 'undefined') return;
  const expires = new Date();
  expires.setTime(expires.getTime() + (days * 24 * 60 * 60 * 1000));
  const isSecure = window.location.protocol === 'https:';
  
  // Check if we're in production (cross-origin scenario)
  const isProduction = process.env.NODE_ENV === 'production' || 
                      window.location.hostname.includes('vercel.app') ||
                      window.location.hostname.includes('onrender.com');
  
  // Use "none" samesite for production cross-origin scenarios, "lax" for development
  const samesiteSetting = isProduction ? 'none' : 'lax';
  
  console.log(`🍪 Client setting cookie: ${name}, isProduction=${isProduction}, samesite=${samesiteSetting}, secure=${isSecure}`);
  
  document.cookie = `${name}=${value};expires=${expires.toUTCString()};path=/;${isSecure ? 'secure;' : ''}samesite=${samesiteSetting}`;
};

const deleteCookie = (name: string) => {
  if (typeof document === 'undefined') return;
  const isSecure = window.location.protocol === 'https:';
  
  // Check if we're in production (cross-origin scenario)
  const isProduction = process.env.NODE_ENV === 'production' || 
                      window.location.hostname.includes('vercel.app') ||
                      window.location.hostname.includes('onrender.com');
  
  // Use "none" samesite for production cross-origin scenarios, "lax" for development
  const samesiteSetting = isProduction ? 'none' : 'lax';
  
  document.cookie = `${name}=;expires=Thu, 01 Jan 1970 00:00:00 UTC;path=/;${isSecure ? 'secure;' : ''}samesite=${samesiteSetting}`;
};

// Types
interface User {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  role: string;
  is_active: boolean;
  is_verified: boolean;
  company_id?: string;
  last_login?: string;
  created_at: string;
  updated_at: string;
}

// Note: LoginRequest and SignupRequest interfaces removed as they're not used
// The application uses OTP authentication with OTPRequest and OTPVerification interfaces

interface OTPRequest {
  email: string;
  purpose: 'login' | 'registration';
}

interface OTPVerification {
  email: string;
  otp: string;
  purpose: 'login' | 'registration';
}

interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
  expires_in: number;
}

interface UserPermissions {
  can_upload: boolean;
  can_edit: boolean;
  is_admin: boolean;
  is_read_only: boolean;
}

interface AuthContextType {
  user: User | null;
  permissions: UserPermissions | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  logout: () => void;
  refreshUser: () => Promise<void>;
  checkPermissions: () => Promise<void>;
  // OTP Methods
  requestOTP: (otpRequest: OTPRequest) => Promise<void>;
  verifyOTP: (otpVerification: OTPVerification) => Promise<LoginResponse>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// API base URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Configure axios defaults
axios.defaults.baseURL = API_BASE_URL;
axios.defaults.withCredentials = true; // Include cookies in requests

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [permissions, setPermissions] = useState<UserPermissions | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [lastActivity, setLastActivity] = useState<number>(Date.now());
  const router = useRouter();

  const isAuthenticated = !!user;

  // Helper function to save auth state to localStorage (for persistence across refreshes)
  const saveAuthState = useCallback((userData: User | null) => {
    if (userData) {
      try {
        localStorage.setItem('auth_user', JSON.stringify(userData));
      } catch (error) {
        console.warn('Failed to save auth state to localStorage:', error);
      }
    } else {
      try {
        localStorage.removeItem('auth_user');
      } catch (error) {
        console.warn('Failed to clear auth state from localStorage:', error);
      }
    }
  }, []);

  // Helper function to load auth state from localStorage
  const loadAuthState = useCallback((): User | null => {
    try {
      const savedUser = localStorage.getItem('auth_user');
      if (savedUser) {
        return JSON.parse(savedUser);
      }
    } catch (error) {
      console.warn('Failed to load auth state from localStorage:', error);
    }
    return null;
  }, []);

  // Token refresh timer and manager
  const refreshTimer = useRef<NodeJS.Timeout | null>(null);
  const tokenRefreshManager = TokenRefreshManager.getInstance();

  const logout = useCallback(async () => {
    try {
      // FIXED: Use authService which now has proper withCredentials
      await authService.logout();
    } catch (error) {
      console.error('Logout error:', error);
    }

    // Clear refresh timer
    if (refreshTimer.current) {
      clearTimeout(refreshTimer.current);
      refreshTimer.current = null;
    }

    // Clear state and localStorage
    setUser(null);
    setPermissions(null);
    saveAuthState(null);

    // Redirect to landing
    router.push('/landing');
  }, [router, saveAuthState]);

  // Proactive token refresh function
  const scheduleTokenRefresh = useCallback(() => {
    if (refreshTimer.current) {
      clearTimeout(refreshTimer.current);
    }

    // Schedule refresh 5 minutes before token expires (55 minutes)
    const refreshInterval = 55 * 60 * 1000; // 55 minutes in milliseconds
    refreshTimer.current = setTimeout(async () => {
      try {
        console.log('Proactively refreshing token...');
        
        // FIXED: Use TokenRefreshManager instead of direct axios call
        await tokenRefreshManager.refreshToken();
        
        console.log('Token refreshed successfully');
        // Schedule the next refresh
        scheduleTokenRefresh();
      } catch (error) {
        console.error('Proactive token refresh failed:', error);
        // Clear the timer to prevent repeated failed attempts
        if (refreshTimer.current) {
          clearTimeout(refreshTimer.current);
          refreshTimer.current = null;
        }
        // Don't logout immediately, let the interceptor handle it
      }
    }, refreshInterval);
  }, [tokenRefreshManager]);  // Add tokenRefreshManager as dependency

  // Set up axios interceptor for auth token
  useEffect(() => {
    // For OTP authentication, we don't need to set Authorization header
    // as tokens are handled via httpOnly cookies

    // Response interceptor to handle token expiration and automatic refresh
    const responseInterceptor = axios.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;
        
        // Prevent infinite loops by checking if this is already a refresh request
        if (error.response?.status === 401 && 
            !originalRequest._retry && 
            !originalRequest.url?.includes('/auth/otp/refresh') &&
            !originalRequest.url?.includes('/auth/otp/logout') &&
            !originalRequest.url?.includes('/auth/otp/status')) {
          originalRequest._retry = true;
          
          try {
            // Use TokenRefreshManager to prevent concurrent refresh attempts
            await tokenRefreshManager.refreshToken();
            // Retry the original request with credentials
            return axios({
              ...originalRequest,
              withCredentials: true
            });
          } catch (refreshError) {
            // Refresh failed - check if this is a file upload operation
            console.log('Token refresh failed:', refreshError);
            
            // For file upload operations, don't immediately logout - show error instead
            if (originalRequest.url?.includes('/extract-tables-smart/') || 
                originalRequest.url?.includes('/extract-tables-')) {
              console.log('File upload failed due to authentication - showing error instead of logout');
              return Promise.reject(new Error('Your session has expired. Please refresh the page and try uploading again.'));
            }
            
            // For permissions endpoint, don't logout immediately - this might be a timing issue
            if (originalRequest.url?.includes('/auth/permissions')) {
              console.log('Permissions check failed - not logging out, might be timing issue');
              return Promise.reject(refreshError);
            }
            
            // For other operations, logout user
            logout();
            return Promise.reject(refreshError);
          }
        }
        return Promise.reject(error);
      }
    );

    return () => {
      axios.interceptors.response.eject(responseInterceptor);
    };
  }, [logout]);

  // Cleanup effect for refresh timer
  useEffect(() => {
    return () => {
      if (refreshTimer.current) {
        clearTimeout(refreshTimer.current);
      }
    };
  }, []);

  // Check if user is logged in on mount
  useEffect(() => {

    const checkAuth = async () => {
      try {
        console.log('Checking auth status...');
        
        // First, try to load from localStorage as a fallback
        const savedUser = loadAuthState();
        if (savedUser) {
          console.log('Found saved user in localStorage, setting as fallback');
          setUser(savedUser);
        }
        
        // FIXED: Use authService which now has proper withCredentials
        console.log('🔍 Checking auth status with server...');
        const authStatus = await authService.checkAuthStatus();
        console.log('📊 Auth status response:', authStatus);
        
        if (authStatus.is_authenticated) {
          console.log('✅ User is authenticated');
          setUser(authStatus.user);
          saveAuthState(authStatus.user); // Save to localStorage
          
          // Don't block authentication on permissions check failure
          // Try to get permissions but don't fail auth if it doesn't work
          try {
            await checkPermissions();
          } catch (permError) {
            console.log('Permissions check failed during auth, using defaults:', permError);
            // Set default permissions instead of failing auth
            setPermissions({
              can_upload: true,
              can_edit: true,
              is_admin: false,
              is_read_only: false
            });
          }
          
          // Start proactive token refresh
          scheduleTokenRefresh();
        } else {
          console.log('User not authenticated');
          setUser(null);
          saveAuthState(null); // Clear localStorage
        }
      } catch (error) {
        console.error('Auth check failed:', error);
        // Don't immediately logout on error - retry logic needed
        // Only set user to null if it's a clear authentication failure
        if (error instanceof Error && error.message.includes('401')) {
          setUser(null);
          saveAuthState(null); // Clear localStorage on auth failure
        }
        // For other errors (network, timeout), keep current state from localStorage
      }
      setIsLoading(false);
    };

    // Add a timeout to prevent infinite loading
    const timeoutId = setTimeout(() => {
      console.log('Auth check timeout, setting loading to false');
      setIsLoading(false);
    }, 5000); // Increased timeout to allow for proper auth check

    checkAuth().finally(() => {
      clearTimeout(timeoutId);
    });
  }, []);

  // Inactivity timeout handling
  useEffect(() => {
    if (!isAuthenticated) return;

    const INACTIVITY_TIMEOUT = 2 * 60 * 60 * 1000; // 2 hours in milliseconds (increased from 1 hour)
    let inactivityTimer: NodeJS.Timeout;

    const resetInactivityTimer = () => {
      setLastActivity(Date.now());
      clearTimeout(inactivityTimer);
      inactivityTimer = setTimeout(() => {
        // Show warning before logout
        const warningTime = 5 * 60 * 1000; // 5 minutes warning
        setTimeout(() => {
          logout();
        }, warningTime);
      }, INACTIVITY_TIMEOUT);
    };

    // Activity event listeners
    const activityEvents = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'];
    
    const handleActivity = () => {
      resetInactivityTimer();
    };

    // Add event listeners
    activityEvents.forEach(event => {
      document.addEventListener(event, handleActivity, true);
    });

    // Initialize timer
    resetInactivityTimer();

  
  

    return () => {
      clearTimeout(inactivityTimer);
      activityEvents.forEach(event => {
        document.removeEventListener(event, handleActivity, true);
      });
      // No longer using beforeunload listener
      // window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [isAuthenticated, logout]);

  // Note: login and signup functions removed as they were calling non-existent endpoints
  // The application uses OTP authentication via requestOTP and verifyOTP functions

  const refreshUser = async () => {
    try {
      // FIXED: Use authService which now has proper withCredentials
      const userData = await authService.getUserProfile();
      console.log('refreshUser: User data received:', userData);
      setUser(userData);
      await checkPermissions();
    } catch (error) {
      console.error('refreshUser: Error:', error);
      throw error;
    }
  };

  const checkPermissions = async () => {
    try {
      console.log('🔐 Checking user permissions...');
      // FIXED: Use authService which now has proper withCredentials
      const permissions = await authService.getUserPermissions();
      setPermissions(permissions);
      console.log('✅ Permissions fetched successfully:', permissions);
    } catch (error) {
      console.error('❌ Failed to fetch permissions:', error);
      // Set default permissions if fetch fails
      setPermissions({
        can_upload: true,
        can_edit: true,
        is_admin: false,
        is_read_only: false
      });
    }
  };

  // OTP Methods
  const requestOTP = async (otpRequest: OTPRequest) => {
    try {
      const response = await axios.post('/api/auth/otp/request', otpRequest, {
        withCredentials: true
      });
      return response.data;
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Failed to send OTP';
      throw new Error(errorMessage);
    }
  };

  const verifyOTP = async (otpVerification: OTPVerification): Promise<LoginResponse> => {
    try {
      console.log('🔐 Starting OTP verification...');
      const response = await axios.post<LoginResponse>('/api/auth/otp/verify', otpVerification, {
        withCredentials: true
      });
      const { user: userData } = response.data;

      console.log('✅ OTP verification successful, user data received:', userData);
      
      // For OTP authentication, tokens are set as httpOnly cookies by the server
      // We don't need to manually set them here
      
      // Set user data
      setUser(userData);
      saveAuthState(userData); // Save to localStorage for persistence
      
      console.log('💾 User data saved to state and localStorage');
      
      // Debug: Check if cookies are being set (we can't read httpOnly cookies, but we can check the response)
      console.log('🍪 Response headers:', response.headers);
      console.log('🍪 Set-Cookie headers:', response.headers['set-cookie']);
      
      // Wait longer for cookies to be set, then check permissions with retry
      setTimeout(async () => {
        try {
          // Retry permissions check up to 3 times with increasing delays
          let retryCount = 0;
          const maxRetries = 3;
          
          while (retryCount < maxRetries) {
            try {
              await checkPermissions();
              // Start proactive token refresh
              scheduleTokenRefresh();
              break; // Success, exit retry loop
            } catch (error) {
              retryCount++;
              console.log(`Permissions check attempt ${retryCount} failed:`, error);
              
              if (retryCount < maxRetries) {
                // Wait longer between retries
                await new Promise(resolve => setTimeout(resolve, 500 * retryCount));
              } else {
                console.error('Failed to check permissions after OTP verification after all retries:', error);
                // Don't logout on permissions failure - just set default permissions
                setPermissions({
                  can_upload: true,
                  can_edit: true,
                  is_admin: false,
                  is_read_only: false
                });
              }
            }
          }
        } catch (error) {
          console.error('Failed to check permissions after OTP verification:', error);
        }
      }, 500); // Increased delay from 100ms to 500ms
      
      return response.data;
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'OTP verification failed';
      throw new Error(errorMessage);
    }
  };

  const value: AuthContextType = {
    user,
    permissions,
    isLoading,
    isAuthenticated,
    logout,
    refreshUser,
    checkPermissions,
    requestOTP,
    verifyOTP,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
