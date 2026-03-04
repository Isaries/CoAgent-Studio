import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface Notification {
  id: string
  title: string
  message: string
  type: 'info' | 'success' | 'warning' | 'error'
  read: boolean
  timestamp: string
}

export const useNotificationStore = defineStore('notifications', () => {
  const items = ref<Notification[]>([])

  const unreadCount = computed(() => items.value.filter((n) => !n.read).length)

  const add = (notification: Omit<Notification, 'id' | 'read' | 'timestamp'>) => {
    items.value.unshift({
      ...notification,
      id: crypto.randomUUID(),
      read: false,
      timestamp: new Date().toISOString(),
    })
  }

  const markRead = (id: string) => {
    const item = items.value.find((n) => n.id === id)
    if (item) item.read = true
  }

  const markAllRead = () => {
    items.value.forEach((n) => (n.read = true))
  }

  const clear = () => {
    items.value = []
  }

  return { items, unreadCount, add, markRead, markAllRead, clear }
})
