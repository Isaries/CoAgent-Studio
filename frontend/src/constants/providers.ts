export const AI_PROVIDERS = {
    GEMINI: 'gemini',
    OPENAI: 'openai',
    CLAUDE: 'claude'
} as const

export type AiProvider = typeof AI_PROVIDERS[keyof typeof AI_PROVIDERS]

export const DEFAULT_PROVIDER = AI_PROVIDERS.GEMINI
