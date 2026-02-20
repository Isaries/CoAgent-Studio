export interface AgentThread {
    id: string
    project_id: string
    agent_id: string
    user_id: string
    name: string
    created_at: string
    updated_at: string
}

export interface ThreadMessage {
    id: string
    thread_id: string
    role: 'user' | 'assistant' | 'system'
    content: string
    metadata_json?: string
    created_at: string
}

export interface ChatRequest {
    message: string
    metadata_json?: string
}

export interface ChatResponse {
    reply: string
    metadata_json?: string
}
