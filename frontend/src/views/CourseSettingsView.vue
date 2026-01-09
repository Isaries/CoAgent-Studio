<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import api from '../api'
import { useAuthStore } from '../stores/auth'
import { useCourse } from '../composables/useCourse'

const route = useRoute()
const authStore = useAuthStore()
const courseId = route.params.id as string

const { course, fetchCourseData } = useCourse(courseId)

// State
const activeTab = ref<'teacher' | 'student'>('teacher')
const configs = ref<any[]>([])
const selectedConfigId = ref<string | null>(null)
const loading = ref(false)

// Editor State
const editName = ref('')
const editPrompt = ref('')
const editApiKey = ref('')
const editProvider = ref('gemini')

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
        const res = await api.post('/agents/generate', {
            requirement: req,
            target_agent_type: activeTab.value,
            course_context: designDb.value.context || course.value?.title,
            api_key: editApiKey.value, // Try to find a key. Ideally use system key or provided key.
            provider: editProvider.value
        })
        editPrompt.value = res.data.generated_prompt
    } catch (e) {
        alert('Generation failed')
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
        .filter(c => c.type === activeTab.value)
        .sort((a, b) => (b.is_active ? 1 : 0) - (a.is_active ? 1 : 0) || new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
})

const selectedConfig = computed(() => {
    return configs.value.find(c => c.id === selectedConfigId.value)
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
        const res = await api.get(`/agents/${courseId}`)
        configs.value = res.data
        
        // If no selected, select active one for current tab
        if (!selectedConfigId.value) {
           const active = currentConfigs.value.find(c => c.is_active)
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
    editApiKey.value = "" // Don't show existing key
    editProvider.value = config.model_provider || 'gemini'
}

const startNewConfig = () => {
    selectedConfigId.value = null
    editName.value = `New ${activeTab.value === 'teacher' ? 'Teacher' : 'Student'} Brain`
    editPrompt.value = ''
    editApiKey.value = ''
    editProvider.value = 'gemini'
    
    // Reset Design Agent
    designDb.value = {
        requirement: '',
        context: '',
        loading: false,
        refineCurrent: false
    }
}

const saveConfig = async () => {
    if (!editName.value) return alert("Name is required")
    
    const payload = {
        name: editName.value,
        system_prompt: editPrompt.value,
        api_key: editApiKey.value,
        model_provider: editProvider.value,
        type: activeTab.value,
        settings: {}
    }
    
    try {
        if (selectedConfigId.value) {
            // Update
             await api.put(`/agents/${selectedConfigId.value}`, payload)
        } else {
            // Create
             const res = await api.post(`/agents/${courseId}`, payload)
             selectedConfigId.value = res.data.id
        }
        await fetchConfigs()
        alert("Saved!")
    } catch (e: any) {
        alert(e.response?.data?.detail || "Failed to save")
    }
}

const activateConfig = async (id: string) => {
    try {
        await api.put(`/agents/${id}/activate`)
        await fetchConfigs()
    } catch (e: any) {
        alert(e.response?.data?.detail || "Failed to activate")
    }
}

const deleteConfig = async (id: string) => {
    if (!confirm("Are you sure?")) return
    try {
        await api.delete(`/agents/${id}`)
        if (selectedConfigId.value === id) selectedConfigId.value = null
        await fetchConfigs()
    } catch (e: any) {
        alert(e.response?.data?.detail || "Failed to delete")
    }
}



// Watchers
watch(activeTab, () => {
    startNewConfig()
    // Try to find active in new tab
    const active = currentConfigs.value.find(c => c.is_active)
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
                <a class="tab" :class="{ 'tab-active': activeTab === 'teacher' }" @click="activeTab = 'teacher'">Teacher</a>
                <a class="tab" :class="{ 'tab-active': activeTab === 'student' }" @click="activeTab = 'student'">Student</a>
            </div>
        </div>
        <router-link :to="`/courses/${courseId}`" class="btn btn-sm btn-ghost">Back to Course</router-link>
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
                :class="{'border-primary ring-1 ring-primary': selectedConfigId === conf.id}"
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
                         <div v-if="selectedConfigId && selectedConfig?.is_active" class="badge badge-success badge-lg gap-2">
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                            Current Active Brain
                        </div>
                        <div v-else-if="selectedConfigId && isOwner" class="tooltip" data-tip="Only Owner can activate">
                             <button @click="activateConfig(selectedConfigId!)" class="btn btn-sm btn-outline">Set as Active</button>
                        </div>
                        <span v-else-if="selectedConfigId" class="badge badge-ghost">Inactive Profile</span>
                        <span v-else class="badge badge-info">Creating New Profile</span>
                    </div>
                    
                    <div class="flex gap-2" v-if="canEdit || selectedConfigId">
                         <button 
                            v-if="selectedConfigId && (isOwner || selectedConfig?.created_by === authStore.user?.id)" 
                            @click="deleteConfig(selectedConfigId)" 
                            class="btn btn-sm btn-ghost text-error"
                         >Delete</button>
                        <button v-if="canEdit" @click="saveConfig" class="btn btn-primary btn-sm">Save Changes</button>
                    </div>
                </div>
                
                <!-- Editor Form -->
                 <div class="form-control mb-4">
                    <label class="label"><span class="label-text">Profile Name</span></label>
                    <input type="text" v-model="editName" :disabled="!canEdit" class="input input-bordered text-lg font-bold" />
                </div>

                <div class="form-control mb-6">
                    <label class="label"><span class="label-text">API Key (Leave empty to keep existing)</span></label>
                    <input type="password" v-model="editApiKey" :disabled="!canEdit" placeholder="Enter new API Key to update..." class="input input-bordered" />
                    <div v-if="selectedConfig && selectedConfig.masked_api_key && !editApiKey" class="label text-xs text-success flex gap-1 items-center">
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>
                        Encryption Active. Current Key: {{ selectedConfig.masked_api_key }}
                    </div>
                </div>

                <!-- Design Agent -->
                <div v-if="canEdit" class="collapse collapse-arrow bg-base-200 mb-6 border border-base-300">
                    <input type="checkbox" /> 
                    <div class="collapse-title font-medium flex items-center gap-2">
                        <span>✨ AI Prompt Designer</span>
                    </div>
                    <div class="collapse-content"> 
                        <div class="p-2">
                            <p class="mb-2 text-sm text-gray-600">Describe the persona and behavior you want.</p>
                            <textarea v-model="designDb.requirement" class="textarea textarea-bordered w-full mb-2" placeholder="e.g. A friendly tutor who explains concepts using pizza analogies..."></textarea>
                            <input v-model="designDb.context" type="text" placeholder="Context (e.g. Intro to Python)" class="input input-bordered w-full mb-2" />
                            
                            <div class="form-control mb-2">
                                <label class="label cursor-pointer justify-start gap-4">
                                    <input type="checkbox" v-model="designDb.refineCurrent" class="checkbox checkbox-sm" :disabled="!editPrompt" />
                                    <span class="label-text">Refine based on current prompt (Pass current version to Design Agent)</span>
                                </label>
                            </div>

                            <button @click="generatePrompt" class="btn btn-secondary btn-sm w-full" :disabled="designDb.loading">
                                {{ designDb.loading ? 'Generating...' : 'Auto-Generate Prompt' }}
                            </button>
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
