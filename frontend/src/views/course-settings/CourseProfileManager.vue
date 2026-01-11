<script setup lang="ts">
import type { AgentConfig } from '../../types/agent'
import type { User } from '../../types/user'

interface Props {
  configs: AgentConfig[]
  selectedConfigId: string | null
  currentUser: User | null
}

defineProps<Props>()
const emit = defineEmits(['select', 'new'])

const selectConfig = (config: AgentConfig) => {
  emit('select', config)
}

const startNewConfig = () => {
  emit('new')
}
</script>

<template>
  <div class="w-80 bg-base-200 border-r overflow-y-auto p-4 flex flex-col gap-2">
    <div class="flex justify-between items-center mb-2">
      <h3 class="font-bold text-gray-500 text-sm">PROFILES</h3>
      <button @click="startNewConfig" class="btn btn-xs btn-outline btn-primary">+ New</button>
    </div>

    <div
      v-for="conf in configs"
      :key="conf.id"
      @click="selectConfig(conf)"
      class="card bg-base-100 shadow-sm border cursor-pointer hover:border-primary transition-all"
      :class="{ 'border-primary ring-1 ring-primary': selectedConfigId === conf.id }"
    >
      <div class="card-body p-3">
        <div class="flex justify-between items-start">
          <div class="font-bold truncate pr-2">{{ conf.name }}</div>
          <div v-if="conf.is_active" class="badge badge-success badge-xs">ACTIVE</div>
        </div>
        <div class="text-xs text-gray-400 mt-1">
          Updated: {{ new Date(conf.updated_at).toLocaleDateString() }}
        </div>
        <div class="text-xs text-gray-400">
          By: {{ conf.created_by === currentUser?.id ? 'Me' : 'Others' }}
        </div>
      </div>
    </div>

    <div v-if="configs.length === 0" class="text-center text-gray-400 text-sm py-8">
      No profiles yet. Create one!
    </div>
  </div>
</template>
