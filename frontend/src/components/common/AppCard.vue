<script setup lang="ts">
withDefaults(
  defineProps<{
    variant?: 'default' | 'hover' | 'bordered'
    padding?: 'none' | 'sm' | 'md' | 'lg'
  }>(),
  {
    variant: 'default',
    padding: 'none'
  }
)
</script>

<template>
  <div
    class="card bg-base-100 shadow-sm"
    :class="{
      'hover:shadow-md transition-shadow': variant === 'hover',
      'border border-base-300 hover:border-primary hover:shadow-md transition-all':
        variant === 'bordered',
      'p-2': padding === 'sm',
      'p-4': padding === 'md',
      'p-6': padding === 'lg'
    }"
  >
    <slot />
  </div>
</template>
