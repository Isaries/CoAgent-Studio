<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useWorkspaceStore } from '../stores/workspace'
import KanbanBoard from '../components/workspace/KanbanBoard.vue'
import RoomChat from '../components/room/RoomChat.vue'
import RoomDocs from '../components/room/RoomDocs.vue'
import RoomProcess from '../components/room/RoomProcess.vue'
import { useRoomChat } from '../composables/useRoomChat'

const route = useRoute()
const authStore = useAuthStore()
const workspaceStore = useWorkspaceStore()
const roomId = route.params.id as string
const activeTab = ref<'chat' | 'board' | 'docs' | 'process'>('chat')

// Use the Chat Composable
const {
  messages,
  showA2ATrace,
  connect,
  disconnect,
  fetchHistory,
  sendMessage,
} = useRoomChat(roomId)

const handleSend = (text: string) => {
  sendMessage(text)
}

onMounted(async () => {
  await fetchHistory()
  connect()
  // Load artifacts for Kanban/Docs/Process views
  workspaceStore.loadArtifacts(roomId)
})

onUnmounted(() => {
  disconnect()
})
</script>

<template>
  <div class="flex flex-col h-[100dvh] w-full bg-base-100">
    <!-- Header -->
    <div class="flex-none navbar bg-base-100 border-b border-base-300 px-4 h-16 shadow-sm z-10">
      <div class="flex-1 flex items-center gap-4">
        <h1 class="font-bold text-lg truncate">Room: {{ roomId }}</h1>

        <!-- View Tabs -->
        <div class="join">
          <button
            class="join-item btn btn-sm"
            :class="{ 'btn-active btn-primary': activeTab === 'chat' }"
            @click="activeTab = 'chat'"
          >
            Chat
          </button>
          <button
            class="join-item btn btn-sm"
            :class="{ 'btn-active btn-primary': activeTab === 'board' }"
            @click="activeTab = 'board'"
          >
            Board
          </button>
          <button
            class="join-item btn btn-sm"
            :class="{ 'btn-active btn-primary': activeTab === 'docs' }"
            @click="activeTab = 'docs'"
          >
            Docs
          </button>
          <button
            class="join-item btn btn-sm"
            :class="{ 'btn-active btn-primary': activeTab === 'process' }"
            @click="activeTab = 'process'"
          >
            Process
          </button>
        </div>
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

    <!-- Chat View -->
    <RoomChat
      v-show="activeTab === 'chat'"
      :messages="messages"
      :show-a2-a-trace="showA2ATrace"
      @send="handleSend"
    />

    <!-- Board View -->
    <div v-if="activeTab === 'board'" class="flex-1 overflow-hidden bg-base-200/50">
      <KanbanBoard :room-id="roomId" />
    </div>

    <!-- Docs View -->
    <RoomDocs v-if="activeTab === 'docs'" />

    <!-- Process View -->
    <RoomProcess v-if="activeTab === 'process'" />
  </div>
</template>
