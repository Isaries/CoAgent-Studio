<script setup lang="ts">
import { ref } from 'vue'
import type { AgentConfigVersion } from '../../types/agent'

interface Props {
  versions: AgentConfigVersion[]
  loading: boolean
}

defineProps<Props>()
const emit = defineEmits(['create', 'restore', 'close'])

const newVersionLabel = ref('')

const handleCreate = () => {
  if (!newVersionLabel.value.trim()) return
  emit('create', newVersionLabel.value)
  newVersionLabel.value = ''
}
</script>

<template>
  <div class="h-full flex flex-col bg-base-100 border-l border-base-300 w-full sm:w-80">
    <div class="p-4 border-b border-base-200 flex justify-between items-center bg-base-200/50">
      <h3 class="font-bold text-sm uppercase tracking-wider opacity-70">Version History</h3>
      <button v-if="$attrs.onClose" @click="$emit('close')" class="btn btn-ghost btn-xs btn-circle">✕</button>
    </div>

    <!-- Create Version -->
    <div class="p-4 border-b border-base-200 bg-base-100">
      <div class="form-control gap-2">
        <label class="label py-0">
          <span class="label-text text-xs font-bold">Save Current State</span>
        </label>
        <div class="flex gap-2">
          <input
            v-model="newVersionLabel"
            type="text"
            placeholder="v1.0 - Initial Draft"
            class="input input-sm input-bordered w-full text-xs"
            @keyup.enter="handleCreate"
          />
          <button 
            @click="handleCreate" 
            class="btn btn-sm btn-primary"
            :disabled="!newVersionLabel.trim() || loading"
          >
            Save
          </button>
        </div>
      </div>
    </div>

    <!-- List -->
    <div class="flex-1 overflow-y-auto p-3 space-y-3">
      <div v-if="versions.length === 0" class="flex flex-col items-center justify-center py-10 text-gray-400 opacity-60">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="mb-2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
        <span class="text-xs">No versions saved yet</span>
      </div>
      
      <div v-else class="flex flex-col gap-2">
        <div 
          v-for="ver in versions" 
          :key="ver.id" 
          class="card bg-base-100 border border-base-300 hover:border-primary/50 transition-colors shadow-sm compact group"
        >
          <div class="card-body p-3">
            <div class="flex justify-between items-start">
              <div>
                <h4 class="font-bold text-sm text-base-content/90">{{ ver.version_label }}</h4>
                <div class="text-[10px] opacity-60 font-mono mt-0.5">
                  {{ new Date(ver.created_at).toLocaleString() }}
                </div>
              </div>
              <div class="badge badge-ghost badge-xs font-mono text-[10px]">{{ ver.model_provider }}</div>
            </div>
            
            <div class="mt-2 text-xs truncate text-base-content/60 font-mono bg-base-200/50 p-1 rounded">
              {{ ver.system_prompt.substring(0, 50) }}...
            </div>

            <div class="card-actions justify-end mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
              <button 
                @click="$emit('restore', ver)" 
                class="btn btn-xs btn-primary btn-outline"
                :disabled="loading"
              >
                Restore
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
