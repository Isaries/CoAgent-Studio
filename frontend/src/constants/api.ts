export const API_ENDPOINTS = {
    REFRESH: '/login/refresh',
    LOGIN: '/login',
    AGENTS: {
        BASE: '/agents',
        SYSTEM: '/agents/system',
        GENERATE: '/agents/generate'
    },
    AGENT_CONFIG: {
        BASE: '/agent-config'
    },
    AGENT_TYPES: {
        BASE: '/agent-types',
        SCHEMA: (typeName: string) => `/agent-types/${typeName}/schema`
    },
    A2A: {
        WEBHOOK: '/a2a/webhook',
        HEALTH: '/a2a/health'
    },
    ORGANIZATIONS: {
        BASE: '/organizations'
    },
    PROJECTS: {
        BASE: '/projects'
    },
    THREADS: {
        BASE: '/threads',
        STATELESS: (agentId: string) => `/threads/stateless/${agentId}`
    }
} as const

export const HTTP_STATUS = {
    UNAUTHORIZED: 401,
    FORBIDDEN: 403,
    SERVER_ERROR: 500
} as const

