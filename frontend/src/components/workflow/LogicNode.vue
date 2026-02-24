<script setup lang="ts">
/**
 * Custom nodes for Start, End, Router, Merge, and Action.
 */
import { Handle, Position } from '@vue-flow/core'

const props = defineProps<{
  id: string
  type: string
  data: {
    label: string
    isActive?: boolean
  }
}>()

const icons: Record<string, string> = {
  start: '▶',
  end: '⏹',
  router: '⑂',
  merge: '⤵',
  action: '⚡',
  tool: '🔧',
}
</script>

<template>
  <div
    class="logic-node px-3 py-2 rounded-lg border-2 min-w-[120px] text-center transition-all duration-300"
    :class="{
      'border-success bg-success/10': type === 'start',
      'border-error bg-error/10': type === 'end',
      'border-warning bg-warning/10': type === 'router',
      'border-info bg-info/10': type === 'merge' || type === 'action' || type === 'tool',
      'shadow-lg ring-2 ring-primary animate-pulse': data.isActive,
    }"
  >
    <!-- Input handle (not on start) -->
    <Handle v-if="type !== 'start'" type="target" :position="Position.Top" class="!bg-base-content !w-2.5 !h-2.5" />

    <div class="text-lg">{{ icons[type] || '◆' }}</div>
    <div class="font-semibold text-xs mt-1">{{ data.label || type.toUpperCase() }}</div>

    <!-- Output handle (not on end) -->
    <Handle v-if="type !== 'end'" type="source" :position="Position.Bottom" class="!bg-base-content !w-2.5 !h-2.5" />
  </div>
</template>

<style scoped>
.logic-node {
  position: relative;
  font-family: inherit;
}
</style>
