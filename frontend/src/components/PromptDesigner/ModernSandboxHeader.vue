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
  <div class="p-3 bg-base-100 rounded-lg border border-primary/20 shadow-[0_0_15px_rgba(var(--p),0.1)] relative overflow-hidden group">
      
      <!-- Glow Effect -->
      <div class="absolute -top-10 -right-10 w-20 h-20 bg-primary/10 rounded-full blur-2xl group-hover:bg-primary/20 transition-all"></div>

      <div class="flex items-center justify-between mb-3 relative z-10">
        <h3 class="text-xs font-bold text-primary flex items-center gap-2">
          <span class="w-2 h-2 rounded-full bg-primary animate-pulse"></span>
          SANDBOX CONFIG
        </h3>
        <button @click="$emit('apply')" class="btn btn-xs btn-ghost text-primary hover:bg-primary/10" title="Apply to Live">
          Apply
        </button>
      </div>

      <div class="space-y-3 relative z-10">
         <!-- Provider & Model Row -->
         <div class="grid grid-cols-2 gap-2">
            <div class="form-control">
              <label class="text-[10px] font-bold text-base-content/50 mb-1">Provider</label>
              <select 
                :value="modelValue.customProvider"
                @change="updateField('customProvider', ($event.target as HTMLSelectElement).value)"
                class="select select-xs select-bordered w-full bg-base-200"
              >
                <option value="gemini">Gemini</option>
                <option value="openai">OpenAI</option>
              </select>
            </div>
            <div class="form-control">
              <label class="text-[10px] font-bold text-base-content/50 mb-1">Model</label>
              <select 
                :value="modelValue.customModel"
                @change="updateField('customModel', ($event.target as HTMLSelectElement).value)"
                class="select select-xs select-bordered w-full bg-base-200"
              >
                <option value="">Default</option>
                <option v-for="m in availableSandboxModels" :key="m.value" :value="m.value">{{ m.label }}</option>
              </select>
            </div>
         </div>

         <!-- API Key -->
         <div class="form-control">
            <label class="text-[10px] font-bold text-base-content/50 mb-1">Temporary API Key</label>
            <input 
              type="password" 
              :value="modelValue.customApiKey"
              @input="updateField('customApiKey', ($event.target as HTMLInputElement).value)"
              placeholder="Paste key to override..." 
              class="input input-xs input-bordered w-full bg-base-200 font-mono text-center tracking-widest" 
            />
         </div>
      </div>
  </div>
</template>
