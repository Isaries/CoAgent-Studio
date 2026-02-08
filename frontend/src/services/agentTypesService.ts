import api from '../api'
import { API_ENDPOINTS } from '../constants/api'
import type { AgentTypeMetadata, AgentTypeCreate, AgentTypeSchema } from '../types/agentTypes'

/**
 * Service for managing agent types via the backend API.
 * Enables dynamic agent type creation and management.
 */
export const agentTypesService = {
    /**
     * List all available agent types
     * @param category Optional filter by category
     * @param includeSystem Whether to include system types (default: true)
     */
    list: (category?: string, includeSystem = true) => {
        const params = new URLSearchParams()
        if (category) params.append('category', category)
        params.append('include_system', String(includeSystem))

        return api.get<AgentTypeMetadata[]>(`${API_ENDPOINTS.AGENT_TYPES.BASE}?${params}`)
    },

    /**
     * Get a specific agent type by name
     */
    get: (typeName: string) =>
        api.get<AgentTypeMetadata>(`${API_ENDPOINTS.AGENT_TYPES.BASE}/${typeName}`),

    /**
     * Get the configuration schema for an agent type
     */
    getSchema: (typeName: string) =>
        api.get<AgentTypeSchema>(API_ENDPOINTS.AGENT_TYPES.SCHEMA(typeName)),

    /**
     * Create a new custom agent type
     */
    create: (data: AgentTypeCreate) =>
        api.post<AgentTypeMetadata>(API_ENDPOINTS.AGENT_TYPES.BASE, data),

    /**
     * Delete a custom agent type (system types cannot be deleted)
     */
    delete: (typeName: string) =>
        api.delete(`${API_ENDPOINTS.AGENT_TYPES.BASE}/${typeName}`),

    // ============================================================
    // External Agent Management
    // ============================================================

    /**
     * List all external agents
     */
    listExternalAgents: () =>
        api.get(`${API_ENDPOINTS.AGENTS.BASE}/external/list`),

    /**
     * Create a new external agent
     */
    createExternalAgent: (data: {
        name: string
        type?: string
        webhook_url: string
        auth_type: 'none' | 'bearer' | 'oauth2'
        auth_token?: string
        oauth_config?: object
        timeout_ms?: number
        fallback_message?: string
        system_prompt?: string
    }) =>
        api.post(`${API_ENDPOINTS.AGENTS.BASE}/external/create`, data),

    /**
     * Test connection to an external agent via ID (for existing agents)
     */
    testConnection: (agentId: string) =>
        api.get<{ success: boolean; status_code?: number; latency_ms?: number; error?: string }>(
            `${API_ENDPOINTS.AGENTS.BASE}/${agentId}/test-connection`
        ),

    /**
     * Test connection parameters (for uncreated agents)
     */
    testConnectionParams: (data: {
        name: string
        webhook_url: string
        auth_type: 'none' | 'bearer' | 'oauth2'
        auth_token?: string
        oauth_config?: object
        timeout_ms?: number
    }) =>
        api.post<{ success: boolean; status_code?: number; latency_ms?: number; error?: string }>(
            `${API_ENDPOINTS.AGENTS.BASE}/external/test-connection`,
            { ...data, type: 'external' }
        ),

    /**
     * Check A2A webhook health
     */
    checkA2AHealth: () =>
        api.get<{ status: string; timestamp: string }>(API_ENDPOINTS.A2A.HEALTH)
}

export default agentTypesService
