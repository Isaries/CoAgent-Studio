import { describe, it, expect } from 'vitest'
import { ref } from 'vue'
import { useFocusTrap } from '../../composables/useFocusTrap'

describe('useFocusTrap', () => {
  it('provides activate and deactivate methods', () => {
    const containerRef = ref(null)
    const { activate, deactivate } = useFocusTrap(containerRef)
    expect(typeof activate).toBe('function')
    expect(typeof deactivate).toBe('function')
  })

  it('activate focuses first focusable element', () => {
    const container = document.createElement('div')
    const btn1 = document.createElement('button')
    const btn2 = document.createElement('button')
    btn1.textContent = 'First'
    btn2.textContent = 'Second'
    container.appendChild(btn1)
    container.appendChild(btn2)
    document.body.appendChild(container)

    const containerRef = ref(container)
    const { activate, deactivate } = useFocusTrap(containerRef)

    activate()
    expect(document.activeElement).toBe(btn1)

    deactivate()
    document.body.removeChild(container)
  })
})
