<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  modelValue: string
  readOnly?: boolean
}

const props = defineProps<Props>()
const emit = defineEmits(['update:modelValue'])

const value = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})
</script>

<template>
  <div class="flex flex-col h-full bg-[#1e1e1e] overflow-hidden group">
    <!-- Header -->
    <div class="flex items-center justify-between px-4 py-2 bg-[#1e1e1e] border-b border-[#3e3e42]">
       <span class="text-xs font-mono text-gray-500 group-hover:text-gray-300 transition-colors">system_prompt.md</span>
       <div class="flex gap-2">
         <!-- Toolbar actions could go here -->
         <div class="flex gap-1">
            <span class="w-2 h-2 rounded-full bg-red-500/20"></span>
            <span class="w-2 h-2 rounded-full bg-yellow-500/20"></span>
            <span class="w-2 h-2 rounded-full bg-green-500/20"></span>
         </div>
       </div>
    </div>
    
    <!-- Editor Area -->
    <textarea
      v-model="value"
      class="flex-1 w-full bg-[#1e1e1e] text-[#d4d4d4] p-4 font-mono text-sm resize-none focus:outline-none leading-relaxed selection:bg-primary/30"
      :readonly="readOnly"
      placeholder="// Generated prompt will appear here..."
      spellcheck="false"
    ></textarea>
  </div>
</template>
