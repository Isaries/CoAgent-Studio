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

const MAX_NOTIFICATIONS = 100

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
    if (items.value.length > MAX_NOTIFICATIONS) {
      items.value = items.value.slice(0, MAX_NOTIFICATIONS)
    }
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
