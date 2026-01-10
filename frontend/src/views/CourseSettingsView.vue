<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
// import api from '../api' // Removed, replaced by service
import { agentService } from '../services/agentService'
import type { AgentConfig, ScheduleConfig, TriggerConfig } from '../types/agent'
import { useAuthStore } from '../stores/auth'
import { useCourse } from '../composables/useCourse'
import { useToastStore } from '../stores/toast'
import { useConfirm } from '../composables/useConfirm'
import AgentKeyManager from '../components/AgentKeyManager.vue'

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
const editApiKey = ref('') // For Teacher/Student
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

// Schedule Config
const editScheduleConfig = ref<ScheduleConfig>({
  specific: [],
  general: { mode: 'none', rules: [] }
})
const syncSchedule = ref(false)

// Design Agent Config State
const designConfig = ref<AgentConfig | null>(null)
const designApiKey = ref('')

// Helper for Schedule Rules

// Helper for Schedule Rules
const addSpecificDate = () => {
  if (syncSchedule.value) return
  editScheduleConfig.value.specific.push({
    date: new Date().toISOString().split('T')[0] || '',
    start: '09:00',
    end: '17:00'
  })
}
const removeSpecificDate = (idx: number) => {
  if (syncSchedule.value) return
  editScheduleConfig.value.specific.splice(idx, 1)
}

const addGeneralRule = () => {
  if (syncSchedule.value) return
  const r: any = { start_time: '09:00', end_time: '17:00', days: [] }
  if (editScheduleConfig.value.general.mode === 'range_weekly') {
    r.days = [1, 3, 5] // Mon, Wed, Fri default
  }
  editScheduleConfig.value.general.rules.push(r)
}
const removeGeneralRule = (idx: number) => {
  if (syncSchedule.value) return
  editScheduleConfig.value.general.rules.splice(idx, 1)
}

// Watcher to ensure 'days' array exists when switching to Weekly mode
watch(
  () => editScheduleConfig.value.general.mode,
  (newMode) => {
    if (newMode === 'range_weekly') {
      editScheduleConfig.value.general.rules.forEach((rule: any) => {
        if (!Array.isArray(rule.days)) {
          rule.days = []
        }
      })
    }
  }
)

// Sync Schedule Logic
const activeTeacherConfig = computed(() => {
  return configs.value.find((c) => c.type === 'teacher' && c.is_active)
})

watch(syncSchedule, (newVal) => {
  if (newVal && activeTab.value === 'student' && activeTeacherConfig.value) {
    // Deep copy teacher schedule
    try {
      const teacherSch = activeTeacherConfig.value.schedule_config
      if (teacherSch) {
        editScheduleConfig.value = JSON.parse(JSON.stringify(teacherSch))
      }
    } catch (e) {
      console.error('Sync error', e)
    }
  }
})

const availableModels = computed(() => {
  if (editProvider.value === 'gemini') {
    return [
      { label: 'Gemini 1.5 Pro', value: 'gemini-1.5-pro' },
      { label: 'Gemini 1.5 Flash', value: 'gemini-1.5-flash' },
      { label: 'Gemini Pro (Legacy)', value: 'gemini-pro' }
    ]
  } else if (editProvider.value === 'openai') {
    return [
      { label: 'GPT-4o', value: 'gpt-4o' },
      { label: 'GPT-4 Turbo', value: 'gpt-4-turbo' },
      { label: 'GPT-3.5 Turbo', value: 'gpt-3.5-turbo' }
    ]
  }
  return []
})

// Design Agent
const designDb = ref({
  requirement: '',
  context: '',
  loading: false,
  refineCurrent: false
})

// ... (lines 33-149) ...
const generatePrompt = async () => {
  if (!designDb.value.requirement) return
  designDb.value.loading = true

  let req = designDb.value.requirement
  if (designDb.value.refineCurrent && editPrompt.value) {
    req += `\n\n[CONTEXT: EXISTING PROMPT TO REFINE]\n${editPrompt.value}\n[END EXISTING PROMPT]\nPlease refine this prompt based on the requirements.`
  }

  try {
    const res = await agentService.generatePrompt({
      requirement: req,
      target_agent_type: activeTab.value,
      course_context: designDb.value.context || course.value?.title || '',
      api_key: editApiKey.value, // Temporary key from main editor used? No, should be from design block
      course_id: courseId,
      provider: editProvider.value
    })
    editPrompt.value = res.data.generated_prompt
  } catch (e: any) {
    if (e.response && e.response.status === 400 && e.response.data.detail) {
      toast.error(e.response.data.detail)
    } else {
      toast.error('Generation failed')
    }
  } finally {
    designDb.value.loading = false
  }
}
const isOwner = computed(() => {
  if (!course.value || !authStore.user) return false
  return authStore.isAdmin || course.value.owner_id === authStore.user.id
})

