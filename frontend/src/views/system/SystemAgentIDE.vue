<script setup lang="ts">
import { ref, computed } from 'vue'
import type { AgentConfig, AgentConfigVersion } from '../../types/agent'
import ModernSandboxHeader from '../../components/PromptDesigner/ModernSandboxHeader.vue'
import ModernRequirementInput from '../../components/PromptDesigner/ModernRequirementInput.vue'
import PromptEditor from '../../components/PromptDesigner/PromptEditor.vue'
import VersionSidebar from '../../components/PromptDesigner/VersionSidebar.vue'

interface SandboxState {
  enabled: boolean
  customApiKey: string
  customProvider: string
  customModel: string
  systemPrompt: string
}

interface Props {
  designConfig: AgentConfig | null
  designApiKey: string
  loading: boolean
  requirement: string
  context: string
  refineCurrent: boolean
  
  sandbox: SandboxState
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
  'generate',
  'createVersion',
  'restoreVersion', 
  'fetchVersions',
  'applySandbox'
])

// Local State
const showVersions = ref(false)

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

// Toggle Versions
const toggleVersions = () => {
  showVersions.value = !showVersions.value
  if (showVersions.value) {
    emit('fetchVersions')
  }
}
</script>

<template>
  <div class="flex flex-col h-[calc(100vh-140px)] min-h-[600px] border border-white/5 rounded-2xl overflow-hidden relative shadow-[0_20px_50px_-12px_rgba(0,0,0,0.5)] bg-[#121212] backdrop-blur-3xl ring-1 ring-white/10">
    
    <!-- Top Bar: Header & Actions -->
    <div class="h-14 bg-[#121212]/90 border-b border-white/5 flex items-center justify-between px-6 z-20">
      
      <!-- Left: Identity -->
      <div class="flex items-center gap-4">
        <div class="flex items-center gap-2">
           <div class="w-2 h-2 rounded-full bg-primary shadow-[0_0_10px_rgba(var(--p),0.8)]"></div>
           <span class="font-bold text-gray-200 tracking-wide text-sm">DESIGN STUDIO</span>
        </div>

        <div class="h-4 w-px bg-white/10 mx-2"></div>

        <!-- Sandbox Toggle -->
        <label class="label cursor-pointer gap-3 group">
          <span class="label-text text-[10px] font-bold uppercase tracking-widest transition-colors duration-300 group-hover:text-primary" 
                :class="sandbox.enabled ? 'text-primary drop-shadow-[0_0_8px_rgba(var(--p),0.6)]' : 'text-gray-500'">Sandbox</span> 
          <input type="checkbox" class="toggle toggle-primary toggle-sm border-white/10 bg-base-300" v-model="sandbox.enabled" />
        </label>
      </div>

      <!-- Right: Actions -->
      <div class="flex items-center gap-3">
         <!-- Standard Key Manager (If sandbox disabled) -->
         <div v-if="!sandbox.enabled" class="flex items-center gap-2 animate-fade-in transition-all">
             <div class="flex items-center bg-white/5 rounded-full px-3 py-1 border border-white/5 focus-within:border-primary/50 transition-colors">
               <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="mr-2 text-gray-500"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"></path></svg>
               <input
                 type="password"
                 v-model="designApiKeyModel"
                 :placeholder="designConfig?.masked_api_key ? `•••••••••••••` : 'System API Key'"
                 class="bg-transparent border-none focus:outline-none w-24 text-xs text-center text-gray-300 placeholder-gray-600"
               />
               <button @click="$emit('saveKey')" class="ml-2 text-primary hover:text-primary-focus transition-colors" :disabled="!designApiKey" title="Save Key">
                  <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path><polyline points="17 21 17 13 7 13 7 21"></polyline><polyline points="7 3 7 8 15 8"></polyline></svg>
               </button>
             </div>
             <button v-if="designConfig?.masked_api_key" @click="$emit('clearKey')" class="btn btn-circle btn-xs btn-ghost text-error opacity-50 hover:opacity-100">
                <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
             </button>
         </div>

         <div class="h-4 w-px bg-white/10 mx-2"></div>

         <button 
          @click="toggleVersions" 
          class="btn btn-sm btn-ghost gap-2 hover:bg-white/10 text-gray-400 hover:text-white transition-all"
          :class="{ 'text-primary bg-primary/10 border-primary/20': showVersions }"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
          <span class="hidden sm:inline text-xs">History</span>
        </button>
      </div>
    </div>

    <!-- Main Workspace -->
    <div class="flex-1 flex overflow-hidden relative">
      
      <!-- Left Pane: Controls (Sidebar) -->
      <div class="w-[360px] border-r border-white/5 bg-[#141414] flex flex-col z-10 shadow-2xl relative">
         
         <!-- Background Gradient Mesh -->
         <div class="absolute top-0 left-0 w-full h-[200px] bg-gradient-to-b from-primary/5 to-transparent pointer-events-none"></div>

         <div class="p-5 flex-1 flex flex-col overflow-y-auto gap-4 relative z-10">
            
            <!-- Sandbox Header Card (Conditional) -->
            <div v-if="sandbox.enabled" class="animate-scale-in origin-top">
                <ModernSandboxHeader 
                  :model-value="sandbox" 
                  @apply="$emit('applySandbox')"
                  @update:modelValue="e => Object.assign(sandbox, e)"
                />
            </div>

            <!-- Requirement Input -->
            <ModernRequirementInput
              v-model:requirement="requirementModel"
              v-model:context="contextModel"
              v-model:refine-current="refineCurrentModel"
              :can-edit="!!designConfig?.system_prompt"
              :loading="loading"
              @generate="$emit('generate')"
            />
         </div>
      </div>

      <!-- Right Pane: Code Editor -->
      <div class="flex-1 bg-[#1e1e1e] relative flex flex-col">
         <!-- Editor Component -->
         <PromptEditor 
           :model-value="designConfig?.system_prompt || ''" 
           @update:modelValue="val => { if(designConfig) designConfig.system_prompt = val }"
           class="flex-1 border-none rounded-none w-full h-full text-sm font-mono"
         />
      </div>

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
