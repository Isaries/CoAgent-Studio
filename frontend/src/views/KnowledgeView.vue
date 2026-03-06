<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { useToastStore } from '../stores/toast'
import { useConfirm } from '../composables/useConfirm'
import { useKnowledgeBase } from '../composables/useKnowledgeBase'
import * as knowledgeService from '../services/knowledgeService'
import type { KnowledgeBase, KBUpdate } from '../types/knowledge'
import KnowledgeBaseCard from '../components/knowledge/KnowledgeBaseCard.vue'
import CreateKBModal from '../components/knowledge/CreateKBModal.vue'

const route = useRoute()
const toast = useToastStore()
const { confirm: confirmDialog } = useConfirm()

const { knowledgeBases, loading, error, fetchKBs, deleteKB, buildKB, mergeKB } = useKnowledgeBase()

// ── View Mode ───────────────────────────────────────────────────
type ViewMode = 'list' | 'detail'
const viewMode = ref<ViewMode>('list')
const selectedKB = ref<KnowledgeBase | null>(null)

// ── List Filters ────────────────────────────────────────────────
const searchQuery = ref('')
const scopeFilter = ref<'all' | 'space' | 'room'>('all')

const filteredKBs = computed(() => {
  let result = knowledgeBases.value

  // Scope filter
  if (scopeFilter.value === 'space') {
    result = result.filter((kb) => kb.space_id && !kb.room_id)
  } else if (scopeFilter.value === 'room') {
    result = result.filter((kb) => kb.room_id)
  }

  // Search filter
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase()
    result = result.filter(
      (kb) =>
        kb.name.toLowerCase().includes(q) ||
        (kb.description && kb.description.toLowerCase().includes(q))
    )
  }

  return result
})

// ── Create Modal ────────────────────────────────────────────────
const showCreateModal = ref(false)
const presetSpaceId = computed(() => (route.query.space_id as string) || '')

function handleKBCreated(kb: KnowledgeBase) {
  knowledgeBases.value.push(kb)
  showCreateModal.value = false
}

// ── Card Actions ────────────────────────────────────────────────
function handleSelectKB(kb: KnowledgeBase) {
  selectedKB.value = kb
  viewMode.value = 'detail'
}

async function handleBuildKB(kb: KnowledgeBase) {
  const success = await buildKB(kb.id)
  if (success) {
    toast.success(`Build started for "${kb.name}"`)
    // Update local status to building
    const idx = knowledgeBases.value.findIndex((k) => k.id === kb.id)
    if (idx !== -1) {
      knowledgeBases.value[idx] = { ...knowledgeBases.value[idx], build_status: 'building' }
    }
    if (selectedKB.value?.id === kb.id) {
      selectedKB.value = { ...selectedKB.value, build_status: 'building' }
    }
    startPolling(kb.id)
  }
}

async function handleDeleteKB(kb: KnowledgeBase) {
  if (
    !(await confirmDialog(
      'Delete Knowledge Base',
      `Are you sure you want to delete "${kb.name}"? This action cannot be undone.`
    ))
  )
    return
  const success = await deleteKB(kb.id)
  if (success) {
    toast.success(`"${kb.name}" deleted`)
    if (selectedKB.value?.id === kb.id) {
      selectedKB.value = null
      viewMode.value = 'list'
    }
  } else {
    toast.error(error.value || 'Failed to delete knowledge base')
  }
}

function handleBackToList() {
  selectedKB.value = null
  viewMode.value = 'list'
}

// ── Build Polling ───────────────────────────────────────────────
const pollTimers = ref<Record<string, ReturnType<typeof setTimeout>>>({})
const pollCounts = ref<Record<string, number>>({})
const MAX_POLL = 20
const POLL_INTERVAL = 3000

function startPolling(kbId: string) {
  // Clear existing poll for this kb if any
  if (pollTimers.value[kbId]) {
    clearTimeout(pollTimers.value[kbId])
  }
  pollCounts.value[kbId] = 0
  pollNext(kbId)
}

