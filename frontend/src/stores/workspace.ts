/**
 * Workspace Store - Pinia store for managing artifacts in a workspace.
 * 
 * Handles:
 * - Loading artifacts from API
 * - Real-time updates via WebSocket
 * - Optimistic UI updates
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import artifactService from '@/services/artifactService'
import type { Artifact, ArtifactCreate, ArtifactUpdate, TaskContent, KanbanColumn } from '@/types/artifact'
import { DEFAULT_KANBAN_COLUMNS } from '@/types/artifact'

export const useWorkspaceStore = defineStore('workspace', () => {
    // State
    const artifacts = ref<Artifact[]>([])
    const loading = ref(false)
    const error = ref<string | null>(null)
    const currentRoomId = ref<string | null>(null)

    // Computed: Kanban columns with tasks
    const kanbanColumns = computed<KanbanColumn[]>(() => {
        const taskArtifacts = artifacts.value.filter(a => a.type === 'task')

        return DEFAULT_KANBAN_COLUMNS.map(col => ({
            ...col,
            tasks: taskArtifacts
                .filter(task => {
                    const content = task.content as TaskContent
                    return content.status === col.status
                })
                .sort((a, b) => {
                    const aOrder = (a.content as TaskContent).order ?? 0
                    const bOrder = (b.content as TaskContent).order ?? 0
                    return aOrder - bOrder
                })
        }))
    })

    // Computed: Documents
    const documents = computed(() =>
        artifacts.value.filter(a => a.type === 'doc')
    )

    // Computed: Processes
    const processes = computed(() =>
        artifacts.value.filter(a => a.type === 'process')
    )

    // Actions
    async function loadArtifacts(roomId: string) {
        if (loading.value) return

        loading.value = true
        error.value = null
        currentRoomId.value = roomId

        try {
            artifacts.value = await artifactService.listArtifacts(roomId)
        } catch (e) {
            error.value = (e as Error).message
            console.error('[WorkspaceStore] Failed to load artifacts:', e)
        } finally {
            loading.value = false
        }
    }

    async function createTask(title: string, status: TaskContent['status'] = 'todo') {
        if (!currentRoomId.value) return null

        const data: ArtifactCreate = {
            type: 'task',
            title,
            content: { status, priority: 'medium', order: artifacts.value.length }
        }

        try {
            const artifact = await artifactService.createArtifact(currentRoomId.value, data)
            artifacts.value.push(artifact)
            return artifact
        } catch (e) {
            error.value = (e as Error).message
            return null
        }
    }

    async function createDoc(title: string) {
        if (!currentRoomId.value) return null

        const data: ArtifactCreate = {
            type: 'doc',
            title,
            content: { type: 'doc', content: [] } // Empty Tiptap doc
        }

        try {
            const artifact = await artifactService.createArtifact(currentRoomId.value, data)
            artifacts.value.push(artifact)
            return artifact
        } catch (e) {
            error.value = (e as Error).message
            return null
        }
    }

    async function createProcess(title: string) {
        if (!currentRoomId.value) return null

        const data: ArtifactCreate = {
            type: 'process',
            title,
            content: { nodes: [], edges: [] } // Empty Process
        }

        try {
            const artifact = await artifactService.createArtifact(currentRoomId.value, data)
            artifacts.value.push(artifact)
            return artifact
        } catch (e) {
            error.value = (e as Error).message
            return null
        }
    }

    // Generic update artifact action
    async function updateArtifact(artifactId: string, updates: ArtifactUpdate) {
        const index = artifacts.value.findIndex(a => a.id === artifactId)
        if (index === -1) return null

        const artifact = artifacts.value[index]

        // Optimistic update
        const oldArtifact = JSON.parse(JSON.stringify(artifact)) as Artifact

        // Prepare new object
        const updatedArtifact: Artifact = {
            ...artifact!,
            title: updates.title ?? artifact!.title,
            content: (updates.content ? { ...artifact!.content, ...updates.content } : artifact!.content) as any,
            id: artifact!.id,
            room_id: artifact!.room_id,
            type: artifact!.type,
            version: artifact!.version,
            created_by: artifact!.created_by,
            created_at: artifact!.created_at,
            updated_at: new Date().toISOString()
        }

        artifacts.value[index] = updatedArtifact

        try {
            const result = await artifactService.updateArtifact(artifactId, updates)
            const currentIndex = artifacts.value.findIndex(a => a.id === artifactId)
            if (currentIndex !== -1) {
                artifacts.value[currentIndex] = result
            }
            return result
        } catch (e) {
            const rollbackIndex = artifacts.value.findIndex(a => a.id === artifactId)
            if (rollbackIndex !== -1) {
                artifacts.value[rollbackIndex] = oldArtifact
            }
            error.value = (e as Error).message
            return null
        }
    }

    async function updateTask(taskId: string, updates: Partial<TaskContent & { title?: string }>) {
        const data: ArtifactUpdate = {}
        if (updates.title) data.title = updates.title

        const contentUpdates = { ...updates }
        delete contentUpdates.title
        if (Object.keys(contentUpdates).length > 0) {
            // We need to fetch current content to merge? 
            // Actually updateArtifact merges it optimistically, but the API expects partial content update?
            // The API (artifactService.updateArtifact) takes ArtifactUpdate which has content?: Record<string, any>
            // So we can just pass the partial content.
            data.content = contentUpdates
        }
        return updateArtifact(taskId, data)
    }

    async function moveTask(taskId: string, newStatus: TaskContent['status']) {
        return updateTask(taskId, { status: newStatus })
    }

    async function deleteTask(taskId: string) {
        const taskIndex = artifacts.value.findIndex(a => a.id === taskId)
        if (taskIndex === -1) return false

        // Optimistic delete
        const removedItems = artifacts.value.splice(taskIndex, 1)
        const removed = removedItems[0]

        try {
            await artifactService.deleteArtifact(taskId)
            return true
        } catch (e) {
            // Rollback
            if (removed) {
                artifacts.value.splice(taskIndex, 0, removed)
            }
            error.value = (e as Error).message
            return false
        }
    }

    // Real-time update handler (called from WebSocket)
    function handleArtifactUpdate(artifact: Artifact) {
        const index = artifacts.value.findIndex(a => a.id === artifact.id)
        if (index !== -1) {
            // Only update if newer version or same version (to allow self-repairs)
            const current = artifacts.value[index]
            if (current && artifact.version >= current.version) {
                artifacts.value[index] = artifact
            }
        } else {
            // New artifact - Check if it belongs to this room (safety check)
            if (currentRoomId.value && artifact.room_id === currentRoomId.value) {
                artifacts.value.unshift(artifact) // Add to top
            }
        }
    }

    function handleArtifactDelete(artifactId: string) {
        const index = artifacts.value.findIndex(a => a.id === artifactId)
        if (index !== -1) {
            artifacts.value.splice(index, 1)
        }
    }

    function $reset() {
        artifacts.value = []
        loading.value = false
        error.value = null
        currentRoomId.value = null
    }

    return {
        // State
        artifacts,
        loading,
        error,
        currentRoomId,
        // Computed
        kanbanColumns,
        documents,
        processes,
        // Actions
        loadArtifacts,
        createTask,
        createDoc,
        createProcess,
        updateArtifact,
        updateTask,
        moveTask,
        deleteTask,
        handleArtifactUpdate,
        handleArtifactDelete,
        $reset,
    }
})
