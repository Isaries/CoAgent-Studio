<script setup lang="ts">
/**
 * WorkflowEditorView – Full-page view wrapping the WorkflowEditor component.
 *
 * Supports two modes:
 *   1. Studio mode: /studio/workflows/:id  →  uses workflowId prop
 *   2. Legacy mode: /rooms/:id/workflow    →  uses roomId prop (backward compat)
 */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import WorkflowEditor from '../components/workflow/WorkflowEditor.vue'

const route = useRoute()
const router = useRouter()

// Determine which mode we're in
const workflowId = computed(() => route.params.workflowId as string || '')
const roomId = computed(() => route.params.id as string || '')
const isStudioMode = computed(() => !!workflowId.value)
</script>

<template>
  <div class="p-4 max-w-full">
    <div class="flex justify-between items-center mb-4">
      <div class="flex items-center gap-3">
        <button
          class="btn btn-ghost btn-sm"
          @click="isStudioMode ? router.push('/studio/workflows') : router.push(`/rooms/${roomId}/settings`)"
        >
          ← {{ isStudioMode ? 'All Workflows' : 'Settings' }}
        </button>
        <h1 class="text-xl font-bold">Workflow Editor</h1>
      </div>
      <template v-if="!isStudioMode">
        <router-link :to="`/rooms/${roomId}`" class="btn btn-ghost btn-sm">
          Back to Room
        </router-link>
      </template>
    </div>

    <!-- Pass workflowId for Studio mode, roomId for legacy mode -->
    <WorkflowEditor
      v-if="isStudioMode"
      :workflow-id="workflowId"
    />
    <WorkflowEditor
      v-else
      :room-id="roomId"
    />
  </div>
</template>
