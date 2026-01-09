<script setup lang="ts">
import { RouterView } from 'vue-router'
import ToastContainer from './components/common/ToastContainer.vue'
import GlobalConfirmModal from './components/common/GlobalConfirmModal.vue'
</script>

<template>
  <div class="min-h-screen bg-base-100 text-base-content font-sans">
    <!-- Main Layout Container -->
    <RouterView />
    <ToastContainer />
    <GlobalConfirmModal />
  </div>
</template>
