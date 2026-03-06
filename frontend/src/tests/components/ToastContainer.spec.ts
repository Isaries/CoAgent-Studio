import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ToastContainer from '@/components/common/ToastContainer.vue'
import { useToastStore } from '@/stores/toast'
import type { Toast, ToastType } from '@/stores/toast'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeToast(overrides: Partial<Toast> = {}): Toast {
  return {
    id: 1,
    message: 'Test message',
    type: 'info',
    duration: 0, // 0 = no auto-remove in tests
    ...overrides
  }
}

function mountContainer() {
  return mount(ToastContainer, {
    global: {
      plugins: [createPinia()]
    }
  })
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('ToastContainer component', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  // --------------------------------------------------------------------------
  // renders no toasts when store is empty
  // --------------------------------------------------------------------------

  it('renders no toast items when the store has no toasts', () => {
    const wrapper = mountContainer()

    // The v-for iterates toastStore.toasts — zero items means no alert divs
    const alerts = wrapper.findAll('.alert')
    expect(alerts).toHaveLength(0)
  })

  it('renders an empty container element even with no toasts', () => {
    const wrapper = mountContainer()

    expect(wrapper.find('.toast').exists()).toBe(true)
  })

  // --------------------------------------------------------------------------
  // renders toast items when store has toasts
  // --------------------------------------------------------------------------

  it('renders one toast when the store has one toast', async () => {
    const wrapper = mountContainer()
    const toastStore = useToastStore()

    toastStore.toasts.push(makeToast({ id: 1, message: 'Hello', type: 'info' }))
    await wrapper.vm.$nextTick()

    expect(wrapper.findAll('.alert')).toHaveLength(1)
  })

  it('displays the toast message text in the rendered element', async () => {
    const wrapper = mountContainer()
    const toastStore = useToastStore()

    toastStore.toasts.push(makeToast({ message: 'Something happened' }))
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('Something happened')
  })

  // --------------------------------------------------------------------------
  // renders correct number of toasts
  // --------------------------------------------------------------------------

  it('renders the correct number of toast items matching store length', async () => {
    const wrapper = mountContainer()
    const toastStore = useToastStore()

    toastStore.toasts.push(makeToast({ id: 1 }))
    toastStore.toasts.push(makeToast({ id: 2 }))
    toastStore.toasts.push(makeToast({ id: 3 }))
    await wrapper.vm.$nextTick()

    expect(wrapper.findAll('.alert')).toHaveLength(3)
  })

  it('updates rendered count when toasts are added reactively', async () => {
    const wrapper = mountContainer()
    const toastStore = useToastStore()

    toastStore.toasts.push(makeToast({ id: 1 }))
    await wrapper.vm.$nextTick()
    expect(wrapper.findAll('.alert')).toHaveLength(1)

    toastStore.toasts.push(makeToast({ id: 2 }))
    await wrapper.vm.$nextTick()
    expect(wrapper.findAll('.alert')).toHaveLength(2)
  })

  // --------------------------------------------------------------------------
  // applies correct CSS class for success type
  // --------------------------------------------------------------------------

  it('applies alert-success class for a toast with type "success"', async () => {
    const wrapper = mountContainer()
    const toastStore = useToastStore()

    toastStore.toasts.push(makeToast({ id: 1, type: 'success' }))
    await wrapper.vm.$nextTick()

    const alert = wrapper.find('.alert')
    expect(alert.classes()).toContain('alert-success')
  })

  it('does not apply alert-success class when type is not "success"', async () => {
    const wrapper = mountContainer()
    const toastStore = useToastStore()

    toastStore.toasts.push(makeToast({ id: 1, type: 'error' }))
    await wrapper.vm.$nextTick()

    const alert = wrapper.find('.alert')
    expect(alert.classes()).not.toContain('alert-success')
  })

  // --------------------------------------------------------------------------
  // applies correct CSS class for error type
  // --------------------------------------------------------------------------

  it('applies alert-error class for a toast with type "error"', async () => {
    const wrapper = mountContainer()
    const toastStore = useToastStore()

    toastStore.toasts.push(makeToast({ id: 1, type: 'error' }))
    await wrapper.vm.$nextTick()

    const alert = wrapper.find('.alert')
    expect(alert.classes()).toContain('alert-error')
  })

  // --------------------------------------------------------------------------
  // applies correct CSS class for all toast types
  // --------------------------------------------------------------------------

  const typeClassMap: Array<{ type: ToastType; expectedClass: string }> = [
    { type: 'info', expectedClass: 'alert-info' },
    { type: 'success', expectedClass: 'alert-success' },
    { type: 'warning', expectedClass: 'alert-warning' },
    { type: 'error', expectedClass: 'alert-error' }
  ]

  typeClassMap.forEach(({ type, expectedClass }) => {
    it(`applies "${expectedClass}" class for toast type "${type}"`, async () => {
      const wrapper = mountContainer()
      const toastStore = useToastStore()

      toastStore.toasts.push(makeToast({ id: 1, type }))
      await wrapper.vm.$nextTick()

      const alert = wrapper.find('.alert')
      expect(alert.classes()).toContain(expectedClass)
    })
  })

  it('only applies one type class per toast (no overlap)', async () => {
    const wrapper = mountContainer()
    const toastStore = useToastStore()

    toastStore.toasts.push(makeToast({ id: 1, type: 'warning' }))
    await wrapper.vm.$nextTick()

    const alert = wrapper.find('.alert')
    const classes = alert.classes()

    expect(classes).toContain('alert-warning')
    expect(classes).not.toContain('alert-info')
    expect(classes).not.toContain('alert-success')
    expect(classes).not.toContain('alert-error')
  })

  // --------------------------------------------------------------------------
  // clicking close calls store remove
  // --------------------------------------------------------------------------

  it('renders a close button for each toast', async () => {
    const wrapper = mountContainer()
    const toastStore = useToastStore()

    toastStore.toasts.push(makeToast({ id: 1 }))
    await wrapper.vm.$nextTick()

    const closeButton = wrapper.find('button')
    expect(closeButton.exists()).toBe(true)
  })

  it('calls toastStore.remove() with the correct toast id when the close button is clicked', async () => {
    const wrapper = mountContainer()
    const toastStore = useToastStore()

    toastStore.toasts.push(makeToast({ id: 42, message: 'Click to close' }))
    await wrapper.vm.$nextTick()

    const removeSpy = vi.spyOn(toastStore, 'remove')

    const closeButton = wrapper.find('button')
    await closeButton.trigger('click')

    expect(removeSpy).toHaveBeenCalledOnce()
    expect(removeSpy).toHaveBeenCalledWith(42)
  })

  it('removes the correct toast when multiple toasts are present', async () => {
    const wrapper = mountContainer()
    const toastStore = useToastStore()

    toastStore.toasts.push(makeToast({ id: 10, message: 'First' }))
    toastStore.toasts.push(makeToast({ id: 20, message: 'Second' }))
    await wrapper.vm.$nextTick()

    const removeSpy = vi.spyOn(toastStore, 'remove')

    // Click the close button on the second toast (index 1)
    const buttons = wrapper.findAll('button')
    await buttons[1].trigger('click')

    expect(removeSpy).toHaveBeenCalledWith(20)
  })

  it('toast is removed from DOM after store.remove() is called', async () => {
    const wrapper = mountContainer()
    const toastStore = useToastStore()

    toastStore.toasts.push(makeToast({ id: 1, message: 'Will be removed' }))
    await wrapper.vm.$nextTick()
    expect(wrapper.findAll('.alert')).toHaveLength(1)

    // Directly call store remove (simulates what clicking the button triggers)
    toastStore.remove(1)
    await wrapper.vm.$nextTick()

    expect(wrapper.findAll('.alert')).toHaveLength(0)
  })
})
