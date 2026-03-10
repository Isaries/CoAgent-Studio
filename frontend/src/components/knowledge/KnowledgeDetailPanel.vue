<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { useToastStore } from '../../stores/toast'
import * as knowledgeService from '../../services/knowledgeService'
import type { KnowledgeBase, KBUpdate } from '../../types/knowledge'

const props = defineProps<{
  kb: KnowledgeBase
  mergeableCount: number
}>()

const emit = defineEmits<{
  back: []
  build: [kb: KnowledgeBase]
  delete: [kb: KnowledgeBase]
  upload: []
  merge: []
  updated: [kb: KnowledgeBase]
}>()

const toast = useToastStore()

// Inline edit state
const isEditingName = ref(false)
const isEditingDescription = ref(false)
const editName = ref('')
const editDescription = ref('')
const isSavingEdit = ref(false)

function startEditName() {
  editName.value = props.kb.name
  isEditingName.value = true
  nextTick(() => {
    const el = document.getElementById('edit-name-input')
    if (el) el.focus()
  })
}

function startEditDescription() {
  editDescription.value = props.kb.description || ''
  isEditingDescription.value = true
  nextTick(() => {
    const el = document.getElementById('edit-desc-input')
    if (el) el.focus()
  })
}

async function saveInlineEdit(field: 'name' | 'description') {
  if (isSavingEdit.value) return

  const payload: KBUpdate = {}
  if (field === 'name') {
    const trimmed = editName.value.trim()
    if (!trimmed) {
      toast.error('Name cannot be empty')
      return
    }
    payload.name = trimmed
  } else {
    payload.description = editDescription.value.trim()
  }

  isSavingEdit.value = true
  try {
    const updated = await knowledgeService.updateKB(props.kb.id, payload)
    emit('updated', updated)
    toast.success('Updated successfully')
  } catch (e: any) {
    toast.error(e.response?.data?.detail || 'Failed to update')
  } finally {
    isSavingEdit.value = false
    isEditingName.value = false
    isEditingDescription.value = false
  }
}

function cancelEdit() {
  isEditingName.value = false
  isEditingDescription.value = false
}

function formatDate(dateStr: string | undefined) {
  if (!dateStr) return 'Never'
  return new Date(dateStr).toLocaleString()
}

function statusBadgeClass(status: string) {
  switch (status) {
    case 'idle': return 'badge-ghost'
    case 'building': return 'badge-warning'
    case 'ready': return 'badge-success'
    case 'error': return 'badge-error'
    default: return 'badge-ghost'
  }
}

function statusLabel(status: string) {
  switch (status) {
    case 'idle': return 'Not Built'
    case 'building': return 'Building'
    case 'ready': return 'Ready'
    case 'error': return 'Error'
    default: return status
  }
}
</script>

<template>
  <div class="mb-6">
    <button class="btn btn-ghost btn-sm gap-1 mb-4" @click="emit('back')">
      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
      </svg>
      Back to Knowledge Bases
    </button>

    <div class="flex flex-col lg:flex-row justify-between items-start gap-4">
      <!-- Name + Description (editable) -->
      <div class="flex-1 min-w-0">
        <!-- Name -->
        <div v-if="isEditingName" class="flex items-center gap-2 mb-1">
          <input id="edit-name-input" v-model="editName" type="text" class="input input-bordered input-sm text-xl font-bold flex-1" @keyup.enter="saveInlineEdit('name')" @keyup.escape="cancelEdit" />
          <button class="btn btn-xs btn-primary" :disabled="isSavingEdit" @click="saveInlineEdit('name')">Save</button>
          <button class="btn btn-xs btn-ghost" @click="cancelEdit">Cancel</button>
        </div>
        <h1 v-else class="text-2xl font-bold cursor-pointer hover:text-primary transition-colors" title="Click to edit" @click="startEditName">
          {{ kb.name }}
        </h1>

        <!-- Description -->
        <div v-if="isEditingDescription" class="flex items-start gap-2 mt-2">
          <textarea id="edit-desc-input" v-model="editDescription" class="textarea textarea-bordered textarea-sm flex-1" rows="2" @keyup.escape="cancelEdit"></textarea>
          <div class="flex flex-col gap-1">
            <button class="btn btn-xs btn-primary" :disabled="isSavingEdit" @click="saveInlineEdit('description')">Save</button>
            <button class="btn btn-xs btn-ghost" @click="cancelEdit">Cancel</button>
          </div>
        </div>
        <p v-else class="text-sm text-base-content/60 mt-1 cursor-pointer hover:text-base-content/80 transition-colors" title="Click to edit" @click="startEditDescription">
          {{ kb.description || 'No description. Click to add one.' }}
        </p>
      </div>

      <!-- Action Buttons -->
      <div class="flex gap-2 flex-shrink-0">
        <button class="btn btn-primary btn-sm" :disabled="kb.build_status === 'building'" @click="emit('build', kb)">
          <span v-if="kb.build_status === 'building'" class="loading loading-spinner loading-xs"></span>
          <svg v-else xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          {{ kb.build_status === 'building' ? 'Building...' : 'Build Graph' }}
        </button>

        <button class="btn btn-sm btn-outline" @click="emit('upload')" >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
          </svg>
          Upload Document
        </button>

        <button class="btn btn-sm btn-outline" @click="emit('merge')" :disabled="mergeableCount === 0">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
          </svg>
          Merge
        </button>

        <button class="btn btn-sm btn-error btn-outline" @click="emit('delete', kb)">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </button>
      </div>
    </div>
  </div>

  <!-- Status Bar -->
  <div class="card bg-base-100 shadow-sm border border-base-200 p-4 mb-6">
    <div class="flex flex-wrap items-center gap-6 text-sm">
      <div class="flex items-center gap-2">
        <span class="text-base-content/50 font-medium">Status:</span>
        <span class="badge gap-1" :class="statusBadgeClass(kb.build_status)">
          <span v-if="kb.build_status === 'building'" class="loading loading-spinner loading-xs"></span>
          {{ statusLabel(kb.build_status) }}
        </span>
      </div>
      <div class="flex items-center gap-2">
        <span class="text-base-content/50 font-medium">Nodes:</span>
        <span class="font-mono font-bold">{{ kb.node_count.toLocaleString() }}</span>
      </div>
      <div class="flex items-center gap-2">
        <span class="text-base-content/50 font-medium">Edges:</span>
        <span class="font-mono font-bold">{{ kb.edge_count.toLocaleString() }}</span>
      </div>
      <div class="flex items-center gap-2">
        <span class="text-base-content/50 font-medium">Source:</span>
        <span class="badge badge-sm badge-outline">{{ kb.source_type }}</span>
      </div>
      <div class="flex items-center gap-2">
        <span class="text-base-content/50 font-medium">Last Built:</span>
        <span>{{ formatDate(kb.last_built_at) }}</span>
      </div>
      <div v-if="kb.extraction_model" class="flex items-center gap-2">
        <span class="text-base-content/50 font-medium">Extraction:</span>
        <span class="text-xs font-mono">{{ kb.extraction_model }}</span>
      </div>
      <div v-if="kb.summarization_model" class="flex items-center gap-2">
        <span class="text-base-content/50 font-medium">Summarization:</span>
        <span class="text-xs font-mono">{{ kb.summarization_model }}</span>
      </div>
    </div>
  </div>
</template>
