import axios from 'axios';

const API_URL = import.meta.env.VITE_API_BASE_URL || "/api/v1";

export interface UserAPIKey {
    id: string;
    user_id: string;
    provider: string;
    alias: string;
    description?: string;
    masked_key: string;
    created_at: string;
}

export interface CreateKeyPayload {
    provider: string;
    alias: string;
    api_key: string;
    description?: string;
}

export const userKeyService = {
    async listKeys(): Promise<UserAPIKey[]> {
        const response = await axios.get(`${API_URL}/users/keys`);
        return response.data;
    },

    async addKey(payload: CreateKeyPayload): Promise<UserAPIKey> {
        const response = await axios.post(`${API_URL}/users/keys`, payload);
        return response.data;
    },

    async deleteKey(keyId: string): Promise<void> {
        await axios.delete(`${API_URL}/users/keys/${keyId}`);
    }
};
