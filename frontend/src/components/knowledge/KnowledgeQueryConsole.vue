<script setup lang="ts">
import { ref } from 'vue'
import * as knowledgeService from '../../services/knowledgeService'
import type { KnowledgeBase } from '../../types/knowledge'

const props = defineProps<{
  kb: KnowledgeBase
}>()

const queryInput = ref('')
const queryLoading = ref(false)
const queryResult = ref<any>(null)

async function submitQuery() {
  if (!queryInput.value.trim() || queryLoading.value) return

  queryLoading.value = true
  queryResult.value = null
  try {
    queryResult.value = await knowledgeService.queryKB(props.kb.id, queryInput.value.trim())
  } catch (e: any) {
    queryResult.value = {
      answer: e.response?.data?.detail || 'Query failed. Make sure the graph is built first.',
      error: true
    }
  } finally {
    queryLoading.value = false
  }
}
</script>

<template>
  <div class="card bg-base-100 shadow-sm border border-base-200">
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
          <svg v-else xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          Query
        </button>
      </div>

      <!-- Query Hint -->
      <div v-if="!queryResult && !queryLoading" class="text-center py-8 text-base-content/40">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 mx-auto mb-3 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
          <path stroke-linecap="round" stroke-linejoin="round" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <p class="text-sm">Enter a question to query the knowledge graph.</p>
        <p class="text-xs mt-1">Example: "What are the main topics discussed?" or "Summarize the key concepts."</p>
      </div>

      <!-- Loading -->
      <div v-if="queryLoading" class="flex justify-center py-8">
        <span class="loading loading-dots loading-lg text-primary"></span>
      </div>

      <!-- Query Result -->
      <div v-if="queryResult && !queryLoading" class="bg-base-200/50 rounded-lg p-4 border border-base-300">
        <div v-if="queryResult.intent" class="mb-2">
          <span class="badge badge-sm" :class="queryResult.intent === 'global' ? 'badge-primary' : 'badge-secondary'">
            {{ queryResult.intent === 'global' ? 'Global Analysis' : 'Local Search' }}
          </span>
        </div>
        <div class="prose max-w-none whitespace-pre-wrap text-sm" :class="{ 'text-error': queryResult.error }">
          {{ queryResult.answer }}
        </div>
        <div v-if="queryResult.sources && queryResult.sources.length > 0" class="mt-3 pt-3 border-t border-base-300">
          <span class="text-xs font-semibold text-base-content/50 mb-1 block">Sources:</span>
          <div class="flex flex-wrap gap-1">
            <span v-for="src in queryResult.sources" :key="src" class="badge badge-outline badge-xs">{{ src }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
