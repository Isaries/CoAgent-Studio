<script setup lang="ts">
import { ref } from 'vue'
import { threadService } from '../../services/threadService'
import type { ChatResponse } from '../../types/thread'

const props = defineProps<{
    agentId: string
}>()

const messages = ref<{role: 'user' | 'agent', text: string}[]>([])
const input = ref('')
const isLoading = ref(false)

const sendMessage = async () => {
    if (!input.value.trim() || isLoading.value) return

    const userMsg = input.value
    messages.value.push({ role: 'user', text: userMsg })
    input.value = ''
    isLoading.value = true

    try {
        const res: ChatResponse = await threadService.testStateless(props.agentId, { message: userMsg })
        messages.value.push({ role: 'agent', text: res.reply })
    } catch (e: any) {
        console.error(e)
        messages.value.push({ role: 'agent', text: 'Error: Failed to get response' })
    } finally {
        isLoading.value = false
    }
}
</script>

<template>
    <div class="flex flex-col h-full bg-base-100">
        <!-- Header -->
        <div class="p-4 border-b border-base-200 bg-base-50">
            <h2 class="font-bold text-lg">Agent Sandbox</h2>
            <p class="text-xs opacity-60">Stateless quick testing mode</p>
        </div>

        <!-- Chat Area -->
        <div class="flex-1 overflow-y-auto p-4 space-y-4">
            <div v-if="messages.length === 0" class="flex h-full items-center justify-center text-center opacity-50 space-y-2 flex-col">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" /></svg>
                <p class="text-sm">Envoy is ready. Say hello!</p>
            </div>

            <div v-for="(msg, idx) in messages" :key="idx" class="chat" :class="msg.role === 'user' ? 'chat-end' : 'chat-start'">
                <div class="chat-bubble whitespace-pre-wrap text-sm" :class="msg.role === 'user' ? 'chat-bubble-primary' : 'chat-bubble-base-200 bg-base-200 text-base-content'">
                    {{ msg.text }}
                </div>
            </div>

            <div v-if="isLoading" class="chat chat-start">
                <div class="chat-bubble chat-bubble-base-200 bg-base-200 text-base-content">
                    <span class="loading loading-dots loading-sm"></span>
                </div>
            </div>
        </div>

        <!-- Input Area -->
        <div class="p-4 border-t border-base-200 bg-base-50">
            <div class="join w-full">
                <input 
                    type="text" 
                    class="input input-bordered join-item flex-1" 
                    placeholder="Message the agent..." 
                    v-model="input"
                    @keyup.enter="sendMessage"
                    :disabled="isLoading"
                />
                <button 
                    class="btn btn-primary join-item" 
                    @click="sendMessage"
                    :disabled="isLoading || !input.trim()"
                >
                    Send
                </button>
            </div>
        </div>
    </div>
</template>
