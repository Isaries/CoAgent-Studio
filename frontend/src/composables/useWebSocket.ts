import { ref, onMounted, onUnmounted } from 'vue'
import type { SocketMessage } from '../types/chat'

type WebSocketStatus = 'CONNECTING' | 'OPEN' | 'CLOSED' | 'RECONNECTING'

interface UseWebSocketOptions {
  onMessage?: (data: SocketMessage) => void
  onOpen?: () => void
  onClose?: () => void
  onError?: (event: Event) => void
  reconnectInterval?: number
  maxReconnectAttempts?: number
}

export function useWebSocket(initialUrl: string, options: UseWebSocketOptions = {}) {
  const ws = ref<WebSocket | null>(null)
  const status = ref<WebSocketStatus>('CLOSED')
  const reconnectAttempts = ref(0)
  const activeUrl = ref(initialUrl)
  let reconnectTimer: number | null = null

  const {
    onMessage,
    onOpen,
    onClose,
    onError,
    reconnectInterval = 3000,
    maxReconnectAttempts = 5
  } = options

  const connect = (newUrl?: string) => {
    if (newUrl) {
      activeUrl.value = newUrl
    }

    if (ws.value) {
      ws.value.close()
    }

    if (!activeUrl.value) return

    try {
      status.value = 'CONNECTING'
      ws.value = new WebSocket(activeUrl.value)

      ws.value.onopen = () => {
        status.value = 'OPEN'
        reconnectAttempts.value = 0
        onOpen?.()
      }

      ws.value.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as SocketMessage
          onMessage?.(data)
        } catch (e) {
          console.error('WebSocket JSON parsing failed:', e, event.data)
        }
      }

      ws.value.onclose = () => {
        if (status.value !== 'CLOSED') {
          // Unexpected close
          handleReconnect()
        } else {
          onClose?.()
        }
      }

      ws.value.onerror = (event) => {
        console.error('WebSocket Error:', event)
        onError?.(event)
        // Error usually triggers close, so let onclose handle reconnect
      }
    } catch (e) {
      console.error('WebSocket Connection Failed:', e)
      handleReconnect()
    }
  }

  const handleReconnect = () => {
    if (reconnectAttempts.value >= maxReconnectAttempts) {
      status.value = 'CLOSED'
      return
    }

    status.value = 'RECONNECTING'
    reconnectAttempts.value++

    // Exponential backoff with cap
    const delay = Math.min(reconnectInterval * Math.pow(1.5, reconnectAttempts.value - 1), 10000)

    console.log(
      `Reconnecting in ${delay}ms... (Attempt ${reconnectAttempts.value}/${maxReconnectAttempts})`
    )

    if (reconnectTimer) clearTimeout(reconnectTimer)
    reconnectTimer = window.setTimeout(() => {
      connect()
    }, delay)
  }

  const disconnect = () => {
    status.value = 'CLOSED' // Prevent reconnect
    if (reconnectTimer) clearTimeout(reconnectTimer)
    if (ws.value) {
      ws.value.close()
      ws.value = null
    }
  }

  const send = (data: any) => {
    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
      const payload = typeof data === 'string' ? data : JSON.stringify(data)
      ws.value.send(payload)
    } else {
      console.warn('WebSocket not open, cannot send:', data)
    }
  }

  onMounted(() => {
    if (activeUrl.value) {
      connect()
    }
  })

  onUnmounted(() => {
    disconnect()
  })

  return {
    status,
    ws,
    send,
    connect, // Manually connect if needed
    disconnect
  }
}
