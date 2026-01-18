<script setup lang="ts">
import { computed, ref } from 'vue'

interface Props {
  modelValue: string
  readOnly?: boolean
}

const props = defineProps<Props>()
const emit = defineEmits(['update:modelValue'])

const textareaRef = ref<HTMLTextAreaElement | null>(null)
const lineNumberRef = ref<HTMLElement | null>(null)

const lineCount = computed(() => {
  return props.modelValue.split('\n').length || 1
})

const value = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})


const handleScroll = () => {
  if (lineNumberRef.value && textareaRef.value) {
    lineNumberRef.value.scrollTop = textareaRef.value.scrollTop
  }
}
</script>

<template>
  <div class="flex flex-col h-full bg-[#1e1e1e] overflow-hidden group border-r border-[#3e3e42]">
    <!-- Header (File Tab) -->
    <div class="flex items-center justify-between px-0 bg-[#252526] border-b border-[#3e3e42]">
       <div class="flex items-center">
         <div class="px-4 py-2 bg-[#1e1e1e] border-t-2 border-primary text-gray-200 text-xs font-mono flex items-center gap-2">
            <span class="text-blue-400">📝</span>
            system_prompt.md
            <span class="ml-2 w-2 h-2 rounded-full bg-white/20" :class="{ '!bg-primary': !readOnly }"></span>
         </div>
       </div>
       
       <div class="flex gap-3 px-4">
         <span class="text-[10px] text-gray-500 font-mono self-center">{{ lineCount }} lines</span>
         <div class="flex gap-1 self-center">
            <span class="w-2 h-2 rounded-full bg-red-500/20"></span>
            <span class="w-2 h-2 rounded-full bg-yellow-500/20"></span>
            <span class="w-2 h-2 rounded-full bg-green-500/20"></span>
         </div>
       </div>
    </div>
    
    <!-- Editor Area with Line Numbers (Simulated) -->
    <div class="flex-1 relative flex">
      <!-- Line Numbers Gutter -->
      <div ref="lineNumberRef" class="w-10 bg-[#1e1e1e] border-r border-[#3e3e42] pt-4 text-right pr-2 select-none hidden md:block overflow-hidden relative">
        <div v-for="n in Math.min(lineCount, 9999)" :key="n" class="text-[10px] font-mono text-[#858585] leading-relaxed h-[20px]">
          {{ n }}
        </div>
      </div>

      <!-- Actual Editor -->
      <textarea
        ref="textareaRef"
        v-model="value"
        class="flex-1 w-full bg-[#1e1e1e] text-[#d4d4d4] p-4 font-mono text-sm resize-none focus:outline-none leading-relaxed selection:bg-primary/30"
        :readonly="readOnly"
        placeholder="// Write your agent's system prompt logic here..."
        spellcheck="false"
        style="font-family: 'Fira Code', 'JetBrains Mono', 'Menlo', 'Consolas', monospace; line-height: 20px;"
        @scroll="handleScroll"
      ></textarea>
    </div>
  </div>
</template>

<style scoped>
/* Scrollbar Styling */
textarea::-webkit-scrollbar {
  width: 10px;
  background: #1e1e1e;
}
textarea::-webkit-scrollbar-thumb {
  background: #424242;
  border-right: 2px solid #1e1e1e;
}
textarea::-webkit-scrollbar-thumb:hover {
  background: #4f4f4f;
}
</style>
