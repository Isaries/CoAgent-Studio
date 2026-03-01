<script setup lang="ts">
/**
 * TriggersView – Manage trigger policies in the Studio.
 */
import { ref, onMounted } from 'vue'
import { workflowService } from '../../services/workflowService'
import type { TriggerPolicy, Workflow } from '../../services/workflowService'
import { useToastStore } from '../../stores/toast'

const toast = useToastStore()
const triggers = ref<TriggerPolicy[]>([])
const workflows = ref<Workflow[]>([])
const isLoading = ref(true)
const showCreateModal = ref(false)

const newTrigger = ref({
  name: '',
  event_type: 'user_message',
  conditions: '{}',
  target_workflow_id: '',
  scope_session_id: '',
  is_active: true,
})

const fetchData = async () => {
  isLoading.value = true
  try {
    const [triggerRes, workflowRes] = await Promise.all([
      workflowService.listTriggers(),
      workflowService.listWorkflows(),
    ])
    triggers.value = triggerRes.data
    workflows.value = workflowRes.data
  } catch (e) {
    console.error(e)
    toast.error('Failed to load data')
  } finally {
    isLoading.value = false
  }
}

const createTrigger = async () => {
  try {
    let conditions = {}
    try {
      conditions = JSON.parse(newTrigger.value.conditions)
    } catch { /* ignore */ }

    await workflowService.createTrigger({
      name: newTrigger.value.name || 'Untitled Trigger',
      event_type: newTrigger.value.event_type,
      conditions,
      target_workflow_id: newTrigger.value.target_workflow_id,
      scope_session_id: newTrigger.value.scope_session_id || undefined,
      is_active: newTrigger.value.is_active,
    } as any)
    toast.success('Trigger created!')
    showCreateModal.value = false
    // Reset form state
    newTrigger.value = {
      name: '',
      event_type: 'user_message',
      conditions: '{}',
      target_workflow_id: '',
      scope_session_id: '',
      is_active: true,
    }
    await fetchData()
  } catch (e) {
    console.error(e)
    toast.error('Failed to create trigger')
  }
}

const deleteTrigger = async (id: string) => {
  if (!confirm('Delete this trigger?')) return
  try {
    await workflowService.deleteTrigger(id)
    toast.success('Trigger deleted')
    await fetchData()
  } catch (e) {
    console.error(e)
    toast.error('Failed to delete trigger')
  }
}

const toggleActive = async (trigger: TriggerPolicy) => {
  try {
    await workflowService.updateTrigger(trigger.id, {
      is_active: !trigger.is_active,
    })
    trigger.is_active = !trigger.is_active
  } catch (e) {
    console.error(e)
    toast.error('Failed to update trigger')
  }
}

const getWorkflowName = (id: string) => {
  const wf = workflows.value.find(w => w.id === id)
  return wf?.name || 'Unknown Workflow'
}

const eventTypeLabels: Record<string, string> = {
  user_message: '💬 User Message',
  silence: '🔕 Silence Timeout',
  timer: '⏰ Timer / Cron',
  webhook: '🔗 Webhook',
  manual: '👆 Manual',
}

onMounted(fetchData)
</script>

<template>
  <div class="p-6 max-w-5xl mx-auto">
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="text-2xl font-bold">⚡ Trigger Policies</h1>
        <p class="text-sm opacity-60 mt-1">Configure when and how workflows are automatically triggered</p>
      </div>
      <button class="btn btn-primary" @click="showCreateModal = true">+ New Trigger</button>
    </div>

    <!-- Loading -->
    <div v-if="isLoading" class="flex justify-center py-12">
      <span class="loading loading-spinner loading-lg text-primary"></span>
    </div>

    <!-- Empty -->
    <div v-else-if="!triggers.length" class="text-center py-16 bg-base-100 rounded-2xl border border-base-300">
      <div class="text-5xl mb-4">⚡</div>
      <h2 class="text-xl font-bold mb-2">No Trigger Policies</h2>
      <p class="opacity-60 mb-4">Create triggers to automatically activate your workflows.</p>
      <button class="btn btn-primary" @click="showCreateModal = true">Create Trigger</button>
    </div>

    <!-- Trigger List -->
    <div v-else class="flex flex-col gap-3">
      <div
        v-for="t in triggers"
        :key="t.id"
        class="card bg-base-100 border border-base-300 shadow-sm"
      >
        <div class="card-body p-4 flex-row items-center justify-between">
          <div class="flex items-center gap-4">
            <input
              type="checkbox"
              class="toggle toggle-primary"
              :checked="t.is_active"
              @change="toggleActive(t)"
            />
            <div>
              <div class="font-bold">{{ t.name }}</div>
              <div class="flex gap-2 mt-1">
                <span class="badge badge-sm badge-ghost">{{ eventTypeLabels[t.event_type] || t.event_type }}</span>
                <span class="badge badge-sm badge-outline">→ {{ getWorkflowName(t.target_workflow_id) }}</span>
              </div>
            </div>
          </div>
          <button class="btn btn-ghost btn-xs text-error" @click="deleteTrigger(t.id)">🗑</button>
        </div>
      </div>
    </div>

    <!-- Create Modal -->
    <dialog :class="{ 'modal-open': showCreateModal }" class="modal">
      <div class="modal-box">
        <h3 class="font-bold text-lg mb-4">Create Trigger Policy</h3>

        <div class="form-control mb-3">
          <label class="label"><span class="label-text">Name</span></label>
          <input v-model="newTrigger.name" class="input input-bordered" placeholder="e.g. Silence Alert" />
        </div>

        <div class="form-control mb-3">
          <label class="label"><span class="label-text">Event Type</span></label>
          <select v-model="newTrigger.event_type" class="select select-bordered">
            <option value="user_message">User Message</option>
            <option value="silence">Silence Timeout</option>
            <option value="timer">Timer / Cron</option>
            <option value="webhook">Webhook</option>
            <option value="manual">Manual</option>
          </select>
        </div>

        <div class="form-control mb-3">
          <label class="label"><span class="label-text">Conditions (JSON)</span></label>
          <textarea v-model="newTrigger.conditions" class="textarea textarea-bordered h-20" placeholder='{"threshold_mins": 5}' />
        </div>

        <div class="form-control mb-3">
          <label class="label"><span class="label-text">Target Workflow</span></label>
          <select v-model="newTrigger.target_workflow_id" class="select select-bordered">
            <option value="" disabled>Select a workflow…</option>
            <option v-for="wf in workflows" :key="wf.id" :value="wf.id">{{ wf.name }}</option>
          </select>
        </div>

        <div class="form-control mb-3">
          <label class="label"><span class="label-text">Scope (Session/Room ID, optional)</span></label>
          <input v-model="newTrigger.scope_session_id" class="input input-bordered" placeholder="Leave empty for global" />
        </div>

        <div class="modal-action">
          <button class="btn btn-ghost" @click="showCreateModal = false">Cancel</button>
          <button class="btn btn-primary" @click="createTrigger" :disabled="!newTrigger.target_workflow_id">Create</button>
        </div>
      </div>
    </dialog>
  </div>
</template>
