import axios from 'axios';

// For mobile testing, replace 'localhost' with your computer's LAN IP (e.g., '192.168.1.100')
// or use '10.0.2.2' for Android Emulator.
// PROXY UPDATE: Using relative path to allow Vite proxy to handle routing
const API_BASE_URL = '';

export const apiClient = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Add auth token interceptor
apiClient.interceptors.request.use((config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// Handle 401 responses (token expired)
apiClient.interceptors.response.use(
    (response) => response,
    async (error) => {
        if (error.response?.status === 401) {
            // Could implement token refresh here
            // For now, just clear tokens on 401
            const originalRequest = error.config;
            if (!originalRequest._retry && originalRequest.url !== '/auth/login') {
                // Clear auth state
                localStorage.removeItem('access_token');
                localStorage.removeItem('refresh_token');
                // Redirect to login
                window.location.href = '/login';
            }
        }
        return Promise.reject(error);
    }
);

export const api = {
    chat: async (userInput: string) => {
        const response = await apiClient.post('/api/chat', { user_input: userInput });
        return response.data;
    },
    admin: {
        getAgents: async () => {
            const response = await apiClient.get('/api/admin/agents');
            return response.data;
        },
        getConversations: async () => {
            const response = await apiClient.get('/api/admin/conversations');
            return response.data;
        }
    }
};

// Auth API
export const authApi = {
    register: async (data: {
        email: string;
        password: string;
        role: string;
        phone_number?: string;
        consent_data_collection: boolean;
        consent_data_sharing?: boolean;
    }) => {
        const response = await apiClient.post('/auth/register', data);
        return response.data;
    },

    login: async (data: { email: string; password: string }) => {
        const response = await apiClient.post('/auth/login', data);
        return response.data;
    },

    verifyMFA: async (data: { mfa_token: string; otp_code: string }) => {
        const response = await apiClient.post('/auth/verify-mfa', data);
        return response.data;
    },

    refresh: async (refreshToken: string) => {
        const response = await apiClient.post('/auth/refresh', { refresh_token: refreshToken });
        return response.data;
    },

    logout: async () => {
        const response = await apiClient.post('/auth/logout');
        return response.data;
    },

    me: async () => {
        const response = await apiClient.get('/auth/me');
        return response.data;
    },

    verifyEmail: async (otpCode: string) => {
        const response = await apiClient.post(`/auth/verify-email?otp_code=${otpCode}`);
        return response.data;
    },

    resendVerification: async () => {

        forgotPassword: async (email: string) => {
        const response = await apiClient.post('/auth/forgot-password', { email });
        return response.data;
    },

    resetPassword: async (data: { email: string; otp_code: string; new_password: string }) => {
        const response = await apiClient.post('/auth/reset-password', data);
        return response.data;
    },
        const response = await apiClient.post('/auth/resend-verification');
        return response.data;
    },

    mfa: {
        status: async () => {
            const response = await apiClient.get('/auth/mfa/status');
            return response.data;
        },
        enable: async (data: { method: string; phone_number?: string }) => {
            const response = await apiClient.post('/auth/mfa/enable', data);
            return response.data;
        },
        disable: async () => {
            const response = await apiClient.post('/auth/mfa/disable');
            return response.data;
        },
    },

    consent: {
        list: async () => {
            const response = await apiClient.get('/auth/consents');
            return response.data;
        },
        update: async (data: { consent_type: string; granted: boolean }) => {
            const response = await apiClient.post('/auth/consent', data);
            return response.data;
        },
    },

    assignments: {
        pending: async () => {
            const response = await apiClient.get('/auth/assignments/pending');
            return response.data;
        },
        myPhysician: async () => {
            const response = await apiClient.get('/auth/assignments/patient/my-physician');
            return response.data;
        },
        myPatients: async () => {
            const response = await apiClient.get('/auth/assignments/physician/my-patients');
            return response.data;
        },
        requestPhysician: async (email: string) => {
            const response = await apiClient.post('/auth/assignments/patient/request-physician', { physician_email: email });
            return response.data;
        },
        invitePatient: async (email: string) => {
            const response = await apiClient.post('/auth/assignments/physician/invite-patient', { patient_email: email });
            return response.data;
        },
        approve: async (assignmentId: string) => {
            const response = await apiClient.post(`/auth/assignments/${assignmentId}/approve`);
            return response.data;
        },
        reject: async (assignmentId: string) => {
            const response = await apiClient.post(`/auth/assignments/${assignmentId}/reject`);
            return response.data;
        },
    }
};
