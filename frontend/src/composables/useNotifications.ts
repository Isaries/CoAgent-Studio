import { useNotificationStore } from '../stores/notifications'

export function useNotifications() {
  const store = useNotificationStore()

  const addNotification = (
    title: string,
    message: string,
    type: 'info' | 'success' | 'warning' | 'error' = 'info'
  ) => {
    store.add({ title, message, type })
  }

  return {
    items: store.items,
    unreadCount: store.unreadCount,
    addNotification,
    markRead: store.markRead,
    markAllRead: store.markAllRead,
    clear: store.clear
  }
}
