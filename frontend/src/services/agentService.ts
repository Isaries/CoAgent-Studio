import api from '../api'
import type {
  AgentConfig,
  AgentConfigVersion,
  GeneratePromptRequest,
  GeneratePromptResponse,
  VersionCreate
} from '../types/agent'

export const agentService = {
  getAgents: (courseId: string) => api.get<AgentConfig[]>(`/agent-config/${courseId}`),

  getSystemAgents: () => api.get<AgentConfig[]>('/agents/system'),

  createAgent: (courseId: string, data: Partial<AgentConfig>) =>
    // Backend uses PUT /{course_id}/{agent_type} for upsert
    api.put<AgentConfig>(`/agent-config/${courseId}/${data.type}`, data),

  updateAgent: (data: Partial<AgentConfig>) => {
    // NOTE: The backend API requires courseId + type.
    // We rely on the payload containing 'course_id'.
    return api.put<AgentConfig>(`/agent-config/${data.course_id}/${data.type}`, data)
  },

  updateSystemAgent: (data: Partial<AgentConfig>) => {
    return api.put<AgentConfig>(`/agents/system/${data.type}`, data)
  },

  getKeys: (agentId: string) =>
    api.get<Record<string, string>>(`/agents/${agentId}/keys`).then((res) => res.data),

  updateKeys: (agentId: string, keys: Record<string, string | null>) =>
    api.put<AgentConfig>(`/agents/${agentId}/keys`, keys).then((res) => res.data),

  deleteAgent: (agentId: string) => api.delete(`/agents/${agentId}`),

  activateAgent: (agentId: string) => api.put(`/agents/${agentId}/activate`),

  generatePrompt: (data: GeneratePromptRequest) =>
    api.post<GeneratePromptResponse>('/agents/generate', data),

  // Versioning
  createVersion: (configId: string, data: VersionCreate) =>
    api.post<AgentConfigVersion>(`/agent-config/${configId}/versions`, data),

  getVersions: (configId: string) =>
    api.get<AgentConfigVersion[]>(`/agent-config/${configId}/versions`),

  restoreVersion: (configId: string, versionId: string) =>
    api.post<AgentConfig>(`/agent-config/${configId}/versions/${versionId}/restore`)
}
