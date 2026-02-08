<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { AgentType } from '../../../types/enums'
import { useAgentTypesStore } from '../../../stores/agentTypes'
import IconSave from '../../../components/icons/IconSave.vue'
import IconHistory from '../../../components/icons/IconHistory.vue'
import IconCode from '../../../components/icons/IconCode.vue'

const props = defineProps<{
  activeTab: AgentType | string
  isSaving: boolean
  hasUnsavedChanges: boolean
  lastSavedAt: string | null
  showHistory: boolean
}>()

const emit = defineEmits<{
  (e: 'update:activeTab', val: AgentType | string): void
  (e: 'save'): void
  (e: 'toggleHistory'): void
  (e: 'importFromMyAgent'): void
}>()

const typesStore = useAgentTypesStore()

// Computed tabs from store, falling back to hardcoded if not loaded
const tabs = computed(() => {
  if (typesStore.types.length > 0) {
    // Filter to non-external types for course settings (instructor, participant, utility)
    return typesStore.types
      .filter(t => t.category !== 'external')
      .map(t => ({
        id: t.type_name,
        label: t.display_name || t.type_name,
        icon: t.icon,
        color: t.color
      }))
  }
  
  return []
})

onMounted(() => {
  typesStore.fetchTypes()
})
</script>

<template>
  <div class="flex flex-col gap-4 mb-6 border-b border-base-300 pb-4">
    <div class="flex justify-between items-center">
      <div>
        <h1 class="text-2xl font-bold flex items-center gap-2">
          <IconCode class="w-6 h-6 text-primary" />
          Course Brain
        </h1>
        <p class="text-sm opacity-60">Configure the AI agents that power this course.</p>
      </div>

      <div class="flex items-center gap-2">
         <!-- Import From My Agent -->
         <button 
           class="btn btn-ghost btn-sm gap-2"
           @click="emit('importFromMyAgent')"
         >
           <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
             <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
           </svg>
           Import
         </button>

         <!-- History Toggle -->
         <button 
           class="btn btn-ghost btn-sm gap-2"
           :class="{ 'btn-active': showHistory }"
           @click="emit('toggleHistory')"
         >
           <IconHistory class="w-4 h-4" />
           History
         </button>

         <!-- Save Button -->
         <button 
           class="btn btn-primary btn-sm gap-2"
           :disabled="isSaving || !hasUnsavedChanges"
           @click="emit('save')"
         >
           <IconSave class="w-4 h-4" />
           {{ isSaving ? 'Saving...' : 'Save Changes' }}
         </button>
      </div>
    </div>

    <!-- Agent Tabs (Dynamic) -->
    <div class="tabs tabs-boxed bg-base-200 w-fit">
      <a 
        v-for="tab in tabs" 
        :key="tab.id"
        class="tab"
        :class="{ 'tab-active': activeTab === tab.id }"
        @click="emit('update:activeTab', tab.id)"
      >
        {{ tab.label }} Agent
      </a>
      
      <!-- Loading indicator -->
      <span v-if="typesStore.loading" class="loading loading-spinner loading-xs ml-2"></span>
    </div>
    
    <div v-if="lastSavedAt" class="text-xs text-right opacity-50 pr-2">
       Last saved: {{ new Date(lastSavedAt).toLocaleTimeString() }}
    </div>
  </div>
</template>

