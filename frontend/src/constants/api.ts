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
    }
} as const

export const HTTP_STATUS = {
    UNAUTHORIZED: 401,
    FORBIDDEN: 403,
    SERVER_ERROR: 500
} as const
