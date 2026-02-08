<script setup lang="ts">
/**
 * KanbanColumn - A single column in the Kanban board.
 */
import { computed } from 'vue'
import type { KanbanColumn } from '@/types/artifact'
import TaskCard from './TaskCard.vue'

const props = defineProps<{
  column: KanbanColumn
}>()

const emit = defineEmits<{
  (e: 'drop', payload: { taskId: string; newStatus: string }): void
  (e: 'edit', taskId: string): void
  (e: 'delete', taskId: string): void
  (e: 'add'): void
}>()

const columnColors = computed(() => {
  switch (props.column.status) {
    case 'todo': return 'bg-base-200'
    case 'in_progress': return 'bg-info/10'
    case 'review': return 'bg-warning/10'
    case 'done': return 'bg-success/10'
    default: return 'bg-base-200'
  }
})

function handleDragOver(e: DragEvent) {
  e.preventDefault()
  if (e.dataTransfer) {
    e.dataTransfer.dropEffect = 'move'
  }
}

function handleDrop(e: DragEvent) {
  e.preventDefault()
  const taskId = e.dataTransfer?.getData('text/plain')
  if (taskId) {
    emit('drop', { taskId, newStatus: props.column.status })
  }
}
</script>

<template>
  <div 
    class="flex flex-col w-72 min-w-72 rounded-lg p-3"
    :class="columnColors"
    @dragover="handleDragOver"
    @drop="handleDrop"
  >
    <!-- Column Header -->
    <div class="flex items-center justify-between mb-3">
      <h3 class="font-semibold text-base-content">
        {{ column.title }}
        <span class="badge badge-sm ml-2">{{ column.tasks.length }}</span>
      </h3>
      <button 
        v-if="column.status === 'todo'"
        class="btn btn-ghost btn-xs btn-circle"
        @click="emit('add')"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
      </button>
    </div>

    <!-- Tasks -->
    <div class="flex flex-col gap-2 flex-1 min-h-32 overflow-y-auto">
      <TaskCard
        v-for="task in column.tasks"
        :key="task.id"
        :task="task"
        class="group"
        @edit="emit('edit', $event)"
        @delete="emit('delete', $event)"
      />

      <!-- Empty State -->
      <div 
        v-if="column.tasks.length === 0"
        class="flex items-center justify-center h-24 border-2 border-dashed border-base-300 rounded-lg text-base-content/50 text-sm"
      >
        拖曳任務到這裡
      </div>
    </div>
  </div>
</template>
