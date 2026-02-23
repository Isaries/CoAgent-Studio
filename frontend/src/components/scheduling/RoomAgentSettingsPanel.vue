<script setup lang="ts">
import { ref, watch, onMounted, computed } from 'vue'
import type { ScheduleConfig, TriggerConfig, RoomAgentLinkSettings } from '../../types/agent'
import { roomService } from '../../services/roomService'
import ScheduleConfigEditor from './ScheduleConfigEditor.vue'
import TriggerConfigEditor from './TriggerConfigEditor.vue'

const props = defineProps<{
  roomId: string
  agentId: string
  agentName?: string
}>()

const emit = defineEmits<{
  (e: 'saved'): void
}>()

const loading = ref(false)
const saving = ref(false)
const syncing = ref(false)
const settings = ref<RoomAgentLinkSettings | null>(null)
const error = ref('')
const successMsg = ref('')

// Editable copies
const isActive = ref(true)
const scheduleConfig = ref<ScheduleConfig | null>(null)
const triggerConfig = ref<TriggerConfig | null>(null)

const hasChanges = computed(() => {
  if (!settings.value) return false
  return (
    isActive.value !== settings.value.is_active ||
    JSON.stringify(scheduleConfig.value) !== JSON.stringify(settings.value.schedule_config) ||
    JSON.stringify(triggerConfig.value) !== JSON.stringify(settings.value.trigger_config)
  )
})

const loadSettings = async () => {
  loading.value = true
  error.value = ''
  try {
    const res = await roomService.getRoomAgentSettings(props.roomId, props.agentId)
    settings.value = res.data
    isActive.value = res.data.is_active
    scheduleConfig.value = res.data.schedule_config ? JSON.parse(JSON.stringify(res.data.schedule_config)) : null
    triggerConfig.value = res.data.trigger_config ? JSON.parse(JSON.stringify(res.data.trigger_config)) : null
  } catch (e: any) {
    if (e.response?.status === 404) {
      // No settings yet — show defaults
      settings.value = {
        room_id: props.roomId,
        agent_id: props.agentId,
        is_active: true,
      }
    } else {
      error.value = 'Failed to load settings'
    }
  } finally {
    loading.value = false
  }
}

const saveSettings = async () => {
  saving.value = true
  error.value = ''
  successMsg.value = ''
  try {
    await roomService.updateRoomAgentSettings(props.roomId, props.agentId, {
      is_active: isActive.value,
      schedule_config: scheduleConfig.value,
      trigger_config: triggerConfig.value,
    })
    successMsg.value = 'Settings saved!'
    setTimeout(() => successMsg.value = '', 3000)
    emit('saved')
    await loadSettings() // Reload
  } catch (e: any) {
    error.value = e.response?.data?.detail || 'Failed to save'
  } finally {
    saving.value = false
  }
}

const syncToCourse = async () => {
  if (!confirm('Copy these settings to ALL rooms in this course? This cannot be undone.')) return
  syncing.value = true
  error.value = ''
  try {
    const res = await roomService.syncSettingsToCourse(props.roomId, props.agentId)
    successMsg.value = res.data.message || 'Synced!'
    setTimeout(() => successMsg.value = '', 3000)
  } catch (e: any) {
    error.value = e.response?.data?.detail || 'Sync failed'
  } finally {
    syncing.value = false
  }
}

onMounted(loadSettings)

// Reload if room/agent changes
watch([() => props.roomId, () => props.agentId], loadSettings)
</script>

<template>
  <div class="flex flex-col gap-4 animate-fade-in">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-lg font-bold">
          Room Agent Settings
          <span v-if="agentName" class="text-primary"> — {{ agentName }}</span>
        </h2>
        <p class="text-xs opacity-50">Per-room scheduling and trigger overrides</p>
      </div>
      <div class="flex items-center gap-2">
        <label class="label cursor-pointer gap-2">
          <span class="label-text font-bold" :class="isActive ? 'text-primary' : 'text-error'">
            {{ isActive ? 'Active' : 'Inactive' }}
          </span>
          <input type="checkbox" class="toggle toggle-primary toggle-sm" v-model="isActive" />
        </label>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex justify-center p-8">
      <span class="loading loading-spinner loading-lg"></span>
    </div>

    <!-- Error -->
    <div v-if="error" class="alert alert-error text-sm">{{ error }}</div>
    <div v-if="successMsg" class="alert alert-success text-sm">{{ successMsg }}</div>

    <!-- Content -->
    <template v-if="!loading">
      <!-- Schedule -->
      <ScheduleConfigEditor v-model="scheduleConfig" label="Room Schedule (overrides Agent)" />

      <!-- Trigger -->
      <TriggerConfigEditor v-model="triggerConfig" label="Room Trigger (overrides Agent)" />

      <!-- Actions -->
      <div class="flex items-center justify-between">
        <button
          class="btn btn-primary btn-sm"
          :class="{ loading: saving }"
          :disabled="saving || !hasChanges"
          @click="saveSettings"
        >
          {{ saving ? 'Saving...' : 'Save Settings' }}
        </button>

        <div class="flex items-center gap-2">
          <button
            class="btn btn-outline btn-sm btn-secondary"
            :class="{ loading: syncing }"
            :disabled="syncing"
            @click="syncToCourse"
            title="Copy these settings to all rooms in the same course"
          >
            🔄 Sync to Course
          </button>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.animate-fade-in {
  animation: fadeIn 0.3s ease-in-out;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(5px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
