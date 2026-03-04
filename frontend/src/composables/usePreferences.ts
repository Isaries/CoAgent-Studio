import { usePreferencesStore, type LocaleCode } from '../stores/preferences'
import { useI18n } from 'vue-i18n'

export function usePreferences() {
  const store = usePreferencesStore()
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
    theme: store.theme,
    locale: store.locale,
    sidebarCollapsed: store.sidebarCollapsed,
    toggleTheme,
    setLocale,
    toggleSidebar,
  }
}
