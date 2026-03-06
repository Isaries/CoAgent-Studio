import { setActivePinia, createPinia } from 'pinia'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useWorkspaceStore } from '@/stores/workspace'
import type { Artifact } from '@/types/artifact'

vi.mock('@/services/artifactService', () => ({
  default: {
    listArtifacts: vi.fn(),
    createArtifact: vi.fn(),
    updateArtifact: vi.fn(),
    deleteArtifact: vi.fn()
  }
}))

function makeTask(overrides: Partial<Artifact> = {}): Artifact {
  return {
    id: 'task-1',
    room_id: 'room-1',
    type: 'task',
    title: 'Test Task',
    content: { status: 'todo', priority: 'medium', order: 0 },
    version: 1,
    created_by: 'user-1',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides
  }
}

describe('Workspace Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('initial state', () => {
    it('has empty artifacts', () => {
      const store = useWorkspaceStore()
      expect(store.artifacts).toEqual([])
    })

    it('loading is false', () => {
      const store = useWorkspaceStore()
      expect(store.loading).toBe(false)
    })

    it('error is null', () => {
      const store = useWorkspaceStore()
      expect(store.error).toBeNull()
    })

    it('currentRoomId is null', () => {
      const store = useWorkspaceStore()
      expect(store.currentRoomId).toBeNull()
    })
  })

  describe('loadArtifacts', () => {
    it('fetches and stores artifacts', async () => {
      const artifactService = (await import('@/services/artifactService')).default
      const mockArtifacts = [makeTask({ id: 'a1' }), makeTask({ id: 'a2' })]
      vi.mocked(artifactService.listArtifacts).mockResolvedValueOnce(mockArtifacts)

      const store = useWorkspaceStore()
      await store.loadArtifacts('room-1')

      expect(store.artifacts).toEqual(mockArtifacts)
      expect(store.currentRoomId).toBe('room-1')
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
    })

    it('sets error message on failure', async () => {
      const artifactService = (await import('@/services/artifactService')).default
      vi.mocked(artifactService.listArtifacts).mockRejectedValueOnce(new Error('Network fail'))

      const store = useWorkspaceStore()
      await store.loadArtifacts('room-1')

      expect(store.artifacts).toEqual([])
      expect(store.error).toBe('Network fail')
      expect(store.loading).toBe(false)
    })

    it('skips fetch when already loading', async () => {
      const artifactService = (await import('@/services/artifactService')).default

      const store = useWorkspaceStore()
      store.loading = true

      await store.loadArtifacts('room-1')

      expect(artifactService.listArtifacts).not.toHaveBeenCalled()
    })
  })

  describe('createTask', () => {
    it('adds task to artifacts list', async () => {
      const artifactService = (await import('@/services/artifactService')).default
      const newTask = makeTask({ id: 'new-1', title: 'My Task' })
      vi.mocked(artifactService.createArtifact).mockResolvedValueOnce(newTask)

      const store = useWorkspaceStore()
      store.currentRoomId = 'room-1'

      const result = await store.createTask('My Task')

      expect(result).toEqual(newTask)
      expect(store.artifacts).toContainEqual(newTask)
    })

    it('returns null when currentRoomId is not set', async () => {
      const store = useWorkspaceStore()
      const result = await store.createTask('Orphan')
      expect(result).toBeNull()
    })

    it('sets status in content', async () => {
      const artifactService = (await import('@/services/artifactService')).default
      vi.mocked(artifactService.createArtifact).mockResolvedValueOnce(makeTask())

      const store = useWorkspaceStore()
      store.currentRoomId = 'room-1'

      await store.createTask('Task', 'in_progress')

      expect(artifactService.createArtifact).toHaveBeenCalledWith(
        'room-1',
        expect.objectContaining({
          type: 'task',
          title: 'Task',
          content: expect.objectContaining({ status: 'in_progress' })
        })
      )
    })
  })

  describe('deleteTask', () => {
    it('removes task on success', async () => {
      const artifactService = (await import('@/services/artifactService')).default
      vi.mocked(artifactService.deleteArtifact).mockResolvedValueOnce(undefined)

      const task = makeTask({ id: 'task-to-delete' })
      const store = useWorkspaceStore()
      store.artifacts = [task]

      const result = await store.deleteTask('task-to-delete')

      expect(result).toBe(true)
      expect(store.artifacts).toHaveLength(0)
    })

    it('rolls back on API error', async () => {
      const artifactService = (await import('@/services/artifactService')).default
      vi.mocked(artifactService.deleteArtifact).mockRejectedValueOnce(new Error('Delete failed'))

      const task = makeTask({ id: 'task-to-delete' })
      const store = useWorkspaceStore()
      store.artifacts = [task]

      const result = await store.deleteTask('task-to-delete')

      expect(result).toBe(false)
      expect(store.artifacts).toHaveLength(1)
      expect(store.error).toBe('Delete failed')
    })

    it('returns false for nonexistent task', async () => {
      const store = useWorkspaceStore()
      const result = await store.deleteTask('nonexistent')
      expect(result).toBe(false)
    })
  })

  describe('moveTask', () => {
    it('calls updateArtifact with new status', async () => {
      const artifactService = (await import('@/services/artifactService')).default
      const task = makeTask({
        id: 'task-1',
        content: { status: 'todo', priority: 'medium', order: 0 }
      })
      const updated = makeTask({
        id: 'task-1',
        content: { status: 'in_progress', priority: 'medium', order: 0 }
      })
      vi.mocked(artifactService.updateArtifact).mockResolvedValueOnce(updated)

      const store = useWorkspaceStore()
      store.artifacts = [task]

      await store.moveTask('task-1', 'in_progress')

      expect(artifactService.updateArtifact).toHaveBeenCalledWith(
        'task-1',
        expect.objectContaining({ content: expect.objectContaining({ status: 'in_progress' }) })
      )
    })
  })

  describe('computed: kanbanColumns', () => {
    it('groups task artifacts by status', () => {
      const store = useWorkspaceStore()
      store.artifacts = [
        makeTask({ id: 't1', content: { status: 'todo', order: 0 } }),
        makeTask({ id: 't2', content: { status: 'in_progress', order: 0 } }),
        makeTask({ id: 't3', content: { status: 'todo', order: 1 } }),
        makeTask({ id: 'd1', type: 'doc', content: {} as any })
      ]

      const cols = store.kanbanColumns
      const todoCol = cols.find((c) => c.status === 'todo')
      const inProgressCol = cols.find((c) => c.status === 'in_progress')
      const reviewCol = cols.find((c) => c.status === 'review')

      expect(cols).toHaveLength(4)
      expect(todoCol?.tasks).toHaveLength(2)
      expect(inProgressCol?.tasks).toHaveLength(1)
      expect(reviewCol?.tasks).toHaveLength(0)
    })

    it('sorts tasks by order within column', () => {
      const store = useWorkspaceStore()
      store.artifacts = [
        makeTask({ id: 't1', content: { status: 'todo', order: 2 } }),
        makeTask({ id: 't2', content: { status: 'todo', order: 0 } }),
        makeTask({ id: 't3', content: { status: 'todo', order: 1 } })
      ]

      const todoCol = store.kanbanColumns.find((c) => c.status === 'todo')
      expect(todoCol!.tasks.map((t) => t.id)).toEqual(['t2', 't3', 't1'])
    })
  })

  describe('computed: documents', () => {
    it('filters doc type artifacts', () => {
      const store = useWorkspaceStore()
      store.artifacts = [
        makeTask({ id: 't1', type: 'task' }),
        makeTask({ id: 'd1', type: 'doc' }),
        makeTask({ id: 'd2', type: 'doc' })
      ]

      expect(store.documents).toHaveLength(2)
      expect(store.documents.every((a) => a.type === 'doc')).toBe(true)
    })
  })

  describe('computed: processes', () => {
    it('filters process type artifacts', () => {
      const store = useWorkspaceStore()
      store.artifacts = [
        makeTask({ id: 't1', type: 'task' }),
        makeTask({ id: 'p1', type: 'process' })
      ]

      expect(store.processes).toHaveLength(1)
      expect(store.processes[0].id).toBe('p1')
    })
  })

  describe('handleArtifactUpdate', () => {
    it('updates existing artifact by id', () => {
      const store = useWorkspaceStore()
      const original = makeTask({ id: 'a1', version: 1, title: 'Old' })
      store.artifacts = [original]

      store.handleArtifactUpdate({ ...original, version: 2, title: 'New' })

      expect(store.artifacts[0].title).toBe('New')
      expect(store.artifacts[0].version).toBe(2)
    })

    it('ignores older version updates', () => {
      const store = useWorkspaceStore()
      const current = makeTask({ id: 'a1', version: 5, title: 'Current' })
      store.artifacts = [current]

      store.handleArtifactUpdate({ ...current, version: 3, title: 'Stale' })

      expect(store.artifacts[0].title).toBe('Current')
    })

    it('adds new artifact belonging to current room', () => {
      const store = useWorkspaceStore()
      store.currentRoomId = 'room-1'

      const newArtifact = makeTask({ id: 'new-1', room_id: 'room-1' })
      store.handleArtifactUpdate(newArtifact)

      expect(store.artifacts).toHaveLength(1)
      expect(store.artifacts[0].id).toBe('new-1')
    })
  })

  describe('handleArtifactDelete', () => {
    it('removes artifact by id', () => {
      const store = useWorkspaceStore()
      store.artifacts = [makeTask({ id: 'a1' }), makeTask({ id: 'a2' })]

      store.handleArtifactDelete('a1')

      expect(store.artifacts).toHaveLength(1)
      expect(store.artifacts[0].id).toBe('a2')
    })
  })

  describe('$reset', () => {
    it('resets all state to initial values', () => {
      const store = useWorkspaceStore()
      store.artifacts = [makeTask()]
      store.loading = true
      store.error = 'Some error'
      store.currentRoomId = 'room-42'

      store.$reset()

      expect(store.artifacts).toEqual([])
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
      expect(store.currentRoomId).toBeNull()
    })
  })
})
