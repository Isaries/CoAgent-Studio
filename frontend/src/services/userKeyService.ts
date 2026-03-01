import api from '../api';
import type { ScheduleConfig } from '../types/agent';

export interface UserAPIKey {
    id: string;
    user_id: string;
    provider: string;
    alias: string;
    description?: string;
    masked_key: string;
    is_active: boolean;
    schedule_config?: ScheduleConfig | null;
    created_at: string;
    updated_at: string;
}

export interface CreateKeyPayload {
    provider: string;
    alias: string;
    api_key: string;
    description?: string;
}

export const userKeyService = {
    async listKeys(): Promise<UserAPIKey[]> {
        const response = await api.get('/users/keys');
        return response.data;
    },

    async addKey(payload: CreateKeyPayload): Promise<UserAPIKey> {
        const response = await api.post('/users/keys', payload);
        return response.data;
    },

    async deleteKey(keyId: string): Promise<void> {
        await api.delete(`/users/keys/${keyId}`);
    },

    async updateKeySchedule(
        keyId: string,
        data: { is_active?: boolean; schedule_config?: ScheduleConfig | null }
    ): Promise<{ message: string; is_active: boolean; schedule_config: ScheduleConfig | null }> {
        const response = await api.put(`/users/keys/${keyId}/schedule`, data);
        return response.data;
    },
};
