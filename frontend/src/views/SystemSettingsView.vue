<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../api'
import { useToastStore } from '../stores/toast'
import { useConfirm } from '../composables/useConfirm'
import { useDesignAgent } from '../composables/useDesignAgent'
import SystemAgentIDE from './system/SystemAgentIDE.vue'

// Config State
const loading = ref(false)
const toast = useToastStore()
const { confirm } = useConfirm()

// Tabs
const activeTab = ref<'design' | 'analytics'>('design')

// Design Agent Logic (System Scope)
const {
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
} = useDesignAgent('system')

// Analytics Config (Legacy Manual Logic for now)
const analyticsConfig = ref({ prompt: '', apiKey: '', provider: 'gemini' })

const fetchSettings = async () => {
  loading.value = true
  try {
    const res = await api.get('/agents/system')
    const data = res.data

    // Populate Design Agent
    const design = data.find((c: any) => c.type === 'design')
    if (design) {
      designConfig.value = design
    }
    
    // Populate Analytics
    const analytics = data.find((c: any) => c.type === 'analytics')
    if (analytics) {
      analyticsConfig.value.prompt = analytics.system_prompt
      analyticsConfig.value.provider = analytics.model_provider
      // analyticsConfig.value.apiKey = ... (masked)
    }

    // Also fetch versions for design agent
    if (design) await fetchVersions()

  } catch (e) {
    console.error('Failed to fetch system settings', e)
  } finally {
    loading.value = false
  }
}

const saveAnalyticsAgent = async () => {
  try {
    await api.put(`/agents/system/analytics`, {
      type: 'analytics',
      system_prompt: analyticsConfig.value.prompt,
      api_key: analyticsConfig.value.apiKey,
      model_provider: analyticsConfig.value.provider,
      settings: {}
    })
    toast.success(`Analytics Agent settings saved!`)
  } catch (e) {
    console.error(e)
    toast.error('Error saving settings')
  }
}

// Wrapper for saving current prompt (manual save equivalent)
const saveCurrentDesignPrompt = async () => {
   // In 99% of cases, we just updated the designConfig ref.
   // But we need to persist it.
   // The useDesignAgent doesn't expose a direct 'saveConfig' for system...
   // Wait, `saveDesignAgentKey` saves key.
   // We might need a manual save if the user edits the prompt directly.
   // Let's implement a manual save for consistency if needed, or rely on generation.
   // Actually, for system agent, we usually just update it.
   
   if (!designConfig.value) return
   
   try {
     await api.put(`/agents/system/design`, {
       type: 'design',
       system_prompt: designConfig.value.system_prompt,
       // We don't send key here usually, handled by separate endpoint or masked.
       // But the PUT endpoint expects full config.
       // Let's reuse the logic from `applySandboxToConfig` but for current state
       model_provider: designConfig.value.model_provider || 'gemini', 
       model: designConfig.value.model
     })
     toast.success('System Prompt Saved')
   } catch (e) {
     toast.error('Failed to save')
   }
}

onMounted(() => {
  fetchSettings()
})
</script>

<template>
  <div class="p-6 max-w-[1600px] mx-auto min-h-screen flex flex-col">
    <!-- Header -->
    <div class="mb-6 flex justify-between items-end">
      <div>
        <h1 class="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary to-secondary">
          CoAgent Intelligence Hub
        </h1>
        <p class="text-gray-500 text-sm mt-1">
          Configure global system behaviors and utility agents.
        </p>
      </div>
      
      <!-- Tabs -->
      <div role="tablist" class="tabs tabs-boxed bg-base-200 p-1">
        <a 
          role="tab" 
          class="tab px-6" 
          :class="{ 'tab-active bg-primary text-primary-content': activeTab === 'design' }"
          @click="activeTab = 'design'"
        >
          <span class="flex items-center gap-2 font-bold">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path><circle cx="12" cy="12" r="3"></circle></svg>
            Design Agent
          </span>
        </a>
        <a 
          role="tab" 
          class="tab px-6"
          :class="{ 'tab-active bg-secondary text-secondary-content': activeTab === 'analytics' }"
          @click="activeTab = 'analytics'"
        >
          <span class="flex items-center gap-2 font-bold">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>
            Analytics Agent
          </span>
        </a>
      </div>
    </div>

    <!-- Content -->
    <div class="flex-1">
      <div v-if="loading" class="flex justify-center p-20">
        <span class="loading loading-spinner loading-lg text-primary"></span>
      </div>

      <div v-else>
        <!-- DESIGN AGENT IDE -->
        <div v-show="activeTab === 'design'" class="animate-fade-in">
           <SystemAgentIDE
            :design-config="designConfig"
            :design-api-key="designApiKey"
            :loading="designDb.loading"
            :requirement="designDb.requirement"
            :context="designDb.context"
            :refine-current="designDb.refineCurrent"
            :sandbox="sandbox"
            :versions="versions"
            
            @update:design-api-key="designApiKey = $event"
            @update:requirement="designDb.requirement = $event"
            @update:context="designDb.context = $event"
            @update:refine-current="designDb.refineCurrent = $event"
            
            @saveKey="saveDesignAgentKey(fetchSettings)"
            @clearKey="handleClearDesignKey(async()=>confirm('Clear Key', 'Remove global key?'), fetchSettings)"
            @generate="generatePrompt(designConfig?.system_prompt || '', designConfig?.model_provider || 'gemini').then(res => { if(res && designConfig) designConfig.system_prompt = res })"
            
            @createVersion="createVersion"
            @restoreVersion="restoreVersion"
            @fetchVersions="fetchVersions"
            @applySandbox="applySandboxToConfig(fetchSettings)"
           />
           
           <!-- Manual Save Bar (Optional Enhancement) -->
           <div class="mt-4 flex justify-end" v-if="designConfig">
              <button @click="saveCurrentDesignPrompt" class="btn btn-primary" :disabled="loading">
                Save System Design Logic
              </button>
           </div>
        </div>

        <!-- ANALYTICS AGENT FORM -->
        <div v-show="activeTab === 'analytics'" class="max-w-2xl mx-auto mt-10 animate-fade-in">
          <div class="card bg-base-100 shadow-xl border border-base-300">
            <div class="card-body">
              <div class="flex justify-between items-start">
                <div>
                  <h2 class="card-title text-secondary flex items-center gap-2">
                    <span class="text-2xl">📊</span> Analytics Agent
                  </h2>
                  <p class="text-sm opacity-70 mt-1">
                    This agent analyzes chat logs and provides insights to teachers across the platform.
                  </p>
                </div>
              </div>

              <div class="divider"></div>

              <div class="form-control mb-4">
                <label class="label"><span class="label-text font-bold">Global API Key</span></label>
                <div class="join">
                  <input
                    type="password"
                    v-model="analyticsConfig.apiKey"
                    placeholder="sk-..."
                    class="input input-bordered join-item w-full"
                  />
                </div>
                <label class="label"><span class="label-text-alt opacity-50">Used for all analytics jobs unless overridden.</span></label>
              </div>

              <div class="form-control mb-4">
                <label class="label"
                  ><span class="label-text font-bold">Analysis Instructions</span></label
                >
                <textarea
                  v-model="analyticsConfig.prompt"
                  class="textarea textarea-bordered h-64 font-mono text-sm leading-relaxed"
                  placeholder="You are an educational data analyst..."
                ></textarea>
              </div>

              <div class="card-actions justify-end mt-4">
                <button @click="saveAnalyticsAgent" class="btn btn-secondary px-8">
                  Save Configuration
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.animate-fade-in {
  animation: fadeIn 0.3s ease-in-out;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