// Filtered Configs for current tab
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
  // Owner or Creator
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
    if (designConfig.value && designConfig.value.masked_api_key) {
      // We don't populate the actual key, just signal it exists
    }

    // If no selected, select active one for current tab
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
  editApiKey.value = '' // Don't show existing key
  editProvider.value = config.model_provider || 'gemini'
  editModel.value = config.model || ''

  // Advanced
  editContextWindow.value = config.context_window || 10
  editTriggerConfig.value = config.trigger_config || { type: 'message_count', value: 10 }

  // Analytics Keys
  editAnalyticsKeys.value = { room_key: '', global_key: '', backup_key: '' }
  if (config.type === 'analytics') {
    // Fetch keys (masked)
    // We can do this async but selectConfig is sync. We should probably do it in valid way.
    // Ideally we load keys when selected.
    // Let's call the service
    agentService.getKeys(config.id).then((keys) => {
      editAnalyticsKeys.value = {
        room_key: keys.room_key || '',
        global_key: keys.global_key || '',
        backup_key: keys.backup_key || ''
      }
    })
  }

  // Settings & Schedule
  const settings = config.settings || {}
  syncSchedule.value = !!settings.sync_schedule

  if (syncSchedule.value && activeTeacherConfig.value) {
    // Force load teacher schedule if synced
    const teacherSch = activeTeacherConfig.value.schedule_config
    editScheduleConfig.value = teacherSch
      ? JSON.parse(JSON.stringify(teacherSch))
      : { specific: [], general: { mode: 'none', rules: [] } }
  } else {
    // Parse Schedule to new format if needed, or take as is
    if (config.schedule_config && Array.isArray(config.schedule_config.specific)) {
      editScheduleConfig.value = config.schedule_config
      // Ensure legacy general has rules array if missing (migration)
      if (!editScheduleConfig.value.general.rules) {
        editScheduleConfig.value.general.rules = []
      }
    } else {
      // Fallback: Migrate old format or Reset
      editScheduleConfig.value = { specific: [], general: { mode: 'none', rules: [] } }
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

  // Advanced Reset
  editContextWindow.value = 10
  editTriggerConfig.value = { type: 'message_count', value: 10 }

  // Default sync to true for new student if teacher exists?
  // Proposal said "Default Checked".
  if (activeTab.value === 'student' && activeTeacherConfig.value) {
    syncSchedule.value = true
    // Copy immediately
    const teacherSch = activeTeacherConfig.value.schedule_config
    editScheduleConfig.value = teacherSch
      ? JSON.parse(JSON.stringify(teacherSch))
      : { specific: [], general: { mode: 'none', rules: [] } }
  } else {
    syncSchedule.value = false
    editScheduleConfig.value = { specific: [], general: { mode: 'none', rules: [] } }
  }

  // Reset Design Agent
  designDb.value = {
    requirement: '',
    context: '',
    loading: false,
    refineCurrent: false
  }
}

const saveConfig = async () => {
  if (!editName.value) return toast.warning('Name is required')

  // Ensure schedule is fresh from teacher if synced
  if (syncSchedule.value && activeTab.value === 'student' && activeTeacherConfig.value) {
    const teacherSch = activeTeacherConfig.value.schedule_config
    if (teacherSch) editScheduleConfig.value = JSON.parse(JSON.stringify(teacherSch))
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
    schedule_config: editScheduleConfig.value,
    context_window: editContextWindow.value
  }

  if (editApiKey.value === 'CLEAR_KEY') {
    payload.api_key = '' // Send empty string to backend to trigger deletion
  } else if (editApiKey.value) {
    payload.api_key = editApiKey.value
  } else {
    payload.api_key = null // Send null to tell backend "Keep Existing"
  }

  try {
    if (selectedConfigId.value) {
      // Update
      await agentService.updateAgent(selectedConfigId.value, payload)
    } else {
      // Create
      const res = await agentService.createAgent(courseId, payload)
      selectedConfigId.value = res.data.id
    }

    // Save Analytics Keys if applicable

    if (activeTab.value === 'analytics' && selectedConfigId.value) {
      const keysToSend: any = {}
      const kMap = editAnalyticsKeys.value as any

      for (const k of ['room_key', 'global_key', 'backup_key']) {
        const val = kMap[k]
        if (val && !val.includes('****')) {
          // New value entered
          keysToSend[k] = val
        } else if (val === '') {
          // Explicitly empty (cleared or never set) -> Send empty to ensure it's removed/cleared in backend
          keysToSend[k] = ''
        }
        // If valid mask (****), ignore (don't send, so backend keeps existing)
      }

      if (Object.keys(keysToSend).length > 0) {
        await agentService.updateKeys(selectedConfigId.value, keysToSend)
      }

      // Always refresh keys to get updated state (masked values)
      if (course.value?.id) {
        const refreshedKeys = await agentService.getKeys(selectedConfigId.value)
        editAnalyticsKeys.value = {
          room_key: refreshedKeys.room_key || '',
          global_key: refreshedKeys.global_key || '',
          backup_key: refreshedKeys.backup_key || ''
        }
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
  editApiKey.value = '' // Reset to empty to show placeholder or clean state
}

const saveDesignAgentKey = async () => {
  if (!designApiKey.value && designApiKey.value !== 'CLEAR_KEY') return

  const payload: any = {
    name: 'Design Agent Config',
    type: 'design',
    system_prompt: 'System Design Agent', // Placeholder, not used but required by schema
    model_provider: 'gemini', // Default or make configurable?
    api_key: designApiKey.value === 'CLEAR_KEY' ? '' : designApiKey.value
  }

  try {
    if (designConfig.value) {
      await agentService.updateAgent(designConfig.value.id, payload)
    } else {
      await agentService.createAgent(courseId, payload)
    }
    toast.success('Design Agent Key Saved for this Course')
    designApiKey.value = ''
    await fetchConfigs()
  } catch (e) {
    console.error(e)
    toast.error('Failed to save Design Agent Key')
  }
}

const handleClearDesignKey = async () => {
  if (!(await confirm('Clear Key', 'Remove stored Design Agent Key?'))) return
  designApiKey.value = 'CLEAR_KEY'
  await saveDesignAgentKey()
}

// Watchers
watch(activeTab, () => {
  startNewConfig()
  // Try to find active in new tab
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
      <!-- Sidebar: Profiles List -->
      <div class="w-80 bg-base-200 border-r overflow-y-auto p-4 flex flex-col gap-2">
        <div class="flex justify-between items-center mb-2">
          <h3 class="font-bold text-gray-500 text-sm">PROFILES</h3>
          <button @click="startNewConfig" class="btn btn-xs btn-outline btn-primary">+ New</button>
        </div>

        <div
          v-for="conf in currentConfigs"
          :key="conf.id"
          @click="selectConfig(conf)"
          class="card bg-base-100 shadow-sm border cursor-pointer hover:border-primary transition-all"
          :class="{ 'border-primary ring-1 ring-primary': selectedConfigId === conf.id }"
        >
          <div class="card-body p-3">
            <div class="flex justify-between items-start">
              <div class="font-bold truncate pr-2">{{ conf.name }}</div>
              <div v-if="conf.is_active" class="badge badge-success badge-xs">ACTIVE</div>
            </div>
            <div class="text-xs text-gray-400 mt-1">
              Updated: {{ new Date(conf.updated_at).toLocaleDateString() }}
            </div>
            <div class="text-xs text-gray-400">
              By: {{ conf.created_by === authStore.user?.id ? 'Me' : 'Others' }}
            </div>
          </div>
        </div>

        <div v-if="currentConfigs.length === 0" class="text-center text-gray-400 text-sm py-8">
          No profiles yet. Create one!
        </div>
      </div>

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
          <div
            v-if="canEdit"
            class="collapse collapse-arrow bg-base-200 mb-6 border border-base-300"
          >
            <input type="checkbox" />
            <div class="collapse-title font-medium flex items-center gap-2">
              <span>✨ AI Prompt Designer</span>
            </div>
            <div class="collapse-content">
              <div class="p-2">
                <p class="mb-2 text-sm text-gray-600">
                  Describe the persona and behavior you want.
                </p>

                <!-- Design Agent API Key Block -->
                <div class="form-control mb-4 p-3 bg-base-100 rounded border border-base-200">
                  <label class="label pt-0"
                    ><span class="label-text font-bold text-xs"
                      >Design Agent API Key (for this course)</span
                    ></label
                  >
                  <div class="join w-full">
                    <input
                      type="password"
                      v-model="designApiKey"
                      :placeholder="
                        designConfig?.masked_api_key
                          ? `Using: ${designConfig.masked_api_key}`
                          : 'Enter API Key for Generator...'
                      "
                      class="input input-sm input-bordered join-item w-full"
                    />
                    <button
                      @click="saveDesignAgentKey"
                      class="btn btn-sm btn-primary join-item"
                      :disabled="!designApiKey"
                    >
                      Save Key
                    </button>
                    <button
                      v-if="designConfig?.masked_api_key"
                      @click="handleClearDesignKey"
                      class="btn btn-sm btn-ghost join-item text-error"
                    >
                      Clear
                    </button>
                  </div>
                  <div class="text-[10px] text-gray-400 mt-1">
                    If set, this key will be used for auto-generation for this course.
                  </div>
                </div>

                <textarea
                  v-model="designDb.requirement"
                  class="textarea textarea-bordered w-full mb-2"
                  placeholder="e.g. A friendly tutor who explains concepts using pizza analogies..."
                ></textarea>
                <input
                  v-model="designDb.context"
                  type="text"
                  placeholder="Context (e.g. Intro to Python)"
                  class="input input-bordered w-full mb-2"
                />

                <div class="form-control mb-2">
                  <label class="label cursor-pointer justify-start gap-4">
                    <input
                      type="checkbox"
                      v-model="designDb.refineCurrent"
                      class="checkbox checkbox-sm"
                      :disabled="!editPrompt"
                    />
                    <span class="label-text"
                      >Refine based on current prompt (Pass current version to Design Agent)</span
                    >
                  </label>
                </div>

                <button
                  @click="generatePrompt"
                  class="btn btn-secondary btn-sm w-full"
                  :disabled="designDb.loading"
                >
                  {{ designDb.loading ? 'Generating...' : 'Auto-Generate Prompt' }}
                </button>
              </div>
            </div>
          </div>

          <!-- Advanced Settings -->
          <div
            v-if="canEdit"
            class="collapse collapse-arrow bg-base-200 mb-6 border border-base-300"
          >
            <input type="checkbox" />
            <div class="collapse-title font-medium flex items-center gap-2">
              <span>⚙️ Advanced: Triggers & Schedule</span>
            </div>
            <div class="collapse-content">
              <div class="p-2 space-y-4">
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
                    />
                  </div>
                </div>

                <div class="divider my-1"></div>

                <!-- Context Window -->
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
                    />
                  </div>
                </div>

                <div class="divider my-1"></div>

                <!-- Schedule -->
                <div>
                  <div class="flex justify-between items-center mb-2">
                    <h4 class="font-bold text-sm">Availability Schedule (UTC+8)</h4>

                    <!-- Sync Checkbox (Student Only) -->
                    <div v-if="activeTab === 'student'" class="form-control">
                      <label class="label cursor-pointer gap-2 py-0">
                        <span class="label-text text-xs font-bold text-primary"
                          >Use Teacher's Schedule</span
                        >
                        <input
                          type="checkbox"
                          v-model="syncSchedule"
                          class="checkbox checkbox-xs checkbox-primary"
                        />
                      </label>
                    </div>
                  </div>

                  <div :class="{ 'opacity-50 pointer-events-none': syncSchedule }">
                    <div v-if="syncSchedule" class="text-xs text-info mb-2 flex items-center gap-1">
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        width="12"
                        height="12"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      >
                        <path
                          d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"
                        ></path>
                        <path
                          d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"
                        ></path>
                      </svg>
                      Linked to Teacher's schedule. Uncheck to customize.
                    </div>

                    <!-- 1. Specific Exceptions -->
                    <div class="mb-4 border rounded-md p-3 bg-base-100">
                      <div class="flex justify-between items-center mb-2">
                        <span class="text-sm font-bold"
                          >1. Specific Date Exceptions (Highest Priority)</span
                        >
                        <button
                          @click="addSpecificDate"
                          class="btn btn-xs btn-outline btn-primary"
                          :disabled="syncSchedule"
                        >
                          + Add Exception
                        </button>
                      </div>
                      <div
                        v-if="editScheduleConfig.specific.length === 0"
                        class="text-xs text-gray-400 italic mb-2"
                      >
                        No specific exceptions defined.
                      </div>
                      <div
                        v-for="(rule, idx) in editScheduleConfig.specific"
                        :key="idx"
                        class="flex items-center gap-2 mb-2 last:mb-0"
                      >
                        <input
                          type="date"
                          v-model="rule.date"
                          class="input input-xs input-bordered"
                          :disabled="syncSchedule"
                        />
                        <input
                          type="time"
                          v-model="rule.start"
                          class="input input-xs input-bordered"
                          :disabled="syncSchedule"
                        />
                        <span class="text-xs">-</span>
                        <input
                          type="time"
                          v-model="rule.end"
                          class="input input-xs input-bordered"
                          :disabled="syncSchedule"
                        />
                        <button
                          @click="removeSpecificDate(idx)"
                          class="btn btn-xs btn-ghost text-error"
                          :disabled="syncSchedule"
                        >
                          ✕
                        </button>
                      </div>
                    </div>

                    <!-- 2. General Pattern -->
                    <div class="border rounded-md p-3 bg-base-100">
                      <span class="text-sm font-bold block mb-2">2. General Schedule Pattern</span>
                      <select
                        v-model="editScheduleConfig.general.mode"
                        class="select select-sm select-bordered w-full mb-2"
                        :disabled="syncSchedule"
                      >
                        <option value="none">Always Active (unless restricted by Schedule)</option>
                        <option value="range_daily">Date Range (Daily Time Period)</option>
                        <option value="range_weekly">Date Range (Weekly Pattern)</option>
                      </select>

                      <div v-if="editScheduleConfig.general.mode !== 'none'" class="mt-2 space-y-2">
                        <!-- Global Date Range -->
                        <div class="grid grid-cols-2 gap-2 p-2 bg-base-200 rounded">
                          <div class="form-control">
                            <label class="label-text text-xs font-bold">Effective From</label>
                            <input
                              type="date"
                              v-model="editScheduleConfig.general.start_date"
                              class="input input-xs input-bordered"
                              :disabled="syncSchedule"
                            />
                          </div>
                          <div class="form-control">
                            <label class="label-text text-xs font-bold">Effective To</label>
                            <input
                              type="date"
                              v-model="editScheduleConfig.general.end_date"
                              class="input input-xs input-bordered"
                              :disabled="syncSchedule"
                            />
                          </div>
                        </div>

                        <!-- Time Rules List -->
                        <div>
                          <label class="label-text text-xs font-bold mb-1 block">Time Rules</label>
                          <div
                            v-for="(rule, rIdx) in editScheduleConfig.general.rules"
                            :key="rIdx"
                            class="border p-2 rounded mb-2 relative"
                          >
                            <button
                              @click="removeGeneralRule(rIdx)"
                              class="btn btn-xs btn-circle btn-ghost absolute right-1 top-1 text-error"
                              :disabled="syncSchedule"
                            >
                              ✕
                            </button>

                            <div class="grid grid-cols-2 gap-2 mb-1">
                              <div class="form-control">
                                <label class="label-text text-[10px]">Start Time</label>
                                <input
                                  type="time"
                                  v-model="rule.start_time"
                                  class="input input-xs input-bordered"
                                  :disabled="syncSchedule"
                                />
                              </div>
                              <div class="form-control">
                                <label class="label-text text-[10px]">End Time</label>
                                <input
                                  type="time"
                                  v-model="rule.end_time"
                                  class="input input-xs input-bordered"
                                  :disabled="syncSchedule"
                                />
                              </div>
                            </div>

                            <!-- Weekly Days -->
                            <div
                              v-if="editScheduleConfig.general.mode === 'range_weekly'"
                              class="flex gap-1 flex-wrap pt-1 border-t mt-1"
                            >
                              <label
                                v-for="(d, i) in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']"
                                :key="d"
                                class="cursor-pointer label p-0 gap-1 border rounded px-1 hover:bg-base-200"
                              >
                                <span class="label-text text-[10px]">{{ d }}</span>
                                <input
                                  type="checkbox"
                                  :value="i"
                                  v-model="rule.days"
                                  class="checkbox checkbox-xs"
                                  :disabled="syncSchedule"
                                />
                              </label>
                            </div>
                          </div>
                          <div
                            v-if="editScheduleConfig.general.rules.length === 0"
                            class="text-xs text-error italic mb-2"
                          >
                            ⚠️ No time rules added. Agent will NOT be active.
                          </div>
                          <button
                            @click="addGeneralRule"
                            class="btn btn-xs btn-outline w-full text-xs"
                            :disabled="syncSchedule"
                          >
                            + Add Time Rule
                          </button>
                        </div>
                      </div>
                      <div v-else class="text-xs text-gray-400 italic">
                        Agent is active 24/7 (except during Specific Exceptions if set).
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

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
