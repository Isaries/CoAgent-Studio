<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api'

const route = useRoute()
const router = useRouter()
const roomId = route.params.id as string
const courseId = ref('')

// Config State
const aiFrequency = ref(0.2)
const isAiActive = ref(false)

const fetchSettings = async () => {
    try {
        // 1. Fetch Room to get Course ID and Room Settings
        const roomRes = await api.get(`/rooms/${roomId}`)
        const room = roomRes.data
        courseId.value = room.course_id
        isAiActive.value = room.is_ai_active
        aiFrequency.value = room.ai_frequency
    } catch (e) {
        console.error("Failed to fetch settings", e)
    }
}

const saveSettings = async () => {
    try {
        // 1. Save Room settings
        await api.put(`/rooms/${roomId}`, {
            is_ai_active: isAiActive.value,
            ai_frequency: aiFrequency.value
        })
        
        alert('Settings saved!')
        router.push(`/rooms/${roomId}`)
    } catch (e) {
        console.error(e)
        alert('Error saving settings')
    }
}

onMounted(() => {
    fetchSettings()
})
</script>

<template>
  <div class="p-6 max-w-3xl mx-auto">
    <div class="flex justify-between items-center mb-6">
        <h1 class="text-2xl font-bold">Room Settings</h1>
        <router-link :to="`/rooms/${roomId}`" class="btn btn-ghost">Back to Room</router-link>
    </div>

    <!-- General Room Settings -->
    <div class="card bg-base-100 shadow p-6 mb-6">
        <h2 class="text-xl font-bold mb-4">General Settings</h2>
        <div class="form-control mb-4">
             <label class="label cursor-pointer justify-start gap-4">
                <span class="label-text font-bold">Enable AI Interventions</span> 
                <input type="checkbox" class="toggle toggle-primary" v-model="isAiActive" />
             </label>
        </div>
        <div class="form-control mb-4">
             <label class="label">
                <span class="label-text">Intervention Frequency ({{ aiFrequency }})</span>
             </label>
             <input type="range" min="0" max="1" step="0.1" v-model.number="aiFrequency" class="range range-primary" />
             <div class="w-full flex justify-between text-xs px-2">
                <span>0 (Passive)</span>
                <span>0.5 (Balanced)</span>
                <span>1 (Active)</span>
             </div>
        </div>
    </div>
    
    <div class="flex justify-end gap-2">
        <button class="btn btn-ghost" @click="router.push(`/rooms/${roomId}`)">Cancel</button>
        <button @click="saveSettings" class="btn btn-primary">Save Configuration</button>
    </div>
  </div>
</template>
