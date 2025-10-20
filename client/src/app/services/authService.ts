import axios, { AxiosResponse } from 'axios';

interface AuthStatus {
    is_authenticated: boolean;
    user?: any;
    token_expires_at?: string;
}

interface RefreshResponse {
    message: string;
}

class AuthService {
    private refreshTokenPromise: Promise<boolean> | null = null;

    constructor() {
        // REMOVED: setupInterceptors() - AuthContext handles interceptors
        // This prevents duplicate interceptors that cause race conditions
    }

    // REMOVED: shouldSkipRefresh method - no longer needed since interceptors are removed

    async checkAuthStatus(): Promise<AuthStatus> {
        try {
            // FIXED: Added withCredentials
            const response: AxiosResponse<AuthStatus> = await axios.get('/api/auth/otp/status', {
                withCredentials: true,  // CRITICAL FIX
                timeout: 10000
            });
            return response.data;
        } catch (error) {
            console.error('Auth status check failed:', error);
            
            // If it's a 401, user is definitely not authenticated
            if (error && typeof error === 'object' && 'response' in error && 
                error.response && typeof error.response === 'object' && 
                'status' in error.response && error.response.status === 401) {
                return { is_authenticated: false };
            }
            
            // For other errors (network, timeout), retry once
            try {
                console.log('Retrying auth status check...');
                const retryResponse: AxiosResponse<AuthStatus> = await axios.get('/api/auth/otp/status', {
                    withCredentials: true,
                    timeout: 5000
                });
                return retryResponse.data;
            } catch (retryError) {
                console.error('Auth status retry failed:', retryError);
                return { is_authenticated: false };
            }
        }
    }

    async refreshToken(): Promise<boolean> {
        if (this.refreshTokenPromise) {
            return this.refreshTokenPromise;
        }

        this.refreshTokenPromise = this.performRefresh();
        
        try {
            const result = await this.refreshTokenPromise;
            return result;
        } finally {
            this.refreshTokenPromise = null;
        }
    }

    private async performRefresh(): Promise<boolean> {
        try {
            // FIXED: Added withCredentials and timeout
            const response: AxiosResponse<RefreshResponse> = await axios.post('/api/auth/otp/refresh', {}, {
                withCredentials: true,  // CRITICAL FIX
                timeout: 10000
            });
            
            console.log('Token refreshed successfully:', response.data.message);
            return true;
        } catch (error) {
            console.error('Token refresh failed:', error);
            return false;
        }
    }

    async logout(): Promise<void> {
        try {
            // FIXED: Added withCredentials
            await axios.post('/api/auth/otp/logout', {}, {
                withCredentials: true  // CRITICAL FIX
            });
        } catch (error) {
            console.error('Logout error:', error);
        } finally {
            this.handleAuthFailure();
        }
    }

    private handleAuthFailure(): void {
        // Clear any cached data - REMOVE localStorage usage
        // localStorage.removeItem('user'); // REMOVE THIS LINE
        
        // Redirect to landing
        if (typeof window !== 'undefined') {
            window.location.href = '/landing';
        }
    }

    async getUserPermissions(): Promise<any> {
        try {
            // FIXED: Added withCredentials
            const response = await axios.get('/api/auth/permissions', {
                withCredentials: true,  // CRITICAL FIX
                timeout: 10000
            });
            return response.data;
        } catch (error) {
            console.error('Failed to fetch permissions:', error);
            // Return default permissions
            return {
                can_upload: true,
                can_edit: true,
                is_admin: false,
                is_read_only: false
            };
        }
    }

    async getUserProfile(): Promise<any> {
        try {
            // FIXED: Added withCredentials
            const response = await axios.get('/api/auth/me', {
                withCredentials: true,  // CRITICAL FIX
                timeout: 10000
            });
            return response.data;
        } catch (error) {
            console.error('Failed to fetch user profile:', error);
            throw error;
        }
    }
}

export const authService = new AuthService();
export default authService;
