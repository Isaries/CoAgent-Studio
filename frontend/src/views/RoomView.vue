<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, watch, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useWorkspaceStore } from '../stores/workspace'
import MessageBubble from '../components/chat/MessageBubble.vue'
import ChatInput from '../components/chat/ChatInput.vue'
import KanbanBoard from '../components/workspace/KanbanBoard.vue'
import DocEditor from '../components/workspace/DocEditor.vue'
import ProcessViewer from '../components/workspace/ProcessViewer.vue'
import { useRoomChat } from '../composables/useRoomChat'

const route = useRoute()
const authStore = useAuthStore()
const workspaceStore = useWorkspaceStore()
const roomId = route.params.id as string
const chatContainer = ref<HTMLElement | null>(null)
const activeTab = ref<'chat' | 'board' | 'docs' | 'process'>('chat')

const selectedDocId = ref<string | null>(null)
const selectedProcessId = ref<string | null>(null)

const selectedDoc = computed(() => 
  workspaceStore.documents.find(d => d.id === selectedDocId.value)
)

const selectedProcess = computed(() => 
  workspaceStore.processes.find(p => p.id === selectedProcessId.value)
)

async function createNewDoc() {
  const title = prompt("Document Title:")
  if (title) {
    const doc = await workspaceStore.createDoc(title)
    if (doc) selectedDocId.value = doc.id
  }
}

async function createNewProcess() {
  const title = prompt("Workflow Title:")
  if (title) {
    const proc = await workspaceStore.createProcess(title)
    if (proc) selectedProcessId.value = proc.id
  }
}

function handleArtifactUpdate(id: string, content: any) {
  workspaceStore.updateArtifact(id, { content })
}

// Use the new Composable
const {
  messages,
  showA2ATrace,
  connect,
  disconnect,
  fetchHistory,
  sendMessage,
} = useRoomChat(roomId)

