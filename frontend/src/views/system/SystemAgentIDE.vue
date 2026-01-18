<script setup lang="ts">
import { ref, computed } from 'vue'
import type { AgentConfig, AgentConfigVersion } from '../../types/agent'
import VersionSidebar from '../../components/PromptDesigner/VersionSidebar.vue'
import SystemAgentHeader from './components/SystemAgentHeader.vue'
import SystemAgentWorkspace from './components/SystemAgentWorkspace.vue'
import { agentService } from '../../services/agentService'
import { useToastStore } from '../../stores/toast'
import { useAgentSandbox } from '../../composables/useAgentSandbox'

interface Props {
  designConfig: AgentConfig | null
  designApiKey: string
  loading: boolean
  requirement: string
  context: string
  refineCurrent: boolean
  
  versions: AgentConfigVersion[]
}

const props = defineProps<Props>()
const emit = defineEmits([
  'update:designApiKey',
  'update:requirement',
  'update:context',
  'update:refineCurrent',
  'saveKey',
  'clearKey',
  'createVersion',
  'restoreVersion', 
  'fetchVersions',
  'update:systemPrompt'
])

const toast = useToastStore()
const { sandbox, getSimulationConfig } = useAgentSandbox()

// Local State (Simulation)
const simulationOutput = ref('')
const isSimulating = ref(false)

// We reuse the parent's version props/events for now to avoid breaking the parent-child contract 
// completely in one go, but ideally we should move version fetching inside here if it was self-contained.
// However, SystemSettingsView controls the state. 
// We will use the toggleVersions event to trigger parent fetch or local toggle.
// Wait, the new header emits 'toggleVersions'. 
const showVersions = ref(false)
const toggleVersions = () => {
  showVersions.value = !showVersions.value
  if (showVersions.value) {
    emit('fetchVersions')
  }
}

// Proxies
const designApiKeyModel = computed({
  get: () => props.designApiKey,
  set: (val) => emit('update:designApiKey', val)
})

const requirementModel = computed({
  get: () => props.requirement,
  set: (val) => emit('update:requirement', val)
})

const contextModel = computed({
  get: () => props.context,
  set: (val) => emit('update:context', val)
})

const refineCurrentModel = computed({
  get: () => props.refineCurrent,
  set: (val) => emit('update:refineCurrent', val)
})

// Meta-Prompt Simulation Logic
const handleSimulation = async () => {
  if (!requirementModel.value) return toast.warning('Please enter a test requirement')
  
  isSimulating.value = true
  try {
     const metaPrompt = props.designConfig?.system_prompt || 'System Design Agent'
     const simConfig = getSimulationConfig(designApiKeyModel.value)
     
     const res = await agentService.generatePrompt({
        requirement: requirementModel.value,
        target_agent_type: 'teacher', // Simulation target
        course_context: contextModel.value,
        
        // REVERTED: Use base key for 'api_key' to match original behavior
        api_key: designApiKeyModel.value,
        
        // Use simulation config for provider/model
        provider: simConfig.provider,
        custom_model: simConfig.model,
        custom_api_key: sandbox.enabled ? sandbox.customApiKey : undefined, // Explicit overrides

        // CRITICAL: We override the system prompt with what's in the editor
        custom_system_prompt: metaPrompt,
     })
     
     simulationOutput.value = res.data.generated_prompt

  } catch (e: any) {
    console.error(e)
    toast.error('Simulation Failed: ' + (e.response?.data?.detail || e.message))
  } finally {
    isSimulating.value = false
  }
}

</script>

<template>
  <div class="flex flex-col h-[calc(100vh-140px)] min-h-[600px] min-w-[900px] border border-white/5 rounded-2xl overflow-hidden relative shadow-[0_20px_50px_-12px_rgba(0,0,0,0.5)] bg-[#121212] backdrop-blur-3xl ring-1 ring-white/10">
    
    <SystemAgentHeader
      v-model:sandbox="sandbox"
      v-model:designApiKey="designApiKeyModel"
      :masked-api-key="!!designConfig?.masked_api_key"
      :show-versions="showVersions"
      @saveKey="$emit('saveKey')"
      @clearKey="$emit('clearKey')"
      @toggleVersions="toggleVersions"
    />

    <SystemAgentWorkspace
      :sandbox="sandbox"
      :design-config="designConfig"
      :loading="loading"
      :is-simulating="isSimulating"
      :simulation-output="simulationOutput"
      v-model:requirement="requirementModel"
      v-model:context="contextModel"
      v-model:refine-current="refineCurrentModel"
      @generate="handleSimulation"
      @clearOutput="simulationOutput = ''"
      @update:systemPrompt="$emit('update:systemPrompt', $event)"
    />

    <!-- Version Sidebar Overlay -->
    <div 
      class="absolute top-0 right-0 h-full bg-[#181818] z-30 transition-transform duration-300 border-l border-white/5 shadow-2xl"
      :class="showVersions ? 'translate-x-0' : 'translate-x-full'"
    >
       <VersionSidebar
         :versions="versions"
         :loading="loading"
         @close="showVersions = false"
         @create="$emit('createVersion', $event)"
         @restore="$emit('restoreVersion', $event)"
       />
    </div>

  </div>
</template>

<style scoped>
.animate-scale-in {
  animation: scaleIn 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}
@keyframes scaleIn {
  from { opacity: 0; transform: scaleY(0.95); margin-bottom: -20px; }
  to { opacity: 1; transform: scaleY(1); margin-bottom: 0; }
}
</style>
