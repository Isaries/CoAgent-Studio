<script setup lang="ts">
import { computed, ref } from 'vue'
import type { AgentConfig, AgentConfigVersion } from '../../types/agent'
import VersionHistoryList from '../../components/PromptDesigner/VersionSidebar.vue'
import SandboxControls from '../../components/PromptDesigner/SandboxControls.vue'
import PromptInputs from '../../components/PromptDesigner/PromptInputs.vue'

interface SandboxState {
  enabled: boolean
  customApiKey: string
  customProvider: string
  customModel: string
  systemPrompt: string
}

interface Props {
  canEdit: boolean
  editPrompt: string
  designConfig: AgentConfig | null
  designApiKey: string
  loading: boolean
  requirement: string
  context: string
  refineCurrent: boolean
  
  sandbox: SandboxState
  versions: AgentConfigVersion[]
  scope?: 'course' | 'system'
}

const props = withDefaults(defineProps<Props>(), {
  scope: 'course'
})
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

// Drawer State
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

// Load versions when drawer opens
const toggleVersions = () => {
  showVersions.value = !showVersions.value
  if (showVersions.value) {
    emit('fetchVersions')
  }
}
</script>

<template>
  <div class="collapse collapse-arrow bg-base-200 mb-6 border border-base-300">
    <input type="checkbox" />
    <div class="collapse-title font-medium flex items-center justify-between pr-10">
      <div class="flex items-center gap-2">
        <span>✨ AI Prompt Designer</span>
      </div>
      <!-- Mode Toggle -->
      <div class="flex items-center gap-2 z-10" @click.stop v-if="canEdit">
        <label class="label cursor-pointer gap-2">
          <span class="label-text text-xs font-bold" :class="sandbox.enabled ? 'text-primary' : ''">Sandbox Mode</span> 
          <input type="checkbox" class="toggle toggle-primary toggle-sm" v-model="sandbox.enabled" />
        </label>
        <button 
          @click="toggleVersions" 
          class="btn btn-xs btn-ghost gap-1"
          :class="{ 'btn-active': showVersions }"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
          History
        </button>
      </div>
    </div>
    
    <div class="collapse-content overflow-visible flex relative min-h-[400px]">
      
      <!-- Main Content -->
      <div class="flex-1 p-2 flex flex-col gap-4">
        
        <!-- Standard Mode Key Manager -->
        <div v-if="!sandbox.enabled" class="form-control mb-2 p-3 bg-base-100 rounded border border-base-200">
           <label class="label pt-0 pb-1">
             <span class="label-text font-bold text-xs">Design Agent API Key ({{ scope === 'system' ? 'System Level' : 'Course Level' }})</span>
           </label>
           <div class="join w-full">
             <input
               type="password"
               v-model="designApiKeyModel"
               :placeholder="designConfig?.masked_api_key ? `Using Saved Key` : 'Enter API Key...'"
               class="input input-sm input-bordered join-item w-full"
             />
             <button @click="$emit('saveKey')" class="btn btn-sm btn-primary join-item" :disabled="!designApiKey">Save</button>
             <button v-if="designConfig?.masked_api_key" @click="$emit('clearKey')" class="btn btn-sm btn-ghost join-item text-error">Clear</button>
           </div>
        </div>

        <!-- Sandbox Toolbar -->
        <SandboxControls 
          v-else 
          :model-value="sandbox"
          @apply="$emit('applySandbox')"
        />

        <!-- Inputs: REUSE SHARABLE COMPONENT -->
        <div class="bg-base-100 p-2 rounded">
           <PromptInputs
             v-model:requirement="requirementModel"
             v-model:context="contextModel"
             v-model:refine-current="refineCurrentModel"
             :can-edit="!!editPrompt"
             :loading="loading"
             @generate="$emit('generate')"
           />
        </div>
        
      </div>

      <!-- Version Drawer (Overlay) -->
      <div v-if="showVersions" class="absolute top-0 right-0 z-20 shadow-xl bg-base-100 h-full max-h-[600px] overflow-y-auto" style="min-width: 300px; right: -10px; top: -10px;">
         <VersionHistoryList 
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
