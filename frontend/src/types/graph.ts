/**
 * GraphRAG TypeScript types — Knowledge graph data models.
 */

export interface GraphNode {
    id: string
    name: string
    type: 'PERSON' | 'AGENT' | 'CONCEPT' | 'TECHNOLOGY' | 'ARTIFACT' | 'ISSUE' | string
    description: string
    community_id?: number | null
}

export interface GraphEdge {
    source: string
    target: string
    relation: string
    evidence: string
}

export interface GraphData {
    nodes: GraphNode[]
    edges: GraphEdge[]
    node_count: number
    edge_count: number
}

export interface GraphStatus {
    room_id: string
    node_count: number
    edge_count: number
    community_count: number
    last_updated: string | null
    is_building: boolean
}

export interface CommunityReport {
    community_id: number
    title: string
    summary: string
    key_findings: string[]
    key_entities: string[]
    level: number
}

export interface GraphQueryRequest {
    question: string
}

export interface GraphQueryResponse {
    answer: string
    intent: 'global' | 'local'
    sources: string[]
}

export interface GraphBuildResponse {
    status: string
    job_id: string
    message: string
}

/** Color mapping for entity types in the visualization */
export const NODE_COLORS: Record<string, string> = {
    PERSON: '#3B82F6',      // blue
    AGENT: '#8B5CF6',       // purple
    CONCEPT: '#10B981',     // green
    TECHNOLOGY: '#F59E0B',  // amber
    ARTIFACT: '#F97316',    // orange
    ISSUE: '#EF4444',       // red
    DEFAULT: '#6B7280',     // gray
}
