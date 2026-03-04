import { setActivePinia, createPinia } from 'pinia'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useAgentTypesStore } from '@/stores/agentTypes'
import { AgentCategory } from '@/types/enums'
import type { AgentTypeMetadata } from '@/types/agentTypes'

vi.mock('@/services/agentTypesService', () => ({
  agentTypesService: {
    list: vi.fn(),
    create: vi.fn(),
    delete: vi.fn(),
  },
}))

function makeType(overrides: Partial<AgentTypeMetadata> = {}): AgentTypeMetadata {
  return {
    type_name: 'teacher',
    display_name: 'Teacher Agent',
    category: AgentCategory.INSTRUCTOR,
    default_model_provider: 'openai',
    is_system: true,
    ...overrides,
  } as AgentTypeMetadata
}

describe('AgentTypes Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('initial state', () => {
    it('has empty types', () => {
      const store = useAgentTypesStore()
      expect(store.types).toEqual([])
    })

    it('loading is false', () => {
      const store = useAgentTypesStore()
      expect(store.loading).toBe(false)
    })

    it('error is null', () => {
      const store = useAgentTypesStore()
      expect(store.error).toBeNull()
    })
  })

  describe('fetchTypes', () => {
    it('loads agent types from API', async () => {
      const { agentTypesService } = await import('@/services/agentTypesService')
      const mockTypes = [makeType({ type_name: 'teacher' }), makeType({ type_name: 'student', category: AgentCategory.PARTICIPANT })]
      vi.mocked(agentTypesService.list).mockResolvedValueOnce({ data: mockTypes } as any)

      const store = useAgentTypesStore()
      const result = await store.fetchTypes()

      expect(result).toEqual(mockTypes)
      expect(store.types).toEqual(mockTypes)
      expect(store.loading).toBe(false)
    })

    it('uses cache when recently fetched', async () => {
      const { agentTypesService } = await import('@/services/agentTypesService')
      vi.mocked(agentTypesService.list).mockResolvedValue({ data: [makeType()] } as any)

      const store = useAgentTypesStore()
      await store.fetchTypes()
      await store.fetchTypes()

      expect(agentTypesService.list).toHaveBeenCalledTimes(1)
    })

    it('bypasses cache with force=true', async () => {
      const { agentTypesService } = await import('@/services/agentTypesService')
      vi.mocked(agentTypesService.list).mockResolvedValue({ data: [makeType()] } as any)

      const store = useAgentTypesStore()
      await store.fetchTypes()
      await store.fetchTypes(true)

      expect(agentTypesService.list).toHaveBeenCalledTimes(2)
    })

    it('fetches again after clearCache', async () => {
      const { agentTypesService } = await import('@/services/agentTypesService')
      vi.mocked(agentTypesService.list).mockResolvedValue({ data: [makeType()] } as any)

      const store = useAgentTypesStore()
      await store.fetchTypes()
      store.clearCache()
      await store.fetchTypes()

      expect(agentTypesService.list).toHaveBeenCalledTimes(2)
    })

    it('sets error and rethrows on failure', async () => {
      const { agentTypesService } = await import('@/services/agentTypesService')
      vi.mocked(agentTypesService.list).mockRejectedValueOnce(new Error('API error'))

      const store = useAgentTypesStore()
      await expect(store.fetchTypes()).rejects.toThrow('API error')
      expect(store.error).toBe('API error')
      expect(store.loading).toBe(false)
    })
  })

  describe('computed getters', () => {
    it('instructorTypes filters by INSTRUCTOR category', () => {
      const store = useAgentTypesStore()
      store.types = [
        makeType({ type_name: 'teacher', category: AgentCategory.INSTRUCTOR }),
        makeType({ type_name: 'student', category: AgentCategory.PARTICIPANT }),
        makeType({ type_name: 'tutor', category: AgentCategory.INSTRUCTOR }),
      ]

      expect(store.instructorTypes).toHaveLength(2)
      expect(store.instructorTypes.every(t => t.category === AgentCategory.INSTRUCTOR)).toBe(true)
    })

    it('participantTypes filters by PARTICIPANT category', () => {
      const store = useAgentTypesStore()
      store.types = [
        makeType({ type_name: 'student', category: AgentCategory.PARTICIPANT }),
        makeType({ type_name: 'teacher', category: AgentCategory.INSTRUCTOR }),
      ]

      expect(store.participantTypes).toHaveLength(1)
      expect(store.participantTypes[0].type_name).toBe('student')
    })

    it('utilityTypes filters by UTILITY category', () => {
      const store = useAgentTypesStore()
      store.types = [
        makeType({ type_name: 'helper', category: AgentCategory.UTILITY }),
        makeType({ type_name: 'teacher', category: AgentCategory.INSTRUCTOR }),
      ]

      expect(store.utilityTypes).toHaveLength(1)
    })

    it('externalTypes filters by EXTERNAL category', () => {
      const store = useAgentTypesStore()
      store.types = [
        makeType({ type_name: 'external-bot', category: AgentCategory.EXTERNAL }),
        makeType({ type_name: 'teacher', category: AgentCategory.INSTRUCTOR }),
      ]

      expect(store.externalTypes).toHaveLength(1)
    })

    it('systemTypes filters is_system=true', () => {
      const store = useAgentTypesStore()
      store.types = [
        makeType({ type_name: 'sys', is_system: true }),
        makeType({ type_name: 'custom', is_system: false }),
      ]

      expect(store.systemTypes).toHaveLength(1)
      expect(store.systemTypes[0].type_name).toBe('sys')
    })

    it('customTypes filters is_system=false', () => {
      const store = useAgentTypesStore()
      store.types = [
        makeType({ type_name: 'sys', is_system: true }),
        makeType({ type_name: 'custom', is_system: false }),
      ]

      expect(store.customTypes).toHaveLength(1)
      expect(store.customTypes[0].type_name).toBe('custom')
    })
  })

  describe('getTypeByName', () => {
    it('returns matching type', () => {
      const store = useAgentTypesStore()
      const target = makeType({ type_name: 'my-agent' })
      store.types = [makeType({ type_name: 'other' }), target]

      expect(store.getTypeByName('my-agent')).toEqual(target)
    })

    it('returns undefined for unknown type name', () => {
      const store = useAgentTypesStore()
      store.types = [makeType({ type_name: 'existing' })]

      expect(store.getTypeByName('nonexistent')).toBeUndefined()
    })
  })

  describe('createType', () => {
    it('adds new type to the list', async () => {
      const { agentTypesService } = await import('@/services/agentTypesService')
      const newType = makeType({ type_name: 'my-custom', is_system: false })
      vi.mocked(agentTypesService.create).mockResolvedValueOnce({ data: newType } as any)

      const store = useAgentTypesStore()
      const result = await store.createType({
        type_name: 'my-custom',
        display_name: 'My Custom',
        category: AgentCategory.UTILITY,
        default_model_provider: 'openai',
      } as any)

      expect(result).toEqual(newType)
      expect(store.types).toContainEqual(newType)
      expect(store.loading).toBe(false)
    })
  })

  describe('deleteType', () => {
    it('removes type from list by type_name', async () => {
      const { agentTypesService } = await import('@/services/agentTypesService')
      vi.mocked(agentTypesService.delete).mockResolvedValueOnce(undefined as any)

      const store = useAgentTypesStore()
      store.types = [
        makeType({ type_name: 'keep-me' }),
        makeType({ type_name: 'delete-me' }),
      ]

      await store.deleteType('delete-me')

      expect(store.types).toHaveLength(1)
      expect(store.types[0].type_name).toBe('keep-me')
    })
  })

  describe('clearCache', () => {
    it('causes next fetchTypes to hit API', async () => {
      const { agentTypesService } = await import('@/services/agentTypesService')
      vi.mocked(agentTypesService.list).mockResolvedValue({ data: [makeType()] } as any)

      const store = useAgentTypesStore()
      await store.fetchTypes()
      expect(agentTypesService.list).toHaveBeenCalledTimes(1)

      store.clearCache()
      await store.fetchTypes()
      expect(agentTypesService.list).toHaveBeenCalledTimes(2)
    })
  })
})
