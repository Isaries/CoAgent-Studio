import { describe, it, expect, vi, beforeEach } from 'vitest'
import { workflowService } from '@/services/workflowService'
import type { Workflow, WorkflowGraphData, WorkflowRun, TriggerPolicy } from '@/services/workflowService'

// ---------------------------------------------------------------------------
// Mock the api module
// ---------------------------------------------------------------------------
vi.mock('@/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

import api from '@/api'

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const emptyGraph: WorkflowGraphData = { nodes: [], edges: [] }

const makeWorkflow = (overrides: Partial<Workflow> = {}): Workflow => ({
  id: 'wf-1',
  name: 'Test Workflow',
  is_active: true,
  graph_data: emptyGraph,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  ...overrides,
})

const makeRun = (overrides: Partial<WorkflowRun> = {}): WorkflowRun => ({
  id: 'run-1',
  workflow_id: 'wf-1',
  session_id: 'sess-1',
  status: 'completed',
  execution_log: [],
  started_at: '2026-01-01T00:00:00Z',
  completed_at: '2026-01-01T00:01:00Z',
  error_message: null,
  ...overrides,
})

const makeTrigger = (overrides: Partial<TriggerPolicy> = {}): TriggerPolicy => ({
  id: 'trig-1',
  name: 'User Message Trigger',
  event_type: 'user_message',
  conditions: {},
  target_workflow_id: 'wf-1',
  scope_session_id: null,
  is_active: true,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  ...overrides,
})

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('workflowService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // --------------------------------------------------------------------------
  // listWorkflows
  // --------------------------------------------------------------------------

  describe('listWorkflows()', () => {
    it('sends GET request to /workflows', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: [] })

      await workflowService.listWorkflows()

      expect(api.get).toHaveBeenCalledWith('/workflows')
    })

    it('returns the list of workflows from the response', async () => {
      const workflows = [makeWorkflow()]
      vi.mocked(api.get).mockResolvedValue({ data: workflows })

      const result = await workflowService.listWorkflows()

      expect(result.data).toEqual(workflows)
    })
  })

  // --------------------------------------------------------------------------
  // getWorkflowById
  // --------------------------------------------------------------------------

  describe('getWorkflowById()', () => {
    it('sends GET request to /workflows/:workflowId', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: makeWorkflow() })

      await workflowService.getWorkflowById('wf-1')

      expect(api.get).toHaveBeenCalledWith('/workflows/wf-1')
    })

    it('returns the workflow from the response', async () => {
      const wf = makeWorkflow({ name: 'My Flow' })
      vi.mocked(api.get).mockResolvedValue({ data: wf })

      const result = await workflowService.getWorkflowById('wf-1')

      expect(result.data).toEqual(wf)
    })
  })

  // --------------------------------------------------------------------------
  // createWorkflow
  // --------------------------------------------------------------------------

  describe('createWorkflow()', () => {
    it('sends POST request to /workflows with the provided data', async () => {
      const payload = { name: 'New Flow', graph_data: emptyGraph, is_active: false }
      vi.mocked(api.post).mockResolvedValue({ data: makeWorkflow(payload) })

      await workflowService.createWorkflow(payload)

      expect(api.post).toHaveBeenCalledWith('/workflows', payload)
    })

    it('returns the created workflow in the response', async () => {
      const created = makeWorkflow({ name: 'Created Flow' })
      vi.mocked(api.post).mockResolvedValue({ data: created })

      const result = await workflowService.createWorkflow({ name: 'Created Flow' })

      expect(result.data).toEqual(created)
    })

    it('works with an empty payload object', async () => {
      vi.mocked(api.post).mockResolvedValue({ data: makeWorkflow() })

      await workflowService.createWorkflow({})

      expect(api.post).toHaveBeenCalledWith('/workflows', {})
    })
  })

  // --------------------------------------------------------------------------
  // updateWorkflow
  // --------------------------------------------------------------------------

  describe('updateWorkflow()', () => {
    it('sends PUT request to /workflows/:workflowId with updated data', async () => {
      const updates = { name: 'Renamed Flow', is_active: false }
      vi.mocked(api.put).mockResolvedValue({ data: makeWorkflow(updates) })

      await workflowService.updateWorkflow('wf-1', updates)

      expect(api.put).toHaveBeenCalledWith('/workflows/wf-1', updates)
    })

    it('returns the updated workflow in the response', async () => {
      const updated = makeWorkflow({ name: 'Updated' })
      vi.mocked(api.put).mockResolvedValue({ data: updated })

      const result = await workflowService.updateWorkflow('wf-1', { name: 'Updated' })

      expect(result.data).toEqual(updated)
    })
  })

  // --------------------------------------------------------------------------
  // deleteWorkflowById
  // --------------------------------------------------------------------------

  describe('deleteWorkflowById()', () => {
    it('sends DELETE request to /workflows/:workflowId', async () => {
      vi.mocked(api.delete).mockResolvedValue({ data: {} })

      await workflowService.deleteWorkflowById('wf-1')

      expect(api.delete).toHaveBeenCalledWith('/workflows/wf-1')
    })
  })

  // --------------------------------------------------------------------------
  // executeWorkflow (runWorkflow)
  // --------------------------------------------------------------------------

  describe('executeWorkflow()', () => {
    it('sends POST request to /workflows/:workflowId/execute', async () => {
      vi.mocked(api.post).mockResolvedValue({ data: makeRun() })

      await workflowService.executeWorkflow('wf-1')

      expect(api.post).toHaveBeenCalledWith('/workflows/wf-1/execute', {})
    })

    it('passes the payload to the execute endpoint', async () => {
      const payload = { input_key: 'value', session_id: 'sess-99' }
      vi.mocked(api.post).mockResolvedValue({ data: makeRun() })

      await workflowService.executeWorkflow('wf-1', payload)

      expect(api.post).toHaveBeenCalledWith('/workflows/wf-1/execute', payload)
    })

    it('uses an empty object as default payload when none provided', async () => {
      vi.mocked(api.post).mockResolvedValue({ data: makeRun() })

      await workflowService.executeWorkflow('wf-2')

      expect(api.post).toHaveBeenCalledWith('/workflows/wf-2/execute', {})
    })
  })

  // --------------------------------------------------------------------------
  // getWorkflowRuns
  // --------------------------------------------------------------------------

  describe('getWorkflowRuns()', () => {
    it('sends GET request to /workflows/:workflowId/runs with default limit', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: [] })

      await workflowService.getWorkflowRuns('wf-1')

      expect(api.get).toHaveBeenCalledWith('/workflows/wf-1/runs', { params: { limit: 20 } })
    })

    it('sends GET with custom limit when provided', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: [] })

      await workflowService.getWorkflowRuns('wf-1', 5)

      expect(api.get).toHaveBeenCalledWith('/workflows/wf-1/runs', { params: { limit: 5 } })
    })
  })

  // --------------------------------------------------------------------------
  // getWorkflowRunById
  // --------------------------------------------------------------------------

  describe('getWorkflowRunById()', () => {
    it('sends GET request to /workflows/:workflowId/runs/:runId', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: makeRun() })

      await workflowService.getWorkflowRunById('wf-1', 'run-1')

      expect(api.get).toHaveBeenCalledWith('/workflows/wf-1/runs/run-1')
    })
  })

  // --------------------------------------------------------------------------
  // Legacy room-scoped methods
  // --------------------------------------------------------------------------

  describe('getWorkflow() — legacy room-scoped', () => {
    it('sends GET request to /rooms/:roomId/workflow', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: makeWorkflow() })

      await workflowService.getWorkflow('room-1')

      expect(api.get).toHaveBeenCalledWith('/rooms/room-1/workflow')
    })
  })

  describe('saveWorkflow() — legacy room-scoped', () => {
    it('sends PUT request to /rooms/:roomId/workflow with the data', async () => {
      const data = { name: 'Room Flow', is_active: true }
      vi.mocked(api.put).mockResolvedValue({ data: makeWorkflow(data) })

      await workflowService.saveWorkflow('room-1', data)

      expect(api.put).toHaveBeenCalledWith('/rooms/room-1/workflow', data)
    })
  })

  describe('deleteWorkflow() — legacy room-scoped', () => {
    it('sends DELETE request to /rooms/:roomId/workflow', async () => {
      vi.mocked(api.delete).mockResolvedValue({ data: {} })

      await workflowService.deleteWorkflow('room-1')

      expect(api.delete).toHaveBeenCalledWith('/rooms/room-1/workflow')
    })
  })

  // --------------------------------------------------------------------------
  // Trigger Policies
  // --------------------------------------------------------------------------

  describe('listTriggers()', () => {
    it('sends GET request to /triggers', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: [] })

      await workflowService.listTriggers()

      expect(api.get).toHaveBeenCalledWith('/triggers')
    })
  })

  describe('createTrigger()', () => {
    it('sends POST request to /triggers with trigger data', async () => {
      const triggerData: Partial<TriggerPolicy> = {
        name: 'On Message',
        event_type: 'user_message',
        target_workflow_id: 'wf-1',
      }
      vi.mocked(api.post).mockResolvedValue({ data: makeTrigger(triggerData) })

      await workflowService.createTrigger(triggerData)

      expect(api.post).toHaveBeenCalledWith('/triggers', triggerData)
    })
  })

  describe('updateTrigger()', () => {
    it('sends PUT request to /triggers/:triggerId with updated data', async () => {
      const updates: Partial<TriggerPolicy> = { is_active: false }
      vi.mocked(api.put).mockResolvedValue({ data: makeTrigger(updates) })

      await workflowService.updateTrigger('trig-1', updates)

      expect(api.put).toHaveBeenCalledWith('/triggers/trig-1', updates)
    })
  })

  describe('deleteTrigger()', () => {
    it('sends DELETE request to /triggers/:triggerId', async () => {
      vi.mocked(api.delete).mockResolvedValue({ data: {} })

      await workflowService.deleteTrigger('trig-1')

      expect(api.delete).toHaveBeenCalledWith('/triggers/trig-1')
    })
  })
})
