import api from '../api'
import type { AgentConfig } from '../types/agent'
import { AgentType } from '../types/enums'

/*
  Standardized Analytics Service
*/
export const analyticsService = {
    async getSystemAnalyticsAgent() {
        // Current backend logic: GET /agents/system returns list. We filter for analytics.
        const res = await api.get<AgentConfig[]>('/agents/system')
        return res.data.find(a => a.type === AgentType.ANALYTICS)
    },

    async updateSystemAnalyticsAgent(payload: {
        type: AgentType.ANALYTICS
        system_prompt: string
        api_key?: string
        model_provider: string
    }) {
        return api.put('/agents/system/analytics', payload)
    }
}
