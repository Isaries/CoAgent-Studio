<script setup lang="ts">
/**
 * GraphQueryPanel — Analytics Agent Q&A + Graph administration.
 *
 * Allows users to:
 * 1. Build/rebuild the knowledge graph
 * 2. Ask natural language questions (global or local)
 * 3. View community summaries
 */
import { ref, onMounted } from 'vue'
import { graphService } from '../../services/graphService'
import type { GraphStatus, GraphQueryResponse, CommunityReport } from '../../types/graph'

const props = defineProps<{
  roomId: string
}>()

const status = ref<GraphStatus | null>(null)
const isBuilding = ref(false)
const buildMessage = ref('')

const question = ref('')
const isQuerying = ref(false)
const queryResult = ref<GraphQueryResponse | null>(null)

const communities = ref<CommunityReport[]>([])
const showCommunities = ref(false)
const loadingCommunities = ref(false)

// Status
async function loadStatus() {
  try {
    status.value = await graphService.getStatus(props.roomId)
  } catch {
    // Graph may not be built yet, that's OK
  }
}

// Build
async function buildGraph() {
  isBuilding.value = true
  buildMessage.value = ''
  try {
    const res = await graphService.buildGraph(props.roomId)
    buildMessage.value = res.message
    // Poll status after a delay
    setTimeout(async () => {
      await loadStatus()
      isBuilding.value = false
    }, 5000)
  } catch (e: any) {
    buildMessage.value = e?.response?.data?.detail || 'Build failed'
    isBuilding.value = false
  }
}

// Query
async function askQuestion() {
  if (!question.value.trim()) return
  isQuerying.value = true
  queryResult.value = null
  try {
    queryResult.value = await graphService.queryGraph(props.roomId, question.value)
  } catch (e: any) {
    queryResult.value = {
      answer: e?.response?.data?.detail || 'Query failed. Make sure the graph is built.',
      intent: 'local',
      sources: [],
    }
  } finally {
    isQuerying.value = false
  }
}

// Communities
async function toggleCommunities() {
  showCommunities.value = !showCommunities.value
  if (showCommunities.value && communities.value.length === 0) {
    loadingCommunities.value = true
    try {
      communities.value = await graphService.getCommunities(props.roomId)
    } catch {
      communities.value = []
    } finally {
      loadingCommunities.value = false
    }
  }
}

onMounted(() => {
  loadStatus()
})
</script>

<template>
  <div class="flex flex-col h-full bg-slate-900 text-slate-200 p-4 overflow-y-auto">
    <!-- Header -->
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-lg font-bold">🧠 Analytics Agent</h3>
      <div class="text-xs text-slate-400" v-if="status">
        {{ status.node_count }} entities · {{ status.edge_count }} relations · {{ status.community_count }} communities
      </div>
    </div>

    <!-- Build Section -->
    <div class="mb-6 p-4 rounded-lg bg-slate-800 border border-slate-700">
      <div class="flex items-center justify-between mb-2">
        <h4 class="text-sm font-semibold">Graph Builder</h4>
        <button
          class="btn btn-sm btn-primary"
          :class="{ loading: isBuilding }"
          :disabled="isBuilding"
          @click="buildGraph"
        >
          {{ isBuilding ? 'Building...' : '🔨 Build Graph' }}
        </button>
      </div>
      <p class="text-xs text-slate-400">
        Extracts entities & relationships from all room conversations, then clusters them into knowledge communities.
      </p>
      <div v-if="buildMessage" class="mt-2 text-xs text-green-400">{{ buildMessage }}</div>
    </div>

    <!-- Query Section -->
    <div class="mb-6">
      <h4 class="text-sm font-semibold mb-2">Ask the Analytics Agent</h4>
      <div class="flex gap-2">
        <input
          v-model="question"
          type="text"
          placeholder="e.g. What are the main learning challenges in this room?"
          class="input input-bordered input-sm flex-1 bg-slate-800 text-slate-200"
          @keyup.enter="askQuestion"
        />
        <button
          class="btn btn-sm btn-accent"
          :disabled="isQuerying || !question.trim()"
          @click="askQuestion"
        >
          {{ isQuerying ? '...' : '🔍' }}
        </button>
      </div>
    </div>

    <!-- Query Result -->
    <div v-if="queryResult" class="mb-6 p-4 rounded-lg bg-slate-800 border border-slate-700">
      <div class="flex items-center gap-2 mb-2">
        <span class="badge badge-sm" :class="queryResult.intent === 'global' ? 'badge-primary' : 'badge-secondary'">
          {{ queryResult.intent === 'global' ? '🌐 Global Analysis' : '🔎 Local Search' }}
        </span>
      </div>
      <div class="text-sm whitespace-pre-wrap leading-relaxed">{{ queryResult.answer }}</div>
      <div v-if="queryResult.sources.length > 0" class="mt-3 flex flex-wrap gap-1">
        <span
          v-for="src in queryResult.sources"
          :key="src"
          class="badge badge-outline badge-xs"
        >{{ src }}</span>
      </div>
    </div>

    <!-- Communities -->
    <div>
      <button
        class="btn btn-sm btn-ghost text-slate-400 mb-2"
        @click="toggleCommunities"
      >
        {{ showCommunities ? '▼' : '►' }} Community Summaries ({{ communities.length || '...' }})
      </button>

      <div v-if="showCommunities">
        <div v-if="loadingCommunities" class="text-center py-4">
          <span class="loading loading-dots loading-sm"></span>
        </div>
        <div v-else-if="communities.length === 0" class="text-xs text-slate-500 py-2">
          No communities found. Build the graph first.
        </div>
        <div
          v-for="c in communities"
          :key="c.community_id"
          class="mb-3 p-3 rounded-lg bg-slate-800/60 border border-slate-700"
        >
          <h5 class="font-semibold text-sm mb-1">{{ c.title }}</h5>
          <p class="text-xs text-slate-300 mb-2">{{ c.summary }}</p>
          <ul v-if="c.key_findings.length > 0" class="list-disc list-inside text-xs text-slate-400 mb-2">
            <li v-for="(f, i) in c.key_findings" :key="i">{{ f }}</li>
          </ul>
          <div class="flex flex-wrap gap-1">
            <span
              v-for="entity in c.key_entities"
              :key="entity"
              class="badge badge-outline badge-xs"
            >{{ entity }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