const scrollToBottom = async () => {
  await nextTick()
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

// Watch messages to auto-scroll
watch(
  () => messages.value.length,
  () => {
    scrollToBottom()
  }
)

const handleSend = (text: string) => {
  sendMessage(text)
  // Optional: Scroll to bottom immediately on send? 
  // The watch will handle it when message is echoed back or optimistically added (if we did that)
}

onMounted(async () => {
  await fetchHistory()
  connect()
  scrollToBottom()
})


import { formatDistanceToNow } from 'date-fns'

// ... existing imports

function formatTime(isoString?: string) {
  if (!isoString) return 'New'
  try {
    return formatDistanceToNow(new Date(isoString), { addSuffix: true })
  } catch (e) {
    return 'Unknown'
  }
}

function isAgent(userId?: string) {
  // Simple check: if userId exists but isn't current user, and maybe based on length/format?
  // Ideally, we'd have a list of agent IDs.
  // For now, let's assume if it's not the current user, it might be an agent or another user.
  // But to be specific about "Agent is writing", we need better metadata.
  // Let's rely on the fact that Agents usually invoke tools which update the artifact.
  // We can check if the ID is known to be an agent.
  // Getting active agents from workspaceStore or simple heuristic for now.
  return userId && userId !== authStore.user?.id && userId.length === 36 // UUID check
}

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
    <div v-show="activeTab === 'chat'" class="flex flex-col flex-1 overflow-hidden">
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

    <!-- Board View -->
    <div v-if="activeTab === 'board'" class="flex-1 overflow-hidden bg-base-200/50">
      <KanbanBoard :room-id="roomId" />
    </div>

    <!-- Docs View -->
    <div v-if="activeTab === 'docs'" class="flex-1 overflow-hidden bg-base-200/50 p-4 flex gap-4">
      <!-- Doc List -->
      <div class="w-72 bg-base-100 rounded-box shadow-sm flex flex-col border border-base-200">
        <div class="p-4 border-b border-base-200 flex justify-between items-center bg-base-50 rounded-t-box">
           <h3 class="font-bold text-sm uppercase tracking-wide opacity-70">Documents</h3>
           <button @click="createNewDoc" class="btn btn-xs btn-primary gap-1">
             <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
             New
           </button>
        </div>
        <div class="flex-1 overflow-y-auto p-2 space-y-1">
           <div 
             v-for="doc in workspaceStore.documents" 
             :key="doc.id"
             @click="selectedDocId = doc.id"
             class="group p-3 rounded-lg cursor-pointer hover:bg-base-200 transition-all border border-transparent hover:border-base-300"
             :class="{ 'bg-primary/5 border-primary/20': selectedDocId === doc.id }"
           >
             <div class="flex items-start gap-3">
               <div class="mt-1 p-1.5 rounded bg-base-200 group-hover:bg-primary/10 text-primary-content group-hover:text-primary transition-colors">
                 <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
               </div>
               <div class="flex-1 min-w-0">
                 <div class="font-medium text-sm truncate" :class="{ 'text-primary': selectedDocId === doc.id }">
                   {{ doc.title }}
                 </div>
                 <div class="text-xs text-base-content/50 mt-0.5 flex items-center gap-1">
                    <span v-if="isAgent(doc.last_modified_by)" class="text-primary font-xs flex items-center gap-0.5">
                      <svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a10 10 0 1 0 10 10H12V2z"></path><path d="M12 2a10 10 0 0 1 10 10"></path><path d="M12 2v10"></path></svg>
                      AI
                    </span>
                    <span v-if="isAgent(doc.last_modified_by)">•</span>
                    <span>v{{ doc.version }}</span>
                    <span>•</span>
                    <span>{{ formatTime(doc.updated_at) }}</span>
                 </div>
               </div>
             </div>
           </div>
           <div v-if="workspaceStore.documents.length === 0" class="flex flex-col items-center justify-center h-40 text-base-content/40">
             <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round" class="mb-2 opacity-50"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>
             <span class="text-sm">No documents yet</span>
           </div>
        </div>
      </div>

      <!-- Doc Editor -->
      <div class="flex-1 bg-base-100 rounded-box shadow-sm border border-base-200 overflow-hidden relative">
        <DocEditor 
          v-if="selectedDoc" 
          :artifact="selectedDoc" 
          :key="selectedDoc.id"
          class="h-full"
          @update="(c) => handleArtifactUpdate(selectedDoc!.id, c)"
        />
        <div v-else class="absolute inset-0 flex flex-col items-center justify-center text-base-content/30 gap-4">
          <div class="w-16 h-16 rounded-full bg-base-200 flex items-center justify-center">
            <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
          </div>
          <p>Select a document to start editing</p>
        </div>
      </div>
    </div>

    <!-- Process View -->
    <div v-if="activeTab === 'process'" class="flex-1 overflow-hidden bg-base-200/50 p-4 flex gap-4">
      <!-- Process List -->
      <div class="w-72 bg-base-100 rounded-box shadow-sm flex flex-col border border-base-200">
        <div class="p-4 border-b border-base-200 flex justify-between items-center bg-base-50 rounded-t-box">
           <h3 class="font-bold text-sm uppercase tracking-wide opacity-70">Workflows</h3>
           <button @click="createNewProcess" class="btn btn-xs btn-primary gap-1">
             <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
             New
           </button>
        </div>
        <div class="flex-1 overflow-y-auto p-2 space-y-1">
           <div 
             v-for="proc in workspaceStore.processes" 
             :key="proc.id"
             @click="selectedProcessId = proc.id"
             class="group p-3 rounded-lg cursor-pointer hover:bg-base-200 transition-all border border-transparent hover:border-base-300"
             :class="{ 'bg-primary/5 border-primary/20': selectedProcessId === proc.id }"
           >
             <div class="flex items-start gap-3">
               <div class="mt-1 p-1.5 rounded bg-base-200 group-hover:bg-primary/10 text-primary-content group-hover:text-primary transition-colors">
                 <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>
               </div>
               <div class="flex-1 min-w-0">
                 <div class="font-medium text-sm truncate" :class="{ 'text-primary': selectedProcessId === proc.id }">
                   {{ proc.title }}
                 </div>
                 <div class="text-xs text-base-content/50 mt-0.5 flex items-center gap-1">
                    <span v-if="isAgent(proc.last_modified_by)" class="text-primary font-xs flex items-center gap-0.5">
                      <svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a10 10 0 1 0 10 10H12V2z"></path><path d="M12 2a10 10 0 0 1 10 10"></path><path d="M12 2v10"></path></svg>
                      AI
                    </span>
                    <span v-if="isAgent(proc.last_modified_by)">•</span>
                    <span>v{{ proc.version }}</span>
                    <span>•</span>
                    <span>{{ formatTime(proc.updated_at) }}</span>
                 </div>
               </div>
             </div>
           </div>
           <div v-if="workspaceStore.processes.length === 0" class="flex flex-col items-center justify-center h-40 text-base-content/40">
             <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round" class="mb-2 opacity-50"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>
             <span class="text-sm">No workflows yet</span>
           </div>
        </div>
      </div>

      <!-- Process Viewer -->
      <div class="flex-1 bg-base-100 rounded-box shadow-sm border border-base-200 overflow-hidden relative">
         <ProcessViewer
          v-if="selectedProcess"
          :artifact="selectedProcess"
          :key="selectedProcess.id"
          :editable="true"
          class="h-full"
          @update="(c) => handleArtifactUpdate(selectedProcess!.id, c)"
         />
         <div v-else class="absolute inset-0 flex items-center justify-center text-base-content/30">
          Select a workflow to view
        </div>
      </div>
    </div>
  </div>
</template>
