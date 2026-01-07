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

// Design Agent State
const designDb = ref({
    requirement: '',
    target: 'teacher',
    context: '',
    loading: false
})

const fetchSettings = async () => {
    try {
        // Fetch Agent Config (Teacher) for this Course
        // Endpoint: GET /agents/{course_id}
        const agentsRes = await api.get(`/agents/${courseId}`)
        const configs = agentsRes.data
        const teacherConfig = configs.find((c: any) => c.type === 'teacher')
        
        if (teacherConfig) {
            teacherPrompt.value = teacherConfig.system_prompt
            // API Key is encrypted/hidden usually
            // teacherApiKey.value = teacherConfig.encrypted_api_key 
        }
    } catch (e) {
        console.error("Failed to fetch settings", e)
    }
}

const saveSettings = async () => {
    try {
        // Save Agent settings (Teacher)
        await api.put(`/agents/${courseId}/teacher`, {
            system_prompt: teacherPrompt.value,
            api_key: teacherApiKey.value, // Only send if updating
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
            api_key: teacherApiKey.value, 
            provider: 'gemini'
        })
        teacherPrompt.value = res.data.generated_prompt
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
    
    <!-- Teacher Agent Configuration -->
    <div class="card bg-base-100 shadow p-6 mb-6">
        <h2 class="text-xl font-bold mb-4">Teacher Agent Configuration</h2>
        
        <!-- API Key -->
        <div class="form-control mb-4">
            <label class="label"><span class="label-text">LLM API Key (Gemini/ChatGPT)</span></label>
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
                <button @click="generatePrompt" class="btn btn-secondary btn-sm" :disabled="designDb.loading">
                    {{ designDb.loading ? 'Generating...' : 'Generate System Prompt' }}
                </button>
            </div>
        </div>

        <!-- System Prompt -->
        <div class="form-control">
            <label class="label"><span class="label-text">System Prompt</span></label>
            <textarea v-model="teacherPrompt" class="textarea textarea-bordered h-48 font-mono text-sm leading-relaxed" placeholder="You are a helpful teacher..."></textarea>
            <div class="label"><span class="label-text-alt">This defines how the AI behaves in all rooms for this course.</span></div>
        </div>
    </div>
    
    <div class="flex justify-end gap-2">
        <router-link :to="`/courses/${courseId}`" class="btn btn-ghost">Cancel</router-link>
        <button @click="saveSettings" class="btn btn-primary">Save Configuration</button>
    </div>
  </div>
</template>
