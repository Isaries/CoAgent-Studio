<script setup lang="ts">
import { computed, ref } from 'vue'
import type { AgentConfig, AgentConfigVersion } from '../../types/agent'
import type { SandboxState } from '../../composables/useAgentSandbox'
import VersionHistoryList from '../../components/PromptDesigner/VersionSidebar.vue'
import ModernSandboxHeader from '../../components/PromptDesigner/ModernSandboxHeader.vue'
import ModernRequirementInput from '../../components/PromptDesigner/ModernRequirementInput.vue'
import IconHistory from '../../components/icons/IconHistory.vue'
import IconKey from '../../components/icons/IconKey.vue'
import IconSave from '../../components/icons/IconSave.vue'
import IconTrash from '../../components/icons/IconTrash.vue'

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
  'applySandbox',
  'update:sandbox'
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
  <div class="collapse collapse-arrow bg-base-100 mb-6 border border-base-300 shadow-sm overflow-visible">
    <input type="checkbox" />
    <div class="collapse-title font-medium flex items-center justify-between pr-10">
      <div class="flex items-center gap-2">
        <span>✨ AI Prompt Designer</span>
        <span v-if="scope==='course'" class="badge badge-sm badge-ghost">Course</span>
      </div>
      <!-- Mode Toggle -->
      <div class="flex items-center gap-2 z-10" @click.stop v-if="canEdit">
        <label class="label cursor-pointer gap-2">
          <span class="label-text text-xs font-bold" :class="sandbox.enabled ? 'text-primary' : ''">Sandbox Mode</span> 
          <input 
            type="checkbox" 
            class="toggle toggle-primary toggle-sm" 
            :checked="sandbox.enabled"
            @change="$emit('update:sandbox', { ...sandbox, enabled: ($event.target as HTMLInputElement).checked })"
          />
        </label>
        <button 
          @click="toggleVersions" 
          class="btn btn-xs btn-ghost gap-1"
          :class="{ 'btn-active': showVersions }"
        >
          <IconHistory class="w-3 h-3" />
          History
        </button>
      </div>
    </div>
    
    <div class="collapse-content overflow-visible flex relative min-h-[500px] p-0">
      
      <!-- Main Content -->
      <div class="flex-1 p-4 flex flex-col gap-6 bg-base-100">
        
        <!-- Standard Mode Key Manager -->
        <div v-if="!sandbox.enabled" class="flex items-center gap-2 p-2 bg-base-200/50 rounded-lg">
           <IconKey class="text-gray-500 ml-2 w-4 h-4" />
           <span class="text-xs font-bold text-gray-500 whitespace-nowrap">API Key ({{ scope === 'system' ? 'System' : 'Course' }})</span>
           <input
             type="password"
             v-model="designApiKeyModel"
             :placeholder="designConfig?.masked_api_key ? `••••••••` : 'Enter Key...'"
             class="input input-sm input-ghost w-full max-w-xs text-xs"
           />
           <button @click="$emit('saveKey')" class="btn btn-sm btn-ghost btn-square text-primary" :disabled="!designApiKey" title="Save">
             <IconSave class="w-4 h-4" />
           </button>
           <button v-if="designConfig?.masked_api_key" @click="$emit('clearKey')" class="btn btn-sm btn-ghost btn-square text-error" title="Clear">
             <IconTrash class="w-4 h-4" />
           </button>
        </div>

        <!-- Sandbox Toolbar -->
        <div v-else class="animate-fade-in">
           <ModernSandboxHeader 
             :model-value="sandbox"
             @apply="$emit('applySandbox')"
             @update:modelValue="e => Object.assign(sandbox, e)"
           />
        </div>

        <!-- Inputs: REUSE MODERN COMPONENT -->
        <div class="flex-1 bg-base-200/30 border border-base-300 rounded-xl overflow-hidden p-4">
           <ModernRequirementInput
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
      <div v-if="showVersions" class="absolute top-0 right-0 z-20 shadow-2xl bg-base-100 h-full max-h-[1000px] border-l border-base-300 w-[300px] overflow-hidden flex flex-col">
         <div class="p-2 border-b border-base-200 flex justify-between items-center bg-base-200/50">
            <span class="text-xs font-bold opacity-50">History</span>
            <button @click="showVersions = false" class="btn btn-xs btn-ghost btn-circle">✕</button>
         </div>
              <div class="form-control">
                <label class="label pb-0 text-xs">Test Custom API Key</label>
                <input 
                  :value="sandbox.customApiKey" 
                  @input="$emit('update:sandbox', { ...sandbox, customApiKey: ($event.target as HTMLInputElement).value })"
                  type="password" 
                  class="input input-xs input-bordered" 
                  placeholder="Override API Key" 
                />
              </div>
         <div class="flex-1 overflow-y-auto">
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
  </div>
</template>

<style scoped>
.animate-fade-in {
  animation: fadeIn 0.3s ease-in-out;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-5px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
