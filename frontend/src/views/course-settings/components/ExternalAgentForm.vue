<script setup lang="ts">
import { computed, ref } from 'vue'
import type { ExternalAgentConfig } from '../../../types/agent'

const props = defineProps<{
  modelValue: ExternalAgentConfig | null | undefined
  loading?: boolean
  disabled?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', val: ExternalAgentConfig): void
  (e: 'test-connection'): void
}>()

// Initialize config with defaults if null
const config = computed({
  get: () => props.modelValue ?? {
    webhook_url: '',
    auth_type: 'none' as const,
    auth_token: '',
    oauth_config: undefined,
    timeout_ms: 30000,
    fallback_message: 'External agent is temporarily unavailable.',
    callback_token: '',
  },
  set: (val) => emit('update:modelValue', val)
})

const authTypes = [
  { value: 'none', label: 'No Authentication' },
  { value: 'bearer', label: 'Bearer Token' },
  { value: 'oauth2', label: 'OAuth2 Client Credentials' },
]

const showOAuthConfig = computed(() => config.value.auth_type === 'oauth2')
const showBearerConfig = computed(() => config.value.auth_type === 'bearer')

const updateField = <K extends keyof ExternalAgentConfig>(key: K, value: ExternalAgentConfig[K]) => {
  emit('update:modelValue', { ...config.value, [key]: value })
}

const updateOAuthField = (key: string, value: string) => {
  const oauth = config.value.oauth_config ?? {
    token_url: '',
    client_id: '',
    client_secret: '',
    scope: '',
  }
  emit('update:modelValue', {
    ...config.value,
    oauth_config: { ...oauth, [key]: value }
  })
}

const testing = ref(false)
const testConnection = async () => {
  testing.value = true
  emit('test-connection')
  // Parent component handles actual test
  setTimeout(() => testing.value = false, 2000)
}

// Generate a random callback token
const generateCallbackToken = () => {
  const token = crypto.randomUUID().replace(/-/g, '')
  updateField('callback_token', token)
}
</script>

