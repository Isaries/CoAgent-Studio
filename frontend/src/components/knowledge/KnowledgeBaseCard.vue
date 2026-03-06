<script setup lang="ts">
import { computed } from 'vue'
import type { KnowledgeBase } from '@/types/knowledge'

const props = defineProps<{
  kb: KnowledgeBase
}>()

const emit = defineEmits<{
  select: [kb: KnowledgeBase]
  build: [kb: KnowledgeBase]
  delete: [kb: KnowledgeBase]
}>()

const sourceLabel = computed(() => {
  switch (props.kb.source_type) {
    case 'conversation':
      return 'Conversation'
    case 'document':
      return 'Document'
    case 'merged':
      return 'Merged'
    default:
      return props.kb.source_type
  }
})

const sourceBadgeClass = computed(() => {
  switch (props.kb.source_type) {
    case 'conversation':
      return 'badge-primary'
    case 'document':
      return 'badge-secondary'
    case 'merged':
      return 'badge-accent'
    default:
      return 'badge-ghost'
  }
})

const statusBadgeClass = computed(() => {
  switch (props.kb.build_status) {
    case 'idle':
      return 'badge-ghost'
    case 'building':
      return 'badge-warning'
    case 'ready':
      return 'badge-success'
    case 'error':
      return 'badge-error'
    default:
      return 'badge-ghost'
  }
})

const statusLabel = computed(() => {
  switch (props.kb.build_status) {
    case 'idle':
      return 'Not Built'
    case 'building':
      return 'Building'
    case 'ready':
      return 'Ready'
    case 'error':
      return 'Error'
    default:
      return props.kb.build_status
  }
})

const scopeLabel = computed(() => {
  if (props.kb.room_id) return `Room: ${props.kb.room_id.slice(0, 8)}...`
  if (props.kb.space_id) return `Space: ${props.kb.space_id.slice(0, 8)}...`
  return 'Global'
})

const lastBuiltFormatted = computed(() => {
  if (!props.kb.last_built_at) return 'Never'
  return new Date(props.kb.last_built_at).toLocaleString()
})

const createdFormatted = computed(() => {
  return new Date(props.kb.created_at).toLocaleDateString()
})

function handleDelete(event: Event) {
  event.stopPropagation()
  emit('delete', props.kb)
}

function handleBuild(event: Event) {
  event.stopPropagation()
  emit('build', props.kb)
}
</script>

<template>
  <div
    class="card bg-base-100 shadow-sm border border-base-200 hover:border-primary/30 hover:shadow-md transition-all cursor-pointer group"
    @click="emit('select', kb)"
  >
    <div class="card-body p-5">
      <!-- Header row -->
      <div class="flex items-start justify-between gap-2">
        <div class="flex-1 min-w-0">
          <h3 class="card-title text-base font-bold truncate">{{ kb.name }}</h3>
          <p v-if="kb.description" class="text-sm text-base-content/60 mt-0.5 line-clamp-2">
            {{ kb.description }}
          </p>
        </div>
        <div class="flex items-center gap-1.5 flex-shrink-0">
          <span class="badge badge-sm" :class="sourceBadgeClass">{{ sourceLabel }}</span>
          <span class="badge badge-sm gap-1" :class="statusBadgeClass">
            <span
              v-if="kb.build_status === 'building'"
              class="loading loading-spinner loading-xs"
            ></span>
            {{ statusLabel }}
          </span>
        </div>
      </div>

      <!-- Stats row -->
      <div class="flex items-center gap-4 mt-3 text-xs text-base-content/50">
        <div class="flex items-center gap-1">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-3.5 w-3.5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
          >
            <circle cx="12" cy="12" r="3" />
            <circle cx="12" cy="12" r="9" stroke-dasharray="4 2" />
          </svg>
          <span>{{ kb.node_count }} nodes</span>
        </div>
        <div class="flex items-center gap-1">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-3.5 w-3.5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
          >
            <path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          <span>{{ kb.edge_count }} edges</span>
        </div>
        <div class="flex items-center gap-1">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-3.5 w-3.5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15"
            />
          </svg>
          <span>{{ scopeLabel }}</span>
        </div>
      </div>

      <!-- Footer row -->
      <div class="flex items-center justify-between mt-3 pt-3 border-t border-base-200">
        <div class="text-xs text-base-content/40">
          <span v-if="kb.last_built_at">Built: {{ lastBuiltFormatted }}</span>
          <span v-else>Created: {{ createdFormatted }}</span>
        </div>
        <div class="flex items-center gap-1.5">
          <button
            class="btn btn-xs btn-ghost opacity-0 group-hover:opacity-100 transition-opacity"
            :class="{ 'btn-disabled': kb.build_status === 'building' }"
            :disabled="kb.build_status === 'building'"
            @click="handleBuild"
            title="Build graph"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-3.5 w-3.5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="2"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            Build
          </button>
          <button
            class="btn btn-xs btn-ghost text-error opacity-0 group-hover:opacity-100 transition-opacity"
            @click="handleDelete"
            title="Delete"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-3.5 w-3.5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="2"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
              />
            </svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
