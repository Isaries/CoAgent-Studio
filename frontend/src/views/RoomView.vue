<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import MessageBubble from '../components/chat/MessageBubble.vue'
import ChatInput from '../components/chat/ChatInput.vue'
import api from '../api'

// Basic Message Interface (MVP)
interface Message {
  sender: string
  content: string
  isSelf: boolean
  isSystem?: boolean
  isAi?: boolean
  timestamp?: string
}

const route = useRoute()
const authStore = useAuthStore()
const roomId = route.params.id as string
const messages = ref<Message[]>([])
const ws = ref<WebSocket | null>(null)
const chatContainer = ref<HTMLElement | null>(null)

const fetchMessages = async () => {
  try {
    const response = await api.get(`/chat/messages/${roomId}`)
    const history = response.data.map((msg: any) => ({
      sender: msg.sender,
      content: msg.content,
      isSelf: msg.sender_id === authStore.user?.id || msg.sender === authStore.user?.email, // Improved check
      isAi: !!msg.agent_type,
      isSystem: false,
      timestamp: msg.created_at
    }))
    messages.value = history
    scrollToBottom()
  } catch (error) {
    console.error('Failed to fetch messages:', error)
  }
}

const connectWebSocket = () => {
  if (!authStore.token) return

  // In dev: proxy /api/v1 -> backend:8000.
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = 'localhost:8000' // Direct to backend
  const url = `${protocol}//${host}/api/v1/chat/ws/${roomId}?token=${authStore.token}`

  ws.value = new WebSocket(url)

  ws.value.onopen = () => {
    messages.value.push({
      sender: 'System',
      content: 'Connected to chat...',
      isSelf: false,
      isSystem: true,
      timestamp: new Date().toISOString()
    })
  }

  ws.value.onmessage = (event) => {
    const raw = event.data as string
    let sender = 'Unknown'
    let content = raw
    let timestamp = ''
    let isAi = false

    // Format: name|timestamp|content
    const parts = raw.split('|')
    if (parts.length >= 3) {
      sender = parts[0] || 'Unknown'
      timestamp = parts[1] || ''
      content = parts.slice(2).join('|')
    } else if (raw.includes(': ')) {
      // Fallback for unexpected messages
      const p = raw.split(': ')
      sender = p[0] || 'Unknown'
      content = p.slice(1).join(': ')
    }

    if (sender.includes('Teacher AI') || sender.includes('Student AI')) isAi = true

    // We rely on name matching for WS messages for now since we don't send ID in string
    // Ideally backend should send JSON.
    const safeEmail = authStore.user?.email ?? ''
    const safeName = authStore.user?.full_name ?? ''
    // Use type assertion if we know username exists or optional chaining if uncertain
    const safeUsername = (authStore.user as any)?.username ?? ''

    const isSelf =
      sender === safeName || sender === safeEmail || (safeUsername && sender === safeUsername)

    messages.value.push({ sender, content, isSelf, isAi, timestamp })
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

onMounted(async () => {
  await fetchMessages()
  connectWebSocket()
})

onUnmounted(() => {
  if (ws.value) ws.value.close()
})
</script>

<template>
  <div class="flex flex-col h-[100dvh] w-full bg-base-100">
    <!-- Header -->
    <div class="flex-none navbar bg-base-100 border-b border-base-300 px-4 h-16 shadow-sm z-10">
      <div class="flex-1">
        <h1 class="font-bold text-lg truncate">Room: {{ roomId }}</h1>
      </div>
      <div class="flex-none gap-2">
        <router-link :to="`/rooms/${roomId}/settings`" class="btn btn-sm btn-ghost btn-circle">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <circle cx="12" cy="12" r="3"></circle>
            <path
              d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"
            ></path>
          </svg>
        </router-link>
        <router-link to="/courses" class="btn btn-sm btn-ghost btn-circle">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </router-link>
      </div>
    </div>

    <!-- Chat Area -->
    <div ref="chatContainer" class="flex-1 overflow-y-auto p-4 space-y-4 bg-base-100">
      <MessageBubble
        v-for="(msg, idx) in messages"
        :key="idx"
        :sender="msg.sender"
        :content="msg.content"
        :is-self="msg.isSelf"
        :is-ai="msg.isAi"
        :is-system="msg.isSystem"
        :timestamp="msg.timestamp"
      />
      <!-- Spacer for auto-scroll visibility -->
      <div class="h-2"></div>
    </div>

    <!-- Input Area -->
    <div class="flex-none p-3 border-t border-base-300 bg-base-100 pb-safe">
      <ChatInput @send="handleSend" />
    </div>
  </div>
</template>
