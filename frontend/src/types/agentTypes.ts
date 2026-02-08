import { AgentCategory } from './enums'

/**
 * Agent Type Metadata - represents a type definition from the backend
 */
export interface AgentTypeMetadata {
    id: string
    type_name: string
    display_name: string
    description?: string
    category: AgentCategory | string
    icon?: string
    color?: string
    default_system_prompt?: string
    default_model_provider: string
    default_model?: string
    default_settings?: Record<string, unknown>
    default_capabilities?: string[]
    is_system: boolean
}

/**
 * Schema for creating a new custom agent type
 */
export interface AgentTypeCreate {
    type_name: string
    display_name: string
    description?: string
    category: AgentCategory | string
    icon?: string
    color?: string
    default_system_prompt?: string
    default_model_provider?: string
    default_model?: string
    default_settings?: Record<string, unknown>
    default_capabilities?: string[]
}

// Re-export ExternalAgentConfig from agent.ts to avoid duplication
export type { ExternalAgentConfig } from './agent'

/**
 * Schema returned from /agent-types/{type}/schema endpoint
 */
export interface AgentTypeSchema {
    type_name: string
    category: string
    defaults: {
        system_prompt?: string
        model_provider: string
        model?: string
        settings?: Record<string, unknown>
        capabilities?: string[]
    }
    is_external: boolean
}
