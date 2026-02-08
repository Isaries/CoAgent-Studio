<script setup lang="ts">
/**
 * TaskCard - Individual task card for Kanban board.
 */
import { computed } from 'vue'
import type { Artifact, TaskContent } from '@/types/artifact'

const props = defineProps<{
  task: Artifact
}>()

const emit = defineEmits<{
  (e: 'edit', taskId: string): void
  (e: 'delete', taskId: string): void
}>()

const content = computed(() => props.task.content as TaskContent)

const priorityClass = computed(() => {
  switch (content.value.priority) {
    case 'high': return 'border-l-4 border-error'
    case 'medium': return 'border-l-4 border-warning'
    case 'low': return 'border-l-4 border-success'
    default: return 'border-l-4 border-base-300'
  }
})

const priorityBadge = computed(() => {
  switch (content.value.priority) {
    case 'high': return { text: '高', class: 'badge-error' }
    case 'medium': return { text: '中', class: 'badge-warning' }
    case 'low': return { text: '低', class: 'badge-success' }
    default: return null
  }
})
</script>

<template>
  <div
    class="card bg-base-100 shadow-sm hover:shadow-md transition-shadow cursor-grab active:cursor-grabbing"
    :class="priorityClass"
    draggable="true"
    @dragstart="$event.dataTransfer?.setData('text/plain', task.id)"
  >
    <div class="card-body p-3">
      <!-- Title -->
      <h4 class="card-title text-sm font-medium line-clamp-2">
        {{ task.title }}
      </h4>

      <!-- Meta -->
      <div class="flex items-center gap-2 mt-2">
        <span v-if="priorityBadge" class="badge badge-sm" :class="priorityBadge.class">
          {{ priorityBadge.text }}
        </span>
        <span v-if="content.assignee" class="badge badge-sm badge-ghost">
          {{ content.assignee }}
        </span>
      </div>

      <!-- Actions -->
      <div class="card-actions justify-end mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
        <button 
          class="btn btn-ghost btn-xs"
          @click.stop="emit('edit', task.id)"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
          </svg>
        </button>
        <button 
          class="btn btn-ghost btn-xs text-error"
          @click.stop="emit('delete', task.id)"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.card:hover .card-actions {
  opacity: 1;
}
</style>
