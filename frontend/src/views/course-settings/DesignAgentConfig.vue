<script setup lang="ts">
import { computed } from 'vue'
import type { AgentConfig } from '../../types/agent'

interface Props {
  canEdit: boolean
  editPrompt: string
  designConfig: AgentConfig | null
  designApiKey: string
  loading: boolean
  requirement: string
  context: string
  refineCurrent: boolean
}

const props = defineProps<Props>()
const emit = defineEmits([
  'update:designApiKey',
  'update:requirement',
  'update:context',
  'update:refineCurrent',
  'saveKey',
  'clearKey',
  'generate'
])

// Proxies
const designApiKeyModel = computed({
  get: () => props.designApiKey,
  set: (val) => emit('update:designApiKey', val)
})

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
</script>

<template>
  <div v-if="canEdit" class="collapse collapse-arrow bg-base-200 mb-6 border border-base-300">
    <input type="checkbox" />
    <div class="collapse-title font-medium flex items-center gap-2">
      <span>✨ AI Prompt Designer</span>
    </div>
    <div class="collapse-content">
      <div class="p-2">
        <p class="mb-2 text-sm text-gray-600">Describe the persona and behavior you want.</p>

        <!-- Design Agent API Key Block -->
        <div class="form-control mb-4 p-3 bg-base-100 rounded border border-base-200">
          <label class="label pt-0"
            ><span class="label-text font-bold text-xs"
              >Design Agent API Key (for this course)</span
            ></label
          >
          <div class="join w-full">
            <input
              type="password"
              v-model="designApiKeyModel"
              :placeholder="
                designConfig?.masked_api_key
                  ? `Using: ${designConfig.masked_api_key}`
                  : 'Enter API Key for Generator...'
              "
              class="input input-sm input-bordered join-item w-full"
            />
            <button
              @click="$emit('saveKey')"
              class="btn btn-sm btn-primary join-item"
              :disabled="!designApiKey"
            >
              Save Key
            </button>
            <button
              v-if="designConfig?.masked_api_key"
              @click="$emit('clearKey')"
              class="btn btn-sm btn-ghost join-item text-error"
            >
              Clear
            </button>
          </div>
          <div class="text-[10px] text-gray-400 mt-1">
            If set, this key will be used for auto-generation for this course.
          </div>
        </div>

        <textarea
          v-model="requirementModel"
          class="textarea textarea-bordered w-full mb-2"
          placeholder="e.g. A friendly tutor who explains concepts using pizza analogies..."
        ></textarea>
        <input
          v-model="contextModel"
          type="text"
          placeholder="Context (e.g. Intro to Python)"
          class="input input-bordered w-full mb-2"
        />

        <div class="form-control mb-2">
          <label class="label cursor-pointer justify-start gap-4">
            <input
              type="checkbox"
              v-model="refineCurrentModel"
              class="checkbox checkbox-sm"
              :disabled="!editPrompt"
            />
            <span class="label-text"
              >Refine based on current prompt (Pass current version to Design Agent)</span
            >
          </label>
        </div>

        <button
          @click="$emit('generate')"
          class="btn btn-secondary btn-sm w-full"
          :disabled="loading"
        >
          {{ loading ? 'Generating...' : 'Auto-Generate Prompt' }}
        </button>
      </div>
    </div>
  </div>
</template>
