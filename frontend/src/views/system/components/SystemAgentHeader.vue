<script setup lang="ts">
import { computed } from 'vue'
import type { SandboxState } from '../../../composables/useAgentSandbox'
import IconHistory from '../../../components/icons/IconHistory.vue'
import IconKey from '../../../components/icons/IconKey.vue'
import IconSave from '../../../components/icons/IconSave.vue'
import IconTrash from '../../../components/icons/IconTrash.vue'

interface Props {
  sandbox: SandboxState
  designApiKey: string
  maskedApiKey?: boolean
  showVersions: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'update:sandbox', value: SandboxState): void
  (e: 'update:designApiKey', value: string): void
  (e: 'saveKey'): void
  (e: 'clearKey'): void
  (e: 'toggleVersions'): void
}>()

const sandboxModel = computed({
  get: () => props.sandbox,
  set: (val) => emit('update:sandbox', val)
})

const apiKeyModel = computed({
  get: () => props.designApiKey,
  set: (val) => emit('update:designApiKey', val)
})
</script>

<template>
  <div class="h-14 bg-[#121212]/90 border-b border-white/5 flex items-center justify-between px-6 z-20 flex-shrink-0">
    
    <!-- Left: Identity -->
    <div class="flex items-center gap-4">
      <div class="flex items-center gap-2">
         <div class="w-2 h-2 rounded-full bg-purple-500 shadow-[0_0_10px_rgba(168,85,247,0.8)]"></div>
         <span class="font-bold text-gray-200 tracking-wide text-sm">META-PROMPT STUDIO</span>
      </div>

      <div class="h-4 w-px bg-white/10 mx-2"></div>

      <!-- Sandbox Toggle -->
      <label class="label cursor-pointer gap-3 group">
        <span class="label-text text-[10px] font-bold uppercase tracking-widest transition-colors duration-300 group-hover:text-primary" 
              :class="sandbox.enabled ? 'text-primary drop-shadow-[0_0_8px_rgba(var(--p),0.6)]' : 'text-gray-500'">Sandbox</span> 
        <input type="checkbox" class="toggle toggle-primary toggle-sm border-white/10 bg-base-300" v-model="sandboxModel.enabled" />
      </label>
    </div>

    <!-- Right: Actions -->
    <div class="flex items-center gap-3">
       <!-- Standard Key Manager (If sandbox disabled) -->
       <div v-if="!sandbox.enabled" class="flex items-center gap-2 animate-fade-in transition-all">
           <div class="flex items-center bg-white/5 rounded-full px-3 py-1 border border-white/5 focus-within:border-primary/50 transition-colors">
             <IconKey class="mr-2 text-gray-500 w-3 h-3" />
             <input
               type="password"
               v-model="apiKeyModel"
               :placeholder="maskedApiKey ? `•••••••••••••` : 'System API Key'"
               class="bg-transparent border-none focus:outline-none w-24 text-xs text-center text-gray-300 placeholder-gray-600"
             />
             <button @click="$emit('saveKey')" class="ml-2 text-primary hover:text-primary-focus transition-colors" :disabled="!designApiKey" title="Save Key">
                <IconSave class="w-3 h-3" />
             </button>
           </div>
           <button v-if="maskedApiKey" @click="$emit('clearKey')" class="btn btn-circle btn-xs btn-ghost text-error opacity-50 hover:opacity-100">
              <IconTrash class="w-3 h-3" />
           </button>
       </div>

       <div class="h-4 w-px bg-white/10 mx-2"></div>

       <button 
        @click="$emit('toggleVersions')" 
        class="btn btn-sm btn-ghost gap-2 hover:bg-white/10 text-gray-400 hover:text-white transition-all"
        :class="{ 'text-primary bg-primary/10 border-primary/20': showVersions }"
      >
        <IconHistory class="w-3.5 h-3.5" />
        <span class="hidden sm:inline text-xs">History</span>
      </button>
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
