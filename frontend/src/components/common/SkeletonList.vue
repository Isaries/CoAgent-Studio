<script setup lang="ts">
withDefaults(
  defineProps<{
    rows?: number
  }>(),
  {
    rows: 5
  }
)
</script>

<template>
  <div class="space-y-3">
    <div v-for="i in rows" :key="i" class="flex items-center gap-3 p-3 bg-base-100 rounded-lg">
      <div class="skeleton h-10 w-10 rounded-full shrink-0"></div>
      <div class="flex-1 space-y-2">
        <div class="skeleton h-4 w-3/4"></div>
        <div class="skeleton h-3 w-1/2"></div>
      </div>
    </div>
  </div>
</template>
