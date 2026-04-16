import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { authApi } from '../api/client';

interface User {
    id: string;
    email: string;
    role: string;
    mfa_enabled: boolean;
    mfa_method: string | null;
    is_verified: boolean;
    created_at: string;
    last_login: string | null;
}

interface AuthContextType {
    user: User | null;
    token: string | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    mfaPending: { mfa_token: string; mfa_method: string } | null;
    login: (email: string, password: string) => Promise<{ success: boolean; mfaRequired?: boolean; error?: string }>;
    verifyMFA: (mfaToken: string, otpCode: string) => Promise<{ success: boolean; error?: string }>;
    register: (data: RegisterData) => Promise<{ success: boolean; error?: string }>;
    logout: () => Promise<void>;
    refreshUser: () => Promise<void>;
}

interface RegisterData {
    email: string;
    password: string;
    role: 'patient' | 'physician';
    mfa_method: 'email' | 'sms';
    phone_number?: string;
    physician_invite_code?: string;
    consent_data_collection: boolean;
    consent_data_sharing?: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};

interface AuthProviderProps {
    children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
    const [user, setUser] = useState<User | null>(null);
    const [token, setToken] = useState<string | null>(localStorage.getItem('access_token'));
    const [isLoading, setIsLoading] = useState(true);
    const [mfaPending, setMfaPending] = useState<{ mfa_token: string; mfa_method: string } | null>(null);

    const isAuthenticated = !!token && !!user;

    // Load user on mount if token exists
    useEffect(() => {
        const loadUser = async () => {
            if (token) {
                try {
                    const userData = await authApi.me();
                    setUser(userData);
                } catch (error) {
                    // Token invalid, clear it
                    localStorage.removeItem('access_token');
                    localStorage.removeItem('refresh_token');
                    setToken(null);
                    setUser(null);
                }
            }
            setIsLoading(false);
        };
        loadUser();
    }, [token]);

    const login = async (email: string, password: string) => {
        try {
            const response = await authApi.login({ email, password });

            if (response.mfa_required) {
                // MFA needed
                setMfaPending({
                    mfa_token: response.mfa_token,
                    mfa_method: response.mfa_method
                });
                return { success: true, mfaRequired: true };
            }

            // No MFA, login complete
            localStorage.setItem('access_token', response.access_token);
            localStorage.setItem('refresh_token', response.refresh_token);
            setToken(response.access_token);

            // Fetch user profile
            const userData = await authApi.me();
            setUser(userData);

            return { success: true };
        } catch (error: any) {
            return {
                success: false,
                error: error.response?.data?.detail || 'Login failed'
            };
        }
    };

    const verifyMFA = async (mfaToken: string, otpCode: string) => {
        try {
            const response = await authApi.verifyMFA({ mfa_token: mfaToken, otp_code: otpCode });

            localStorage.setItem('access_token', response.access_token);
            localStorage.setItem('refresh_token', response.refresh_token);
            setToken(response.access_token);
            setMfaPending(null);

            // Fetch user profile
            const userData = await authApi.me();
            setUser(userData);

            return { success: true };
        } catch (error: any) {
            return {
                success: false,
                error: error.response?.data?.detail || 'MFA verification failed'
            };
        }
    };

    const register = async (data: RegisterData) => {
        try {
            await authApi.register(data);
            return { success: true };
        } catch (error: any) {
            return {
                success: false,
                error: error.response?.data?.detail || 'Registration failed'
            };
        }
    };

    const logout = async () => {
        try {
            await authApi.logout();
        } catch (error) {
            // Ignore logout errors
        }
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        setToken(null);
        setUser(null);
        setMfaPending(null);
    };

    const refreshUser = async () => {
        if (token) {
            try {
                const userData = await authApi.me();
                setUser(userData);
            } catch (error) {
                // Token may be invalid
            }
        }
    };

    return (
        <AuthContext.Provider value={{
            user,
            token,
            isAuthenticated,
            isLoading,
            mfaPending,
            login,
            verifyMFA,
            register,
            logout,
            refreshUser
        }}>
            {children}
        </AuthContext.Provider>
    );
};
