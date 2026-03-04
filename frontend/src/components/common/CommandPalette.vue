<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { useCommandPalette } from '../../composables/useCommandPalette'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const {
  isOpen,
  query,
  selectedIndex,
  results,
  close,
  moveUp,
  moveDown,
  executeSelected,
  execute,
} = useCommandPalette()

const inputRef = ref<HTMLInputElement | null>(null)

watch(isOpen, async (val) => {
  if (val) {
    await nextTick()
    inputRef.value?.focus()
  }
})

const handleKeydown = (e: KeyboardEvent) => {
  if (e.key === 'ArrowUp') {
    e.preventDefault()
    moveUp()
  } else if (e.key === 'ArrowDown') {
    e.preventDefault()
    moveDown()
  } else if (e.key === 'Enter') {
    e.preventDefault()
    executeSelected()
  } else if (e.key === 'Escape') {
    close()
  }
}

defineExpose({ open: () => { isOpen.value = true } })
</script>

<template>
  <Teleport to="body">
    <div v-if="isOpen" class="fixed inset-0 z-[100] flex items-start justify-center pt-[20vh]" @click.self="close">
      <div class="fixed inset-0 bg-black/50 backdrop-blur-sm" @click="close"></div>
      <div class="relative w-full max-w-lg bg-base-100 rounded-box shadow-2xl border border-base-300 overflow-hidden">
        <!-- Search Input -->
        <div class="flex items-center gap-3 px-4 py-3 border-b border-base-300">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-base-content/40" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            ref="inputRef"
            v-model="query"
            :placeholder="t('commandPalette.placeholder')"
            class="flex-1 bg-transparent outline-none text-base-content placeholder:text-base-content/40"
            @keydown="handleKeydown"
          />
          <kbd class="kbd kbd-sm">Esc</kbd>
        </div>

        <!-- Results -->
        <div class="max-h-72 overflow-y-auto py-2">
          <div v-if="results.length === 0" class="px-4 py-8 text-center text-base-content/50">
            {{ t('commandPalette.noResults') }}
          </div>
          <template v-else>
            <div
              v-for="(item, idx) in results"
              :key="item.id"
              @click="execute(item)"
              @mouseenter="selectedIndex = idx"
              class="flex items-center gap-3 px-4 py-2.5 cursor-pointer transition-colors"
              :class="idx === selectedIndex ? 'bg-primary/10 text-primary' : 'hover:bg-base-200'"
            >
              <span class="badge badge-ghost badge-sm">{{ item.category }}</span>
              <span class="text-sm">{{ item.label }}</span>
            </div>
          </template>
        </div>

        <!-- Footer -->
        <div class="flex items-center gap-4 px-4 py-2 border-t border-base-300 text-xs text-base-content/40">
          <span><kbd class="kbd kbd-xs">&uarr;</kbd><kbd class="kbd kbd-xs">&darr;</kbd> navigate</span>
          <span><kbd class="kbd kbd-xs">&crarr;</kbd> select</span>
          <span><kbd class="kbd kbd-xs">esc</kbd> close</span>
        </div>
      </div>
    </div>
  </Teleport>
</template>
