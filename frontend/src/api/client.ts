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

export const api = {
    chat: async (userId: string, userInput: string) => {
        const response = await apiClient.post('/api/chat', { user_id: userId, user_input: userInput });
        return response.data;
    },
    warmup: async () => {
        const response = await apiClient.post('/api/chat/warmup');
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
