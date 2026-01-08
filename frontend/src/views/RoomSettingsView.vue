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
const aiMode = ref('teacher_only') // off, teacher_only, both

const fetchSettings = async () => {
    try {
        const roomRes = await api.get(`/rooms/${roomId}`)
        const room = roomRes.data
        courseId.value = room.course_id
        aiMode.value = room.ai_mode || 'teacher_only'
        aiFrequency.value = room.ai_frequency
    } catch (e) {
        console.error("Failed to fetch settings", e)
    }
}

const saveSettings = async () => {
    try {
        await api.put(`/rooms/${roomId}`, {
            ai_mode: aiMode.value,
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
        <h2 class="text-xl font-bold mb-4">AI 介入設定</h2>
        
        <div class="form-control mb-6">
            <label class="label"><span class="label-text font-bold text-lg">選擇 AI 介入模式</span></label>
            <div class="flex flex-col gap-3 mt-2">
                <label class="flex items-center gap-4 p-3 border rounded-lg cursor-pointer hover:bg-base-200 transition-colors" :class="{ 'border-primary bg-primary/5': aiMode === 'off' }">
                    <input type="radio" v-model="aiMode" value="off" class="radio radio-primary" />
                    <div>
                        <div class="font-bold">關閉 AI 介入</div>
                        <div class="text-xs opacity-70">在此討論室中，AI 將不會提供任何建議或回覆。</div>
                    </div>
                </label>

                <label class="flex items-center gap-4 p-3 border rounded-lg cursor-pointer hover:bg-base-200 transition-colors" :class="{ 'border-primary bg-primary/5': aiMode === 'teacher_only' }">
                    <input type="radio" v-model="aiMode" value="teacher_only" class="radio radio-primary" />
                    <div>
                        <div class="font-bold">僅啟用 Teacher Agent</div>
                        <div class="text-xs opacity-70">僅老師 Agent 會根據討論內容提供指導與回覆。</div>
                    </div>
                </label>

                <label class="flex items-center gap-4 p-3 border rounded-lg cursor-pointer hover:bg-base-200 transition-colors" :class="{ 'border-primary bg-primary/5': aiMode === 'both' }">
                    <input type="radio" v-model="aiMode" value="both" class="radio radio-primary" />
                    <div>
                        <div class="font-bold">啟用 Teacher Agent 與 Student Agent</div>
                        <div class="text-xs opacity-70">兩位 Agent 都會參與討論（學生發言需經過老師審核）。</div>
                    </div>
                </label>
            </div>
        </div>

        <div class="form-control mb-4">
             <label class="label">
                <span class="label-text font-bold">介入頻率 ({{ aiFrequency }})</span>
             </label>
             <input type="range" min="0" max="1" step="0.1" v-model.number="aiFrequency" class="range range-primary" :disabled="aiMode === 'off'" />
             <div class="w-full flex justify-between text-xs px-2 mt-1">
                <span>被動 (僅在被標記時回覆)</span>
                <span>平衡 (隨機參與討論)</span>
                <span>主動 (頻繁引導討論)</span>
             </div>
        </div>
    </div>
    
    <div class="flex justify-end gap-2">
        <button class="btn btn-ghost" @click="router.push(`/rooms/${roomId}`)">Cancel</button>
        <button @click="saveSettings" class="btn btn-primary">Save Configuration</button>
    </div>
  </div>
</template>
