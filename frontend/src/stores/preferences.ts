import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export type ThemeMode = 'light' | 'dark'
export type LocaleCode = 'en' | 'zh-TW'

export const usePreferencesStore = defineStore('preferences', () => {
  const theme = ref<ThemeMode>(
    (localStorage.getItem('theme') as ThemeMode) || 'light'
  )
  const locale = ref<LocaleCode>(
    (localStorage.getItem('locale') as LocaleCode) || 'en'
  )
  const sidebarCollapsed = ref(
    localStorage.getItem('sidebarCollapsed') === 'true'
  )

  const applyTheme = (t: ThemeMode) => {
    document.documentElement.setAttribute('data-theme', t)
  }

  // Apply on init
  applyTheme(theme.value)

  watch(theme, (val) => {
    localStorage.setItem('theme', val)
    applyTheme(val)
  }, { flush: 'sync' })

  watch(locale, (val) => {
    localStorage.setItem('locale', val)
  }, { flush: 'sync' })

  watch(sidebarCollapsed, (val) => {
    localStorage.setItem('sidebarCollapsed', String(val))
  }, { flush: 'sync' })

  return { theme, locale, sidebarCollapsed }
})