async function pollNext(kbId: string) {
  if ((pollCounts.value[kbId] || 0) >= MAX_POLL) {
    toast.warning('Build status check timed out. Refresh to check status.')
    delete pollTimers.value[kbId]
    delete pollCounts.value[kbId]
    return
  }

  pollCounts.value[kbId] = (pollCounts.value[kbId] || 0) + 1

  try {
    const statusResult = await knowledgeService.getKBStatus(kbId)
    // Update in the list
    const idx = knowledgeBases.value.findIndex((k) => k.id === kbId)
    if (idx !== -1) {
      knowledgeBases.value[idx] = {
        ...knowledgeBases.value[idx],
        build_status: statusResult.build_status as KnowledgeBase['build_status'],
        node_count: statusResult.node_count,
        edge_count: statusResult.edge_count
      }
    }
    // Update detail view if this KB is selected
    if (selectedKB.value?.id === kbId) {
      selectedKB.value = {
        ...selectedKB.value,
        build_status: statusResult.build_status as KnowledgeBase['build_status'],
        node_count: statusResult.node_count,
        edge_count: statusResult.edge_count
      }
    }

    if (statusResult.build_status === 'building') {
      pollTimers.value[kbId] = setTimeout(() => pollNext(kbId), POLL_INTERVAL)
    } else {
      // Done polling
      delete pollTimers.value[kbId]
      delete pollCounts.value[kbId]
      if (statusResult.build_status === 'ready') {
        toast.success('Knowledge graph build completed!')
      } else if (statusResult.build_status === 'error') {
        toast.error('Knowledge graph build failed.')
      }
    }
  } catch {
    delete pollTimers.value[kbId]
    delete pollCounts.value[kbId]
  }
}

// ── Detail Mode: Inline Edit ────────────────────────────────────
const isEditingName = ref(false)
const isEditingDescription = ref(false)
const editName = ref('')
const editDescription = ref('')
const isSavingEdit = ref(false)

function startEditName() {
  if (!selectedKB.value) return
  editName.value = selectedKB.value.name
  isEditingName.value = true
  nextTick(() => {
    const el = document.getElementById('edit-name-input')
    if (el) el.focus()
  })
}

function startEditDescription() {
  if (!selectedKB.value) return
  editDescription.value = selectedKB.value.description || ''
  isEditingDescription.value = true
  nextTick(() => {
    const el = document.getElementById('edit-desc-input')
    if (el) el.focus()
  })
}

async function saveInlineEdit(field: 'name' | 'description') {
  if (!selectedKB.value || isSavingEdit.value) return

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
    const updated = await knowledgeService.updateKB(selectedKB.value.id, payload)
    selectedKB.value = updated
    const idx = knowledgeBases.value.findIndex((k) => k.id === updated.id)
    if (idx !== -1) knowledgeBases.value[idx] = updated
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

// ── Detail Mode: Tabs ───────────────────────────────────────────
type DetailTab = 'query' | 'graph'
const activeTab = ref<DetailTab>('query')

// ── Detail Mode: Query Console ──────────────────────────────────
const queryInput = ref('')
const queryLoading = ref(false)
const queryResult = ref<any>(null)

async function submitQuery() {
  if (!selectedKB.value || !queryInput.value.trim() || queryLoading.value) return

  queryLoading.value = true
  queryResult.value = null
  try {
    queryResult.value = await knowledgeService.queryKB(selectedKB.value.id, queryInput.value.trim())
  } catch (e: any) {
    queryResult.value = {
      answer: e.response?.data?.detail || 'Query failed. Make sure the graph is built first.',
      error: true
    }
  } finally {
    queryLoading.value = false
  }
}

// ── Detail Mode: Upload Document ────────────────────────────────
const fileInput = ref<HTMLInputElement | null>(null)
const isUploading = ref(false)

function triggerUpload() {
  fileInput.value?.click()
}

async function handleFileUpload(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file || !selectedKB.value) return

  isUploading.value = true
  try {
    await knowledgeService.uploadDocument(selectedKB.value.id, file)
    toast.success(`Document "${file.name}" uploaded successfully`)
  } catch (e: any) {
    toast.error(e.response?.data?.detail || 'Failed to upload document')
  } finally {
    isUploading.value = false
    // Reset file input
    if (fileInput.value) fileInput.value.value = ''
  }
}

// ── Detail Mode: Merge ──────────────────────────────────────────
const showMergeModal = ref(false)
const mergeTargetId = ref('')
const isMerging = ref(false)

