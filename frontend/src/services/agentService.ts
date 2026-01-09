import api from '../api'
import type { AgentConfig, GeneratePromptRequest, GeneratePromptResponse } from '../types/agent'

export const agentService = {
    getAgents: (courseId: string) => api.get<AgentConfig[]>(`/agents/${courseId}`),

    getAgent: (agentId: string) => api.get<AgentConfig>(`/agents/${agentId}`), // Although typically we fetch all by course

    createAgent: (courseId: string, data: Partial<AgentConfig>) => api.post<AgentConfig>(`/agents/${courseId}`, data),

    updateAgent: (agentId: string, data: Partial<AgentConfig>) => api.put<AgentConfig>(`/agents/${agentId}`, data),

    deleteAgent: (agentId: string) => api.delete(`/agents/${agentId}`),

    activateAgent: (agentId: string) => api.put(`/agents/${agentId}/activate`),

    generatePrompt: (data: GeneratePromptRequest) => api.post<GeneratePromptResponse>('/agents/generate', data)
}
