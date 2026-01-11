import { ref, type Ref } from 'vue'
import { agentService } from '../services/agentService'
import type { AgentConfig, DesignDbState } from '../types/agent'
import { useToastStore } from '../stores/toast'

export function useDesignAgent(
  courseId: string,
  courseTitle: Ref<string | undefined>,
  activeTab: Ref<string>
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
        target_agent_type: activeTab.value,
        course_context: designDb.value.context || courseTitle.value || '',
        api_key: designApiKey.value,
        course_id: courseId,
        provider: provider
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

  const saveDesignAgentKey = async (fetchConfigsCallback?: () => Promise<void>) => {
    if (!designApiKey.value && designApiKey.value !== 'CLEAR_KEY') return

    const payload: any = {
      name: 'Design Agent Config',
      type: 'design',
      system_prompt: 'System Design Agent',
      model_provider: 'gemini',
      api_key: designApiKey.value === 'CLEAR_KEY' ? '' : designApiKey.value
    }

    try {
      if (designConfig.value) {
        await agentService.updateAgent(designConfig.value.id, payload)
      } else {
        await agentService.createAgent(courseId, payload)
      }
      toast.success('Design Agent Key Saved for this Course')
      designApiKey.value = ''
      if (fetchConfigsCallback) await fetchConfigsCallback()
    } catch (e) {
      console.error(e)
      toast.error('Failed to save Design Agent Key')
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

  return {
    designConfig,
    designApiKey,
    designDb,
    generatePrompt,
    saveDesignAgentKey,
    handleClearDesignKey
  }
}
