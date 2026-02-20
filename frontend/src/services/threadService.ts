import api from '../api'
import { API_ENDPOINTS } from '../constants/api'
import type { AgentThread, ThreadMessage, ChatRequest, ChatResponse } from '../types/thread'

export const threadService = {
    createThread: (data: { project_id: string; agent_id: string; name: string }) =>
        api.post<AgentThread>(API_ENDPOINTS.THREADS.BASE, data).then(res => res.data),

    getThread: (threadId: string) =>
        api.get<AgentThread>(`${API_ENDPOINTS.THREADS.BASE}/${threadId}`).then(res => res.data),

    getMessages: (threadId: string) =>
        api.get<ThreadMessage[]>(`${API_ENDPOINTS.THREADS.BASE}/${threadId}/messages`).then(res => res.data),

    sendMessage: (threadId: string, request: ChatRequest) =>
        api.post<ThreadMessage>(`${API_ENDPOINTS.THREADS.BASE}/${threadId}/messages`, request).then(res => res.data),

    // Stateless test directly bound to agent config
    testStateless: (agentId: string, request: ChatRequest) =>
        api.post<ChatResponse>(API_ENDPOINTS.THREADS.STATELESS(agentId), request).then(res => res.data),
}
