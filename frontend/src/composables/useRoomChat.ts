import { ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useWebSocket } from './useWebSocket'
import api from '../api'
import type { Message, SocketMessage } from '../types/chat'

export function useRoomChat(roomId: string) {
    const authStore = useAuthStore()
    const messages = ref<Message[]>([])
    const showA2ATrace = ref(false)
    const isConnected = ref(false)

    // Integrate useWebSocket
    // We initialize with empty URL, connect() will set it.
    const { status, send: wsSend, connect: wsConnect, disconnect: wsDisconnect } = useWebSocket('', {
        reconnectInterval: 3000,
        maxReconnectAttempts: 10,
        onOpen: () => {
            isConnected.value = true
            messages.value.push({
                sender: 'System',
                content: 'Connected to chat...',
                isSelf: false,
                isSystem: true,
                timestamp: new Date().toISOString()
            })
        },
        onClose: () => {
            isConnected.value = false
        },
        onMessage: (msg: SocketMessage) => {
            handleIncomingMessage(msg)
        }
    })

    // --- Actions ---

    const connect = () => {
        if (authStore.user) {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
            const host = window.location.host
            // Assumes /api/v1 prefix is handled by proxy or server
            const url = `${protocol}//${host}/api/v1/chat/ws/${roomId}`
            wsConnect(url)
        }
    }

    const disconnect = () => {
        wsDisconnect()
    }

    const fetchHistory = async () => {
        try {
            const response = await api.get(`/chat/messages/${roomId}`)
            const history = response.data.map((msg: any) => ({
                sender: msg.sender,
                content: msg.content,
                isSelf: isMessageSelf(msg.sender, msg.sender_id),
                isAi: !!msg.agent_type,
                isSystem: false,
                timestamp: msg.created_at
            }))
            messages.value = history
        } catch (error) {
            console.error('Failed to fetch messages:', error)
        }
    }

    const sendMessage = (text: string) => {
        if (status.value !== 'OPEN') {
            console.warn('Chat not connected')
            return
        }
        wsSend(text)
    }

    // --- Helpers ---

    const isMessageSelf = (senderName: string, senderId?: string) => {
        const user = authStore.user
        if (!user) return false

        // Check ID first if available
        if (senderId && senderId === user.id) return true

        // Fallback to name/email matching
        const safeEmail = user.email ?? ''
        const safeName = user.full_name ?? ''
        const safeUsername = (user as any)?.username ?? ''

        return (
            senderName === safeName ||
            senderName === safeEmail ||
            (safeUsername && senderName === safeUsername)
        )
    }

    const handleIncomingMessage = (msg: SocketMessage) => {
        // 1. A2A Trace Handling
        if (msg.content?.startsWith('[A2A]')) {
            if (showA2ATrace.value) {
                const parts = msg.content.split('|')
                const eventType = parts[1] || 'TRACE'
                const details = parts[2] || ''

                messages.value.push({
                    sender: `[A2A ${eventType}]`,
                    content: details,
                    isSelf: false,
                    isAi: false,
                    isSystem: true,
                    isA2ATrace: true, // Type definition might need this if not present
                    timestamp: new Date().toISOString()
                })
            }
            return
        }

        // 2. External Agent Message Handling (from webhook broadcast)
        if (msg.type === 'a2a_external_message') {
            const externalMsg = msg as any
            messages.value.push({
                sender: externalMsg.agent_name || `External Agent`,
                content: externalMsg.content,
                isSelf: false,
                isAi: true,
                isExternal: true,
                isSystem: false,
                timestamp: externalMsg.timestamp || new Date().toISOString()
            })
            return
        }

        // 3. Normal Message Handling
        let isAi = !!msg.metadata?.is_ai || msg.sender.includes('AI')
        if (msg.sender.includes('Teacher AI') || msg.sender.includes('Student AI')) {
            isAi = true
        }

        const isSelf = isMessageSelf(msg.sender, msg.metadata?.sender_id)

        messages.value.push({
            sender: msg.sender,
            content: msg.content,
            isSelf,
            isAi,
            isSystem: msg.type === 'system',
            timestamp: msg.timestamp
        })
    }

    return {
        messages,
        showA2ATrace,
        status,
        isConnected,
        connect,
        disconnect,
        fetchHistory,
        sendMessage
    }
}
