<script setup lang="ts">
import { computed } from 'vue'
import { AgentType, ModelProvider, TriggerType } from '../../../types/enums'
import type { AgentConfig } from '../../../types/agent'

const props = defineProps<{
  modelValue: AgentConfig | null
  loading: boolean
  agentType: AgentType
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', val: AgentConfig): void
}>()

const config = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val!)
})

// Provider Options
const providers = Object.values(ModelProvider)
</script>

<template>
  <div v-if="loading" class="flex justify-center p-12">
    <span class="loading loading-spinner loading-lg"></span>
  </div>

  <div v-else-if="!config" class="alert alert-warning">
    <span>No configuration found for this agent type. Please initialize it.</span>
  </div>

  <div v-else class="flex flex-col gap-6 animate-fade-in">
    <div class="flex items-center justify-between p-1">
       <span class="text-xs font-bold opacity-50 uppercase tracking-widest pl-1">Status</span>
       <div class="form-control">
         <label class="label cursor-pointer gap-2">
           <span class="label-text font-bold" :class="config.is_active ? 'text-primary' : ''">
             {{ config.is_active ? 'Active' : 'Inactive' }}
           </span>
           <input type="checkbox" class="toggle toggle-primary toggle-sm" v-model="config.is_active" />
         </label>
       </div>
    </div>

    <!-- Main Prompts -->
    <div class="card bg-base-100 shadow-sm border border-base-200">
      <div class="card-body">
        <h3 class="card-title text-sm uppercase tracking-wide opacity-70">Core Logic</h3>
        
        <div class="form-control">
          <label class="label">
            <span class="label-text font-bold">System Prompt</span>
            <span class="label-text-alt">The brain of the agent</span>
          </label>
          <textarea 
            v-model="config.system_prompt" 
            class="textarea textarea-bordered h-64 font-mono text-sm leading-relaxed"
            placeholder="You are a helpful teaching assistant..."
          ></textarea>
        </div>
      </div>
    </div>

    <!-- Triggers & Behavior -->
    <div class="card bg-base-100 shadow-sm border border-base-200">
      <div class="card-body">
         <h3 class="card-title text-sm uppercase tracking-wide opacity-70">Behavior & Triggers</h3>
         <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="form-control">
              <label class="label"><span class="label-text">Trigger Type</span></label>
              <select v-model="config.trigger_config.type" class="select select-bordered w-full">
                <option :value="TriggerType.MESSAGE_COUNT">Message Count</option>
                <option :value="TriggerType.TIME_INTERVAL">Time Interval</option>
                <option :value="TriggerType.MANUAL">Manual Only</option>
              </select>
            </div>
            
            <div class="form-control" v-if="config.trigger_config.type !== TriggerType.MANUAL">
              <label class="label"><span class="label-text">Threshold Value</span></label>
              <input type="number" v-model.number="config.trigger_config.value" class="input input-bordered w-full" />
              <label class="label">
                <span class="label-text-alt opacity-60">
                  {{ config.trigger_config.type === TriggerType.MESSAGE_COUNT ? 'Messages' : 'Seconds' }}
                </span>
              </label>
            </div>
         </div>
      </div>
    </div>

    <!-- Model Settings -->
    <div class="card bg-base-100 shadow-sm border border-base-200">
      <div class="card-body">
         <h3 class="card-title text-sm uppercase tracking-wide opacity-70">Model Configuration</h3>
         
         <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
           <div class="form-control">
             <label class="label"><span class="label-text">Provider</span></label>
             <select v-model="config.model_provider" class="select select-bordered w-full">
               <option v-for="p in providers" :key="p" :value="p">{{ p }}</option>
             </select>
           </div>

           <div class="form-control">
             <label class="label"><span class="label-text">Model</span></label>
             <input type="text" v-model="config.model" class="input input-bordered w-full" />
           </div>
           
           <div class="form-control">
             <label class="label"><span class="label-text">Context Window</span></label>
             <input type="number" v-model.number="config.context_window" class="input input-bordered w-full" />
           </div>
         </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.animate-fade-in {
  animation: fadeIn 0.3s ease-in-out;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(5px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
