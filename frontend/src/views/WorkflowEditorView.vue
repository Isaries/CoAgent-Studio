<script setup lang="ts">
/**
 * WorkflowEditorView – Full-page view wrapping the WorkflowEditor component.
 * Accessible via /rooms/:id/workflow
 */
import { useRoute, useRouter } from 'vue-router'
import WorkflowEditor from '../components/workflow/WorkflowEditor.vue'

const route = useRoute()
const router = useRouter()
const roomId = route.params.id as string
</script>

<template>
  <div class="p-4 max-w-full">
    <div class="flex justify-between items-center mb-4">
      <div class="flex items-center gap-3">
        <button class="btn btn-ghost btn-sm" @click="router.push(`/rooms/${roomId}/settings`)">
          ← Settings
        </button>
        <h1 class="text-xl font-bold">Workflow Editor</h1>
      </div>
      <router-link :to="`/rooms/${roomId}`" class="btn btn-ghost btn-sm">
        Back to Room
      </router-link>
    </div>

    <WorkflowEditor :room-id="roomId" />
  </div>
</template>
