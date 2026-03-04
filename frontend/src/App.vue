<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterView } from 'vue-router'
import ToastContainer from './components/common/ToastContainer.vue'
import GlobalConfirmModal from './components/common/GlobalConfirmModal.vue'
import { usePreferencesStore } from './stores/preferences'

onMounted(() => {
  // Ensure theme is applied on app mount
  const prefs = usePreferencesStore()
  document.documentElement.setAttribute('data-theme', prefs.theme)
})
</script>

<template>
  <div class="min-h-screen bg-base-100 text-base-content font-sans">
    <!-- Main Layout Container -->
    <RouterView />
    <ToastContainer />
    <GlobalConfirmModal />
  </div>
</template>
