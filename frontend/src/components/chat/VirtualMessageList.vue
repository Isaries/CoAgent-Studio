<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import MessageBubble from './MessageBubble.vue'
import type { Message } from '@/types/chat'

const props = defineProps<{
  messages: Message[]
}>()

const containerRef = ref<HTMLElement | null>(null)

const scrollToBottom = async () => {
  await nextTick()
  if (containerRef.value) {
    containerRef.value.scrollTop = containerRef.value.scrollHeight
  }
}

watch(
  () => props.messages.length,
  () => scrollToBottom()
)
</script>

<template>
  <div ref="containerRef" class="flex-1 overflow-y-auto p-4 space-y-4 bg-base-100">
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
    <div class="h-2"></div>
  </div>
</template>
