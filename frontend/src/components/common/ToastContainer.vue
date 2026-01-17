<script setup lang="ts">
import { useToastStore } from '../../stores/toast'

const toastStore = useToastStore()
</script>

<template>
  <div class="toast toast-end z-50">
    <div
      v-for="toast in toastStore.toasts"
      :key="toast.id"
      class="alert shadow-lg transition-all duration-300"
      :class="{
        'alert-info': toast.type === 'info',
        'alert-success': toast.type === 'success',
        'alert-warning': toast.type === 'warning',
        'alert-error': toast.type === 'error'
      }"
    >
      <span>{{ toast.message }}</span>
      <button @click="toastStore.remove(toast.id)" class="btn btn-xs btn-ghost btn-circle">
        ✕
      </button>
    </div>
  </div>
</template>

<style scoped>
/* Basic fade transition */
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(20px);
}
</style>
