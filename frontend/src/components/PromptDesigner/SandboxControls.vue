<script setup lang="ts">
import { computed } from 'vue'
import { AI_MODELS } from '../../constants/ai-models'

interface SandboxState {
  enabled: boolean
  customApiKey: string
  customProvider: string
  customModel: string
  systemPrompt: string
}

interface Props {
  modelValue: SandboxState
}

const props = defineProps<Props>()
const emit = defineEmits(['update:modelValue', 'apply'])

const updateField = (field: keyof SandboxState, value: any) => {
  emit('update:modelValue', {
    ...props.modelValue,
    [field]: value
  })
}

const availableSandboxModels = computed(() => {
  if (props.modelValue.customProvider === 'gemini') return AI_MODELS.gemini
  if (props.modelValue.customProvider === 'openai') return AI_MODELS.openai
  return []
})
</script>

<template>
  <div class="p-4 bg-primary/5 rounded-lg border border-primary/20 flex flex-col gap-4">
    <div class="flex items-center gap-2 text-primary font-bold text-xs">
      <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line></svg>
      SANDBOX CONFIGURATION
    </div>
    
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
       <div class="form-control">
         <label class="label text-xs font-semibold opacity-70">Temporary API Key</label>
         <input 
           type="password" 
           :value="modelValue.customApiKey"
           @input="updateField('customApiKey', ($event.target as HTMLInputElement).value)"
           placeholder="Paste Key for Testing" 
           class="input input-sm input-bordered bg-base-100" 
         />
       </div>
       <div class="grid grid-cols-2 gap-2">
          <div class="form-control">
             <label class="label text-xs font-semibold opacity-70">Provider</label>
             <select 
               :value="modelValue.customProvider"
               @change="updateField('customProvider', ($event.target as HTMLSelectElement).value)"
               class="select select-sm select-bordered bg-base-100"
             >
               <option value="gemini">Gemini</option>
               <option value="openai">OpenAI</option>
             </select>
          </div>
          <div class="form-control">
             <label class="label text-xs font-semibold opacity-70">Model</label>
             <select 
               :value="modelValue.customModel"
               @change="updateField('customModel', ($event.target as HTMLSelectElement).value)"
               class="select select-sm select-bordered bg-base-100"
             >
               <option value="">Default</option>
               <option v-for="m in availableSandboxModels" :key="m.value" :value="m.value">{{ m.label }}</option>
             </select>
          </div>
       </div>
    </div>

    <div class="form-control">
      <label class="label text-xs font-semibold opacity-70">Design Agent Instruction Override</label>
      <textarea 
        :value="modelValue.systemPrompt"
        @input="updateField('systemPrompt', ($event.target as HTMLTextAreaElement).value)"
        class="textarea textarea-sm textarea-bordered w-full bg-base-100 font-mono text-xs" 
        placeholder="Override the system prompt for the Design Agent itself..."
        rows="2"
      ></textarea>
    </div>
    
    <button @click="$emit('apply')" class="btn btn-sm btn-outline btn-primary w-full">
      Apply Sandbox Settings to Live Config
    </button>
  </div>
</template>