<template>
  <div class="space-y-6">
    <!-- Webhook URL -->
    <div class="card bg-base-100 shadow-sm border border-base-200">
      <div class="card-body">
        <h3 class="card-title text-sm uppercase tracking-wide opacity-70">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
          </svg>
          Webhook Endpoint
        </h3>
        
        <div class="form-control">
          <label class="label">
            <span class="label-text font-bold">Webhook URL</span>
            <span class="label-text-alt">The external agent's HTTP endpoint</span>
          </label>
          <input 
            type="url" 
            :value="config.webhook_url"
            @input="updateField('webhook_url', ($event.target as HTMLInputElement).value)"
            class="input input-bordered w-full font-mono text-sm"
            placeholder="https://your-agent.example.com/a2a/receive"
            :disabled="disabled"
          />
        </div>

        <div class="form-control mt-4">
          <label class="label">
            <span class="label-text font-bold">Timeout (ms)</span>
            <span class="label-text-alt">Max wait time for response</span>
          </label>
          <input 
            type="number" 
            :value="config.timeout_ms"
            @input="updateField('timeout_ms', parseInt(($event.target as HTMLInputElement).value))"
            class="input input-bordered w-32"
            :disabled="disabled"
          />
        </div>
      </div>
    </div>

    <!-- Authentication -->
    <div class="card bg-base-100 shadow-sm border border-base-200">
      <div class="card-body">
        <h3 class="card-title text-sm uppercase tracking-wide opacity-70">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
          </svg>
          Authentication
        </h3>

        <div class="form-control">
          <label class="label">
            <span class="label-text font-bold">Auth Type</span>
          </label>
          <select 
            :value="config.auth_type"
            @change="updateField('auth_type', ($event.target as HTMLSelectElement).value as any)"
            class="select select-bordered w-full"
            :disabled="disabled"
          >
            <option v-for="t in authTypes" :key="t.value" :value="t.value">
              {{ t.label }}
            </option>
          </select>
        </div>

        <!-- Bearer Token -->
        <div v-if="showBearerConfig" class="form-control mt-4">
          <label class="label">
            <span class="label-text font-bold">Bearer Token</span>
            <span class="label-text-alt">Token to include in Authorization header</span>
          </label>
          <input 
            type="password" 
            :value="config.auth_token"
            @input="updateField('auth_token', ($event.target as HTMLInputElement).value)"
            class="input input-bordered w-full font-mono"
            placeholder="your-secret-token"
            :disabled="disabled"
          />
        </div>

        <!-- OAuth2 Config -->
        <div v-if="showOAuthConfig" class="space-y-4 mt-4 p-4 bg-base-200/50 rounded-lg">
          <div class="form-control">
            <label class="label"><span class="label-text">Token URL</span></label>
            <input 
              type="url" 
              :value="config.oauth_config?.token_url"
              @input="updateOAuthField('token_url', ($event.target as HTMLInputElement).value)"
              class="input input-bordered w-full font-mono text-sm"
              placeholder="https://auth.example.com/oauth/token"
              :disabled="disabled"
            />
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div class="form-control">
              <label class="label"><span class="label-text">Client ID</span></label>
              <input 
                type="text" 
                :value="config.oauth_config?.client_id"
                @input="updateOAuthField('client_id', ($event.target as HTMLInputElement).value)"
                class="input input-bordered w-full"
                :disabled="disabled"
              />
            </div>
            <div class="form-control">
              <label class="label"><span class="label-text">Client Secret</span></label>
              <input 
                type="password" 
                :value="config.oauth_config?.client_secret"
                @input="updateOAuthField('client_secret', ($event.target as HTMLInputElement).value)"
                class="input input-bordered w-full"
                :disabled="disabled"
              />
            </div>
          </div>
          <div class="form-control">
            <label class="label"><span class="label-text">Scope (optional)</span></label>
            <input 
              type="text" 
              :value="config.oauth_config?.scope"
              @input="updateOAuthField('scope', ($event.target as HTMLInputElement).value)"
              class="input input-bordered w-full"
              placeholder="read write"
              :disabled="disabled"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- Callback Token (for external agent to call back) -->
    <div class="card bg-base-100 shadow-sm border border-base-200">
      <div class="card-body">
        <h3 class="card-title text-sm uppercase tracking-wide opacity-70">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
          </svg>
          Callback Authentication
        </h3>
        <p class="text-xs text-base-content/60 mb-4">
          Token the external agent must use when calling back to this system via webhook.
        </p>

        <div class="form-control">
          <label class="label">
            <span class="label-text font-bold">Callback Token</span>
          </label>
          <div class="flex gap-2">
            <input 
              type="text" 
              :value="config.callback_token"
              @input="updateField('callback_token', ($event.target as HTMLInputElement).value)"
              class="input input-bordered flex-1 font-mono text-sm"
              placeholder="Generated token for X-Agent-Token header"
              :disabled="disabled"
            />
            <button 
              class="btn btn-outline btn-sm"
              @click="generateCallbackToken"
              :disabled="disabled"
            >
              Generate
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Fallback Message -->
    <div class="card bg-base-100 shadow-sm border border-base-200">
      <div class="card-body">
        <h3 class="card-title text-sm uppercase tracking-wide opacity-70">Fallback Behavior</h3>
        
        <div class="form-control">
          <label class="label">
            <span class="label-text font-bold">Fallback Message</span>
            <span class="label-text-alt">Shown when agent is unavailable</span>
          </label>
          <textarea 
            :value="config.fallback_message"
            @input="updateField('fallback_message', ($event.target as HTMLTextAreaElement).value)"
            class="textarea textarea-bordered h-20"
            placeholder="The external agent is temporarily unavailable."
            :disabled="disabled"
          ></textarea>
        </div>
      </div>
    </div>

    <!-- Test Connection Button -->
    <div class="flex justify-end">
      <button 
        class="btn btn-primary"
        :class="{ 'loading': testing }"
        @click="testConnection"
        :disabled="disabled || !config.webhook_url || testing"
      >
        <svg v-if="!testing" xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
        {{ testing ? 'Testing...' : 'Test Connection' }}
      </button>
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
