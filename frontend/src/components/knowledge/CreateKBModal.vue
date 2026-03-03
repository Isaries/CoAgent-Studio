<script setup lang="ts">
import { ref, computed } from 'vue'
import { useToastStore } from '@/stores/toast'
import * as knowledgeService from '@/services/knowledgeService'
import type { KnowledgeBase, KBCreate } from '@/types/knowledge'

const props = defineProps<{
  visible: boolean
  presetSpaceId?: string
}>()

const emit = defineEmits<{
  close: []
  created: [kb: KnowledgeBase]
}>()

const toast = useToastStore()

const name = ref('')
const description = ref('')
const sourceType = ref<'conversation' | 'document'>('conversation')
const extractionModel = ref('gpt-4o-mini')
const summarizationModel = ref('gpt-4o-mini')
const spaceId = ref('')
const isSubmitting = ref(false)

const availableModels = [
  { label: 'GPT-4o Mini (Fast, Low Cost)', value: 'gpt-4o-mini' },
  { label: 'GPT-4o (Balanced)', value: 'gpt-4o' },
  { label: 'Claude Sonnet 4 (Balanced)', value: 'claude-sonnet-4-20250514' },
  { label: 'Claude Haiku 4.5 (Fast)', value: 'claude-haiku-4-5-20251001' },
  { label: 'Gemini 2.0 Flash (Fast)', value: 'gemini-2.0-flash' },
  { label: 'Gemini 1.5 Pro (High Quality)', value: 'gemini-1.5-pro' },
]

const isValid = computed(() => name.value.trim().length > 0)

function resetForm() {
  name.value = ''
  description.value = ''
  sourceType.value = 'conversation'
  extractionModel.value = 'gpt-4o-mini'
  summarizationModel.value = 'gpt-4o-mini'
  spaceId.value = props.presetSpaceId || ''
  isSubmitting.value = false
}

function handleClose() {
  resetForm()
  emit('close')
}

async function handleSubmit() {
  if (!isValid.value || isSubmitting.value) return

  isSubmitting.value = true
  try {
    const payload: KBCreate = {
      name: name.value.trim(),
      description: description.value.trim() || undefined,
      source_type: sourceType.value,
      extraction_model: extractionModel.value,
      summarization_model: summarizationModel.value,
      space_id: spaceId.value || undefined,
    }

    const kb = await knowledgeService.createKB(payload)
    toast.success(`Knowledge base "${kb.name}" created successfully`)
    emit('created', kb)
    handleClose()
  } catch (e: any) {
    toast.error(e.response?.data?.detail || 'Failed to create knowledge base')
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <dialog class="modal" :class="{ 'modal-open': visible }">
    <div class="modal-box max-w-lg">
      <button class="btn btn-sm btn-circle btn-ghost absolute right-3 top-3" @click="handleClose">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>

      <h3 class="font-bold text-lg mb-1">Create Knowledge Base</h3>
      <p class="text-sm text-base-content/60 mb-6">
        Configure a new knowledge graph for extracting and querying structured knowledge.
      </p>

      <form @submit.prevent="handleSubmit" class="flex flex-col gap-4">
        <!-- Name -->
        <div class="form-control">
          <label class="label">
            <span class="label-text font-semibold">Name <span class="text-error">*</span></span>
          </label>
          <input
            v-model="name"
            type="text"
            placeholder="e.g. Course Materials KB"
            class="input input-bordered w-full"
            maxlength="100"
            required
          />
        </div>

        <!-- Description -->
        <div class="form-control">
          <label class="label">
            <span class="label-text font-semibold">Description</span>
          </label>
          <textarea
            v-model="description"
            placeholder="Optional description of this knowledge base..."
            class="textarea textarea-bordered w-full"
            rows="2"
            maxlength="500"
          ></textarea>
        </div>

        <!-- Source Type -->
        <div class="form-control">
          <label class="label">
            <span class="label-text font-semibold">Source Type</span>
          </label>
          <select v-model="sourceType" class="select select-bordered w-full">
            <option value="conversation">Conversation - Extract from room discussions</option>
            <option value="document">Document - Extract from uploaded files</option>
          </select>
        </div>

        <!-- Model Selection Row -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="form-control">
            <label class="label">
              <span class="label-text font-semibold">Extraction Model</span>
            </label>
            <select v-model="extractionModel" class="select select-bordered w-full">
              <option v-for="m in availableModels" :key="m.value" :value="m.value">
                {{ m.label }}
              </option>
            </select>
            <label class="label">
              <span class="label-text-alt text-base-content/50">Extracts entities and relationships</span>
            </label>
          </div>

          <div class="form-control">
            <label class="label">
              <span class="label-text font-semibold">Summarization Model</span>
            </label>
            <select v-model="summarizationModel" class="select select-bordered w-full">
              <option v-for="m in availableModels" :key="m.value" :value="m.value">
                {{ m.label }}
              </option>
            </select>
            <label class="label">
              <span class="label-text-alt text-base-content/50">Generates community summaries</span>
            </label>
          </div>
        </div>

        <!-- Space ID (optional) -->
        <div class="form-control">
          <label class="label">
            <span class="label-text font-semibold">Space ID (optional)</span>
          </label>
          <input
            v-model="spaceId"
            type="text"
            placeholder="Leave empty for global scope"
            class="input input-bordered w-full"
          />
          <label class="label">
            <span class="label-text-alt text-base-content/50">Attach this KB to a specific space, or leave blank for a global knowledge base</span>
          </label>
        </div>

        <!-- Actions -->
        <div class="modal-action mt-2">
          <button type="button" class="btn btn-ghost" @click="handleClose">Cancel</button>
          <button
            type="submit"
            class="btn btn-primary"
            :disabled="!isValid || isSubmitting"
          >
            <span v-if="isSubmitting" class="loading loading-spinner loading-xs"></span>
            {{ isSubmitting ? 'Creating...' : 'Create Knowledge Base' }}
          </button>
        </div>
      </form>
    </div>
    <form method="dialog" class="modal-backdrop">
      <button @click="handleClose">close</button>
    </form>
  </dialog>
</template>
