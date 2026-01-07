<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import MessageBubble from '../components/chat/MessageBubble.vue'
import ChatInput from '../components/chat/ChatInput.vue'

// Basic Message Interface (MVP)
interface Message {
  sender: string
  content: string
  isSelf: boolean
  isSystem?: boolean
  isAi?: boolean
}

const route = useRoute()
const authStore = useAuthStore()
const roomId = route.params.id as string
const messages = ref<Message[]>([])
const ws = ref<WebSocket | null>(null)
const chatContainer = ref<HTMLElement | null>(null)

const connectWebSocket = () => {
    if (!authStore.token) return
    
    // In dev: proxy /api/v1 -> backend:8000.
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = 'localhost:8000' // Direct to backend
    const url = `${protocol}//${host}/api/v1/ws/${roomId}?token=${authStore.token}`
    
    ws.value = new WebSocket(url)
    
    ws.value.onopen = () => {
        messages.value.push({ sender: 'System', content: 'Connected to chat...', isSelf: false, isSystem: true })
    }
    
    ws.value.onmessage = (event) => {
        // Simple parsing logic for MVP (backend sends "email: message")
        const raw = event.data as string
        let sender = 'Unknown'
        let content = raw
        let isAi = false
        
        if (raw.includes(': ')) {
            const parts = raw.split(': ')
            sender = parts[0] ?? 'Unknown'
            content = parts.slice(1).join(': ')
        }
        
        if (sender.includes('Teacher AI')) isAi = true
        
        const safeEmail = authStore.user?.email ?? ''
        const isSelf = sender === safeEmail
        
        messages.value.push({ sender, content, isSelf, isAi })
        scrollToBottom()
    }
    
    ws.value.onclose = () => {
        console.log('WS Closed')
    }
}

const handleSend = (text: string) => {
    if (!ws.value) return
    ws.value.send(text)
    // Optimistic UI update or wait for echo? 
    // WebSocket echoes back usually, let's wait for echo to avoid dupes if backend broadcasts to sender too
    // Our backend DOES broadcast to sender.
}

const scrollToBottom = () => {
    nextTick(() => {
        if (chatContainer.value) {
            chatContainer.value.scrollTop = chatContainer.value.scrollHeight
        }
    })
}

onMounted(() => {
    connectWebSocket()
})

onUnmounted(() => {
    if (ws.value) ws.value.close()
})
</script>

<template>
  <div class="flex flex-col h-[calc(100vh-64px)] p-4 max-w-4xl mx-auto w-full">
    <div class="mb-2 flex justify-between items-center bg-base-100 p-2 rounded shadow">
        <h1 class="font-bold text-xl">Room: {{ roomId }}</h1>
        <div>
           <router-link :to="`/rooms/${roomId}/settings`" class="btn btn-sm btn-ghost">Settings</router-link>
           <router-link to="/courses" class="btn btn-sm">Back</router-link>
        </div>
    </div>
    
    <!-- Chat Area -->
    <div ref="chatContainer" class="flex-1 bg-base-100 rounded-box shadow-inner p-4 overflow-y-auto mb-4 border border-base-300">
        <MessageBubble 
            v-for="(msg, idx) in messages" 
            :key="idx" 
            :sender="msg.sender"
            :content="msg.content"
            :is-self="msg.isSelf"
            :is-ai="msg.isAi"
            :is-system="msg.isSystem"
        />
    </div>
    
    <!-- Input -->
    <ChatInput @send="handleSend" />
  </div>
</template>

