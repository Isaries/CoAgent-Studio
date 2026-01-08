<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api'

const route = useRoute()
const router = useRouter()
const courseId = route.params.id as string

// Config State
const teacherPrompt = ref('')
const teacherApiKey = ref('')
const studentPrompt = ref('')
const studentApiKey = ref('')

const activeTab = ref('teacher')

// Design Agent State
const designDb = ref({
    requirement: '',
    target: 'teacher',
    context: '',
    loading: false
})

const fetchSettings = async () => {
    try {
        const agentsRes = await api.get(`/agents/${courseId}`)
        const configs = agentsRes.data
        
        const teacherConfig = configs.find((c: any) => c.type === 'teacher')
        if (teacherConfig) {
            teacherPrompt.value = teacherConfig.system_prompt
        }

        const studentConfig = configs.find((c: any) => c.type === 'student')
        if (studentConfig) {
            studentPrompt.value = studentConfig.system_prompt
        }
    } catch (e) {
        console.error("Failed to fetch settings", e)
    }
}

const saveSettings = async () => {
    try {
        // Save Teacher settings
        await api.put(`/agents/${courseId}/teacher`, {
            system_prompt: teacherPrompt.value,
            api_key: teacherApiKey.value,
            model_provider: 'gemini', 
            settings: {}
        })

        // Save Student settings
        await api.put(`/agents/${courseId}/student`, {
            system_prompt: studentPrompt.value,
            api_key: studentApiKey.value,
            model_provider: 'gemini', 
            settings: {}
        })
        
        alert('Settings saved!')
        router.push(`/courses/${courseId}`)
    } catch (e) {
        console.error(e)
        alert('Error saving settings')
    }
}

const generatePrompt = async () => {
    if (!designDb.value.requirement) return
    designDb.value.loading = true
    try {
        const res = await api.post('/agents/generate', {
            requirement: designDb.value.requirement,
            target_agent_type: designDb.value.target,
            course_context: designDb.value.context,
            api_key: teacherApiKey.value || studentApiKey.value, // Try to find a key
            provider: 'gemini'
        })
        
        if (designDb.value.target === 'teacher') {
            teacherPrompt.value = res.data.generated_prompt
        } else {
            studentPrompt.value = res.data.generated_prompt
        }
    } catch (e) {
        alert('Generation failed')
    } finally {
        designDb.value.loading = false
    }
}

onMounted(() => {
    fetchSettings()
})
</script>

<template>
  <div class="p-6 max-w-3xl mx-auto">
    <div class="flex justify-between items-center mb-6">
        <h1 class="text-2xl font-bold">Course Settings (AI Brain)</h1>
        <router-link :to="`/courses/${courseId}`" class="btn btn-ghost">Back to Course</router-link>
    </div>
    
    <!-- Tabs for Agent Selection -->
    <div class="tabs tabs-boxed mb-6">
        <a class="tab" :class="{ 'tab-active': activeTab === 'teacher' }" @click="activeTab = 'teacher'">Teacher Agent</a>
        <a class="tab" :class="{ 'tab-active': activeTab === 'student' }" @click="activeTab = 'student'">Student Agent</a>
    </div>
    
    <!-- Teacher Agent Configuration -->
    <div v-if="activeTab === 'teacher'" class="card bg-base-100 shadow p-6 mb-6">
        <h2 class="text-xl font-bold mb-4">Teacher Agent Configuration</h2>
        
        <!-- API Key -->
        <div class="form-control mb-4">
            <label class="label"><span class="label-text">Teacher LLM API Key (Gemini/ChatGPT)</span></label>
            <input type="password" v-model="teacherApiKey" placeholder="sk-..." class="input input-bordered" />
            <div class="label"><span class="label-text-alt text-warning">Stored securely (Encrypted)</span></div>
        </div>

         <!-- Design Agent Helper -->
        <div class="collapse collapse-arrow bg-base-200 mb-4">
            <input type="checkbox" /> 
            <div class="collapse-title text-lg font-medium">✨ Design Agent (Prompt Generator)</div>
            <div class="collapse-content"> 
                <p class="mb-2 text-sm">Describe what kind of teacher you want, and I'll write the prompt for you.</p>
                <textarea v-model="designDb.requirement" class="textarea textarea-bordered w-full mb-2" placeholder="Ex: A strict math teacher who asks socratic questions..."></textarea>
                <input v-model="designDb.context" type="text" placeholder="Context (e.g. Calculus 101)" class="input input-bordered w-full mb-2" />
                <button @click="designDb.target = 'teacher'; generatePrompt()" class="btn btn-secondary btn-sm" :disabled="designDb.loading">
                    {{ designDb.loading ? 'Generating...' : 'Generate Teacher System Prompt' }}
                </button>
            </div>
        </div>

        <!-- System Prompt -->
        <div class="form-control">
            <label class="label"><span class="label-text">Teacher System Prompt</span></label>
            <textarea v-model="teacherPrompt" class="textarea textarea-bordered h-48 font-mono text-sm leading-relaxed" placeholder="You are a helpful teacher..."></textarea>
            <div class="label"><span class="label-text-alt">This defines how the Teacher AI behaves in all rooms for this course.</span></div>
        </div>
    </div>

    <!-- Student Agent Configuration -->
    <div v-if="activeTab === 'student'" class="card bg-base-100 shadow p-6 mb-6">
        <h2 class="text-xl font-bold mb-4">Student Agent Configuration</h2>
        
        <!-- API Key -->
        <div class="form-control mb-4">
            <label class="label"><span class="label-text">Student LLM API Key (Optional, defaults to Teacher Key)</span></label>
            <input type="password" v-model="studentApiKey" placeholder="sk-..." class="input input-bordered" />
        </div>

         <!-- Design Agent Helper -->
        <div class="collapse collapse-arrow bg-base-200 mb-4">
            <input type="checkbox" /> 
            <div class="collapse-title text-lg font-medium">✨ Design Agent (Prompt Generator)</div>
            <div class="collapse-content"> 
                <p class="mb-2 text-sm">Describe what kind of student you want in the discussion, and I'll write the prompt for you.</p>
                <textarea v-model="designDb.requirement" class="textarea textarea-bordered w-full mb-2" placeholder="Ex: A curious student who asks deep questions..."></textarea>
                <input v-model="designDb.context" type="text" placeholder="Context (e.g. Calculus 101)" class="input input-bordered w-full mb-2" />
                <button @click="designDb.target = 'student'; generatePrompt()" class="btn btn-secondary btn-sm" :disabled="designDb.loading">
                    {{ designDb.loading ? 'Generating...' : 'Generate Student System Prompt' }}
                </button>
            </div>
        </div>

        <!-- System Prompt -->
        <div class="form-control">
            <label class="label"><span class="label-text">Student System Prompt</span></label>
            <textarea v-model="studentPrompt" class="textarea textarea-bordered h-48 font-mono text-sm leading-relaxed" placeholder="You are a student who..."></textarea>
            <div class="label"><span class="label-text-alt">This defines how the Student AI behaves when interventions are active.</span></div>
        </div>
    </div>
    
    <div class="flex justify-end gap-2">
        <router-link :to="`/courses/${courseId}`" class="btn btn-ghost">Cancel</router-link>
        <button @click="saveSettings" class="btn btn-primary">Save Configuration</button>
    </div>
  </div>
</template>
