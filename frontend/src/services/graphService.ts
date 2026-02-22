/**
 * Graph Service — API wrapper for GraphRAG endpoints.
 */
import api from '../api'
import type {
    GraphData,
    GraphStatus,
    GraphQueryResponse,
    GraphBuildResponse,
    CommunityReport,
} from '../types/graph'

export const graphService = {
    /**
     * Get the full knowledge graph for a room.
     */
    async getGraph(roomId: string): Promise<GraphData> {
        const res = await api.get(`/graph/${roomId}`)
        return res.data
    },

    /**
     * Get the graph build/indexing status for a room.
     */
    async getStatus(roomId: string): Promise<GraphStatus> {
        const res = await api.get(`/graph/${roomId}/status`)
        return res.data
    },

    /**
     * Trigger a full graph build for a room.
     */
    async buildGraph(roomId: string): Promise<GraphBuildResponse> {
        const res = await api.post(`/graph/${roomId}/build`)
        return res.data
    },

    /**
     * Query the knowledge graph with a natural language question.
     */
    async queryGraph(roomId: string, question: string): Promise<GraphQueryResponse> {
        const res = await api.post(`/graph/${roomId}/query`, { question })
        return res.data
    },

    /**
     * Get all community summaries for a room.
     */
    async getCommunities(roomId: string): Promise<CommunityReport[]> {
        const res = await api.get(`/graph/${roomId}/communities`)
        return res.data
    },
}
