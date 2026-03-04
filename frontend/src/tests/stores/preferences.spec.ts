import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { usePreferencesStore } from '../../stores/preferences'

describe('usePreferencesStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
  })

  it('initializes with default values', () => {
    const store = usePreferencesStore()
    expect(store.theme).toBe('light')
    expect(store.locale).toBe('en')
    expect(store.sidebarCollapsed).toBe(false)
  })

  it('reads initial theme from localStorage', () => {
    localStorage.setItem('theme', 'dark')
    const store = usePreferencesStore()
    expect(store.theme).toBe('dark')
  })

  it('reads initial locale from localStorage', () => {
    localStorage.setItem('locale', 'zh-TW')
    const store = usePreferencesStore()
    expect(store.locale).toBe('zh-TW')
  })

  it('persists theme changes to localStorage', () => {
    const store = usePreferencesStore()
    store.theme = 'dark'
    expect(localStorage.getItem('theme')).toBe('dark')
  })

  it('persists locale changes to localStorage', () => {
    const store = usePreferencesStore()
    store.locale = 'zh-TW'
    expect(localStorage.getItem('locale')).toBe('zh-TW')
  })

  it('applies data-theme attribute', () => {
    const store = usePreferencesStore()
    store.theme = 'dark'
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
  })
})
