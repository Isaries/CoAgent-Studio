<script setup lang="ts">
import { ref, computed } from 'vue'
import { agentTypesService } from '../services/agentTypesService'
import type { ExternalAgentConfig } from '../types/agentTypes'
import { useToastStore } from '../stores/toast'

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'created', agentId: string): void
}>()

const toast = useToastStore()

// Form state
const formData = ref({
  name: '',
  type_name: '',
  webhook_url: '',
  auth_type: 'bearer' as 'none' | 'bearer' | 'oauth2',
  auth_token: '',
  oauth_token_url: '',
  oauth_client_id: '',
  oauth_client_secret: '',
  oauth_scope: '',
  timeout_ms: 30000,
  fallback_message: '⚠️ External agent is temporarily unavailable. Please try again later.'
})

const isSubmitting = ref(false)
const isTesting = ref(false)
const testResult = ref<{ success: boolean; latency_ms?: number; error?: string } | null>(null)

const isFormValid = computed(() => {
  if (!formData.value.name || !formData.value.type_name || !formData.value.webhook_url) {
    return false
  }
  if (formData.value.auth_type === 'bearer' && !formData.value.auth_token) {
    return false
  }
  if (formData.value.auth_type === 'oauth2') {
    if (!formData.value.oauth_token_url || !formData.value.oauth_client_id || !formData.value.oauth_client_secret) {
      return false
    }
  }
  return true
})

const buildExternalConfig = (): ExternalAgentConfig => {
  const config: ExternalAgentConfig = {
    webhook_url: formData.value.webhook_url,
    auth_type: formData.value.auth_type,
    timeout_ms: formData.value.timeout_ms,
    fallback_message: formData.value.fallback_message
  }

  if (formData.value.auth_type === 'bearer') {
    config.auth_token = formData.value.auth_token
  }

  if (formData.value.auth_type === 'oauth2') {
    config.oauth_config = {
      token_url: formData.value.oauth_token_url,
      client_id: formData.value.oauth_client_id,
      client_secret: formData.value.oauth_client_secret,
      scope: formData.value.oauth_scope
    }
  }

  return config
}

const testConnection = async () => {
  isTesting.value = true
  testResult.value = null
  
  try {
    const config = buildExternalConfig()
    
    const res = await agentTypesService.testConnectionParams({
      name: formData.value.name || 'test',
      webhook_url: config.webhook_url,
      auth_type: config.auth_type,
      auth_token: config.auth_token,
      oauth_config: config.oauth_config,
      timeout_ms: config.timeout_ms
    })
    
    if (res.data.success) {
      testResult.value = {
        success: true,
        latency_ms: res.data.latency_ms
      }
      toast.success('Connection test successful')
    } else {
      throw new Error(res.data.error || 'Connection failed')
    }
  } catch (e) {
    testResult.value = {
      success: false,
      error: e instanceof Error ? e.message : 'Connection failed'
    }
    toast.error('Connection test failed')
  } finally {
    isTesting.value = false
  }
}

