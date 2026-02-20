<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useDesignAgent } from '../composables/useDesignAgent'
import { agentService } from '../services/agentService'
import type { AgentConfig } from '../types/agent'

import CourseBrainEditor from './course-settings/components/CourseBrainEditor.vue'
import ResizableSplitPane from '../components/common/ResizableSplitPane.vue'
import AgentSandbox from '../components/workspace/AgentSandbox.vue'
import { useToastStore } from '../stores/toast'
import { AgentType } from '../types/enums'

const route = useRoute()
const projectId = route.params.projectId as string
const agentId = route.params.agentId as string
const toast = useToastStore()

const currentAgentConfig = ref<AgentConfig | null>(null)
const isLoading = ref(false)
const isSaving = ref(false)
const hasUnsavedChanges = ref(false)

const {
  designConfig,
  fetchVersions,
  createVersion
} = useDesignAgent('project', projectId)

const loadAgent = async () => {
    isLoading.value = true
    try {
        const res = await agentService.getAgents(projectId)
        const agent = res.data.find(a => a.id === agentId)
        if (agent) {
            currentAgentConfig.value = agent
            designConfig.value = agent
            await fetchVersions()
        }
    } catch(e) {
        console.error(e)
        toast.error("Failed to load agent")
    } finally {
        isLoading.value = false
    }
}

const saveAgent = async () => {
  if (!currentAgentConfig.value) return
  isSaving.value = true
  try {
    await agentService.updateAgent(currentAgentConfig.value)
    await createVersion(`Auto-save ${new Date().toLocaleTimeString()}`)
    hasUnsavedChanges.value = false
    toast.success('Agent saved successfully')
  } catch (e) {
    console.error(e)
    toast.error('Failed to save')
  } finally {
    isSaving.value = false
  }
}

watch(currentAgentConfig, (val) => {
    if (val) hasUnsavedChanges.value = true
}, { deep: true })

onMounted(() => {
    loadAgent()
})
</script>

<template>
  <div class="h-full flex flex-col overflow-hidden">
    <!-- Header -->
    <div class="h-16 border-b border-base-300 bg-base-100 flex items-center justify-between px-6 shrink-0">
      <div class="flex items-center gap-4">
        <router-link to="/workspace" class="btn btn-ghost btn-sm btn-circle">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" /></svg>
        </router-link>
        <div>
          <h1 class="text-xl font-bold">{{ currentAgentConfig?.name || 'Loading Agent...' }}</h1>
          <div class="text-xs opacity-60">{{ currentAgentConfig?.type }} | {{ currentAgentConfig?.model_provider }}</div>
        </div>
      </div>
      <div>
        <button 
          class="btn btn-primary btn-sm" 
          @click="saveAgent" 
          :disabled="isSaving || !hasUnsavedChanges"
        >
          <span v-if="isSaving" class="loading loading-spinner loading-xs"></span>
          Save Changes
        </button>
      </div>
    </div>

    <!-- Content Split: Editor / Sandbox -->
    <div class="flex-1 min-h-0 relative">
       <ResizableSplitPane
         :initial-left-width="800"
         :min-left-width="400"
         :min-right-width="400"
       >
         <template #left>
            <div class="h-full overflow-y-auto p-6 bg-base-200">
              <CourseBrainEditor 
                v-model="currentAgentConfig"
                :loading="isLoading"
                :agentType="(currentAgentConfig?.type as AgentType) || AgentType.TEACHER"
              />
            </div>
         </template>
         
         <template #right>
            <div class="h-full bg-base-100 border-l border-base-300">
              <!-- Thread Chat Sandbox goes here -->
              <AgentSandbox v-if="currentAgentConfig" :agentId="currentAgentConfig.id" />
            </div>
         </template>
       </ResizableSplitPane>
    </div>
  </div>
</template>
