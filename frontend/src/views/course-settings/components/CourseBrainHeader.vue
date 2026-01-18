<script setup lang="ts">
import { AgentType } from '../../../types/enums'
import IconSave from '../../../components/icons/IconSave.vue'
import IconHistory from '../../../components/icons/IconHistory.vue'
import IconCode from '../../../components/icons/IconCode.vue'

defineProps<{
  activeTab: AgentType
  isSaving: boolean
  hasUnsavedChanges: boolean
  lastSavedAt: string | null
  showHistory: boolean
}>()

const emit = defineEmits<{
  (e: 'update:activeTab', val: AgentType): void
  (e: 'save'): void
  (e: 'toggleHistory'): void
}>()

const tabs = [
  { id: AgentType.TEACHER, label: 'Teacher' },
  { id: AgentType.STUDENT, label: 'Student' },
  { id: AgentType.ANALYTICS, label: 'Analytics' }
]
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

    <!-- Agent Tabs -->
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
    </div>
    
    <div v-if="lastSavedAt" class="text-xs text-right opacity-50 pr-2">
       Last saved: {{ new Date(lastSavedAt).toLocaleTimeString() }}
    </div>
  </div>
</template>
