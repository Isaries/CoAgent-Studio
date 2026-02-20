<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { workspaceService } from '../services/workspaceService'
import { agentService } from '../services/agentService'
import type { Organization, Project } from '../types/workspace'
import type { AgentConfig } from '../types/agent'

const router = useRouter()

const organizations = ref<Organization[]>([])
const selectedOrgId = ref<string | null>(null)

const projects = ref<Project[]>([])
const selectedProjectId = ref<string | null>(null)

const agents = ref<AgentConfig[]>([])

const isLoading = ref(false)

// Create Modals State
const showCreateOrgModal = ref(false)
const newOrgName = ref('')
const newOrgDescription = ref('')

const showCreateProjectModal = ref(false)
const newProjectName = ref('')
const newProjectDescription = ref('')

// Fetching Data
const fetchOrgs = async () => {
  isLoading.value = true
  try {
    const res = await workspaceService.getOrganizations()
    organizations.value = res.data
    if (organizations.value && organizations.value.length > 0) {
      selectedOrgId.value = organizations.value[0]?.id || null
      if (selectedOrgId.value) {
        await fetchProjects(selectedOrgId.value)
      }
    }
  } catch (e) {
    console.error(e)
  } finally {
    isLoading.value = false
  }
}

const fetchProjects = async (orgId: string) => {
  isLoading.value = true
  try {
    const res = await workspaceService.getProjects(orgId)
    projects.value = res.data
    if (projects.value && projects.value.length > 0) {
      selectedProjectId.value = projects.value[0]?.id || null
      if (selectedProjectId.value) {
        await fetchAgents(selectedProjectId.value)
      }
    } else {
      selectedProjectId.value = null
      agents.value = []
    }
  } catch (e) {
    console.error(e)
  } finally {
    isLoading.value = false
  }
}

const fetchAgents = async (projectId: string) => {
  isLoading.value = true
  try {
    const res = await agentService.getAgents(projectId)
    agents.value = res.data
  } catch (e) {
    console.error(e)
  } finally {
    isLoading.value = false
  }
}

// Handlers
const selectOrg = async (orgId: string) => {
  selectedOrgId.value = orgId
  await fetchProjects(orgId)
}

const selectProject = async (projectId: string) => {
  selectedProjectId.value = projectId
  await fetchAgents(projectId)
}

const goToAgentDesign = (agentId?: string) => {
  if (agentId) {
    router.push(`/projects/${selectedProjectId.value}/agents/${agentId}`)
  } else {
    router.push(`/projects/${selectedProjectId.value}/agents/new`)
  }
}

// Create Handlers
const createOrganization = async () => {
  if (!newOrgName.value.trim()) return
  try {
    isLoading.value = true
    const res = await workspaceService.createOrganization({ 
      name: newOrgName.value,
      description: newOrgDescription.value 
    })
    organizations.value.push(res.data)
    showCreateOrgModal.value = false
    newOrgName.value = ''
    newOrgDescription.value = ''
    if (!selectedOrgId.value) {
      await selectOrg(res.data.id)
    }
  } catch(e) {
    console.error("Failed to create org", e)
  } finally {
    isLoading.value = false
  }
}

const createProject = async () => {
  if (!newProjectName.value.trim() || !selectedOrgId.value) return
  try {
    isLoading.value = true
    const res = await workspaceService.createProject({ 
      name: newProjectName.value,
      description: newProjectDescription.value,
      organization_id: selectedOrgId.value
    })
    projects.value.push(res.data)
    showCreateProjectModal.value = false
    newProjectName.value = ''
    newProjectDescription.value = ''
    if (!selectedProjectId.value) {
      await selectProject(res.data.id)
    }
  } catch(e) {
    console.error("Failed to create project", e)
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  fetchOrgs()
})
</script>

