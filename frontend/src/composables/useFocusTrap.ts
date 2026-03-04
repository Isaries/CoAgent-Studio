import { ref, onUnmounted, type Ref } from 'vue'

export function useFocusTrap(containerRef: Ref<HTMLElement | null>) {
  const previousFocus = ref<HTMLElement | null>(null)
  let isActive = false

  const getFocusableElements = (): HTMLElement[] => {
    if (!containerRef.value) return []
    return Array.from(
      containerRef.value.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'
      )
    )
  }

  const handleKeydown = (e: KeyboardEvent) => {
    if (e.key !== 'Tab' || !isActive) return

    const focusable = getFocusableElements()
    if (focusable.length === 0) return

    const first = focusable[0]!
    const last = focusable[focusable.length - 1]!

    if (e.shiftKey) {
      if (document.activeElement === first) {
        e.preventDefault()
        last.focus()
      }
    } else {
      if (document.activeElement === last) {
        e.preventDefault()
        first.focus()
      }
    }
  }

  const activate = () => {
    previousFocus.value = document.activeElement as HTMLElement
    isActive = true
    document.addEventListener('keydown', handleKeydown)

    // Focus first focusable element
    const focusable = getFocusableElements()
    if (focusable.length > 0) {
      focusable[0]!.focus()
    }
  }

  const deactivate = () => {
    isActive = false
    document.removeEventListener('keydown', handleKeydown)

    // Return focus to previous element
    if (previousFocus.value) {
      previousFocus.value.focus()
      previousFocus.value = null
    }
  }

  onUnmounted(() => {
    deactivate()
  })

  return { activate, deactivate }
}
