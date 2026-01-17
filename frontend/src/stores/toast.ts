import { defineStore } from 'pinia'
import { ref } from 'vue'

export type ToastType = 'info' | 'success' | 'warning' | 'error'

export interface Toast {
  id: number
  message: string
  type: ToastType
  duration?: number
}

export const useToastStore = defineStore('toast', () => {
  const toasts = ref<Toast[]>([])
  let nextId = 1

  const add = (message: string, type: ToastType = 'info', duration = 3000) => {
    const id = nextId++
    const toast: Toast = { id, message, type, duration }
    toasts.value.push(toast)

    if (duration > 0) {
      setTimeout(() => {
        remove(id)
      }, duration)
    }
  }

  const remove = (id: number) => {
    const index = toasts.value.findIndex((t) => t.id === id)
    if (index !== -1) {
      toasts.value.splice(index, 1)
    }
  }

  const error = (msg: string) => add(msg, 'error')
  const success = (msg: string) => add(msg, 'success')
  const info = (msg: string) => add(msg, 'info')
  const warning = (msg: string) => add(msg, 'warning')

  return {
    toasts,
    add,
    remove,
    error,
    success,
    info,
    warning
  }
})
