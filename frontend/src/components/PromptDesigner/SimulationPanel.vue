<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import ModernRequirementInput from './ModernRequirementInput.vue'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'

const md = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
  typographer: true
})

interface Props {
  requirement: string
  context: string
  refineCurrent: boolean
  loading: boolean
  simulationOutput: string
}

const props = defineProps<Props>()
const emit = defineEmits([
  'update:requirement',
  'update:context',
  'update:refineCurrent',
  'generate',
  'clearOutput'
])

// Refs
const messagesEndRef = ref<HTMLElement | null>(null)

const requirementModel = computed({
  get: () => props.requirement,
  set: (val) => emit('update:requirement', val)
})

const contextModel = computed({
  get: () => props.context,
  set: (val) => emit('update:context', val)
})

const refineCurrentModel = computed({
  get: () => props.refineCurrent,
  set: (val) => emit('update:refineCurrent', val)
})

// Markdown Rendering
const renderedOutput = computed(() => {
  if (!props.simulationOutput) return ''
  const rawHtml = md.render(props.simulationOutput)
  return DOMPurify.sanitize(rawHtml)
})

// Scroll to bottom when output changes
watch(() => props.simulationOutput, async () => {
    await nextTick()
    scrollToBottom()
})

const scrollToBottom = () => {
   if (messagesEndRef.value) {
     messagesEndRef.value.scrollIntoView({ behavior: 'smooth' })
   }
}

const copyOutput = () => {
  navigator.clipboard.writeText(props.simulationOutput)
}
</script>

<template>
  <div class="flex flex-col h-full bg-[#181818] relative">
    
    <!-- Top: Chat History / Preview Area -->
    <div class="flex-1 overflow-y-auto p-6 scroll-smooth custom-scrollbar relative">
       
       <!-- Empty State -->
       <div v-if="!simulationOutput && !loading" class="h-full flex flex-col items-center justify-center opacity-30 select-none">
          <div class="w-16 h-16 bg-white/10 rounded-full flex items-center justify-center mb-4">
             <span class="text-3xl">💬</span>
          </div>
          <p class="text-sm font-mono">Test Playground</p>
          <p class="text-xs text-gray-500 mt-2">Enter a requirement below to simulate the agent.</p>
       </div>

       <!-- Loading State -->
       <div v-if="loading" class="flex justify-start mb-6 animate-pulse">
          <div class="flex gap-3 max-w-[80%]">
             <div class="w-8 h-8 rounded-full bg-purple-500/20 flex flex-shrink-0 items-center justify-center border border-purple-500/30">
                <span class="loading loading-spinner loading-xs text-purple-400"></span>
             </div>
             <div class="space-y-2">
                <div class="h-4 w-32 bg-white/10 rounded"></div>
                <div class="h-4 w-48 bg-white/5 rounded"></div>
             </div>
          </div>
       </div>

       <!-- AI Response Bubble -->
       <div v-if="simulationOutput" class="flex justify-start mb-10 group">
          <div class="flex gap-4 w-full max-w-4xl">
             <!-- Avatar -->
             <div class="w-8 h-8 rounded-full bg-purple-600 flex flex-shrink-0 items-center justify-center shadow-lg shadow-purple-900/50 mt-1">
                <span class="text-xs font-bold text-white">AI</span>
             </div>
             
             <!-- Content -->
             <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 mb-1">
                   <span class="text-xs font-bold text-gray-300">Design Agent</span>
                   <span class="text-[10px] text-gray-600">{{ new Date().toLocaleTimeString() }}</span>
                   <div class="flex-1"></div>
                   
                   <!-- Actions -->
                   <div class="opacity-0 group-hover:opacity-100 transition-opacity flex gap-2">
                      <button @click="copyOutput" class="btn btn-xs btn-ghost text-gray-400 hover:text-white" title="Copy Markdown">
                         <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                      </button>
                      <button @click="$emit('clearOutput')" class="btn btn-xs btn-ghost text-error opacity-70 hover:opacity-100" title="Clear">
                         <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>
                      </button>
                   </div>
                </div>
                
                <!-- Markdown Content -->
                <div class="markdown-body text-sm leading-relaxed text-gray-300 p-4 bg-[#232323] rounded-2xl rounded-tl-none border border-white/5 shadow-sm">
                   <div v-html="renderedOutput"></div>
                </div>
             </div>
          </div>
       </div>

       <div ref="messagesEndRef"></div>
    </div>

    <!-- Bottom: Chat Input -->
    <div class="border-t border-white/5 bg-[#1e1e1e] p-4 relative z-20 shadow-[0_-5px_20px_rgba(0,0,0,0.3)]">
       <div class="max-w-4xl mx-auto">
          <ModernRequirementInput
             v-model:requirement="requirementModel"
             v-model:context="contextModel"
             v-model:refine-current="refineCurrentModel"
             :can-edit="true" 
             :loading="loading"
             :compact-mode="true"
             @generate="$emit('generate')"
          />
       </div>
    </div>

  </div>
</template>

<style>
/* Custom Scrollbar */
.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 10px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.2);
}

/* Markdown Styles (Minimal Reset for Dark Mode) */
.markdown-body pre {
  background-color: #111 !important;
  border-radius: 8px;
  padding: 1rem;
  overflow-x: auto;
  margin: 1rem 0;
  border: 1px solid rgba(255, 255, 255, 0.1);
}
.markdown-body code {
  font-family: 'Fira Code', monospace;
  font-size: 0.9em;
  color: #a5b4fc;
}
.markdown-body p {
  margin-bottom: 0.8em;
}
.markdown-body ul, .markdown-body ol {
  padding-left: 1.5em;
  margin-bottom: 1em;
}
.markdown-body ul {
  list-style-type: disc;
}
.markdown-body ol {
  list-style-type: decimal;
}
.markdown-body h1, .markdown-body h2, .markdown-body h3 {
  color: #fff;
  font-weight: bold;
  margin-top: 1.5em;
  margin-bottom: 0.5em;
}
.markdown-body strong {
  color: #fff;
  font-weight: 600;
}
.markdown-body blockquote {
  border-left: 3px solid #6366f1;
  padding-left: 1rem;
  color: #9ca3af;
  font-style: italic;
}
</style>
