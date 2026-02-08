<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { AgentType } from '../types/enums'
import { useToastStore } from '../stores/toast'
import type { AgentConfig, AgentConfigCreate } from '../types/agent'
import api from '../api'

const toast = useToastStore()

// State
const agents = ref<AgentConfig[]>([])
const isLoading = ref(false)
const showCreateModal = ref(false)
const showEditModal = ref(false)
const selectedAgent = ref<AgentConfig | null>(null)

// Form
const formData = ref<AgentConfigCreate>({
  type: AgentType.TEACHER,
  name: '',
  system_prompt: '',
  model_provider: 'gemini',
  model: 'gemini-2.0-flash',
  api_key: '',
  settings: {},
  trigger_config: null,
  schedule_config: null,
  context_window: 10
})

const resetForm = () => {
  formData.value = {
    type: AgentType.TEACHER,
    name: '',
    system_prompt: '',
    model_provider: 'gemini',
    model: 'gemini-2.0-flash',
    api_key: '',
    settings: {},
    trigger_config: null,
    schedule_config: null,
    context_window: 10
  }
}

// API Calls
const fetchAgents = async () => {
  isLoading.value = true
  try {
    const res = await api.get('/agents/global/list')
    agents.value = res.data
  } catch (e) {
    console.error(e)
    toast.error('Failed to load agents')
  } finally {
    isLoading.value = false
  }
}

const createAgent = async () => {
  try {
    await api.post('/agents/global', formData.value)
    toast.success('Agent created successfully')
    showCreateModal.value = false
    resetForm()
    await fetchAgents()
  } catch (e) {
    console.error(e)
    toast.error('Failed to create agent')
  }
}

const updateAgent = async () => {
  if (!selectedAgent.value) return
  try {
    await api.put(`/agents/${selectedAgent.value.id}`, formData.value)
    toast.success('Agent updated successfully')
    showEditModal.value = false
    selectedAgent.value = null
    resetForm()
    await fetchAgents()
  } catch (e) {
    console.error(e)
    toast.error('Failed to update agent')
  }
}

const deleteAgent = async (agent: AgentConfig) => {
  if (!confirm(`Delete agent "${agent.name}"?`)) return
  try {
    await api.delete(`/agents/${agent.id}`)
    toast.success('Agent deleted')
    await fetchAgents()
  } catch (e) {
    console.error(e)
    toast.error('Failed to delete agent')
  }
}

const openEditModal = (agent: AgentConfig) => {
  selectedAgent.value = agent
  formData.value = {
    type: agent.type as AgentType,
    name: agent.name || '',
    system_prompt: agent.system_prompt || '',
    model_provider: agent.model_provider || 'gemini',
    model: agent.model || 'gemini-2.0-flash',
    api_key: '', // Don't show existing key
    settings: agent.settings || {},
    trigger_config: agent.trigger_config || null,
    schedule_config: agent.schedule_config || null,
    context_window: agent.context_window || 10
  }
  showEditModal.value = true
}

const getTypeLabel = (type: string) => {
  switch (type) {
    case AgentType.TEACHER: return 'Teacher'
    case AgentType.STUDENT: return 'Student'
    case AgentType.DESIGN: return 'Design'
    case AgentType.ANALYTICS: return 'Analytics'
    default: return type
  }
}

const getTypeBadgeClass = (type: string) => {
  switch (type) {
    case AgentType.TEACHER: return 'badge-primary'
    case AgentType.STUDENT: return 'badge-secondary'
    case AgentType.DESIGN: return 'badge-accent'
    case AgentType.ANALYTICS: return 'badge-info'
    default: return 'badge-ghost'
  }
}

onMounted(() => {
  fetchAgents()
})
</script>

