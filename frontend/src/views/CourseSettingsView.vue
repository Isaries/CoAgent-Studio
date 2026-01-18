<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { AgentType } from '../types/enums'
import { useDesignAgent } from '../composables/useDesignAgent'
import { useToastStore } from '../stores/toast'
import type { AgentConfig } from '../types/agent'

// Components
// Components
import CourseBrainHeader from './course-settings/components/CourseBrainHeader.vue'
import CourseBrainEditor from './course-settings/components/CourseBrainEditor.vue'
import ResizableSplitPane from '../components/common/ResizableSplitPane.vue'
import VersionSidebar from '../components/PromptDesigner/VersionSidebar.vue'

const route = useRoute()
const courseId = route.params.id as string
const toast = useToastStore()

// State
const activeTab = ref<AgentType>(AgentType.TEACHER)
const showHistory = ref(false)
const hasUnsavedChanges = ref(false) // Simple tracking
const lastSavedAt = ref<string | null>(null)

// Composable
const {
  designConfig, // This will hold the CURRENT agent config being edited
  fetchVersions,
  versions,
  restoreVersion,
  createVersion
} = useDesignAgent('course', courseId) // Initialize with course context

// Helper: which agent are we editing?
// useDesignAgent typically manages ONE agent at a time designated by 'type' or just generic config.
// Since we have multiple agents (Teacher, Student, Analytics) for one course,
// we need to fetch the specific agent when tab changes.

import { agentService } from '../services/agentService'

const currentAgentConfig = ref<AgentConfig | null>(null)
const isLoading = ref(false)
const isSaving = ref(false)

const loadAgent = async (type: AgentType) => {
  isLoading.value = true
  try {
    // Fetch specifically for this course and type
    const res = await agentService.getAgents(courseId)
    const agent = res.data.find((a: any) => a.type === type)
    
    if (agent) {
      currentAgentConfig.value = agent
      // Sync with useDesignAgent for versioning support
      designConfig.value = agent 
      await fetchVersions() 
    } else {
      currentAgentConfig.value = null
      // Create stub?
    }
  } catch (e) {
    console.error(e)
    toast.error('Failed to load agent')
  } finally {
    isLoading.value = false
  }
}

const saveAgent = async () => {
  if (!currentAgentConfig.value) return
  isSaving.value = true
  try {
    await agentService.updateAgent(currentAgentConfig.value)
    // Create a version checkpoint automatically?
    // Or let user do it?
    // Let's auto-create version on save for safety
    await createVersion(`Auto-save ${new Date().toLocaleTimeString()}`)
    
    lastSavedAt.value = new Date().toISOString()
    hasUnsavedChanges.value = false
    toast.success('Agent saved successfully')
  } catch (e) {
    console.error(e)
    toast.error('Failed to save')
  } finally {
    isSaving.value = false
  }
}

// Watchers
watch(activeTab, (newTab) => {
  loadAgent(newTab)
})

watch(currentAgentConfig, (val) => {
    if (val) hasUnsavedChanges.value = true
}, { deep: true })


onMounted(() => {
  loadAgent(activeTab.value)
})
</script>

<template>
  <div class="h-full flex flex-col p-6 overflow-hidden">
    <CourseBrainHeader 
      v-model:activeTab="activeTab"
      :isSaving="isSaving"
      :hasUnsavedChanges="hasUnsavedChanges"
      :lastSavedAt="lastSavedAt"
      :showHistory="showHistory"
      @save="saveAgent"
      @toggleHistory="showHistory = !showHistory"
    />

    <div class="flex-1 min-h-0 relative">
       <ResizableSplitPane
         :initial-left-width="800"
         :min-left-width="400"
         :min-right-width="300"
       >
         <template #left>
            <div class="h-full overflow-y-auto pr-4">
              <CourseBrainEditor 
                v-model="currentAgentConfig"
                :loading="isLoading"
                :agentType="activeTab"
              />
            </div>
         </template>
         
         <template #right>
           <div v-if="showHistory" class="h-full border-l border-base-300 pl-4 bg-base-100">
             <VersionSidebar
                :versions="versions"
                :loading="isLoading" 
                @restore="restoreVersion"
                @create="createVersion"
                @close="showHistory = false"
             />
           </div>
           <div v-else class="h-full flex items-center justify-center text-base-content/30 bg-base-200/30">
              <span class="text-sm">History Hidden</span>
           </div>
         </template>
       </ResizableSplitPane>
    </div>
  </div>
</template>
