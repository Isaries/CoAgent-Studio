<script setup lang="ts">
import { ref } from 'vue'

const emit = defineEmits<{
  (e: 'send', text: string): void
}>()

const message = ref('')

const send = () => {
    if (!message.value.trim()) return
    emit('send', message.value)
    message.value = ''
}
</script>

<template>
  <div class="flex gap-2 p-2 bg-base-200 rounded-lg">
    <input 
        v-model="message" 
        @keyup.enter="send"
        type="text" 
        placeholder="Type your message..." 
        class="input input-bordered flex-1 focus:outline-none" 
    />
    <button @click="send" class="btn btn-primary">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-5 h-5">
        <path d="M3.478 2.405a.75.75 0 00-.926.94l2.432 7.905H13.5a.75.75 0 010 1.5H4.984l-2.432 7.905a.75.75 0 00.926.94 60.519 60.519 0 0018.445-8.986.75.75 0 000-1.218A60.517 60.517 0 003.478 2.405z" />
      </svg>
    </button>
  </div>
</template>
