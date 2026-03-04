<script setup lang="ts">
import { useConfirm } from '../../composables/useConfirm'

const { isVisible, title, message, onConfirm, onCancel } = useConfirm()
</script>

<template>
  <dialog
    class="modal"
    :class="{ 'modal-open': isVisible }"
    role="alertdialog"
    aria-modal="true"
    :aria-labelledby="'confirm-modal-title'"
    :aria-describedby="'confirm-modal-desc'"
  >
    <div class="modal-box">
      <h3 id="confirm-modal-title" class="font-bold text-lg text-warning">{{ title }}</h3>
      <p id="confirm-modal-desc" class="py-4">{{ message }}</p>
      <div class="modal-action">
        <button class="btn" @click="onCancel">Cancel</button>
        <button class="btn btn-error" @click="onConfirm">Confirm</button>
      </div>
    </div>
    <form method="dialog" class="modal-backdrop">
      <button @click="onCancel">close</button>
    </form>
  </dialog>
</template>
