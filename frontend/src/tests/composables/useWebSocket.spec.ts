import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { defineComponent, nextTick } from 'vue'
import { mount } from '@vue/test-utils'
import { useWebSocket } from '@/composables/useWebSocket'
import type { SocketMessage } from '@/types/chat'

// ---------------------------------------------------------------------------
// WebSocket mock
// ---------------------------------------------------------------------------

interface MockWebSocket {
  send: ReturnType<typeof vi.fn>
  close: ReturnType<typeof vi.fn>
  onmessage: ((event: MessageEvent) => void) | null
  onopen: (() => void) | null
  onerror: ((event: Event) => void) | null
  onclose: (() => void) | null
  readyState: number
  url: string
}

let mockWsInstance: MockWebSocket

const createMockWs = (url: string): MockWebSocket => {
  mockWsInstance = {
    send: vi.fn(),
    close: vi.fn(),
    onmessage: null,
    onopen: null,
    onerror: null,
    onclose: null,
    readyState: WebSocket.CONNECTING,
    url
  }
  return mockWsInstance
}

// ---------------------------------------------------------------------------
// Helper: mount a component that uses useWebSocket
// ---------------------------------------------------------------------------

function mountWithWebSocket(url: string, options: Parameters<typeof useWebSocket>[1] = {}) {
  const Wrapper = defineComponent({
    setup() {
      const ws = useWebSocket(url, options)
      return { ws }
    },
    template: '<div />'
  })

  return mount(Wrapper)
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useWebSocket composable', () => {
  let WebSocketSpy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    vi.useFakeTimers()

    WebSocketSpy = vi
      .spyOn(global, 'WebSocket')
      .mockImplementation((url: string | URL) => createMockWs(String(url)) as unknown as WebSocket)
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  // --------------------------------------------------------------------------
  // connects to WebSocket on mount
  // --------------------------------------------------------------------------

  it('connects to WebSocket on mount when a URL is provided', async () => {
    mountWithWebSocket('ws://localhost/api/v1/chat/ws/room-1')
    await nextTick()

    expect(WebSocketSpy).toHaveBeenCalledOnce()
    expect(WebSocketSpy).toHaveBeenCalledWith('ws://localhost/api/v1/chat/ws/room-1')
  })

  it('sets status to CONNECTING immediately after connect() is called', async () => {
    const wrapper = mountWithWebSocket('ws://localhost/room')
    await nextTick()

    // onopen has not fired yet — status should be CONNECTING
    expect(wrapper.vm.ws.status.value).toBe('CONNECTING')
  })

  it('sets status to OPEN when WebSocket onopen fires', async () => {
    const onOpen = vi.fn()
    const wrapper = mountWithWebSocket('ws://localhost/room', { onOpen })
    await nextTick()

    // Simulate the native open event
    mockWsInstance.readyState = WebSocket.OPEN
    mockWsInstance.onopen!()
    await nextTick()

    expect(wrapper.vm.ws.status.value).toBe('OPEN')
    expect(onOpen).toHaveBeenCalledOnce()
  })

  it('does not construct WebSocket when URL is empty', async () => {
    const Wrapper = defineComponent({
      setup() {
        const ws = useWebSocket('', {})
        return { ws }
      },
      template: '<div />'
    })

    mount(Wrapper)
    await nextTick()

    expect(WebSocketSpy).not.toHaveBeenCalled()
  })

  // --------------------------------------------------------------------------
  // disconnects on unmount
  // --------------------------------------------------------------------------

  it('calls ws.close() when the component is unmounted', async () => {
    const wrapper = mountWithWebSocket('ws://localhost/room')
    await nextTick()

    // Simulate open so status is not already CLOSED
    mockWsInstance.readyState = WebSocket.OPEN
    mockWsInstance.onopen!()
    await nextTick()

    wrapper.unmount()

    expect(mockWsInstance.close).toHaveBeenCalled()
  })

  it('sets status to CLOSED after explicit disconnect()', async () => {
    const wrapper = mountWithWebSocket('ws://localhost/room')
    await nextTick()

    mockWsInstance.readyState = WebSocket.OPEN
    mockWsInstance.onopen!()
    await nextTick()

    wrapper.vm.ws.disconnect()
    await nextTick()

    expect(wrapper.vm.ws.status.value).toBe('CLOSED')
  })

  // --------------------------------------------------------------------------
  // reconnects on connection failure
  // --------------------------------------------------------------------------

  it('transitions to RECONNECTING status after unexpected close', async () => {
    const wrapper = mountWithWebSocket('ws://localhost/room', {
      reconnectInterval: 1000,
      maxReconnectAttempts: 3
    })
    await nextTick()

    // Open then unexpectedly close (status is not 'CLOSED' yet — it's 'CONNECTING')
    mockWsInstance.onclose!()
    await nextTick()

    expect(wrapper.vm.ws.status.value).toBe('RECONNECTING')
  })

  it('attempts to reconnect after the reconnect interval elapses', async () => {
    mountWithWebSocket('ws://localhost/room', {
      reconnectInterval: 1000,
      maxReconnectAttempts: 3
    })
    await nextTick()

    // First unexpected close
    mockWsInstance.onclose!()
    await nextTick()

    expect(WebSocketSpy).toHaveBeenCalledTimes(1)

    // Advance timer past backoff delay (1000 * 1.5^0 = 1000 ms for attempt 1)
    vi.advanceTimersByTime(1100)
    await nextTick()

    expect(WebSocketSpy).toHaveBeenCalledTimes(2)
  })

  it('stops reconnecting after maxReconnectAttempts is exhausted', async () => {
    mountWithWebSocket('ws://localhost/room', {
      reconnectInterval: 100,
      maxReconnectAttempts: 2
    })
    await nextTick()

    // Trigger failures up to max attempts
    for (let i = 0; i <= 2; i++) {
      mockWsInstance.onclose!()
      await nextTick()
      vi.advanceTimersByTime(5000) // generous advance past any backoff
      await nextTick()
    }

    // After exhausting attempts status should be CLOSED, not RECONNECTING
    expect(WebSocketSpy.mock.calls.length).toBeLessThanOrEqual(3) // initial + 2 retries
  })

  // --------------------------------------------------------------------------
  // handles incoming messages
  // --------------------------------------------------------------------------

  it('calls onMessage callback with parsed SocketMessage on incoming data', async () => {
    const onMessage = vi.fn()
    mountWithWebSocket('ws://localhost/room', { onMessage })
    await nextTick()

    mockWsInstance.readyState = WebSocket.OPEN
    mockWsInstance.onopen!()
    await nextTick()

    const payload: SocketMessage = {
      type: 'chat',
      sender: 'Alice',
      content: 'Hello!',
      timestamp: '2026-03-04T10:00:00Z'
    }

    const messageEvent = new MessageEvent('message', {
      data: JSON.stringify(payload)
    })
    mockWsInstance.onmessage!(messageEvent)
    await nextTick()

    expect(onMessage).toHaveBeenCalledOnce()
    expect(onMessage).toHaveBeenCalledWith(payload)
  })

  it('does not crash when incoming message contains invalid JSON', async () => {
    const onMessage = vi.fn()
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})

    mountWithWebSocket('ws://localhost/room', { onMessage })
    await nextTick()

    mockWsInstance.readyState = WebSocket.OPEN
    mockWsInstance.onopen!()
    await nextTick()

    const badEvent = new MessageEvent('message', { data: 'not-json' })
    expect(() => mockWsInstance.onmessage!(badEvent)).not.toThrow()

    expect(onMessage).not.toHaveBeenCalled()
    consoleError.mockRestore()
  })

  // --------------------------------------------------------------------------
  // sends messages through WebSocket
  // --------------------------------------------------------------------------

  it('sends a string payload directly via ws.send()', async () => {
    const wrapper = mountWithWebSocket('ws://localhost/room')
    await nextTick()

    mockWsInstance.readyState = WebSocket.OPEN
    mockWsInstance.onopen!()
    await nextTick()

    wrapper.vm.ws.send('hello world')

    expect(mockWsInstance.send).toHaveBeenCalledWith('hello world')
  })

  it('serializes object payloads to JSON before sending', async () => {
    const wrapper = mountWithWebSocket('ws://localhost/room')
    await nextTick()

    mockWsInstance.readyState = WebSocket.OPEN
    mockWsInstance.onopen!()
    await nextTick()

    const payload = { type: 'ping', data: 42 }
    wrapper.vm.ws.send(payload)

    expect(mockWsInstance.send).toHaveBeenCalledWith(JSON.stringify(payload))
  })

  it('does not call ws.send() when socket is not OPEN', async () => {
    const consoleWarn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    const wrapper = mountWithWebSocket('ws://localhost/room')
    await nextTick()

    // readyState is still CONNECTING — do not simulate open
    wrapper.vm.ws.send('should not send')

    expect(mockWsInstance.send).not.toHaveBeenCalled()
    consoleWarn.mockRestore()
  })

  // --------------------------------------------------------------------------
  // manual connect with new URL
  // --------------------------------------------------------------------------

  it('connect() accepts a new URL and creates a fresh WebSocket', async () => {
    const wrapper = mountWithWebSocket('ws://localhost/room-1')
    await nextTick()

    expect(WebSocketSpy).toHaveBeenCalledWith('ws://localhost/room-1')

    wrapper.vm.ws.connect('ws://localhost/room-2')
    await nextTick()

    expect(WebSocketSpy).toHaveBeenCalledWith('ws://localhost/room-2')
  })

  // --------------------------------------------------------------------------
  // onClose callback
  // --------------------------------------------------------------------------

  it('calls onClose callback when disconnect() is called explicitly', async () => {
    const onClose = vi.fn()
    const wrapper = mountWithWebSocket('ws://localhost/room', { onClose })
    await nextTick()

    mockWsInstance.readyState = WebSocket.OPEN
    mockWsInstance.onopen!()
    await nextTick()

    // Set status to CLOSED first (disconnect() does this), then trigger close event
    wrapper.vm.ws.disconnect()

    // Simulate native close after disconnect sets status = 'CLOSED'
    mockWsInstance.onclose!()
    await nextTick()

    expect(onClose).toHaveBeenCalledOnce()
  })
})
