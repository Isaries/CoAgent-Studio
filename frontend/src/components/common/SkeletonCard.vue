<script setup lang="ts">
withDefaults(defineProps<{
  lines?: number
  showAction?: boolean
}>(), {
  lines: 3,
  showAction: false,
})
</script>

<template>
  <div class="card bg-base-100 shadow-sm">
    <div class="card-body">
      <div class="skeleton h-5 w-3/4"></div>
      <div
        v-for="i in lines - 1"
        :key="i"
        class="skeleton h-3 mt-2"
        :class="i === lines - 1 ? 'w-1/3' : 'w-full'"
      ></div>
      <div v-if="showAction" class="card-actions justify-end mt-4">
        <div class="skeleton h-8 w-16"></div>
      </div>
    </div>
  </div>
</template>
