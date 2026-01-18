import { reactive } from 'vue'
import { DEFAULT_PROVIDER, type AiProvider } from '../constants/providers'

export interface SandboxState {
    enabled: boolean
    customApiKey: string
    customProvider: AiProvider | string
    customModel: string
    systemPrompt: string
}

export function useAgentSandbox() {
    const sandbox = reactive<SandboxState>({
        enabled: false,
        customApiKey: '',
        customProvider: DEFAULT_PROVIDER,
        customModel: '',
        systemPrompt: ''
    })

    // Toggle sandbox mode
    const toggleSandbox = () => {
        sandbox.enabled = !sandbox.enabled
    }

    // Reset sandbox to default state
    const resetSandbox = () => {
        sandbox.enabled = false
        sandbox.customApiKey = ''
        sandbox.customProvider = DEFAULT_PROVIDER
        sandbox.customModel = ''
        sandbox.systemPrompt = ''
    }

    // Helper to get effective configuration for requests
    const getSimulationConfig = (baseApiKey: string) => {
        if (!sandbox.enabled) {
            return {
                apiKey: baseApiKey,
                provider: DEFAULT_PROVIDER,
                model: undefined
            }
        }

        return {
            apiKey: sandbox.customApiKey || baseApiKey, // Fallback to base key if custom not provided, or strict? Usually fallback.
            provider: sandbox.customProvider || DEFAULT_PROVIDER,
            model: sandbox.customModel || undefined
        }
    }

    return {
        sandbox,
        toggleSandbox,
        resetSandbox,
        getSimulationConfig
    }
}
