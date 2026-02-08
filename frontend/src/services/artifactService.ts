/**
 * Artifact API Service - HTTP client for artifact CRUD operations.
 */

import api from '@/api'
import type { Artifact, ArtifactCreate, ArtifactUpdate } from '@/types/artifact'

const BASE_URL = '/workspaces'

export const artifactService = {
    /**
     * List all artifacts in a workspace/room.
     */
    async listArtifacts(roomId: string, type?: string): Promise<Artifact[]> {
        const params = type ? { artifact_type: type } : {}
        const response = await api.get(`${BASE_URL}/${roomId}/artifacts`, { params })
        return response.data
    },

    /**
     * Get a single artifact by ID.
     */
    async getArtifact(artifactId: string): Promise<Artifact> {
        const response = await api.get(`${BASE_URL}/artifacts/${artifactId}`)
        return response.data
    },

    /**
     * Create a new artifact in a workspace.
     */
    async createArtifact(roomId: string, data: ArtifactCreate): Promise<Artifact> {
        const response = await api.post(`${BASE_URL}/${roomId}/artifacts`, data)
        return response.data
    },

    /**
     * Update an artifact (partial update with optimistic locking).
     */
    async updateArtifact(artifactId: string, data: ArtifactUpdate): Promise<Artifact> {
        const response = await api.put(`${BASE_URL}/artifacts/${artifactId}`, data)
        return response.data
    },

    /**
     * Delete an artifact (soft delete by default).
     */
    async deleteArtifact(artifactId: string, hardDelete = false): Promise<void> {
        await api.delete(`${BASE_URL}/artifacts/${artifactId}`, {
            params: { hard_delete: hardDelete }
        })
    },

    /**
     * List only task artifacts for Kanban board.
     */
    async listTasks(roomId: string): Promise<Artifact[]> {
        return this.listArtifacts(roomId, 'task')
    },
}

export default artifactService
