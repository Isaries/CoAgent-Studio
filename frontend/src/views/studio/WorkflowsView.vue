<script setup lang="ts">
/**
 * WorkflowsView – Lists all available workflows in the Studio.
 * Users can create, open, or delete workflows from here.
 */
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { workflowService } from '../../services/workflowService'
import type { Workflow } from '../../services/workflowService'
import { useToastStore } from '../../stores/toast'

const router = useRouter()
const toast = useToastStore()
const workflows = ref<Workflow[]>([])
const isLoading = ref(true)
const isCreating = ref(false)

const fetchWorkflows = async () => {
  isLoading.value = true
  try {
    const res = await workflowService.listWorkflows()
    workflows.value = res.data
  } catch (e) {
    console.error(e)
    toast.error('Failed to load workflows')
  } finally {
    isLoading.value = false
  }
}

const createWorkflow = async () => {
  isCreating.value = true
  try {
    const res = await workflowService.createWorkflow({
      name: 'New Workflow',
      graph_data: { nodes: [], edges: [] },
      is_active: true,
    })
    toast.success('Workflow created!')
    router.push(`/studio/workflows/${res.data.id}`)
  } catch (e) {
    console.error(e)
    toast.error('Failed to create workflow')
  } finally {
    isCreating.value = false
  }
}

const deleteWorkflow = async (id: string) => {
  if (!confirm('Are you sure you want to delete this workflow?')) return
  try {
    await workflowService.deleteWorkflowById(id)
    toast.success('Workflow deleted')
    await fetchWorkflows()
  } catch (e) {
    console.error(e)
    toast.error('Failed to delete workflow')
  }
}

onMounted(fetchWorkflows)
</script>

<template>
  <div class="p-6 max-w-5xl mx-auto">
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="text-2xl font-bold">🔀 Workflow Studio</h1>
        <p class="text-sm opacity-60 mt-1">Design, manage, and deploy multi-agent workflows</p>
      </div>
      <button
        class="btn btn-primary"
        :disabled="isCreating"
        @click="createWorkflow"
      >
        <span v-if="isCreating" class="loading loading-spinner loading-sm"></span>
        + New Workflow
      </button>
    </div>

    <!-- Loading -->
    <div v-if="isLoading" class="flex justify-center py-12">
      <span class="loading loading-spinner loading-lg text-primary"></span>
    </div>

    <!-- Empty State -->
    <div v-else-if="!workflows.length" class="text-center py-16 bg-base-100 rounded-2xl border border-base-300">
      <div class="text-5xl mb-4">🔀</div>
      <h2 class="text-xl font-bold mb-2">No Workflows Yet</h2>
      <p class="opacity-60 mb-4">Create your first multi-agent workflow to get started.</p>
      <button class="btn btn-primary" @click="createWorkflow">Create Workflow</button>
    </div>

    <!-- Workflow Grid -->
    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div
        v-for="wf in workflows"
        :key="wf.id"
        class="card bg-base-100 border border-base-300 shadow-sm hover:shadow-md hover:border-primary/30 transition-all cursor-pointer"
        @click="router.push(`/studio/workflows/${wf.id}`)"
      >
        <div class="card-body p-5">
          <div class="flex items-start justify-between">
            <div>
              <h3 class="font-bold text-lg">{{ wf.name }}</h3>
              <div class="flex gap-2 mt-1">
                <span class="badge badge-sm" :class="wf.is_active ? 'badge-success' : 'badge-ghost'">
                  {{ wf.is_active ? 'Active' : 'Inactive' }}
                </span>
                <span class="badge badge-sm badge-ghost">
                  {{ wf.graph_data?.nodes?.length || 0 }} nodes
                </span>
              </div>
            </div>
            <button
              class="btn btn-ghost btn-xs text-error"
              @click.stop="deleteWorkflow(wf.id)"
            >
              🗑
            </button>
          </div>
          <div class="text-xs opacity-40 mt-3">
            Updated: {{ new Date(wf.updated_at).toLocaleString() }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
