import { setActivePinia, createPinia } from 'pinia'
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { useToastStore } from '@/stores/toast'

describe('Toast Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  describe('initial state', () => {
    it('has empty toasts array', () => {
      const store = useToastStore()
      expect(store.toasts).toEqual([])
    })
  })

  describe('add', () => {
    it('creates toast with given message', () => {
      vi.useFakeTimers()
      const store = useToastStore()
      store.add('Hello world', 'info', 0)

      expect(store.toasts).toHaveLength(1)
      expect(store.toasts[0].message).toBe('Hello world')
    })

    it('defaults type to info', () => {
      vi.useFakeTimers()
      const store = useToastStore()
      store.add('Test', undefined, 0)

      expect(store.toasts[0].type).toBe('info')
    })

    it('defaults duration to 3000', () => {
      const store = useToastStore()
      store.add('Test')

      expect(store.toasts[0].duration).toBe(3000)
    })

    it('assigns a numeric id', () => {
      vi.useFakeTimers()
      const store = useToastStore()
      store.add('Test', 'info', 0)

      expect(typeof store.toasts[0].id).toBe('number')
    })

    it('assigns incrementing unique ids', () => {
      vi.useFakeTimers()
      const store = useToastStore()
      store.add('First', 'info', 0)
      store.add('Second', 'info', 0)
      store.add('Third', 'info', 0)

      const ids = store.toasts.map((t) => t.id)
      expect(new Set(ids).size).toBe(3)
      expect(ids[1]).toBeGreaterThan(ids[0])
      expect(ids[2]).toBeGreaterThan(ids[1])
    })

    it('auto-removes after duration', () => {
      vi.useFakeTimers()
      const store = useToastStore()
      store.add('Temporary', 'info', 1000)

      expect(store.toasts).toHaveLength(1)
      vi.advanceTimersByTime(999)
      expect(store.toasts).toHaveLength(1)
      vi.advanceTimersByTime(1)
      expect(store.toasts).toHaveLength(0)
    })

    it('does not auto-remove when duration is 0', () => {
      vi.useFakeTimers()
      const store = useToastStore()
      store.add('Persistent', 'info', 0)

      vi.advanceTimersByTime(60000)
      expect(store.toasts).toHaveLength(1)
    })
  })

  describe('typed shortcuts', () => {
    it('success creates toast with success type', () => {
      vi.useFakeTimers()
      const store = useToastStore()
      store.success('Done!')
      // advance timers to prevent auto-cleanup affecting assertion
      expect(store.toasts[0].type).toBe('success')
      expect(store.toasts[0].message).toBe('Done!')
    })

    it('error creates toast with error type', () => {
      const store = useToastStore()
      store.error('Oops')
      expect(store.toasts[0].type).toBe('error')
    })

    it('info creates toast with info type', () => {
      const store = useToastStore()
      store.info('FYI')
      expect(store.toasts[0].type).toBe('info')
    })

    it('warning creates toast with warning type', () => {
      const store = useToastStore()
      store.warning('Be careful')
      expect(store.toasts[0].type).toBe('warning')
    })
  })

  describe('remove', () => {
    it('removes toast by id', () => {
      vi.useFakeTimers()
      const store = useToastStore()
      store.add('First', 'info', 0)
      store.add('Second', 'info', 0)

      const firstId = store.toasts[0].id
      store.remove(firstId)

      expect(store.toasts).toHaveLength(1)
      expect(store.toasts[0].message).toBe('Second')
    })

    it('does nothing for nonexistent id', () => {
      vi.useFakeTimers()
      const store = useToastStore()
      store.add('Hello', 'info', 0)

      store.remove(9999)

      expect(store.toasts).toHaveLength(1)
    })
  })

  describe('multiple toasts', () => {
    it('multiple toasts coexist', () => {
      vi.useFakeTimers()
      const store = useToastStore()
      store.add('A', 'info', 0)
      store.add('B', 'success', 0)
      store.add('C', 'error', 0)

      expect(store.toasts).toHaveLength(3)
    })
  })
})
