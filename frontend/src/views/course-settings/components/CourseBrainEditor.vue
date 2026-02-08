<script setup lang="ts">
import { computed, ref, onMounted, watch } from 'vue'
import { AgentType, ModelProvider, TriggerType } from '../../../types/enums'
import type { AgentConfig } from '../../../types/agent'
import { userKeyService, type UserAPIKey } from '../../../services/userKeyService'
import ExternalAgentForm from './ExternalAgentForm.vue'

const props = defineProps<{
  modelValue: AgentConfig | null
  loading: boolean
  agentType: AgentType
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', val: AgentConfig): void
  (e: 'test-external-connection'): void
}>()

const config = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val!)
})

// Check if this is an external agent
const isExternalAgent = computed(() => config.value?.is_external ?? false)

// Provider Options
const providers = Object.values(ModelProvider)

// Key Management
const userKeys = ref<UserAPIKey[]>([])
const loadingKeys = ref(false)

onMounted(async () => {
  loadingKeys.value = true
  try {
    userKeys.value = await userKeyService.listKeys()
  } catch (e) {
    console.error("Failed to load user keys", e)
  } finally {
    loadingKeys.value = false
  }
})

// Ensure user_key_ids is initialized
watch(() => config.value, (newVal) => {
  if (newVal && !newVal.user_key_ids) {
    newVal.user_key_ids = []
  }
}, { immediate: true })

const filteredKeys = computed(() => {
  if (!config.value) return []
  return userKeys.value.filter(k => k.provider === config.value!.model_provider)
})

// Handle external agent test connection
const handleTestConnection = () => {
  emit('test-external-connection')
}
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

    <!-- External Agent Configuration -->
    <div v-if="isExternalAgent" class="animate-fade-in">
      <div class="alert alert-info mb-4">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span>This is an external agent. Configure the webhook endpoint and authentication below.</span>
      </div>
      <ExternalAgentForm 
        v-model="config.external_config"
        :loading="loading"
        @test-connection="handleTestConnection"
      />
    </div>

    <!-- Internal Agent Configuration -->
    <template v-else>
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
    </template>

    <!-- Internal Agent Only: Triggers & Model Config -->
    <template v-if="!isExternalAgent">
    <!-- Triggers & Behavior -->
    <div class="card bg-base-100 shadow-sm border border-base-200">
      <div class="card-body">
         <h3 class="card-title text-sm uppercase tracking-wide opacity-70">Behavior & Triggers</h3>
         <div v-if="config.trigger_config" class="grid grid-cols-1 md:grid-cols-2 gap-4">
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
         <div v-else class="text-base-content/50 text-sm">
           No trigger configuration set.
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

         <!-- API Key Selection -->
         <div class="divider text-xs opacity-50">API CREDENTIALS</div>
         
         <div v-if="loadingKeys" class="text-sm opacity-50">Loading your keys...</div>
         <div v-else>
           <div class="border rounded-lg p-4 bg-base-50">
             <h4 class="font-medium text-sm mb-2 text-gray-700">Select Keys from Wallet</h4>
             <p class="text-xs text-gray-500 mb-3">
                Select one or more keys for redundancy. The agent will try them in order.
                <router-link to="/my-keys" class="text-primary hover:underline ml-1">Manage Keys</router-link>
             </p>

             <div v-if="filteredKeys.length === 0" class="text-sm text-yellow-600 bg-yellow-50 p-2 rounded">
                No keys found for {{ config.model_provider }}. Please add one in your wallet.
             </div>

             <div v-else class="space-y-2 max-h-40 overflow-y-auto">
               <label v-for="k in filteredKeys" :key="k.id" class="flex items-center gap-3 p-2 hover:bg-white rounded cursor-pointer border border-transparent hover:border-gray-200 transition-colors">
                  <input 
                    type="checkbox" 
                    :value="k.id" 
                    v-model="config.user_key_ids" 
                    class="checkbox checkbox-primary checkbox-sm" 
                  />
                  <div class="flex flex-col">
                    <span class="text-sm font-medium">{{ k.alias }}</span>
                    <span class="text-xs opacity-50 font-mono">{{ k.masked_key }}</span>
                  </div>
               </label>
             </div>
           </div>
         </div>
      </div>
    </div>
    </template>
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
