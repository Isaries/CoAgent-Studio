<script setup lang="ts">
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'

const md = new MarkdownIt()

const props = defineProps<{
  sender: string
  content: string
  isSelf: boolean
  isSystem?: boolean
  isAi?: boolean
  timestamp?: string
}>()

const bubbleClass = computed(() => {
  if (props.isSystem) return 'chat-bubble-warning'
  if (props.isAi) return 'chat-bubble-primary'
  if (props.isSelf) return 'chat-bubble-info'
  return 'chat-bubble-secondary'
})

const alignClass = computed(() => {
    return props.isSelf ? 'chat-end' : 'chat-start'
})

const renderedContent = computed(() => {
    // Only render markdown for AI or System, or maybe all?
    // Let's render for all for consistency.
    const rawHtml = md.render(props.content)
    return DOMPurify.sanitize(rawHtml)
})
</script>

<template>
  <div class="chat" :class="alignClass">
    <div class="chat-header text-xs opacity-50 mb-1">
      {{ sender }}
      <time v-if="timestamp" class="text-xs opacity-50 ml-1">{{ timestamp }}</time>
    </div>
    <div class="chat-bubble prose prose-sm max-w-none" :class="bubbleClass">
      <!-- Using v-html for markdown -->
      <div v-html="renderedContent"></div>
    </div>
    <div class="chat-footer opacity-50 text-xs">
       <!-- Status (Delivered etc) -->
    </div>
  </div>
</template>
<style>
/* Override daisyUI/Tailwind prose colors for better contrast in bubbles if needed */
.chat-bubble.prose {
    color: inherit; /* Inherit text color from bubble */
}
.chat-bubble.prose code {
    @apply bg-base-300 rounded px-1;
    color: inherit;
}
.chat-bubble.prose pre {
    @apply bg-base-300 p-2 rounded;
    color: inherit;
}
</style>
