export interface Message {
  sender: string
  content: string
  isSelf: boolean
  isSystem?: boolean
  isAi?: boolean
  timestamp?: string
}
