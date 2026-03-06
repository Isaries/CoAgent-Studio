<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()

const shortcuts = [
  {
    scope: 'global',
    items: [
      { keys: 'Ctrl+K', label: 'commandPalette' },
      { keys: '?', label: 'showShortcuts' },
      { keys: 'Escape', label: 'closeModal' }
    ]
  },
  {
    scope: 'navigation',
    items: [
      { keys: 'g then h', label: 'goHome' },
      { keys: 'g then s', label: 'goSpaces' }
    ]
  }
]
</script>

<template>
  <dialog class="modal" :class="{ 'modal-open': modelValue }">
    <div class="modal-box max-w-md">
      <h3 class="font-bold text-lg mb-4">{{ t('shortcuts.title') }}</h3>
      <div v-for="group in shortcuts" :key="group.scope" class="mb-4">
        <h4 class="text-sm font-semibold text-base-content/60 uppercase tracking-wider mb-2">
          {{ t(`shortcuts.${group.scope}`) }}
        </h4>
        <div class="space-y-2">
          <div
            v-for="item in group.items"
            :key="item.keys"
            class="flex items-center justify-between py-1"
          >
            <span class="text-sm">{{ t(`shortcuts.${item.label}`) }}</span>
            <div class="flex gap-1">
              <kbd v-for="key in item.keys.split(' then ')" :key="key" class="kbd kbd-sm">{{
                key
              }}</kbd>
            </div>
          </div>
        </div>
      </div>
      <div class="modal-action">
        <button class="btn btn-ghost btn-sm" @click="emit('update:modelValue', false)">
          {{ t('common.close') }}
        </button>
      </div>
    </div>
    <form method="dialog" class="modal-backdrop">
      <button @click="emit('update:modelValue', false)">close</button>
    </form>
  </dialog>
</template>
