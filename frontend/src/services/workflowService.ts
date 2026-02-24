import api from '../api'

export interface WorkflowNodeData {
    id: string
    type: 'agent' | 'router' | 'action' | 'start' | 'end' | 'merge' | 'tool'
    config: Record<string, any>
    position: { x: number; y: number }
}

export interface WorkflowEdgeData {
    id: string
    source: string
    target: string
    type: string  // evaluate, forward, summarize, critique, trigger
    condition?: string
}

export interface WorkflowGraphData {
    nodes: WorkflowNodeData[]
    edges: WorkflowEdgeData[]
}

export interface RoomWorkflow {
    id: string
    room_id: string
    name: string
    is_active: boolean
    graph_data: WorkflowGraphData
    created_at: string
    updated_at: string
}

export interface WorkflowRun {
    id: string
    room_id: string
    workflow_id: string
    status: 'pending' | 'running' | 'paused' | 'completed' | 'failed'
    execution_log: Array<Record<string, any>>
    started_at: string
    completed_at: string | null
    error_message: string | null
}

export const workflowService = {
    async getWorkflow(roomId: string) {
        return api.get<RoomWorkflow | null>(`/rooms/${roomId}/workflow`)
    },

    async saveWorkflow(roomId: string, data: {
        name?: string
        graph_data?: WorkflowGraphData
        is_active?: boolean
    }) {
        return api.put<RoomWorkflow>(`/rooms/${roomId}/workflow`, data)
    },

    async deleteWorkflow(roomId: string) {
        return api.delete(`/rooms/${roomId}/workflow`)
    },

    async getWorkflowRuns(roomId: string, limit = 20) {
        return api.get<WorkflowRun[]>(`/rooms/${roomId}/workflow/runs`, {
            params: { limit }
        })
    },

    async getWorkflowRun(roomId: string, runId: string) {
        return api.get<WorkflowRun>(`/rooms/${roomId}/workflow/runs/${runId}`)
    },
}
