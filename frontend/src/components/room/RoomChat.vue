<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import MessageBubble from '../chat/MessageBubble.vue'
import ChatInput from '../chat/ChatInput.vue'
import type { Message } from '@/types/chat'

const props = defineProps<{
  messages: Message[]
  showA2ATrace: boolean
}>()

const emit = defineEmits<{
  (e: 'send', text: string): void
  (e: 'update:showA2ATrace', value: boolean): void
}>()

const chatContainer = ref<HTMLElement | null>(null)

const scrollToBottom = async () => {
  await nextTick()
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

// Watch messages to auto-scroll
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
    <!-- Chat Area -->
    <div ref="chatContainer" class="flex-1 overflow-y-auto p-4 space-y-4 bg-base-100">
      <MessageBubble
        v-for="(msg, idx) in messages"
        :key="`${msg.timestamp}-${msg.sender}-${idx}`"
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
