<script setup lang="ts">
/**
 * Custom Vue Flow node for Agent nodes.
 * Displays the agent name, type badge, and connection handles.
 */
import { Handle, Position } from '@vue-flow/core'

const props = defineProps<{
  id: string
  data: {
    label: string
    agentType?: string
    agentId?: string
    isActive?: boolean
  }
}>()
</script>

<template>
  <div
    class="agent-node px-4 py-3 rounded-xl border-2 min-w-[160px] text-center transition-all duration-300"
    :class="{
      'border-primary bg-primary/10 shadow-lg shadow-primary/20': data.isActive,
      'border-base-300 bg-base-100 shadow-md hover:shadow-lg hover:border-primary/50': !data.isActive
    }"
  >
    <!-- Top handle (input) -->
    <Handle type="target" :position="Position.Top" class="!bg-primary !w-3 !h-3" />

    <!-- Agent Icon -->
    <div class="flex items-center justify-center gap-2 mb-1">
      <div class="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23.693L5 14.5m14.8.8l1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0112 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5" />
        </svg>
      </div>
    </div>

    <!-- Agent Name -->
    <div class="font-bold text-sm truncate">{{ data.label || 'Agent' }}</div>

    <!-- Type Badge -->
    <div v-if="data.agentType" class="mt-1">
      <span class="badge badge-xs badge-outline opacity-70">{{ data.agentType }}</span>
    </div>

    <!-- Pulse animation when active -->
    <div
      v-if="data.isActive"
      class="absolute inset-0 rounded-xl border-2 border-primary animate-ping opacity-20 pointer-events-none"
    />

    <!-- Bottom handle (output) -->
    <Handle type="source" :position="Position.Bottom" class="!bg-secondary !w-3 !h-3" />
  </div>
</template>

<style scoped>
.agent-node {
  position: relative;
  font-family: inherit;
}
</style>
