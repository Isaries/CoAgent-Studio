<script setup lang="ts">
import { ref, watch, nextTick, computed } from 'vue'
import MessageBubble from '../chat/MessageBubble.vue'
import ChatInput from '../chat/ChatInput.vue'
import ChatSearch from '../chat/ChatSearch.vue'
import { useChatSearch } from '../../composables/useChatSearch'
import type { Message } from '@/types/chat'

const props = defineProps<{
  messages: Message[]
  showA2ATrace: boolean
}>()

const emit = defineEmits<{
  (e: 'send', text: string): void
  (e: 'update:showA2ATrace', value: boolean): void
}>()

const messagesRef = computed(() => props.messages)
const {
  searchQuery,
  isSearchOpen,
  currentMatchIndex,
  filteredMessages,
  matchCount,
  nextMatch,
  prevMatch,
  openSearch,
  closeSearch,
} = useChatSearch(messagesRef)

const displayMessages = computed(() => {
  return isSearchOpen.value && searchQuery.value.trim()
    ? filteredMessages.value
    : props.messages
})

const chatContainer = ref<HTMLElement | null>(null)

const scrollToBottom = async () => {
  await nextTick()
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

watch(
  () => props.messages.length,
  () => {
    scrollToBottom()
  }
)

const handleSend = (text: string) => {
  emit('send', text)
}
</script>

<template>
  <div class="flex flex-col flex-1 overflow-hidden">
    <!-- Search Bar -->
    <ChatSearch
      v-if="isSearchOpen"
      v-model="searchQuery"
      :match-count="matchCount"
      :current-match="currentMatchIndex"
      @next="nextMatch"
      @prev="prevMatch"
      @close="closeSearch"
    />

    <!-- Chat Area -->
    <div ref="chatContainer" class="flex-1 overflow-y-auto p-4 space-y-4 bg-base-100">
      <MessageBubble
        v-for="(msg, idx) in displayMessages"
        :key="`${msg.timestamp}-${msg.sender}-${idx}`"
        :sender="msg.sender"
        :content="msg.content"
        :is-self="msg.isSelf"
        :is-ai="msg.isAi"
        :is-system="msg.isSystem"
        :timestamp="msg.timestamp"
      />
      <div class="h-2"></div>
    </div>

    <!-- Input Area -->
    <div class="flex-none p-3 border-t border-base-300 bg-base-100 pb-safe">
      <div class="flex items-center gap-2">
        <button
          class="btn btn-ghost btn-sm btn-circle"
          @click="openSearch"
          title="Search messages"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </button>
        <div class="flex-1">
          <ChatInput @send="handleSend" />
        </div>
      </div>
    </div>
  </div>
</template>
