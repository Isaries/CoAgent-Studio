<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import MessageBubble from '../components/chat/MessageBubble.vue'
import ChatInput from '../components/chat/ChatInput.vue'
import api from '../api'

import type { Message } from '../types/chat'

const route = useRoute()
const authStore = useAuthStore()
const roomId = route.params.id as string
const messages = ref<Message[]>([])
const ws = ref<WebSocket | null>(null)
const chatContainer = ref<HTMLElement | null>(null)
const showA2ATrace = ref(false) // Toggle for A2A debug trace


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

import { useWebSocket } from '../composables/useWebSocket'

// ... existing imports ...

// ... inside setup ...
// import { useWebSocket } from '../composables/useWebSocket' // REMOVED duplicate

const { status, send, connect } = useWebSocket('', {
  reconnectInterval: 3000,
  maxReconnectAttempts: 10,
  onOpen: () => {
    messages.value.push({
      sender: 'System',
      content: 'Connected to chat...',
      isSelf: false,
      isSystem: true,
      timestamp: new Date().toISOString()
    })
  },
  onMessage: (msg) => {
    // Check for A2A trace messages
    if (msg.content?.startsWith('[A2A]')) {
      if (showA2ATrace.value) {
        const parts = msg.content.split('|')
        const eventType = parts[1] || 'TRACE'
        const details = parts[2] || ''
        messages.value.push({
          sender: `[A2A ${eventType}]`,
          content: details,
          isSelf: false,
          isAi: false,
          isSystem: true,
          isA2ATrace: true,
          timestamp: new Date().toISOString()
        })
        scrollToBottom()
      }
      return // Don't process further
    }

    // msg is already typed as SocketMessage from composable
    let isAi = !!msg.metadata?.is_ai || msg.sender.includes('AI')
    if (msg.sender.includes('Teacher AI') || msg.sender.includes('Student AI')) {
      isAi = true
    }

    const safeEmail = authStore.user?.email ?? ''
    const safeName = authStore.user?.full_name ?? ''
    const safeUsername = (authStore.user as any)?.username ?? ''

    const isSelf =
      msg.sender === safeName ||
      msg.sender === safeEmail ||
      (safeUsername && msg.sender === safeUsername) ||
      msg.metadata?.sender_id === authStore.user?.id

    messages.value.push({
      sender: msg.sender,
      content: msg.content,
      isSelf,
      isAi,
      isSystem: msg.type === 'system',
      timestamp: msg.timestamp
    })
    scrollToBottom()
  }
})

const scrollToBottom = () => {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  })
}

const handleSend = (text: string) => {
  if (status.value !== 'OPEN') {
    console.warn('Chat not connected')
    return
  }
  // Backend expects plain text? Or JSON?
  // Old implementation sent raw text 'data'.
  // Backend: data = await websocket.receive_text() -> Message(content=data)
  // So plain text is fine for now.
  send(text)
}

onMounted(async () => {
  await fetchMessages()

  if (authStore.user) {
    // user implies logged in (cookie present)
    // Use current host (via Proxy if dev, or same origin if prod)
    // This ensures Cookies are sent.
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host // e.g. localhost:5173 or production.com
    // We assume Vite proxy forwards /api/v1/chat/ws/... to backend
    // If proxy handles WS, this works.
    // If proxy does NOT handle WS (common vite config issue), we might need direct.
    // But `api.ts` works, so Proxy likely exists.
    // Let's try Proxy path first.
    const url = `${protocol}//${host}/api/v1/chat/ws/${roomId}`

    connect(url)
  }
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
      <div class="flex-none gap-2 flex items-center">
        <!-- A2A Trace Toggle -->
        <label class="swap swap-rotate btn btn-sm btn-ghost" title="Toggle A2A Debug Trace">
          <input type="checkbox" v-model="showA2ATrace" />
          <span class="swap-off text-xs opacity-50">A2A</span>
          <span class="swap-on text-xs text-primary font-bold">A2A</span>
        </label>
        <router-link v-if="!authStore.isStudent" :to="`/rooms/${roomId}/settings`" class="btn btn-sm btn-ghost btn-circle">
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