<template>
  <div class="h-full flex flex-col bg-base-200 overflow-hidden">
    
    <!-- Top Bar Navigation (Workspace Context) -->
    <div class="w-full bg-base-100 border-b border-base-300 px-6 py-3 flex justify-between items-center shadow-sm">
        
        <!-- Left Side: Org & Project Selection -->
        <div class="flex items-center gap-4">
            
            <!-- Organization Selector -->
            <div class="flex items-center gap-2">
                <span class="text-xs uppercase font-bold opacity-50 tracking-wider">Org</span>
                <select 
                    v-model="selectedOrgId" 
                    @change="selectOrg(($event.target as HTMLSelectElement).value)" 
                    class="select select-sm select-bordered w-48 font-semibold"
                >
                    <option v-for="org in organizations" :key="org.id" :value="org.id">
                        {{ org.name }}
                    </option>
                </select>
                <button 
                  class="btn btn-sm btn-ghost btn-square" 
                  @click="showCreateOrgModal = true"
                  title="New Organization"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" /></svg>
                </button>
            </div>

            <div class="divider divider-horizontal my-1 opacity-30"></div>

            <!-- Project Selector -->
            <div class="flex items-center gap-2">
                <span class="text-xs uppercase font-bold opacity-50 tracking-wider">Project</span>
                <select 
                    v-model="selectedProjectId" 
                    @change="selectProject(($event.target as HTMLSelectElement).value)" 
                    class="select select-sm select-bordered w-48 font-semibold"
                    :disabled="!selectedOrgId"
                >
                    <option v-for="proj in projects" :key="proj.id" :value="proj.id">
                        {{ proj.name }}
                    </option>
                    <option v-if="projects.length === 0" disabled value="">No projects found</option>
                </select>
                <button 
                  class="btn btn-sm btn-ghost btn-square" 
                  @click="showCreateProjectModal = true"
                  :disabled="!selectedOrgId"
                  title="New Project"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" /></svg>
                </button>
            </div>

        </div>

        <!-- Right Side: Actions -->
        <div>
            <button class="btn btn-sm btn-primary" :disabled="!selectedProjectId" @click="goToAgentDesign()">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" /></svg>
                New Agent
            </button>
        </div>
    </div>


    <!-- Main Content Area: Agent Grid -->
    <div class="flex-1 p-6 overflow-y-auto">
        <div v-if="isLoading" class="flex justify-center py-12">
            <span class="loading loading-spinner loading-lg text-primary"></span>
        </div>
        
        <div v-else-if="!selectedProjectId" class="flex flex-col items-center justify-center p-12 opacity-50 h-full">
             <svg xmlns="http://www.w3.org/2000/svg" class="h-16 w-16 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 002-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" /></svg>
             <h3 class="text-xl font-bold">No Project Selected</h3>
             <p class="text-sm mt-2">Select or create a project to view its agents.</p>
        </div>

        <div v-else-if="!agents?.length" class="flex flex-col items-center justify-center p-12 opacity-50 h-full bg-base-100 rounded-xl border border-dashed border-base-300">
             <svg xmlns="http://www.w3.org/2000/svg" class="h-16 w-16 mb-4 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M14 10l-2 1m0 0l-2-1m2 1v2.5M20 7l-2 1m2-1l-2-1m2 1v2.5M14 4l-2-1-2 1M4 7l2-1M4 7l2 1M4 7v2.5M12 21l-2-1m2 1l2-1m-2 1v-2.5M6 18l-2-1v-2.5M18 18l2-1v-2.5" /></svg>
             <h3 class="text-xl font-bold">No Agents Configured</h3>
             <p class="text-sm mt-2 mb-4">You haven't designed any Agents for this project yet.</p>
             <button class="btn btn-primary" @click="goToAgentDesign()">Design Your First Agent</button>
        </div>

        <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            <div 
              v-for="agent in agents" :key="agent.id"
              class="card bg-base-100 shadow-sm border border-base-300 cursor-pointer hover:border-primary hover:shadow-md transition-all group"
              @click="goToAgentDesign(agent.id)"
            >
              <div class="card-body p-6">
                <!-- Header -->
                <div class="flex justify-between items-start mb-2">
                    <h3 class="font-bold text-lg leading-tight group-hover:text-primary transition-colors">{{ agent.name }}</h3>
                    <div class="badge badge-sm badge-ghost">{{ agent.type }}</div>
                </div>
                
                <!-- Description -->
                <p class="text-xs opacity-70 line-clamp-3 my-2 flex-grow">
                    {{ agent.system_prompt || 'No system prompt defined.' }}
                </p>

                <!-- Footer -->
                <div class="mt-4 pt-4 border-t border-base-200 flex items-center justify-between text-xs opacity-60">
                    <div class="flex items-center gap-1 font-mono">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" /></svg>
                        {{ agent.model_provider }}
                    </div>
                    <div class="flex items-center text-primary font-medium opacity-0 group-hover:opacity-100 transition-opacity">
                        Configure <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" /></svg>
                    </div>
                </div>
              </div>
            </div>
        </div>
    </div>

    <!-- Modals -->
    <dialog class="modal" :class="{ 'modal-open': showCreateOrgModal }">
      <div class="modal-box">
        <h3 class="font-bold text-lg mb-4">Create Organization</h3>
        <div class="form-control mb-4">
          <label class="label"><span class="label-text">Name</span></label>
          <input type="text" v-model="newOrgName" class="input input-bordered" placeholder="Acme Corp" />
        </div>
        <div class="form-control mb-6">
          <label class="label"><span class="label-text">Description (Optional)</span></label>
          <input type="text" v-model="newOrgDescription" class="input input-bordered" />
        </div>
        <div class="modal-action">
          <button class="btn btn-ghost" @click="showCreateOrgModal = false">Cancel</button>
          <button class="btn btn-primary" @click="createOrganization" :disabled="!newOrgName || isLoading">
            Create
          </button>
        </div>
      </div>
    </dialog>

    <dialog class="modal" :class="{ 'modal-open': showCreateProjectModal }">
      <div class="modal-box">
        <h3 class="font-bold text-lg mb-4">Create Project</h3>
        <div class="form-control mb-4">
          <label class="label"><span class="label-text">Name</span></label>
          <input type="text" v-model="newProjectName" class="input input-bordered" placeholder="Project Phoenix" />
        </div>
        <div class="form-control mb-6">
          <label class="label"><span class="label-text">Description (Optional)</span></label>
          <input type="text" v-model="newProjectDescription" class="input input-bordered" />
        </div>
        <div class="modal-action">
          <button class="btn btn-ghost" @click="showCreateProjectModal = false">Cancel</button>
          <button class="btn btn-primary" @click="createProject" :disabled="!newProjectName || isLoading">
            Create
          </button>
        </div>
      </div>
    </dialog>
  </div>
</template>
