<script setup lang="ts">
import { ref, computed } from 'vue'
import type { AgentConfig, AgentConfigVersion } from '../../types/agent'
import SandboxControls from '../../components/PromptDesigner/SandboxControls.vue'
import PromptInputs from '../../components/PromptDesigner/PromptInputs.vue'
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
  <div class="flex flex-col h-[calc(100vh-200px)] min-h-[600px] border border-base-300 rounded-lg overflow-hidden relative shadow-2xl bg-base-200/50 backdrop-blur">
    
    <!-- Top Bar: Toolbar -->
    <div class="h-14 bg-base-100 border-b border-base-300 flex items-center justify-between px-4 z-20">
      <div class="flex items-center gap-2">
        <div class="badge badge-primary badge-outline text-xs font-bold gap-1">
           <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path><circle cx="12" cy="12" r="3"></circle></svg>
           DESIGN MODE
        </div>
        <div class="h-4 w-px bg-base-300 mx-2"></div>
        
        <!-- Standard Key Manager (Top Bar) -->
        <div v-if="!sandbox.enabled" class="flex items-center gap-2">
           <div class="join">
             <input
               type="password"
               v-model="designApiKeyModel"
               :placeholder="designConfig?.masked_api_key ? `Using Saved Key` : 'Enter System API Key...'"
               class="input input-xs input-bordered join-item w-40"
             />
             <button @click="$emit('saveKey')" class="btn btn-xs btn-primary join-item" :disabled="!designApiKey">Save</button>
           </div>
           <button v-if="designConfig?.masked_api_key" @click="$emit('clearKey')" class="btn btn-xs btn-ghost text-error">Clear Key</button>
        </div>
        
        <div v-else class="text-xs font-bold text-primary flex items-center animate-pulse gap-2">
           <span class="badge badge-xs badge-primary">SANDBOX ACTIVE</span>
           <span class="opacity-70">Using temporary credentials</span>
        </div>
      </div>

      <div class="flex items-center gap-3">
        <!-- Sandbox Toggle -->
        <label class="label cursor-pointer gap-2 hover:bg-base-200 px-2 rounded transition-colors">
          <span class="label-text text-xs font-bold" :class="sandbox.enabled ? 'text-primary' : ''">Sandbox Mode</span> 
          <input type="checkbox" class="toggle toggle-primary toggle-sm" v-model="sandbox.enabled" />
        </label>

        <!-- Version Toggle -->
        <button 
          @click="toggleVersions" 
          class="btn btn-sm btn-ghost gap-2 border border-base-300"
          :class="{ 'btn-active': showVersions }"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
          History
        </button>
      </div>
    </div>

    <!-- Main Workspace -->
    <div class="flex-1 flex overflow-hidden relative">
      
      <!-- Left Pane: Inputs & Config -->
      <div class="w-80 border-r border-base-300 bg-base-100 flex flex-col overflow-y-auto">
         <div class="p-4 flex-1 flex flex-col gap-6">
            <!-- Sandbox Controls (if enabled) -->
            <div v-if="sandbox.enabled" class="mb-2">
              <SandboxControls 
                :model-value="sandbox" 
                @apply="$emit('applySandbox')"
              />
            </div>

            <!-- Main Inputs -->
            <PromptInputs
              v-model:requirement="requirementModel"
              v-model:context="contextModel"
              v-model:refine-current="refineCurrentModel"
              :can-edit="!!designConfig?.system_prompt"
              :loading="loading"
              @generate="$emit('generate')"
            />
         </div>
         
         <div class="p-4 border-t border-base-200 text-[10px] text-center opacity-50">
            CoAgent Intelligence Engine v1.0
         </div>
      </div>

      <!-- Right Pane: Editor -->
      <div class="flex-1 bg-[#1e1e1e] relative flex flex-col">
         <!-- Editor Component -->
         <PromptEditor 
           :model-value="designConfig?.system_prompt || ''" 
           @update:modelValue="val => { if(designConfig) designConfig.system_prompt = val }"
           class="flex-1 border-none rounded-none"
         />
      </div>

      <!-- Version Sidebar Overlay (Slide Over) -->
      <div 
        class="absolute top-0 right-0 h-full bg-base-100 z-30 transition-transform duration-300 border-l border-base-300 shadow-xl"
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
