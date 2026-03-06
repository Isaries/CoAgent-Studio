import { usePreferencesStore, type LocaleCode } from '../stores/preferences'
import { storeToRefs } from 'pinia'
import { useI18n } from 'vue-i18n'

export function usePreferences() {
  const store = usePreferencesStore()
  const { theme, locale, sidebarCollapsed } = storeToRefs(store)
  const { locale: i18nLocale } = useI18n()

  const toggleTheme = () => {
    store.theme = store.theme === 'light' ? 'dark' : 'light'
  }

  const setLocale = (code: LocaleCode) => {
    store.locale = code
    i18nLocale.value = code
  }

  const toggleSidebar = () => {
    store.sidebarCollapsed = !store.sidebarCollapsed
  }

  return {
    theme,
    locale,
    sidebarCollapsed,
    toggleTheme,
    setLocale,
    toggleSidebar,
  }
}
