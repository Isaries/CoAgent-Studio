<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { agentService } from '../services/agentService'
import type { AgentConfig, TriggerConfig } from '../types/agent'
import { useAuthStore } from '../stores/auth'
import { useCourse } from '../composables/useCourse'
import { AI_MODELS } from '../constants/ai-models'
import { useToastStore } from '../stores/toast'
import { useConfirm } from '../composables/useConfirm'

// Components
import AgentKeyManager from '../components/AgentKeyManager.vue'
import CourseProfileManager from './course-settings/CourseProfileManager.vue'
import CourseScheduleSettings from './course-settings/CourseScheduleSettings.vue'
import DesignAgentConfig from './course-settings/DesignAgentConfig.vue'

// Composables
import { useScheduleConfig } from '../composables/useScheduleConfig'
import { useDesignAgent } from '../composables/useDesignAgent'

const route = useRoute()
const authStore = useAuthStore()
const toast = useToastStore()
const { confirm } = useConfirm()
const courseId = route.params.id as string

const { course, fetchCourseData } = useCourse(courseId)

// State
const activeTab = ref<'teacher' | 'student' | 'analytics'>('teacher')
const configs = ref<AgentConfig[]>([])
const selectedConfigId = ref<string | null>(null)
const loading = ref(false)

// Editor State
const editName = ref('')
const editPrompt = ref('')
const editApiKey = ref('')
const editProvider = ref('gemini')
const editModel = ref('')

// Analytics Specific
const editAnalyticsKeys = ref({
  room_key: '',
  global_key: '',
  backup_key: ''
})

// Advanced State
const editContextWindow = ref(10)
const editTriggerConfig = ref<TriggerConfig>({ type: 'message_count', value: 10 })

// Computed properties for logic
const activeTeacherConfig = computed(() => {
  return configs.value.find((c) => c.type === 'teacher' && c.is_active)
})

const courseTitle = computed(() => course.value?.title || '') // Helper

// Composables
const {
  scheduleConfig,
  syncSchedule,
  addSpecificDate,
  removeSpecificDate,
  addGeneralRule,
  removeGeneralRule
} = useScheduleConfig(activeTab as any, activeTeacherConfig) // Cast activeTab if needed

const {
  designConfig,
  designApiKey,
  designDb,
  generatePrompt: execGeneratePrompt,
  saveDesignAgentKey,
  handleClearDesignKey: execClearDesignKey
} = useDesignAgent(courseId, courseTitle, activeTab as any)

// Logic
const availableModels = computed(() => {
  if (editProvider.value === 'gemini') {
    return AI_MODELS.gemini
  } else if (editProvider.value === 'openai') {
    return AI_MODELS.openai
  }
  return []
})

// Design Agent Wrappers
const handleGeneratePrompt = async () => {
  const res = await execGeneratePrompt(editPrompt.value, editProvider.value)
  if (res) editPrompt.value = res
}

const handleClearDesignKey = async () => {
  await execClearDesignKey(
    () => confirm('Clear Key', 'Remove stored Design Agent Key?'),
    fetchConfigs
  )
}

const handleSaveDesignKey = async () => {
  await saveDesignAgentKey(fetchConfigs)
}

// Permissions
const isOwner = computed(() => {
  if (!course.value || !authStore.user) return false
  return authStore.isAdmin || course.value.owner_id === authStore.user.id
})

// Filtered Configs
const currentConfigs = computed(() => {
  return configs.value
    .filter((c: any) => c.type === activeTab.value && c.type !== 'design')
    .sort(
      (a, b) =>
        (b.is_active ? 1 : 0) - (a.is_active ? 1 : 0) ||
        new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
    )
})

const selectedConfig = computed(() => {
  return configs.value.find((c) => c.id === selectedConfigId.value)
})

const canEdit = computed(() => {
  if (!selectedConfig.value) return true // Creating new
  if (isOwner.value) return true
  return selectedConfig.value.created_by === authStore.user?.id
})