const submit = async () => {
  if (!isFormValid.value) return
  
  isSubmitting.value = true
  try {
    const config = buildExternalConfig()
    
    await agentTypesService.createExternalAgent({
      name: formData.value.name,
      type: formData.value.type_name,
      webhook_url: config.webhook_url,
      auth_type: config.auth_type,
      auth_token: config.auth_token,
      oauth_config: config.oauth_config,
      timeout_ms: config.timeout_ms,
      fallback_message: config.fallback_message
    })

    toast.success('External agent registered successfully')
    emit('created', formData.value.type_name) // returning type name as ID for now
    emit('close')
  } catch (e) {
    toast.error('Failed to register external agent')
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div class="modal-box max-w-2xl">
    <h3 class="font-bold text-lg mb-4 flex items-center gap-2">
      <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
      </svg>
      Connect External Agent
    </h3>

    <form @submit.prevent="submit" class="space-y-4">
      <!-- Basic Info -->
      <div class="grid grid-cols-2 gap-4">
        <div class="form-control">
          <label class="label"><span class="label-text">Agent Name</span></label>
          <input 
            v-model="formData.name"
            type="text" 
            class="input input-bordered" 
            placeholder="My External Agent"
          />
        </div>
        <div class="form-control">
          <label class="label"><span class="label-text">Type Identifier</span></label>
          <input 
            v-model="formData.type_name"
            type="text" 
            class="input input-bordered" 
            placeholder="external_researcher"
          />
        </div>
      </div>

      <!-- Webhook URL -->
      <div class="form-control">
        <label class="label"><span class="label-text">Webhook URL</span></label>
        <input 
          v-model="formData.webhook_url"
          type="url" 
          class="input input-bordered" 
          placeholder="https://api.external-agent.com/a2a/webhook"
        />
      </div>

      <!-- Authentication -->
      <div class="form-control">
        <label class="label"><span class="label-text">Authentication Type</span></label>
        <select v-model="formData.auth_type" class="select select-bordered">
          <option value="none">None</option>
          <option value="bearer">Bearer Token</option>
          <option value="oauth2">OAuth 2.0 (Client Credentials)</option>
        </select>
      </div>

      <!-- Bearer Token -->
      <div v-if="formData.auth_type === 'bearer'" class="form-control">
        <label class="label"><span class="label-text">Bearer Token</span></label>
        <input 
          v-model="formData.auth_token"
          type="password" 
          class="input input-bordered" 
          placeholder="Enter token"
        />
      </div>

      <!-- OAuth2 Config -->
      <div v-if="formData.auth_type === 'oauth2'" class="space-y-3 p-4 bg-base-200 rounded-lg">
        <div class="form-control">
          <label class="label"><span class="label-text">Token URL</span></label>
          <input 
            v-model="formData.oauth_token_url"
            type="url" 
            class="input input-bordered input-sm" 
            placeholder="https://auth.example.com/oauth/token"
          />
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div class="form-control">
            <label class="label"><span class="label-text">Client ID</span></label>
            <input 
              v-model="formData.oauth_client_id"
              type="text" 
              class="input input-bordered input-sm" 
            />
          </div>
          <div class="form-control">
            <label class="label"><span class="label-text">Client Secret</span></label>
            <input 
              v-model="formData.oauth_client_secret"
              type="password" 
              class="input input-bordered input-sm" 
            />
          </div>
        </div>
        <div class="form-control">
          <label class="label"><span class="label-text">Scope (optional)</span></label>
          <input 
            v-model="formData.oauth_scope"
            type="text" 
            class="input input-bordered input-sm" 
            placeholder="agent:read agent:write"
          />
        </div>
      </div>

      <!-- Advanced -->
      <div class="collapse collapse-arrow bg-base-200">
        <input type="checkbox" />
        <div class="collapse-title font-medium">Advanced Settings</div>
        <div class="collapse-content space-y-3">
          <div class="form-control">
            <label class="label"><span class="label-text">Timeout (ms)</span></label>
            <input 
              v-model.number="formData.timeout_ms"
              type="number" 
              class="input input-bordered input-sm" 
            />
          </div>
          <div class="form-control">
            <label class="label"><span class="label-text">Fallback Message</span></label>
            <textarea 
              v-model="formData.fallback_message"
              class="textarea textarea-bordered textarea-sm" 
              rows="2"
            ></textarea>
          </div>
        </div>
      </div>

      <!-- Test Result -->
      <div v-if="testResult" class="alert" :class="testResult.success ? 'alert-success' : 'alert-error'">
        <span v-if="testResult.success">
          ✓ Connection successful ({{ testResult.latency_ms }}ms)
        </span>
        <span v-else>
          ✗ {{ testResult.error }}
        </span>
      </div>

      <!-- Actions -->
      <div class="modal-action">
        <button type="button" class="btn btn-ghost" @click="emit('close')">Cancel</button>
        <button 
          type="button" 
          class="btn btn-outline"
          :disabled="!formData.webhook_url || isTesting"
          @click="testConnection"
        >
          <span v-if="isTesting" class="loading loading-spinner loading-sm"></span>
          Test Connection
        </button>
        <button 
          type="submit" 
          class="btn btn-primary"
          :disabled="!isFormValid || isSubmitting"
        >
          <span v-if="isSubmitting" class="loading loading-spinner loading-sm"></span>
          Register Agent
        </button>
      </div>
    </form>
  </div>
</template>
