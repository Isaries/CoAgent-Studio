import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useNotificationStore } from '../../stores/notifications'

describe('useNotificationStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('starts with empty items', () => {
    const store = useNotificationStore()
    expect(store.items).toHaveLength(0)
    expect(store.unreadCount).toBe(0)
  })

  it('adds a notification', () => {
    const store = useNotificationStore()
    store.add({ title: 'Test', message: 'Hello', type: 'info' })
    expect(store.items).toHaveLength(1)
    expect(store.items[0]!.title).toBe('Test')
    expect(store.items[0]!.read).toBe(false)
    expect(store.unreadCount).toBe(1)
  })

  it('marks a notification as read', () => {
    const store = useNotificationStore()
    store.add({ title: 'Test', message: 'Hello', type: 'info' })
    const id = store.items[0]!.id
    store.markRead(id)
    expect(store.items[0]!.read).toBe(true)
    expect(store.unreadCount).toBe(0)
  })

  it('marks all as read', () => {
    const store = useNotificationStore()
    store.add({ title: 'A', message: 'a', type: 'info' })
    store.add({ title: 'B', message: 'b', type: 'success' })
    expect(store.unreadCount).toBe(2)
    store.markAllRead()
    expect(store.unreadCount).toBe(0)
  })

  it('clears all notifications', () => {
    const store = useNotificationStore()
    store.add({ title: 'A', message: 'a', type: 'info' })
    store.add({ title: 'B', message: 'b', type: 'info' })
    store.clear()
    expect(store.items).toHaveLength(0)
  })
})