// Actions
const fetchConfigs = async () => {
  loading.value = true
  try {
    const res = await agentService.getAgents(courseId)
    configs.value = res.data

    // Extract Design Config
    designConfig.value = configs.value.find((c: any) => c.type === 'design') || null

    if (!selectedConfigId.value) {
      const active = currentConfigs.value.find((c) => c.is_active)
      if (active) selectConfig(active)
      else if (currentConfigs.value.length > 0) selectConfig(currentConfigs.value[0])
      else startNewConfig()
    }
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const selectConfig = (config: any) => {
  selectedConfigId.value = config.id
  editName.value = config.name
  editPrompt.value = config.system_prompt
  editApiKey.value = ''
  editProvider.value = config.model_provider || 'gemini'
  editModel.value = config.model || ''
  editContextWindow.value = config.context_window || 10
  editTriggerConfig.value = config.trigger_config || { type: 'message_count', value: 10 }

  // Analytics Keys
  editAnalyticsKeys.value = { room_key: '', global_key: '', backup_key: '' }
  if (config.type === 'analytics') {
    agentService.getKeys(config.id).then((keys) => {
      editAnalyticsKeys.value = {
        room_key: keys.room_key || '',
        global_key: keys.global_key || '',
        backup_key: keys.backup_key || ''
      }
    })
  }

  // Schedule Sync
  const settings = config.settings || {}
  syncSchedule.value = !!settings.sync_schedule

  if (syncSchedule.value && activeTeacherConfig.value) {
    const teacherSch = activeTeacherConfig.value.schedule_config
    scheduleConfig.value = teacherSch
      ? JSON.parse(JSON.stringify(teacherSch))
      : { specific: [], general: { mode: 'none', rules: [] } }
  } else {
    if (config.schedule_config && Array.isArray(config.schedule_config.specific)) {
      scheduleConfig.value = config.schedule_config
      if (!scheduleConfig.value.general.rules) {
        scheduleConfig.value.general.rules = []
      }
    } else {
      scheduleConfig.value = { specific: [], general: { mode: 'none', rules: [] } }
    }
  }
}

const startNewConfig = () => {
  selectedConfigId.value = null
  let defaultName = 'New Brain'
  if (activeTab.value === 'teacher') defaultName = 'New Teacher Brain'
  else if (activeTab.value === 'student') defaultName = 'New Student Brain'
  else if (activeTab.value === 'analytics') defaultName = 'New Analytics Brain'

  editName.value = defaultName
  editPrompt.value = ''
  editApiKey.value = ''
  editAnalyticsKeys.value = { room_key: '', global_key: '', backup_key: '' }
  editProvider.value = 'gemini'
  editModel.value = ''
  editContextWindow.value = 10
  editTriggerConfig.value = { type: 'message_count', value: 10 }

  // Design Agent Reset
  designDb.value.requirement = ''
  designDb.value.context = ''

  if (activeTab.value === 'student' && activeTeacherConfig.value) {
    syncSchedule.value = true
    const teacherSch = activeTeacherConfig.value.schedule_config
    scheduleConfig.value = teacherSch
      ? JSON.parse(JSON.stringify(teacherSch))
      : { specific: [], general: { mode: 'none', rules: [] } }
  } else {
    syncSchedule.value = false
    scheduleConfig.value = { specific: [], general: { mode: 'none', rules: [] } }
  }
}

const saveConfig = async () => {
  if (!editName.value) return toast.warning('Name is required')

  if (syncSchedule.value && activeTab.value === 'student' && activeTeacherConfig.value) {
    const teacherSch = activeTeacherConfig.value.schedule_config
    if (teacherSch) scheduleConfig.value = JSON.parse(JSON.stringify(teacherSch))
  }

  const payload: any = {
    name: editName.value,
    system_prompt: editPrompt.value,
    model_provider: editProvider.value,
    model: editModel.value,
    type: activeTab.value,
    settings: {
      ...((selectedConfig.value as any)?.settings || {}),
      sync_schedule: syncSchedule.value
    },
    trigger_config: editTriggerConfig.value,
    schedule_config: scheduleConfig.value,
    context_window: editContextWindow.value
  }

  if (editApiKey.value === 'CLEAR_KEY') {
    payload.api_key = ''
  } else if (editApiKey.value) {
    payload.api_key = editApiKey.value
  } else {
    payload.api_key = null
  }

  try {
    if (selectedConfigId.value) {
      await agentService.updateAgent(selectedConfigId.value, payload)
    } else {
      const res = await agentService.createAgent(courseId, payload)
      selectedConfigId.value = res.data.id
    }

    // Analytics Keys Logic
    if (activeTab.value === 'analytics' && selectedConfigId.value) {
      const keysToSend: any = {}
      const kMap = editAnalyticsKeys.value as any
      for (const k of ['room_key', 'global_key', 'backup_key']) {
        const val = kMap[k]
        if (val && !val.includes('****')) {
          keysToSend[k] = val
        } else if (val === '') {
          keysToSend[k] = ''
        }
      }
      if (Object.keys(keysToSend).length > 0) {
        await agentService.updateKeys(selectedConfigId.value, keysToSend)
      }
      if (course.value?.id) {
        const refreshedKeys = await agentService.getKeys(selectedConfigId.value)
        editAnalyticsKeys.value = { ...editAnalyticsKeys.value, ...refreshedKeys }
      }
    }

    await fetchConfigs()
    toast.success('Saved!')
  } catch (e: any) {
    toast.error(e.response?.data?.detail || 'Failed to save')
  }
}

const activateConfig = async (id: string) => {
  try {
    await agentService.activateAgent(id)
    await fetchConfigs()
    toast.success('Brain activated')
  } catch (e: any) {
    toast.error(e.response?.data?.detail || 'Failed to activate')
  }
}

const deleteConfig = async (id: string) => {
  if (!(await confirm('Delete Brain', 'Are you sure you want to delete this brain profile?')))
    return
  try {
    await agentService.deleteAgent(id)
    if (selectedConfigId.value === id) selectedConfigId.value = null
    await fetchConfigs()
    toast.success('Brain deleted')
  } catch (e: any) {
    toast.error(e.response?.data?.detail || 'Failed to delete')
  }
}

const handleClearApiKey = async () => {
  if (!(await confirm('Clear API Key', 'Are you sure? This will remove the key immediately.')))
    return
  editApiKey.value = 'CLEAR_KEY'
  await saveConfig()
  editApiKey.value = ''
}

// Watchers
watch(activeTab, () => {
  startNewConfig()
  const active = currentConfigs.value.find((c) => c.is_active)
  if (active) selectConfig(active)
  else if (currentConfigs.value.length > 0) selectConfig(currentConfigs.value[0])
})

onMounted(async () => {
  await fetchCourseData()
  await fetchConfigs()
})
</script>

<template>
  <div class="h-[calc(100vh-64px)] flex flex-col">
    <!-- Header -->
    <div class="bg-base-100 border-b p-4 flex justify-between items-center shadow-sm z-10">
      <div class="flex items-center gap-4">
        <h1 class="text-xl font-bold">Brain Management</h1>
        <div class="tabs tabs-boxed">
          <a
            class="tab"
            :class="{ 'tab-active': activeTab === 'teacher' }"
            @click="activeTab = 'teacher'"
            >Teacher</a
          >
          <a
            class="tab"
            :class="{ 'tab-active': activeTab === 'student' }"
            @click="activeTab = 'student'"
            >Student</a
          >
          <a
            class="tab"
            :class="{ 'tab-active': activeTab === 'analytics' }"
            @click="activeTab = 'analytics'"
            >Analytics</a
          >
        </div>
      </div>
      <router-link :to="`/courses/${courseId}`" class="btn btn-sm btn-ghost"
        >Back to Course</router-link
      >
    </div>

    <div class="flex-1 flex overflow-hidden">
      <!-- Sidebar -->
      <CourseProfileManager
        :configs="currentConfigs"
        :selectedConfigId="selectedConfigId"
        :currentUser="authStore.user"
        @select="selectConfig"
        @new="startNewConfig"
      />

      <!-- Main: Editor -->
      <div class="flex-1 overflow-y-auto p-8 bg-base-100">
        <div class="max-w-4xl mx-auto">
          <!-- Toolbar -->
          <div class="flex justify-between items-center mb-6">
            <div class="flex items-center gap-2">
              <div
                v-if="selectedConfigId && selectedConfig?.is_active"
                class="badge badge-success badge-lg gap-2"
              >
                <!-- Icon -->
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
                Current Active Brain
              </div>
              <div
                v-else-if="selectedConfigId && isOwner"
                class="tooltip"
                data-tip="Only Owner can activate"
              >
                <button @click="activateConfig(selectedConfigId!)" class="btn btn-sm btn-outline">
                  Set as Active
                </button>
              </div>
              <span v-else-if="selectedConfigId" class="badge badge-ghost">Inactive Profile</span>
              <span v-else class="badge badge-info">Creating New Profile</span>
            </div>

            <div class="flex gap-2" v-if="canEdit || selectedConfigId">
              <button
                v-if="
                  selectedConfigId && (isOwner || selectedConfig?.created_by === authStore.user?.id)
                "
                @click="deleteConfig(selectedConfigId)"
                class="btn btn-sm btn-ghost text-error"
              >
                Delete
              </button>
              <button v-if="canEdit" @click="saveConfig" class="btn btn-primary btn-sm">
                Save Changes
              </button>
            </div>
          </div>

          <!-- Editor Form -->
          <div class="form-control mb-4">
            <label class="label"><span class="label-text">Profile Name</span></label>
            <input
              type="text"
              v-model="editName"
              :disabled="!canEdit"
              class="input input-bordered text-lg font-bold"
            />
          </div>

          <!-- API Keys Section -->
          <AgentKeyManager
            :agent-type="activeTab"
            :can-edit="canEdit"
            v-model:simple-key="editApiKey"
            v-model:analytics-keys="editAnalyticsKeys"
            :masked-simple-key="selectedConfig?.masked_api_key"
            @clear-simple-key="handleClearApiKey"
          />

          <div class="grid grid-cols-2 gap-4 mb-6">
            <div class="form-control">
              <label class="label"><span class="label-text">Provider</span></label>
              <select
                v-model="editProvider"
                :disabled="!canEdit"
                class="select select-bordered w-full"
              >
                <option value="gemini">Google Gemini</option>
                <option value="openai">OpenAI GPT</option>
              </select>
            </div>
            <div class="form-control">
              <label class="label"><span class="label-text">Model Version</span></label>
              <select
                v-model="editModel"
                :disabled="!canEdit"
                class="select select-bordered w-full"
              >
                <option value="" disabled selected>Default (Auto)</option>
                <option v-for="m in availableModels" :key="m.value" :value="m.value">
                  {{ m.label }}
                </option>
              </select>
            </div>
          </div>

          <!-- Design Agent -->
          <DesignAgentConfig
            :can-edit="canEdit"
            :edit-prompt="editPrompt"
            :design-config="designConfig"
            :loading="designDb.loading"
            v-model:design-api-key="designApiKey"
            v-model:requirement="designDb.requirement"
            v-model:context="designDb.context"
            v-model:refine-current="designDb.refineCurrent"
            @save-key="handleSaveDesignKey"
            @clear-key="handleClearDesignKey"
            @generate="handleGeneratePrompt"
          />

          <!-- Advanced Settings & Schedule -->
          <CourseScheduleSettings
            v-model:schedule-config="scheduleConfig"
            :active-tab="activeTab"
            :can-edit="canEdit"
            v-model:sync-schedule="syncSchedule"
            @add-specific="addSpecificDate"
            @remove-specific="removeSpecificDate"
            @add-general="addGeneralRule"
            @remove-general="removeGeneralRule"
          >
            <template #triggers>
              <!-- Trigger Logic -->
              <div>
                <h4 class="font-bold text-sm mb-2">Trigger Logic</h4>
                <div class="flex flex-col gap-2">
                  <label class="label cursor-pointer justify-start gap-4">
                    <input
                      type="radio"
                      v-model="editTriggerConfig.type"
                      value="message_count"
                      class="radio radio-sm"
                      :disabled="!canEdit"
                    />
                    <span class="label-text"
                      >Every <strong>N</strong> messages (excluding agents)</span
                    >
                  </label>
                  <label class="label cursor-pointer justify-start gap-4">
                    <input
                      type="radio"
                      v-model="editTriggerConfig.type"
                      value="time_interval"
                      class="radio radio-sm"
                      :disabled="!canEdit"
                    />
                    <span class="label-text">Every <strong>T</strong> seconds</span>
                  </label>
                  <label
                    v-if="activeTab === 'student'"
                    class="label cursor-pointer justify-start gap-4"
                  >
                    <input
                      type="radio"
                      v-model="editTriggerConfig.type"
                      value="silence"
                      class="radio radio-sm"
                      :disabled="!canEdit"
                    />
                    <span class="label-text">Silence > <strong>T</strong> seconds</span>
                  </label>
                </div>
                <div class="mt-2 flex items-center gap-2">
                  <span class="text-sm">Value (N or T):</span>
                  <input
                    type="number"
                    v-model="editTriggerConfig.value"
                    class="input input-sm input-bordered w-24"
                    min="1"
                    :disabled="!canEdit"
                  />
                </div>
              </div>
            </template>
            <template #contextWindow>
              <div>
                <h4 class="font-bold text-sm mb-2">Context Window</h4>
                <div class="flex items-center gap-2">
                  <span class="text-sm">Previous messages to read:</span>
                  <input
                    type="number"
                    v-model="editContextWindow"
                    class="input input-sm input-bordered w-24"
                    min="1"
                    max="50"
                    :disabled="!canEdit"
                  />
                </div>
              </div>
            </template>
          </CourseScheduleSettings>

          <div class="form-control flex-1">
            <label class="label">
              <span class="label-text">System Prompt</span>
              <span v-if="!canEdit" class="label-text-alt text-error">Read Only</span>
            </label>
            <textarea
              v-model="editPrompt"
              :disabled="!canEdit"
              class="textarea textarea-bordered h-[500px] font-mono text-sm leading-relaxed"
              placeholder="System prompt goes here..."
            ></textarea>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
