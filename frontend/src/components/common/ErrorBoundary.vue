<script setup lang="ts">
import { ref, onErrorCaptured } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const error = ref<Error | null>(null)

onErrorCaptured((err: Error) => {
  error.value = err
  console.error('[ErrorBoundary]', err)
  return false
})

const retry = () => {
  error.value = null
}
</script>

<template>
  <div v-if="error" class="flex flex-col items-center justify-center py-20 px-6">
    <svg
      xmlns="http://www.w3.org/2000/svg"
      class="h-16 w-16 text-error mb-4"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      stroke-width="1.5"
    >
      <path
        stroke-linecap="round"
        stroke-linejoin="round"
        d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z"
      />
    </svg>
    <h2 class="text-xl font-bold text-error mb-2">{{ t('error.title') }}</h2>
    <p class="text-base-content/60 mb-4 text-center max-w-md">{{ error.message }}</p>
    <button class="btn btn-primary" @click="retry">{{ t('error.retry') }}</button>
  </div>
  <slot v-else />
</template>
