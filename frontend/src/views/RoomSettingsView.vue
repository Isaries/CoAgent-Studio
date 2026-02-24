<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api'
import { roomService } from '../services/roomService'
import { workspaceService } from '../services/workspaceService'
import { agentService } from '../services/agentService'
import { useToastStore } from '../stores/toast'
import type { Project } from '../types/workspace'
import type { AgentConfig } from '../types/agent'
import RoomAgentSettingsPanel from '../components/scheduling/RoomAgentSettingsPanel.vue'

const route = useRoute()
const router = useRouter()
const roomId = route.params.id as string
const toast = useToastStore()
const courseId = ref('')

// Config State
const aiFrequency = ref(0.2)
const isAnalyticsActive = ref(false)

// Agent Assignment State
const roomAgents = ref<any[]>([])
const availableProjects = ref<Project[]>([])
const selectedProjectId = ref<string>('')
const projectAgents = ref<AgentConfig[]>([])
const isLoading = ref(false)

const fetchSettings = async () => {
  try {
    const roomRes = await api.get(`/rooms/${roomId}`)
    const room = roomRes.data
    courseId.value = room.course_id
    aiFrequency.value = room.ai_frequency || 0.2
    isAnalyticsActive.value = !!room.is_analytics_active

    await fetchRoomAgents()
    await fetchAvailableProjects()
  } catch (e: any) {
    console.error('Failed to fetch settings', e)
    if (e.response?.status === 403 || e.response?.status === 404) {
      toast.error('You do not have access to this room.')
      router.push('/courses')
      return
    }
  }
}

const fetchRoomAgents = async () => {
  try {
    const res = await roomService.getRoomAgents(roomId)
    roomAgents.value = res.data
  } catch(e) {
    console.error(e)
  }
}

const fetchAvailableProjects = async () => {
  try {
    const res = await workspaceService.getProjects()
    availableProjects.value = res.data
    if (availableProjects.value && availableProjects.value.length > 0) {
      selectedProjectId.value = availableProjects.value[0]?.id || ''
      if (selectedProjectId.value) {
          await fetchProjectAgents()
      }
    }
  } catch(e) {
    console.error(e)
  }
}

const fetchProjectAgents = async () => {
  if (!selectedProjectId.value) return
  isLoading.value = true
  try {
    const res = await agentService.getAgents(selectedProjectId.value)
    projectAgents.value = res.data
  } catch(e) {
    console.error(e)
  } finally {
    isLoading.value = false
  }
}

const assignAgent = async (agentId: string) => {
  try {
    await roomService.assignAgentToRoom(roomId, agentId)
    toast.success("Agent assigned to room")
    await fetchRoomAgents()
  } catch(e) {
    console.error(e)
    toast.error("Failed to assign agent")
  }
}

const removeAgent = async (agentId: string) => {
  try {
    await roomService.removeAgentFromRoom(roomId, agentId)
    toast.success("Agent removed from room")
    await fetchRoomAgents()
  } catch(e) {
    console.error(e)
    toast.error("Failed to remove agent")
  }
}

const isAgentAssigned = (agentId: string) => {
  return roomAgents.value.some(a => a.id === agentId)
}

const saveSettings = async () => {
  try {
    await api.put(`/rooms/${roomId}`, {
      ai_frequency: aiFrequency.value,
      is_analytics_active: isAnalyticsActive.value
    })

    toast.success('Settings saved!')
    router.push(`/rooms/${roomId}`)
  } catch (e) {
    console.error(e)
    toast.error('Error saving settings')
  }
}

onMounted(() => {
  fetchSettings()
})
</script>

