<script setup lang="ts">
import type { KnowledgeBase } from '../../types/knowledge'
import AppModal from '../common/AppModal.vue'

defineProps<{
  modelValue: boolean
  kb: KnowledgeBase | null
  mergeableKBs: KnowledgeBase[]
  isMerging: boolean
}>()

const mergeTargetId = defineModel<string>('targetId', { default: '' })

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  merge: []
}>()
</script>

<template>
  <AppModal
    :model-value="modelValue"
    @update:model-value="emit('update:modelValue', $event)"
    title="Merge Knowledge Bases"
  >
    <p class="text-sm text-base-content/60 mb-4">
      Merge another knowledge base into <strong>{{ kb?.name }}</strong>.
      The source data will be combined into this knowledge base.
    </p>

    <div class="form-control mb-4">
      <label class="label">
        <span class="label-text font-semibold">Source Knowledge Base</span>
      </label>
      <select v-model="mergeTargetId" class="select select-bordered w-full">
        <option value="" disabled>Select a knowledge base to merge from...</option>
        <option v-for="mkb in mergeableKBs" :key="mkb.id" :value="mkb.id">
          {{ mkb.name }} ({{ mkb.node_count }} nodes, {{ mkb.edge_count }} edges)
        </option>
      </select>
    </div>

    <template #actions>
      <button class="btn btn-ghost" @click="emit('update:modelValue', false)">Cancel</button>
      <button class="btn btn-primary" :disabled="!mergeTargetId || isMerging" @click="emit('merge')">
        <span v-if="isMerging" class="loading loading-spinner loading-xs"></span>
        {{ isMerging ? 'Merging...' : 'Merge' }}
      </button>
    </template>
  </AppModal>
</template>
