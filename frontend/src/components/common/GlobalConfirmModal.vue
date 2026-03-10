<script setup lang="ts">
import { useConfirm } from '../../composables/useConfirm'
import AppModal from './AppModal.vue'

const { isVisible, title, message, onConfirm, onCancel } = useConfirm()
</script>

<template>
  <AppModal
    :model-value="isVisible"
    :title="title"
    size="md"
    :closable="true"
    @update:model-value="(v: boolean) => { if (!v) onCancel() }"
    @close="onCancel"
  >
    <p class="py-4">{{ message }}</p>
    <template #actions>
      <button class="btn" @click="onCancel">Cancel</button>
      <button class="btn btn-error" @click="onConfirm">Confirm</button>
    </template>
  </AppModal>
</template>