<template>
  <div class="p-6">
    <!-- Header -->
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="text-2xl font-bold">My Agents</h1>
        <p class="text-base-content/60">Create and manage your global agent templates</p>
      </div>
      <button class="btn btn-primary" @click="showCreateModal = true">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        New Agent
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="flex justify-center py-12">
      <span class="loading loading-spinner loading-lg"></span>
    </div>

    <!-- Empty State -->
    <div v-else-if="agents.length === 0" class="card bg-base-100 shadow-xl">
      <div class="card-body items-center text-center py-12">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-16 w-16 text-base-content/30 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
        </svg>
        <h2 class="text-xl font-semibold mb-2">No Agents Yet</h2>
        <p class="text-base-content/60 mb-4">Create your first global agent template to get started.</p>
        <button class="btn btn-primary" @click="showCreateModal = true">Create Agent</button>
      </div>
    </div>

    <!-- Agent Cards -->
    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div v-for="agent in agents" :key="agent.id" class="card bg-base-100 shadow-xl hover:shadow-2xl transition-shadow">
        <div class="card-body">
          <div class="flex justify-between items-start">
            <h2 class="card-title">{{ agent.name }}</h2>
            <span :class="['badge', getTypeBadgeClass(agent.type)]">{{ getTypeLabel(agent.type) }}</span>
          </div>
          
          <p class="text-sm text-base-content/60 line-clamp-2 mt-2">
            {{ agent.system_prompt?.substring(0, 100) }}{{ agent.system_prompt && agent.system_prompt.length > 100 ? '...' : '' }}
          </p>

          <div class="flex gap-2 mt-2">
            <span class="badge badge-outline badge-sm">{{ agent.model_provider }}</span>
            <span class="badge badge-outline badge-sm">{{ agent.model || 'default' }}</span>
          </div>

          <div class="card-actions justify-end mt-4">
            <button class="btn btn-ghost btn-sm" @click="openEditModal(agent)">Edit</button>
            <button class="btn btn-error btn-sm btn-outline" @click="deleteAgent(agent)">Delete</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Create Modal -->
    <dialog :class="{ 'modal-open': showCreateModal }" class="modal">
      <div class="modal-box max-w-2xl">
        <h3 class="font-bold text-lg mb-4">Create New Agent</h3>
        
        <div class="form-control w-full mb-4">
          <label class="label"><span class="label-text">Agent Type</span></label>
          <select v-model="formData.type" class="select select-bordered w-full">
            <option :value="AgentType.TEACHER">Teacher</option>
            <option :value="AgentType.STUDENT">Student</option>
          </select>
        </div>

        <div class="form-control w-full mb-4">
          <label class="label"><span class="label-text">Name</span></label>
          <input type="text" v-model="formData.name" placeholder="My Teacher Agent" class="input input-bordered w-full" />
        </div>

        <div class="form-control w-full mb-4">
          <label class="label"><span class="label-text">System Prompt</span></label>
          <textarea v-model="formData.system_prompt" class="textarea textarea-bordered h-32" placeholder="You are a helpful teaching assistant..."></textarea>
        </div>

        <div class="grid grid-cols-2 gap-4 mb-4">
          <div class="form-control w-full">
            <label class="label"><span class="label-text">Provider</span></label>
            <select v-model="formData.model_provider" class="select select-bordered w-full">
              <option value="gemini">Gemini</option>
              <option value="openai">OpenAI</option>
            </select>
          </div>
          <div class="form-control w-full">
            <label class="label"><span class="label-text">Model</span></label>
            <input type="text" v-model="formData.model" class="input input-bordered w-full" />
          </div>
        </div>

        <div class="form-control w-full mb-4">
          <label class="label"><span class="label-text">API Key (Optional)</span></label>
          <input type="password" v-model="formData.api_key" placeholder="sk-..." class="input input-bordered w-full" />
          <label class="label"><span class="label-text-alt">Enter your API key for this agent</span></label>
        </div>

        <div class="modal-action">
          <button class="btn btn-ghost" @click="showCreateModal = false; resetForm()">Cancel</button>
          <button class="btn btn-primary" @click="createAgent">Create</button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop">
        <button @click="showCreateModal = false">close</button>
      </form>
    </dialog>

    <!-- Edit Modal -->
    <dialog :class="{ 'modal-open': showEditModal }" class="modal">
      <div class="modal-box max-w-2xl">
        <h3 class="font-bold text-lg mb-4">Edit Agent</h3>
        
        <div class="form-control w-full mb-4">
          <label class="label"><span class="label-text">Agent Type</span></label>
          <select v-model="formData.type" class="select select-bordered w-full" disabled>
            <option :value="AgentType.TEACHER">Teacher</option>
            <option :value="AgentType.STUDENT">Student</option>
          </select>
        </div>

        <div class="form-control w-full mb-4">
          <label class="label"><span class="label-text">Name</span></label>
          <input type="text" v-model="formData.name" class="input input-bordered w-full" />
        </div>

        <div class="form-control w-full mb-4">
          <label class="label"><span class="label-text">System Prompt</span></label>
          <textarea v-model="formData.system_prompt" class="textarea textarea-bordered h-32"></textarea>
        </div>

        <div class="grid grid-cols-2 gap-4 mb-4">
          <div class="form-control w-full">
            <label class="label"><span class="label-text">Provider</span></label>
            <select v-model="formData.model_provider" class="select select-bordered w-full">
              <option value="gemini">Gemini</option>
              <option value="openai">OpenAI</option>
            </select>
          </div>
          <div class="form-control w-full">
            <label class="label"><span class="label-text">Model</span></label>
            <input type="text" v-model="formData.model" class="input input-bordered w-full" />
          </div>
        </div>

        <div class="form-control w-full mb-4">
          <label class="label"><span class="label-text">API Key (Leave empty to keep existing)</span></label>
          <input type="password" v-model="formData.api_key" placeholder="Enter new key to update..." class="input input-bordered w-full" />
        </div>

        <div class="modal-action">
          <button class="btn btn-ghost" @click="showEditModal = false; selectedAgent = null; resetForm()">Cancel</button>
          <button class="btn btn-primary" @click="updateAgent">Save Changes</button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop">
        <button @click="showEditModal = false">close</button>
      </form>
    </dialog>
  </div>
</template>
