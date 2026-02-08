/**
 * Artifact Types - TypeScript interfaces for workspace artifacts.
 * 
 * Supports:
 * - Task artifacts (Kanban cards)
 * - Doc artifacts (Collaborative documents)
 * - Process artifacts (Workflow states)
 */

export type ArtifactType = 'task' | 'doc' | 'process'

export interface TaskContent {
    status: 'todo' | 'in_progress' | 'review' | 'done'
    priority?: 'low' | 'medium' | 'high'
    assignee?: string
    order?: number
    dueDate?: string
}

// Tiptap JSON content is loosely typed as Record<string, any> or clearer structure if known
export interface DocContent {
    type?: 'doc'; // Tiptap root node type
    content?: any[]; // Tiptap JSON content array
}

// Vue Flow Node/Edge types
export interface ProcessNode {
    id: string;
    type?: string;
    label?: string;
    position: { x: number; y: number };
    data?: Record<string, any>;
    [key: string]: any;
}

export interface ProcessEdge {
    id: string;
    source: string;
    target: string;
    label?: string;
    [key: string]: any;
}

export interface ProcessContent {
    nodes: ProcessNode[];
    edges: ProcessEdge[];
}

export interface Artifact {
    id: string
    room_id: string
    type: ArtifactType
    title: string
    content: TaskContent | DocContent | ProcessContent | Record<string, unknown>
    parent_artifact_id?: string
    version: number
    created_by: string
    last_modified_by?: string
    created_at: string
    updated_at: string
}

export interface ArtifactCreate {
    type: ArtifactType
    title: string
    content?: Record<string, unknown>
    parent_artifact_id?: string
}

export interface ArtifactUpdate {
    title?: string
    content?: Record<string, unknown>
    expected_version?: number
}

// Kanban-specific helpers
export interface KanbanColumn {
    id: string
    title: string
    status: TaskContent['status']
    tasks: Artifact[]
}

export const DEFAULT_KANBAN_COLUMNS: Omit<KanbanColumn, 'tasks'>[] = [
    { id: 'todo', title: '待辦', status: 'todo' },
    { id: 'in_progress', title: '進行中', status: 'in_progress' },
    { id: 'review', title: '審核', status: 'review' },
    { id: 'done', title: '完成', status: 'done' },
]