<template>
  <div class="p-6 max-w-4xl mx-auto flex flex-col gap-6">
    <div class="flex justify-between items-center mb-2">
      <h1 class="text-2xl font-bold">Room Settings</h1>
      <div class="flex gap-2">
        <router-link :to="`/rooms/${roomId}/workflow`" class="btn btn-secondary">
          🔀 Workflow Editor
        </router-link>
        <router-link :to="`/rooms/${roomId}`" class="btn btn-ghost">Back to Room</router-link>
        <button @click="saveSettings" class="btn btn-primary">Save Configuration</button>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 relative items-start">
      <!-- General Room Settings -->
      <div class="card bg-base-100 shadow p-6 h-fit sticky top-6">
        <h2 class="text-xl font-bold mb-4">Engagement Settings</h2>

        <div class="form-control mb-4">
          <label class="label">
            <span class="label-text font-bold">Intervention Frequency ({{ aiFrequency }})</span>
          </label>
          <input
            type="range"
            min="0"
            max="1"
            step="0.1"
            v-model.number="aiFrequency"
            class="range range-primary"
          />
          <div class="w-full flex justify-between text-xs px-2 mt-1">
            <span>Passive (Mentions only)</span>
            <span>Balanced</span>
            <span>Active</span>
          </div>
        </div>

        <!-- Analytics Agent Toggle -->
        <div class="form-control mt-6 pt-4 border-t">
          <label class="label cursor-pointer justify-start gap-4">
            <span class="label-text font-bold text-lg">Enable Analytics Agent</span>
            <input type="checkbox" class="toggle toggle-secondary" v-model="isAnalyticsActive" />
          </label>
          <div class="text-xs opacity-70 mt-1">
            When enabled, the Analytics Agent automatically summarizes discussions in this room.
          </div>
        </div>
      </div>

      <!-- Agent Assignment Panel -->
      <div class="card bg-base-100 shadow p-6 h-fit min-h-[500px]">
        <h2 class="text-xl font-bold mb-2">Assigned Agents</h2>
        <p class="text-xs opacity-70 mb-4">Select agents from your projects to invite them into this room.</p>
        
        <!-- Currently Assigned -->
        <div class="mb-6">
        <div v-if="isLoading" class="flex justify-center py-8">
           <span class="loading loading-spinner text-primary"></span>
        </div>
        <div v-if="!roomAgents?.length" class="text-sm opacity-50 text-center py-4 bg-base-200 rounded-lg">
            No agents assigned yet.
          </div>
          <div v-else class="flex flex-col gap-3">
             <div v-for="agent in roomAgents" :key="agent.id" class="collapse collapse-arrow bg-base-200 border border-primary/20 shadow-sm">
               <input type="checkbox" /> 
               <div class="collapse-title flex items-center justify-between font-medium">
                  <div class="flex items-center gap-3">
                    <div class="font-bold border-r pr-3 border-base-300">{{ agent.name }}</div>
                    <div class="text-xs opacity-80 uppercase tracking-widest">{{ agent.type }}</div>
                  </div>
               </div>
               <div class="collapse-content bg-base-100/50 pt-4">
                 <RoomAgentSettingsPanel :room-id="roomId" :agent-id="agent.id" />
                 
                 <div class="divider mt-8 mb-4">Danger Zone</div>
                 <div class="flex justify-end">
                   <button class="btn btn-outline btn-error btn-sm" @click="removeAgent(agent.id)">Remove Agent from Room</button>
                 </div>
               </div>
             </div>
          </div>
        </div>

        <!-- Available From Project -->
        <div class="border-t pt-4">
          <div v-if="availableProjects.length === 0" class="text-center py-6 bg-base-200 rounded-lg">
             <p class="text-sm opacity-70 mb-3">You don't have any Projects to assign agents from.</p>
             <router-link to="/workspace" class="btn btn-outline btn-sm">Create a Project</router-link>
          </div>
          <div v-else>
            <div class="flex justify-between items-center mb-3">
               <h3 class="font-bold text-sm uppercase tracking-wider opacity-50">Available Agents</h3>
               <select v-model="selectedProjectId" @change="fetchProjectAgents" class="select select-bordered select-sm max-w-xs">
                  <option v-for="proj in availableProjects" :key="proj.id" :value="proj.id">
                     {{ proj.name }}
                  </option>
               </select>
            </div>

            <div v-if="isLoading" class="flex justify-center py-8">
               <span class="loading loading-spinner text-primary"></span>
            </div>
            <div v-else-if="projectAgents.length === 0" class="text-sm text-center py-6 bg-base-200 rounded-lg mt-2">
              <p class="opacity-70 mb-3">No agents found in this project.</p>
              <router-link :to="`/workspace`" class="btn btn-primary btn-sm">Design New Agent</router-link>
            </div>
            <div v-else class="flex flex-col gap-2 max-h-64 overflow-y-auto pr-2">
               <div v-for="agent in projectAgents" :key="agent.id" class="flex items-center justify-between p-3 border rounded-lg hover:border-base-300">
                 <div>
                    <div class="font-bold text-sm">{{ agent.name }}</div>
                    <div class="text-xs opacity-60">{{ agent.model_provider }} / {{ agent.model }}</div>
                 </div>
                 <button 
                    v-if="!isAgentAssigned(agent.id)" 
                    class="btn btn-primary btn-xs" 
                    @click="assignAgent(agent.id)"
                 >Assign</button>
                 <span v-else class="text-xs font-bold text-success flex items-center gap-1">
                   <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" /></svg> Active
                 </span>
               </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>
