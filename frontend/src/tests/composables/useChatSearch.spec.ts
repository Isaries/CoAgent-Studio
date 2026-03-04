import { describe, it, expect } from 'vitest'
import { ref } from 'vue'
import { useChatSearch } from '../../composables/useChatSearch'
import type { Message } from '../../types/chat'

const makeMessages = (): Message[] => [
  { sender: 'Alice', content: 'Hello world', isSelf: true, timestamp: '2024-01-01' },
  { sender: 'Bot', content: 'Hi there!', isSelf: false, isAi: true, timestamp: '2024-01-01' },
  { sender: 'Alice', content: 'How are you?', isSelf: true, timestamp: '2024-01-01' },
  { sender: 'Bot', content: 'I am fine, hello again', isSelf: false, isAi: true, timestamp: '2024-01-01' },
]

describe('useChatSearch', () => {
  it('returns all messages when no query', () => {
    const msgs = ref(makeMessages())
    const { filteredMessages } = useChatSearch(msgs)
    expect(filteredMessages.value).toHaveLength(4)
  })

  it('filters messages by content', () => {
    const msgs = ref(makeMessages())
    const { searchQuery, filteredMessages } = useChatSearch(msgs)
    searchQuery.value = 'hello'
    expect(filteredMessages.value).toHaveLength(2)
  })

  it('filters messages by sender', () => {
    const msgs = ref(makeMessages())
    const { searchQuery, filteredMessages } = useChatSearch(msgs)
    searchQuery.value = 'bot'
    expect(filteredMessages.value).toHaveLength(2)
  })

  it('matchCount is 0 when no query', () => {
    const msgs = ref(makeMessages())
    const { matchCount } = useChatSearch(msgs)
    expect(matchCount.value).toBe(0)
  })

  it('navigates matches with next/prev', () => {
    const msgs = ref(makeMessages())
    const { searchQuery, currentMatchIndex, nextMatch, prevMatch } = useChatSearch(msgs)
    searchQuery.value = 'hello'
    expect(currentMatchIndex.value).toBe(0)
    nextMatch()
    expect(currentMatchIndex.value).toBe(1)
    nextMatch()
    expect(currentMatchIndex.value).toBe(0) // wraps around
    prevMatch()
    expect(currentMatchIndex.value).toBe(1)
  })

  it('openSearch and closeSearch toggle state', () => {
    const msgs = ref(makeMessages())
    const { isSearchOpen, searchQuery, openSearch, closeSearch } = useChatSearch(msgs)
    expect(isSearchOpen.value).toBe(false)
    openSearch()
    expect(isSearchOpen.value).toBe(true)
    searchQuery.value = 'test'
    closeSearch()
    expect(isSearchOpen.value).toBe(false)
    expect(searchQuery.value).toBe('')
  })
})
