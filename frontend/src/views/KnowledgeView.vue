<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useToastStore } from '../stores/toast'
import { useConfirm } from '../composables/useConfirm'
import { useKnowledgeBase } from '../composables/useKnowledgeBase'
import * as knowledgeService from '../services/knowledgeService'
import type { KnowledgeBase } from '../types/knowledge'
import KnowledgeBaseCard from '../components/knowledge/KnowledgeBaseCard.vue'
import CreateKBModal from '../components/knowledge/CreateKBModal.vue'
import KnowledgeDetailPanel from '../components/knowledge/KnowledgeDetailPanel.vue'
import KnowledgeQueryConsole from '../components/knowledge/KnowledgeQueryConsole.vue'
import KnowledgeMergeModal from '../components/knowledge/KnowledgeMergeModal.vue'

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

  if (scopeFilter.value === 'space') {
    result = result.filter((kb) => kb.space_id && !kb.room_id)
  } else if (scopeFilter.value === 'room') {
    result = result.filter((kb) => kb.room_id)
  }

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

function handleKBUpdated(updated: KnowledgeBase) {
  selectedKB.value = updated
  const idx = knowledgeBases.value.findIndex((k) => k.id === updated.id)
  if (idx !== -1) knowledgeBases.value[idx] = updated
}

// ── Build Polling ───────────────────────────────────────────────
const pollTimers = ref<Record<string, ReturnType<typeof setTimeout>>>({})
const pollCounts = ref<Record<string, number>>({})
const MAX_POLL = 20
const POLL_INTERVAL = 3000

function startPolling(kbId: string) {
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
    const idx = knowledgeBases.value.findIndex((k) => k.id === kbId)
    if (idx !== -1) {
      knowledgeBases.value[idx] = {
        ...knowledgeBases.value[idx],
        build_status: statusResult.build_status as KnowledgeBase['build_status'],
        node_count: statusResult.node_count,
        edge_count: statusResult.edge_count
      }
    }
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

// ── Detail Mode: Tabs ───────────────────────────────────────────
type DetailTab = 'query' | 'graph'
const activeTab = ref<DetailTab>('query')

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
      await fetchKBs(
        route.query.space_id ? { space_id: route.query.space_id as string } : undefined
      )
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

// ── Lifecycle ───────────────────────────────────────────────────
onMounted(() => {
  const params: { space_id?: string } = {}
  if (route.query.space_id) {
    params.space_id = route.query.space_id as string
  }
  fetchKBs(params)
})

watch(
  () => route.query.space_id,
  (newSpaceId) => {
    const params: { space_id?: string } = {}
    if (newSpaceId) params.space_id = newSpaceId as string
    fetchKBs(params)
  }
)

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
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
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
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-base-content/40" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input v-model="searchQuery" type="text" placeholder="Search knowledge bases..." class="input input-bordered input-sm w-full pl-9" />
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
      <div v-else-if="filteredKBs.length === 0 && knowledgeBases.length === 0" class="text-center py-16 bg-base-100 rounded-box shadow">
        <div class="w-16 h-16 mx-auto rounded-full bg-base-200 flex items-center justify-center mb-4">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 text-base-content/30" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
          </svg>
        </div>
        <h3 class="font-bold text-lg mb-2">No Knowledge Bases Yet</h3>
        <p class="text-base-content/60 mb-4 max-w-md mx-auto">
          Create your first knowledge base to start extracting structured knowledge from conversations and documents.
        </p>
        <button class="btn btn-primary" @click="showCreateModal = true">
          Create Your First Knowledge Base
        </button>
      </div>

      <!-- No Results (with filter) -->
      <div v-else-if="filteredKBs.length === 0" class="text-center py-16">
        <p class="text-base-content/60">No knowledge bases match your search criteria.</p>
        <button class="btn btn-sm btn-ghost mt-2" @click="searchQuery = ''; scopeFilter = 'all'">
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
      <KnowledgeDetailPanel
        :kb="selectedKB"
        :mergeable-count="mergeableKBs.length"
        @back="handleBackToList"
        @build="handleBuildKB"
        @delete="handleDeleteKB"
        @upload="triggerUpload"
        @merge="showMergeModal = true"
        @updated="handleKBUpdated"
      />

      <input
        ref="fileInput"
        type="file"
        class="hidden"
        accept=".pdf,.txt,.md,.docx,.csv"
        @change="handleFileUpload"
      />

      <!-- Tabs -->
      <div class="tabs tabs-bordered mb-4">
        <a class="tab" :class="{ 'tab-active': activeTab === 'query' }" @click="activeTab = 'query'">
          Query Console
        </a>
        <a class="tab" :class="{ 'tab-active': activeTab === 'graph' }" @click="activeTab = 'graph'">
          Graph View
        </a>
      </div>

      <!-- Tab: Query Console -->
      <KnowledgeQueryConsole v-if="activeTab === 'query'" :kb="selectedKB" />

      <!-- Tab: Graph View -->
      <div v-if="activeTab === 'graph'" class="card bg-base-100 shadow-sm border border-base-200">
        <div class="card-body">
          <div class="flex flex-col items-center justify-center py-16 text-base-content/40">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-16 w-16 mb-4 opacity-40" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
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
    <CreateKBModal
      :visible="showCreateModal"
      :preset-space-id="presetSpaceId"
      @close="showCreateModal = false"
      @created="handleKBCreated"
    />

    <KnowledgeMergeModal
      v-model="showMergeModal"
      v-model:target-id="mergeTargetId"
      :kb="selectedKB"
      :mergeable-k-bs="mergeableKBs"
      :is-merging="isMerging"
      @merge="handleMerge"
    />
  </div>
</template>
