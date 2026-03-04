<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps<{
  modelValue: string
  matchCount: number
  currentMatch: number
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'next'): void
  (e: 'prev'): void
  (e: 'close'): void
}>()
</script>

<template>
  <div class="flex items-center gap-2 px-4 py-2 bg-base-200 border-b border-base-300">
    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-base-content/50" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
      <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
    </svg>
    <input
      type="text"
      :value="modelValue"
      @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
      :placeholder="t('room.searchMessages')"
      class="input input-sm input-ghost flex-1 focus:outline-none"
      autofocus
    />
    <span v-if="modelValue" class="text-xs text-base-content/50 whitespace-nowrap">
      {{ matchCount > 0 ? `${currentMatch + 1}/${matchCount}` : '0/0' }}
    </span>
    <div class="join" v-if="modelValue">
      <button class="btn btn-ghost btn-xs join-item" @click="emit('prev')" :disabled="matchCount === 0">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M5 15l7-7 7 7" />
        </svg>
      </button>
      <button class="btn btn-ghost btn-xs join-item" @click="emit('next')" :disabled="matchCount === 0">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
    </div>
    <button class="btn btn-ghost btn-xs btn-circle" @click="emit('close')">
      <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
      </svg>
    </button>
  </div>
</template>