const mergeableKBs = computed(() => {
  if (!selectedKB.value) return []
  return knowledgeBases.value.filter((kb) => kb.id !== selectedKB.value!.id)
})

async function handleMerge() {
  if (!selectedKB.value || !mergeTargetId.value || isMerging.value) return

  isMerging.value = true
  try {
    const success = await mergeKB(selectedKB.value.id, mergeTargetId.value)
    if (success) {
      toast.success('Knowledge bases merged successfully')
      showMergeModal.value = false
      mergeTargetId.value = ''
      // Refresh KB data
      await fetchKBs(
        route.query.space_id ? { space_id: route.query.space_id as string } : undefined
      )
      // Reload selected KB
      if (selectedKB.value) {
        const refreshed = knowledgeBases.value.find((kb) => kb.id === selectedKB.value!.id)
        if (refreshed) selectedKB.value = refreshed
      }
    } else {
      toast.error(error.value || 'Failed to merge knowledge bases')
    }
  } finally {
    isMerging.value = false
  }
}

// ── Detail Mode: Helpers ────────────────────────────────────────
function formatDate(dateStr: string | undefined) {
  if (!dateStr) return 'Never'
  return new Date(dateStr).toLocaleString()
}

function statusBadgeClass(status: string) {
  switch (status) {
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
}

function statusLabel(status: string) {
  switch (status) {
    case 'idle':
      return 'Not Built'
    case 'building':
      return 'Building'
    case 'ready':
      return 'Ready'
    case 'error':
      return 'Error'
    default:
      return status
  }
}

// ── Lifecycle ───────────────────────────────────────────────────
onMounted(() => {
  const params: { space_id?: string } = {}
  if (route.query.space_id) {
    params.space_id = route.query.space_id as string
  }
  fetchKBs(params)
})

// Watch for query param changes
watch(
  () => route.query.space_id,
  (newSpaceId) => {
    const params: { space_id?: string } = {}
    if (newSpaceId) params.space_id = newSpaceId as string
    fetchKBs(params)
  }
)

// Start polling for any KBs that are currently building
watch(
  knowledgeBases,
  (kbs) => {
    for (const kb of kbs) {
      if (kb.build_status === 'building' && !pollTimers.value[kb.id]) {
        startPolling(kb.id)
      }
    }
  },
  { immediate: true }
)

// Cleanup polling timers on unmount
onUnmounted(() => {
  for (const timer of Object.values(pollTimers.value)) {
    clearTimeout(timer)
  }
})
</script>

<template>
  <div class="p-6 max-w-7xl mx-auto">
    <!-- ════════════════════════════════════════════════════════ -->
    <!-- LIST MODE                                               -->
    <!-- ════════════════════════════════════════════════════════ -->
    <template v-if="viewMode === 'list'">
      <!-- Header -->
      <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
        <div>
          <h1 class="text-2xl font-bold">Knowledge Engine</h1>
          <p class="text-sm text-base-content/60 mt-1">
            Create, build, and query knowledge graphs from conversations and documents.
          </p>
        </div>
        <button class="btn btn-primary" @click="showCreateModal = true">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-5 w-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
          >
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Create Knowledge Base
        </button>
      </div>

      <!-- Filter Bar -->
      <div class="flex flex-col sm:flex-row gap-3 mb-6">
        <select v-model="scopeFilter" class="select select-bordered select-sm w-full sm:w-48">
          <option value="all">All Scopes</option>
          <option value="space">Space-level</option>
          <option value="room">Room-level</option>
        </select>
        <div class="relative flex-1">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-base-content/40"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search knowledge bases..."
            class="input input-bordered input-sm w-full pl-9"
          />
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="flex justify-center py-16">
        <span class="loading loading-spinner loading-lg text-primary"></span>
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="text-center py-16">
        <div class="text-error mb-2">{{ error }}</div>
        <button class="btn btn-sm btn-ghost" @click="fetchKBs()">Retry</button>
      </div>

      <!-- Empty State -->
      <div
        v-else-if="filteredKBs.length === 0 && knowledgeBases.length === 0"
        class="text-center py-16 bg-base-100 rounded-box shadow"
      >
        <div
          class="w-16 h-16 mx-auto rounded-full bg-base-200 flex items-center justify-center mb-4"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-8 w-8 text-base-content/30"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="1.5"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25"
            />
          </svg>
        </div>
        <h3 class="font-bold text-lg mb-2">No Knowledge Bases Yet</h3>
        <p class="text-base-content/60 mb-4 max-w-md mx-auto">
          Create your first knowledge base to start extracting structured knowledge from
          conversations and documents.
        </p>
        <button class="btn btn-primary" @click="showCreateModal = true">
          Create Your First Knowledge Base
        </button>
      </div>

      <!-- No Results (with filter) -->
      <div v-else-if="filteredKBs.length === 0" class="text-center py-16">
        <p class="text-base-content/60">No knowledge bases match your search criteria.</p>
        <button
          class="btn btn-sm btn-ghost mt-2"
          @click="
            searchQuery = ''
            scopeFilter = 'all'
          "
        >
          Clear Filters
        </button>
      </div>

      <!-- KB Grid -->
      <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        <KnowledgeBaseCard
          v-for="kb in filteredKBs"
          :key="kb.id"
          :kb="kb"
          @select="handleSelectKB"
          @build="handleBuildKB"
          @delete="handleDeleteKB"
        />
      </div>
    </template>

    <!-- ════════════════════════════════════════════════════════ -->
    <!-- DETAIL MODE                                             -->
    <!-- ════════════════════════════════════════════════════════ -->
    <template v-else-if="viewMode === 'detail' && selectedKB">
      <!-- Back Button + Header -->
      <div class="mb-6">
        <button class="btn btn-ghost btn-sm gap-1 mb-4" @click="handleBackToList">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-4 w-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
          >
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
          Back to Knowledge Bases
        </button>

        <div class="flex flex-col lg:flex-row justify-between items-start gap-4">
          <!-- Name + Description (editable) -->
          <div class="flex-1 min-w-0">
            <!-- Name -->
            <div v-if="isEditingName" class="flex items-center gap-2 mb-1">
              <input
                id="edit-name-input"
                v-model="editName"
                type="text"
                class="input input-bordered input-sm text-xl font-bold flex-1"
                @keyup.enter="saveInlineEdit('name')"
                @keyup.escape="cancelEdit"
              />
              <button
                class="btn btn-xs btn-primary"
                :disabled="isSavingEdit"
                @click="saveInlineEdit('name')"
              >
                Save
              </button>
              <button class="btn btn-xs btn-ghost" @click="cancelEdit">Cancel</button>
            </div>
            <h1
              v-else
              class="text-2xl font-bold cursor-pointer hover:text-primary transition-colors"
              title="Click to edit"
              @click="startEditName"
            >
              {{ selectedKB.name }}
            </h1>

            <!-- Description -->
            <div v-if="isEditingDescription" class="flex items-start gap-2 mt-2">
              <textarea
                id="edit-desc-input"
                v-model="editDescription"
                class="textarea textarea-bordered textarea-sm flex-1"
                rows="2"
                @keyup.escape="cancelEdit"
              ></textarea>
              <div class="flex flex-col gap-1">
                <button
                  class="btn btn-xs btn-primary"
                  :disabled="isSavingEdit"
                  @click="saveInlineEdit('description')"
                >
                  Save
                </button>
                <button class="btn btn-xs btn-ghost" @click="cancelEdit">Cancel</button>
              </div>
            </div>
            <p
              v-else
              class="text-sm text-base-content/60 mt-1 cursor-pointer hover:text-base-content/80 transition-colors"
              title="Click to edit"
              @click="startEditDescription"
            >
              {{ selectedKB.description || 'No description. Click to add one.' }}
            </p>
          </div>

          <!-- Action Buttons -->
          <div class="flex gap-2 flex-shrink-0">
            <button
              class="btn btn-primary btn-sm"
              :disabled="selectedKB.build_status === 'building'"
              @click="handleBuildKB(selectedKB)"
            >
              <span
                v-if="selectedKB.build_status === 'building'"
                class="loading loading-spinner loading-xs"
              ></span>
              <svg
                v-else
                xmlns="http://www.w3.org/2000/svg"
                class="h-4 w-4"
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
              {{ selectedKB.build_status === 'building' ? 'Building...' : 'Build Graph' }}
            </button>

            <button class="btn btn-sm btn-outline" @click="triggerUpload" :disabled="isUploading">
              <span v-if="isUploading" class="loading loading-spinner loading-xs"></span>
              <svg
                v-else
                xmlns="http://www.w3.org/2000/svg"
                class="h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"
                />
              </svg>
              Upload Document
            </button>
            <input
              ref="fileInput"
              type="file"
              class="hidden"
              accept=".pdf,.txt,.md,.docx,.csv"
              @change="handleFileUpload"
            />

            <button
              class="btn btn-sm btn-outline"
              @click="showMergeModal = true"
              :disabled="mergeableKBs.length === 0"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"
                />
              </svg>
              Merge
            </button>

            <button class="btn btn-sm btn-error btn-outline" @click="handleDeleteKB(selectedKB)">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-4 w-4"
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

      <!-- Status Bar -->
      <div class="card bg-base-100 shadow-sm border border-base-200 p-4 mb-6">
        <div class="flex flex-wrap items-center gap-6 text-sm">
          <div class="flex items-center gap-2">
            <span class="text-base-content/50 font-medium">Status:</span>
            <span class="badge gap-1" :class="statusBadgeClass(selectedKB.build_status)">
              <span
                v-if="selectedKB.build_status === 'building'"
                class="loading loading-spinner loading-xs"
              ></span>
              {{ statusLabel(selectedKB.build_status) }}
            </span>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-base-content/50 font-medium">Nodes:</span>
            <span class="font-mono font-bold">{{ selectedKB.node_count.toLocaleString() }}</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-base-content/50 font-medium">Edges:</span>
            <span class="font-mono font-bold">{{ selectedKB.edge_count.toLocaleString() }}</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-base-content/50 font-medium">Source:</span>
            <span class="badge badge-sm badge-outline">{{ selectedKB.source_type }}</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-base-content/50 font-medium">Last Built:</span>
            <span>{{ formatDate(selectedKB.last_built_at) }}</span>
          </div>
          <div v-if="selectedKB.extraction_model" class="flex items-center gap-2">
            <span class="text-base-content/50 font-medium">Extraction:</span>
            <span class="text-xs font-mono">{{ selectedKB.extraction_model }}</span>
          </div>
          <div v-if="selectedKB.summarization_model" class="flex items-center gap-2">
            <span class="text-base-content/50 font-medium">Summarization:</span>
            <span class="text-xs font-mono">{{ selectedKB.summarization_model }}</span>
          </div>
        </div>
      </div>

      <!-- Tabs -->
      <div class="tabs tabs-bordered mb-4">
        <a
          class="tab"
          :class="{ 'tab-active': activeTab === 'query' }"
          @click="activeTab = 'query'"
        >
          Query Console
        </a>
        <a
          class="tab"
          :class="{ 'tab-active': activeTab === 'graph' }"
          @click="activeTab = 'graph'"
        >
          Graph View
        </a>
      </div>

      <!-- Tab: Query Console -->
      <div v-if="activeTab === 'query'" class="card bg-base-100 shadow-sm border border-base-200">
        <div class="card-body">
          <h3 class="card-title text-base mb-4">Query the Knowledge Graph</h3>

          <!-- Query Input -->
          <div class="flex gap-2 mb-4">
            <input
              v-model="queryInput"
              type="text"
              placeholder="Ask a question about this knowledge base..."
              class="input input-bordered flex-1"
              @keyup.enter="submitQuery"
              :disabled="queryLoading"
            />
            <button
              class="btn btn-primary"
              :disabled="queryLoading || !queryInput.trim()"
              @click="submitQuery"
            >
              <span v-if="queryLoading" class="loading loading-spinner loading-sm"></span>
              <svg
                v-else
                xmlns="http://www.w3.org/2000/svg"
                class="h-5 w-5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
              Query
            </button>
          </div>

          <!-- Query Hint -->
          <div v-if="!queryResult && !queryLoading" class="text-center py-8 text-base-content/40">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-12 w-12 mx-auto mb-3 opacity-50"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="1"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <p class="text-sm">Enter a question to query the knowledge graph.</p>
            <p class="text-xs mt-1">
              Example: "What are the main topics discussed?" or "Summarize the key concepts."
            </p>
          </div>

          <!-- Loading -->
          <div v-if="queryLoading" class="flex justify-center py-8">
            <span class="loading loading-dots loading-lg text-primary"></span>
          </div>

          <!-- Query Result -->
          <div
            v-if="queryResult && !queryLoading"
            class="bg-base-200/50 rounded-lg p-4 border border-base-300"
          >
            <div v-if="queryResult.intent" class="mb-2">
              <span
                class="badge badge-sm"
                :class="queryResult.intent === 'global' ? 'badge-primary' : 'badge-secondary'"
              >
                {{ queryResult.intent === 'global' ? 'Global Analysis' : 'Local Search' }}
              </span>
            </div>
            <div
              class="prose max-w-none whitespace-pre-wrap text-sm"
              :class="{ 'text-error': queryResult.error }"
            >
              {{ queryResult.answer }}
            </div>
            <div
              v-if="queryResult.sources && queryResult.sources.length > 0"
              class="mt-3 pt-3 border-t border-base-300"
            >
              <span class="text-xs font-semibold text-base-content/50 mb-1 block">Sources:</span>
              <div class="flex flex-wrap gap-1">
                <span
                  v-for="src in queryResult.sources"
                  :key="src"
                  class="badge badge-outline badge-xs"
                  >{{ src }}</span
                >
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Tab: Graph View -->
      <div v-if="activeTab === 'graph'" class="card bg-base-100 shadow-sm border border-base-200">
        <div class="card-body">
          <div class="flex flex-col items-center justify-center py-16 text-base-content/40">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-16 w-16 mb-4 opacity-40"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="1"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25"
              />
            </svg>
            <h3 class="font-bold text-lg mb-2">Graph Visualization</h3>
            <p class="text-sm text-center max-w-md mb-4">
              Interactive graph visualization is available in the Room view. Navigate to the room
              associated with this knowledge base to view and explore the entity-relationship graph.
            </p>
            <div v-if="selectedKB.room_id" class="flex gap-2">
              <router-link :to="`/rooms/${selectedKB.room_id}`" class="btn btn-primary btn-sm">
                Open Room View
              </router-link>
            </div>
            <div v-else class="text-xs text-base-content/30">
              This knowledge base is not attached to a specific room.
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- ════════════════════════════════════════════════════════ -->
    <!-- MODALS                                                  -->
    <!-- ════════════════════════════════════════════════════════ -->

    <!-- Create KB Modal -->
    <CreateKBModal
      :visible="showCreateModal"
      :preset-space-id="presetSpaceId"
      @close="showCreateModal = false"
      @created="handleKBCreated"
    />

    <!-- Merge Modal -->
    <dialog class="modal" :class="{ 'modal-open': showMergeModal }">
      <div class="modal-box">
        <button
          class="btn btn-sm btn-circle btn-ghost absolute right-3 top-3"
          @click="showMergeModal = false"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-5 w-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
          >
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        <h3 class="font-bold text-lg mb-1">Merge Knowledge Bases</h3>
        <p class="text-sm text-base-content/60 mb-4">
          Merge another knowledge base into <strong>{{ selectedKB?.name }}</strong
          >. The source data will be combined into this knowledge base.
        </p>

        <div class="form-control mb-4">
          <label class="label">
            <span class="label-text font-semibold">Source Knowledge Base</span>
          </label>
          <select v-model="mergeTargetId" class="select select-bordered w-full">
            <option value="" disabled>Select a knowledge base to merge from...</option>
            <option v-for="kb in mergeableKBs" :key="kb.id" :value="kb.id">
              {{ kb.name }} ({{ kb.node_count }} nodes, {{ kb.edge_count }} edges)
            </option>
          </select>
        </div>

        <div class="modal-action">
          <button class="btn btn-ghost" @click="showMergeModal = false">Cancel</button>
          <button
            class="btn btn-primary"
            :disabled="!mergeTargetId || isMerging"
            @click="handleMerge"
          >
            <span v-if="isMerging" class="loading loading-spinner loading-xs"></span>
            {{ isMerging ? 'Merging...' : 'Merge' }}
          </button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop">
        <button @click="showMergeModal = false">close</button>
      </form>
    </dialog>
  </div>
</template>
