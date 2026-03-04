import { ref, onMounted, onUnmounted } from 'vue'

export interface Shortcut {
  keys: string
  label: string
  scope: string
  action: () => void
}

const shortcuts = ref<Shortcut[]>([])
const isHelpOpen = ref(false)
let listenerCount = 0

export function useKeyboardShortcuts() {
  const register = (shortcut: Shortcut) => {
    // Avoid duplicates
    if (!shortcuts.value.find((s) => s.keys === shortcut.keys)) {
      shortcuts.value.push(shortcut)
    }
  }

  const unregister = (keys: string) => {
    shortcuts.value = shortcuts.value.filter((s) => s.keys !== keys)
  }

  const handleKeydown = (e: KeyboardEvent) => {
    const target = e.target as HTMLElement
    const isInput = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable

    // Ctrl/Cmd+K — always works
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault()
      const paletteShortcut = shortcuts.value.find((s) => s.keys === 'Ctrl+K')
      paletteShortcut?.action()
      return
    }

    // Don't trigger other shortcuts when typing in inputs
    if (isInput) return

    // ? — show shortcuts help
    if (e.key === '?' && !e.ctrlKey && !e.metaKey) {
      e.preventDefault()
      isHelpOpen.value = !isHelpOpen.value
      return
    }

    // Escape — close modals/panels
    if (e.key === 'Escape') {
      isHelpOpen.value = false
      const escShortcut = shortcuts.value.find((s) => s.keys === 'Escape')
      escShortcut?.action()
      return
    }
  }

  const registerDefaults = () => {
    register({
      keys: 'Ctrl+K',
      label: 'commandPalette',
      scope: 'global',
      action: () => {} // Will be overridden by CommandPalette
    })
    register({
      keys: '?',
      label: 'showShortcuts',
      scope: 'global',
      action: () => { isHelpOpen.value = true }
    })
    register({
      keys: 'Escape',
      label: 'closeModal',
      scope: 'global',
      action: () => {}
    })
  }

  onMounted(() => {
    if (listenerCount === 0) {
      document.addEventListener('keydown', handleKeydown)
    }
    listenerCount++
  })

  onUnmounted(() => {
    listenerCount--
    if (listenerCount === 0) {
      document.removeEventListener('keydown', handleKeydown)
    }
  })

  return {
    shortcuts,
    isHelpOpen,
    register,
    unregister,
    registerDefaults,
  }
}
