import { ref, computed, watch, type Ref } from 'vue'
import type { Message } from '../types/chat'

export function useChatSearch(messages: Ref<Message[]>) {
  const searchQuery = ref('')
  const isSearchOpen = ref(false)
  const currentMatchIndex = ref(0)

  const filteredMessages = computed(() => {
    if (!searchQuery.value.trim()) return messages.value
    const q = searchQuery.value.toLowerCase()
    return messages.value.filter(
      (m) =>
        m.content.toLowerCase().includes(q) ||
        m.sender.toLowerCase().includes(q)
    )
  })

  const matchCount = computed(() => {
    if (!searchQuery.value.trim()) return 0
    return filteredMessages.value.length
  })

  // Reset currentMatchIndex when searchQuery changes
  watch(searchQuery, () => {
    currentMatchIndex.value = 0
  })

  const nextMatch = () => {
    if (matchCount.value === 0) return
    currentMatchIndex.value = (currentMatchIndex.value + 1) % matchCount.value
  }

  const prevMatch = () => {
    if (matchCount.value === 0) return
    currentMatchIndex.value =
      (currentMatchIndex.value - 1 + matchCount.value) % matchCount.value
  }

  const openSearch = () => {
    isSearchOpen.value = true
    currentMatchIndex.value = 0
  }

  const closeSearch = () => {
    isSearchOpen.value = false
    searchQuery.value = ''
    currentMatchIndex.value = 0
  }

  return {
    searchQuery,
    isSearchOpen,
    currentMatchIndex,
    filteredMessages,
    matchCount,
    nextMatch,
    prevMatch,
    openSearch,
    closeSearch,
  }
}
