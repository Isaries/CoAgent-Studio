import { describe, it, expect, vi, beforeEach } from 'vitest'
import { agentService } from '@/services/agentService'

// ---------------------------------------------------------------------------
// Mock the api module and the constants (agentService imports API_ENDPOINTS)
// ---------------------------------------------------------------------------
vi.mock('@/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

// API_ENDPOINTS used by agentService — replicate exact values from constants/api.ts
vi.mock('@/constants/api', () => ({
  API_ENDPOINTS: {
    REFRESH: '/login/refresh',
    LOGIN: '/login',
    AGENTS: {
      BASE: '/agents',
      SYSTEM: '/agents/system',
      GENERATE: '/agents/generate',
    },
    AGENT_CONFIG: {
      BASE: '/agent-config',
    },
    AGENT_TYPES: {
      BASE: '/agent-types',
      SCHEMA: (typeName: string) => `/agent-types/${typeName}/schema`,
    },
    A2A: { WEBHOOK: '/a2a/webhook', HEALTH: '/a2a/health' },
    ORGANIZATIONS: { BASE: '/organizations' },
    PROJECTS: { BASE: '/projects' },
    THREADS: {
      BASE: '/threads',
      STATELESS: (agentId: string) => `/threads/stateless/${agentId}`,
    },
  },
  HTTP_STATUS: { UNAUTHORIZED: 401, FORBIDDEN: 403, SERVER_ERROR: 500 },
}))

import api from '@/api'
import type { AgentConfig } from '@/types/agent'

// ---------------------------------------------------------------------------
// Minimal AgentConfig fixture
// ---------------------------------------------------------------------------

const makeAgent = (overrides: Partial<AgentConfig> = {}): AgentConfig =>
  ({
    id: 'agent-1',
    name: 'Test Agent',
    type: 'teacher',
    model: 'gemini',
    project_id: 'project-1',
    system_prompt: '',
    is_active: true,
    ...overrides,
  } as AgentConfig)

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('agentService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // --------------------------------------------------------------------------
  // listAgents (getAgents)
  // --------------------------------------------------------------------------

  describe('getAgents()', () => {
    it('sends GET request to /agents/:projectId', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: [] })

      await agentService.getAgents('project-1')

      expect(api.get).toHaveBeenCalledWith('/agents/project-1')
    })

    it('returns response containing an array of agents', async () => {
      const agents = [makeAgent()]
      vi.mocked(api.get).mockResolvedValue({ data: agents })

      const result = await agentService.getAgents('project-1')

      expect(result.data).toEqual(agents)
    })
  })

  // --------------------------------------------------------------------------
  // getSystemAgents
  // --------------------------------------------------------------------------

  describe('getSystemAgents()', () => {
    it('sends GET request to /agents/system', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: [] })

      await agentService.getSystemAgents()

      expect(api.get).toHaveBeenCalledWith('/agents/system')
    })
  })

  // --------------------------------------------------------------------------
  // createAgent
  // --------------------------------------------------------------------------

  describe('createAgent()', () => {
    it('sends POST request to /agents/:projectId with the agent data', async () => {
      const agentData: Partial<AgentConfig> = { name: 'New Agent', type: 'teacher' }
      vi.mocked(api.post).mockResolvedValue({ data: makeAgent(agentData) })

      await agentService.createAgent('project-1', agentData)

      expect(api.post).toHaveBeenCalledWith('/agents/project-1', agentData)
    })

    it('returns the created agent in the response', async () => {
      const newAgent = makeAgent({ name: 'Created Agent' })
      vi.mocked(api.post).mockResolvedValue({ data: newAgent })

      const result = await agentService.createAgent('project-1', { name: 'Created Agent' })

      expect(result.data).toEqual(newAgent)
    })
  })

  // --------------------------------------------------------------------------
  // getAgent (via getAgents — service has no single-get; closest is getAgents)
  // A dedicated "getAgent" does not exist in agentService; the list is fetched
  // per project. We test the URL construction instead.
  // --------------------------------------------------------------------------

  describe('getAgents() with specific projectId', () => {
    it('sends GET request with the correct ID in the URL', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: [] })

      await agentService.getAgents('project-xyz')

      expect(api.get).toHaveBeenCalledWith('/agents/project-xyz')
    })
  })

  // --------------------------------------------------------------------------
  // updateAgent
  // --------------------------------------------------------------------------

  describe('updateAgent()', () => {
    it('sends PUT request to /agents/:agentId with the agent data', async () => {
      const updatedData: Partial<AgentConfig> = { id: 'agent-1', name: 'Updated Name' }
      vi.mocked(api.put).mockResolvedValue({ data: makeAgent(updatedData) })

      await agentService.updateAgent(updatedData)

      expect(api.put).toHaveBeenCalledWith('/agents/agent-1', updatedData)
    })

    it('throws an error when the agent data has no id', () => {
      const dataWithoutId: Partial<AgentConfig> = { name: 'No ID' }

      expect(() => agentService.updateAgent(dataWithoutId)).toThrow('Config ID required for update')
    })

    it('returns the updated agent in the response', async () => {
      const updated = makeAgent({ name: 'New Name' })
      vi.mocked(api.put).mockResolvedValue({ data: updated })

      const result = await agentService.updateAgent({ id: 'agent-1', name: 'New Name' })

      expect(result.data).toEqual(updated)
    })
  })

  // --------------------------------------------------------------------------
  // updateSystemAgent
  // --------------------------------------------------------------------------

  describe('updateSystemAgent()', () => {
    it('sends PUT request to /agents/system/:type', async () => {
      const data: Partial<AgentConfig> = { type: 'teacher', name: 'Teacher AI' }
      vi.mocked(api.put).mockResolvedValue({ data: makeAgent(data) })

      await agentService.updateSystemAgent(data)

      expect(api.put).toHaveBeenCalledWith('/agents/system/teacher', data)
    })
  })

  // --------------------------------------------------------------------------
  // deleteAgent
  // --------------------------------------------------------------------------

  describe('deleteAgent()', () => {
    it('sends DELETE request to /agents/:agentId', async () => {
      vi.mocked(api.delete).mockResolvedValue({ data: {} })

      await agentService.deleteAgent('agent-1')

      expect(api.delete).toHaveBeenCalledWith('/agents/agent-1')
    })
  })

  // --------------------------------------------------------------------------
  // activateAgent
  // --------------------------------------------------------------------------

  describe('activateAgent()', () => {
    it('sends PUT request to /agents/:agentId/activate', async () => {
      vi.mocked(api.put).mockResolvedValue({ data: {} })

      await agentService.activateAgent('agent-1')

      expect(api.put).toHaveBeenCalledWith('/agents/agent-1/activate')
    })
  })

  // --------------------------------------------------------------------------
  // getKeys / updateKeys
  // --------------------------------------------------------------------------

  describe('getKeys()', () => {
    it('sends GET request to /agents/:agentId/keys and resolves to data', async () => {
      const keys = { OPENAI_KEY: 'sk-abc' }
      vi.mocked(api.get).mockResolvedValue({ data: keys })

      const result = await agentService.getKeys('agent-1')

      expect(api.get).toHaveBeenCalledWith('/agents/agent-1/keys')
      expect(result).toEqual(keys)
    })
  })

  describe('updateKeys()', () => {
    it('sends PUT request to /agents/:agentId/keys with the keys payload', async () => {
      const keys = { OPENAI_KEY: 'sk-new', OLD_KEY: null }
      vi.mocked(api.put).mockResolvedValue({ data: makeAgent() })

      await agentService.updateKeys('agent-1', keys)

      expect(api.put).toHaveBeenCalledWith('/agents/agent-1/keys', keys)
    })
  })

  // --------------------------------------------------------------------------
  // generatePrompt
  // --------------------------------------------------------------------------

  describe('generatePrompt()', () => {
    it('sends POST request to /agents/generate with the request payload', async () => {
      const requestData = { agent_type: 'teacher', context: 'math' }
      vi.mocked(api.post).mockResolvedValue({ data: { prompt: 'Generated prompt' } })

      await agentService.generatePrompt(requestData as any)

      expect(api.post).toHaveBeenCalledWith('/agents/generate', requestData)
    })
  })

  // --------------------------------------------------------------------------
  // Versioning: createVersion / getVersions / restoreVersion
  // --------------------------------------------------------------------------

  describe('createVersion()', () => {
    it('sends POST request to /agent-config/:configId/versions', async () => {
      const versionData = { label: 'v1', snapshot: {} }
      vi.mocked(api.post).mockResolvedValue({ data: {} })

      await agentService.createVersion('config-1', versionData as any)

      expect(api.post).toHaveBeenCalledWith('/agent-config/config-1/versions', versionData)
    })
  })

  describe('getVersions()', () => {
    it('sends GET request to /agent-config/:configId/versions', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: [] })

      await agentService.getVersions('config-1')

      expect(api.get).toHaveBeenCalledWith('/agent-config/config-1/versions')
    })
  })

  describe('restoreVersion()', () => {
    it('sends POST request to /agent-config/:configId/versions/:versionId/restore', async () => {
      vi.mocked(api.post).mockResolvedValue({ data: makeAgent() })

      await agentService.restoreVersion('config-1', 'version-42')

      expect(api.post).toHaveBeenCalledWith(
        '/agent-config/config-1/versions/version-42/restore'
      )
    })
  })
})
