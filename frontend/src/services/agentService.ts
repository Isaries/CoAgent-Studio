import api from '../api'
import { API_ENDPOINTS } from '../constants/api'
import type {
  AgentConfig,
  AgentConfigVersion,
  GeneratePromptRequest,
  GeneratePromptResponse,
  VersionCreate
} from '../types/agent'

export const agentService = {
  getAgents: (courseId: string) =>
    api.get<AgentConfig[]>(`${API_ENDPOINTS.AGENTS.BASE}/${courseId}`),

  getSystemAgents: () =>
    api.get<AgentConfig[]>(API_ENDPOINTS.AGENTS.SYSTEM),

  createAgent: (courseId: string, data: Partial<AgentConfig>) =>
    api.post<AgentConfig>(`${API_ENDPOINTS.AGENTS.BASE}/${courseId}`, data),

  updateAgent: (data: Partial<AgentConfig>) => {
    if (!data.id) throw new Error('Config ID required for update')
    return api.put<AgentConfig>(`${API_ENDPOINTS.AGENTS.BASE}/${data.id}`, data)
  },

  updateSystemAgent: (data: Partial<AgentConfig>) => {
    return api.put<AgentConfig>(`${API_ENDPOINTS.AGENTS.SYSTEM}/${data.type}`, data)
  },

  getKeys: (agentId: string) =>
    api.get<Record<string, string>>(`${API_ENDPOINTS.AGENTS.BASE}/${agentId}/keys`).then((res) => res.data),

  updateKeys: (agentId: string, keys: Record<string, string | null>) =>
    api.put<AgentConfig>(`${API_ENDPOINTS.AGENTS.BASE}/${agentId}/keys`, keys).then((res) => res.data),

  deleteAgent: (agentId: string) =>
    api.delete(`${API_ENDPOINTS.AGENTS.BASE}/${agentId}`),

  activateAgent: (agentId: string) =>
    api.put(`${API_ENDPOINTS.AGENTS.BASE}/${agentId}/activate`),

  generatePrompt: (data: GeneratePromptRequest) =>
    api.post<GeneratePromptResponse>(API_ENDPOINTS.AGENTS.GENERATE, data),

  // Versioning
  createVersion: (configId: string, data: VersionCreate) =>
    api.post<AgentConfigVersion>(`${API_ENDPOINTS.AGENT_CONFIG.BASE}/${configId}/versions`, data),

  getVersions: (configId: string) =>
    api.get<AgentConfigVersion[]>(`${API_ENDPOINTS.AGENT_CONFIG.BASE}/${configId}/versions`),

  restoreVersion: (configId: string, versionId: string) =>
    api.post<AgentConfig>(`${API_ENDPOINTS.AGENT_CONFIG.BASE}/${configId}/versions/${versionId}/restore`)
}
