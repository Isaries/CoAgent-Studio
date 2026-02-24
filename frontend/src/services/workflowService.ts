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

/** Decoupled Workflow – no longer bound to a Room */
export interface Workflow {
    id: string
    name: string
    is_active: boolean
    graph_data: WorkflowGraphData
    created_at: string
    updated_at: string
}

/** @deprecated Use Workflow instead */
export type RoomWorkflow = Workflow & { room_id?: string }

export interface WorkflowRun {
    id: string
    workflow_id: string
    session_id: string
    status: 'pending' | 'running' | 'paused' | 'completed' | 'failed'
    execution_log: Array<Record<string, any>>
    started_at: string
    completed_at: string | null
    error_message: string | null
}

export interface TriggerPolicy {
    id: string
    name: string
    event_type: string
    conditions: Record<string, any>
    target_workflow_id: string
    scope_session_id: string | null
    is_active: boolean
    created_at: string
    updated_at: string
}

export const workflowService = {
    // ===========================================
    // Global Workflow CRUD  (new decoupled API)
    // ===========================================
    async listWorkflows() {
        return api.get<Workflow[]>('/workflows')
    },

    async getWorkflowById(workflowId: string) {
        return api.get<Workflow>(`/workflows/${workflowId}`)
    },

    async createWorkflow(data: {
        name?: string
        graph_data?: WorkflowGraphData
        is_active?: boolean
    }) {
        return api.post<Workflow>('/workflows', data)
    },

    async updateWorkflow(workflowId: string, data: {
        name?: string
        graph_data?: WorkflowGraphData
        is_active?: boolean
    }) {
        return api.put<Workflow>(`/workflows/${workflowId}`, data)
    },

    async deleteWorkflowById(workflowId: string) {
        return api.delete(`/workflows/${workflowId}`)
    },

    async executeWorkflow(workflowId: string, payload: Record<string, any> = {}) {
        return api.post(`/workflows/${workflowId}/execute`, payload)
    },

    // Runs (global)
    async getWorkflowRuns(workflowId: string, limit = 20) {
        return api.get<WorkflowRun[]>(`/workflows/${workflowId}/runs`, {
            params: { limit }
        })
    },

    async getWorkflowRunById(workflowId: string, runId: string) {
        return api.get<WorkflowRun>(`/workflows/${workflowId}/runs/${runId}`)
    },

    // ===========================================
    // Legacy Room-scoped (backward compat)
    // ===========================================
    async getWorkflow(roomId: string) {
        return api.get<Workflow | null>(`/rooms/${roomId}/workflow`)
    },

    async saveWorkflow(roomId: string, data: {
        name?: string
        graph_data?: WorkflowGraphData
        is_active?: boolean
    }) {
        return api.put<Workflow>(`/rooms/${roomId}/workflow`, data)
    },

    async deleteWorkflow(roomId: string) {
        return api.delete(`/rooms/${roomId}/workflow`)
    },

    // ===========================================
    // Trigger Policies
    // ===========================================
    async listTriggers() {
        return api.get<TriggerPolicy[]>('/triggers')
    },

    async createTrigger(data: Partial<TriggerPolicy>) {
        return api.post<TriggerPolicy>('/triggers', data)
    },

    async updateTrigger(triggerId: string, data: Partial<TriggerPolicy>) {
        return api.put<TriggerPolicy>(`/triggers/${triggerId}`, data)
    },

    async deleteTrigger(triggerId: string) {
        return api.delete(`/triggers/${triggerId}`)
    },
}
