<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useWorkspaceStore } from '../stores/workspace'
import api from '../api'
import KanbanBoard from '../components/workspace/KanbanBoard.vue'
import RoomChat from '../components/room/RoomChat.vue'
import RoomDocs from '../components/room/RoomDocs.vue'
import RoomProcess from '../components/room/RoomProcess.vue'
import RoomGraphView from '../components/room/RoomGraphView.vue'
import GraphQueryPanel from '../components/room/GraphQueryPanel.vue'
import { useRoomChat } from '../composables/useRoomChat'
import type { TabKey } from '../types/enums'

const route = useRoute()
const authStore = useAuthStore()
const workspaceStore = useWorkspaceStore()
const roomId = route.params.id as string
const activeTab = ref<TabKey>('chat')

// Room data
const room = ref<{ id: string; name: string; enabled_tabs?: Record<string, boolean> } | null>(null)

// Tab definitions
const ALL_TABS: readonly { key: TabKey; label: string; alwaysVisible: boolean }[] = [
  { key: 'chat', label: 'Chat', alwaysVisible: true },
  { key: 'board', label: 'Board', alwaysVisible: false },
  { key: 'docs', label: 'Docs', alwaysVisible: false },
  { key: 'process', label: 'Process', alwaysVisible: false },
  { key: 'graph', label: 'Knowledge Graph', alwaysVisible: false },
] as const

const visibleTabs = computed(() => {
  return ALL_TABS.filter(tab =>
    tab.alwaysVisible || room.value?.enabled_tabs?.[tab.key] !== false
  )
})

// Room display name
const roomName = computed(() => room.value?.name || `Room ${roomId}`)

// Use the Chat Composable
const {
  messages,
  connect,
  disconnect,
  fetchHistory,
  sendMessage,
} = useRoomChat(roomId)

const handleSend = (text: string) => {
  sendMessage(text)
}

onMounted(async () => {
  // Fetch room data for name and enabled_tabs
  try {
    const res = await api.get(`/rooms/${roomId}`)
    room.value = res.data
  } catch (e) {
    console.error('Failed to fetch room data', e)
  }

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
        <h1 class="font-bold text-lg truncate">{{ roomName }}</h1>

        <!-- View Tabs (dynamically filtered by enabled_tabs) -->
        <div class="join overflow-x-auto">
          <button
            v-for="tab in visibleTabs"
            :key="tab.key"
            class="join-item btn btn-sm"
            :class="{
              'btn-active btn-primary': activeTab === tab.key && tab.key !== 'graph',
              'btn-active btn-accent': activeTab === tab.key && tab.key === 'graph',
            }"
            @click="activeTab = tab.key"
          >
            {{ tab.label }}
          </button>
        </div>
      </div>
      <div class="flex-none gap-2 flex items-center">
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
        <router-link to="/spaces" class="btn btn-sm btn-ghost btn-circle">
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

    <!-- Knowledge Graph View -->
    <div v-if="activeTab === 'graph'" class="flex-1 flex overflow-hidden">
      <div class="flex-1">
        <RoomGraphView :room-id="roomId" />
      </div>
      <div class="w-96 border-l border-base-300">
        <GraphQueryPanel :room-id="roomId" />
      </div>
    </div>
  </div>
</template>
