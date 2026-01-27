export interface Message {
  sender: string
  content: string
  isSelf: boolean
  isSystem?: boolean
  isAi?: boolean
  isA2ATrace?: boolean
  timestamp?: string
}

export interface SocketMessage {
  type: string
  sender: string
  content: string
  timestamp: string
  room_id?: string
  metadata?: Record<string, any>
}
