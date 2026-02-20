import { ref, type Ref } from 'vue'
import { agentService } from '../services/agentService'
import type { AgentConfig, DesignDbState, AgentConfigVersion } from '../types/agent'
import { useToastStore } from '../stores/toast'

export function useDesignAgent(
  scope: 'project' | 'system',
  projectId?: string,
  projectTitle?: Ref<string | undefined>,
  activeTab?: Ref<string>
) {
  const toast = useToastStore()

  const designConfig = ref<AgentConfig | null>(null)
  const designApiKey = ref('')

  const designDb = ref<DesignDbState>({
    requirement: '',
    context: '',
    loading: false,
    refineCurrent: false
  })

  // Sandbox State
  const sandbox = ref({
    enabled: false,
    customApiKey: '',
    customProvider: 'gemini',
    customModel: '', // will default in backend or UI
    systemPrompt: '' // override for design agent itself
  })

  // Versioning
  const versions = ref<AgentConfigVersion[]>([])

  const fetchVersions = async () => {
    if (!designConfig.value) return
    try {
      const res = await agentService.getVersions(designConfig.value.id)
      versions.value = res.data
    } catch (e) {
      console.error(e)
    }
  }

  const createVersion = async (label: string) => {
    if (!designConfig.value) return
    try {
      await agentService.createVersion(designConfig.value.id, { version_label: label })
      toast.success('Version saved')
      await fetchVersions()
    } catch (e) {
      toast.error('Failed to save version')
    }
  }

  const restoreVersion = async (version: AgentConfigVersion, callback?: () => void) => {
    if (!designConfig.value) return
    if (!confirm(`Restoring version "${version.version_label}". Current unsaved changes will be lost. Continue?`)) return

    try {
      const res = await agentService.restoreVersion(designConfig.value.id, version.id)
      designConfig.value = res.data
      toast.success('Version restored')
      if (callback) callback()
    } catch (e) {
      toast.error('Failed to restore version')
    }
  }

  // We need access to the current editing prompt to refine it
  const generatePrompt = async (currentPrompt: string, provider: string) => {
    if (!designDb.value.requirement) return null
    designDb.value.loading = true

    let req = designDb.value.requirement
    if (designDb.value.refineCurrent && currentPrompt) {
      req += `\n\n[CONTEXT: EXISTING PROMPT TO REFINE]\n${currentPrompt}\n[END EXISTING PROMPT]\nPlease refine this prompt based on the requirements.`
    }

    try {
      const res = await agentService.generatePrompt({
        requirement: req,
        target_agent_type: activeTab?.value || 'teacher', // Default to teacher for system
        project_id: scope === 'project' ? projectId : undefined,
        provider: provider,
        // Optional sandbox context/overrides
        custom_system_prompt: designDb.value.context || projectTitle?.value || '',
        ...(sandbox.value.enabled ? {
          custom_system_prompt: sandbox.value.systemPrompt || undefined,
          custom_api_key: sandbox.value.customApiKey || undefined,
          custom_provider: sandbox.value.customProvider || undefined,
          custom_model: sandbox.value.customModel || undefined
        } : {})
      })
      return res.data.generated_prompt
    } catch (e: any) {
      if (e.response && e.response.status === 400 && e.response.data.detail) {
        toast.error(e.response.data.detail)
      } else {
        toast.error('Generation failed')
      }
      return null
    } finally {
      designDb.value.loading = false
    }
  }

  const saveDesignAgentKey = async (
    fetchConfigsCallback?: () => Promise<void>,
    overrides?: Partial<AgentConfig>
  ) => {
    // If clearing key, allow. If saving normal key, check presence.
    if (!overrides && !designApiKey.value && designApiKey.value !== 'CLEAR_KEY') return

    const payload: any = {
      name: 'Design Agent Config',
      type: 'design',
      project_id: scope === 'project' ? projectId : undefined,
      // Default values if not overridden
      system_prompt: 'System Design Agent',
      model_provider: 'gemini',
      ...overrides
    }

    // Handle API Key logic
    if (designApiKey.value === 'CLEAR_KEY') {
      payload.api_key = ''
    } else if (designApiKey.value) {
      payload.api_key = designApiKey.value
    } else if (payload.encrypted_api_key === undefined) {
      // If we are not setting a new key, and not clearing, we might be just updating other fields
      // But for safety, if this function is primarily for KEY saving, we keep existing logic.
      // However, with overrides, we might be updating model/prompt without touching key.
      payload.api_key = null
    }

    try {
      if (scope === 'system') {
        await agentService.updateSystemAgent(payload)
      } else {
        if (designConfig.value) {
          await agentService.updateAgent(payload)
        } else if (projectId) {
          await agentService.createAgent(projectId, payload)
        }
      }

      toast.success('Design Agent Config Saved')
      if (designApiKey.value && designApiKey.value !== 'CLEAR_KEY') {
        designApiKey.value = '' // clear input after save
      }
      if (fetchConfigsCallback) await fetchConfigsCallback()
    } catch (e) {
      console.error(e)
      toast.error('Failed to save Design Agent Config')
    }
  }

  const handleClearDesignKey = async (
    confirmCallback: () => Promise<boolean>,
    fetchConfigsCallback?: () => Promise<void>
  ) => {
    if (!(await confirmCallback())) return
    designApiKey.value = 'CLEAR_KEY'
    await saveDesignAgentKey(fetchConfigsCallback)
  }

  const applySandboxToConfig = async (fetchConfigsCallback?: () => Promise<void>) => {
    if (!sandbox.value.enabled) return

    // If sandbox has a custom key, set it as the live key for this save
    if (sandbox.value.customApiKey) {
      designApiKey.value = sandbox.value.customApiKey
    }

    await saveDesignAgentKey(fetchConfigsCallback, {
      system_prompt: sandbox.value.systemPrompt || 'System Design Agent',
      model_provider: sandbox.value.customProvider || 'gemini',
      model: sandbox.value.customModel || ''
    })
  }

  return {
    designConfig,
    designApiKey,
    designDb,
    generatePrompt,
    saveDesignAgentKey,
    handleClearDesignKey,
    sandbox,
    versions,
    fetchVersions,
    createVersion,
    restoreVersion,
    applySandboxToConfig
  }
}
