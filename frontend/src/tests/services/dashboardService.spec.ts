import { describe, it, expect, vi, beforeEach } from 'vitest'
import { dashboardService } from '../../services/dashboardService'

vi.mock('../../api', () => ({
  default: {
    get: vi.fn(),
  },
}))

import api from '../../api'

describe('dashboardService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getStats', () => {
    it('returns counts for non-student', async () => {
      vi.mocked(api.get)
        .mockResolvedValueOnce({ data: [{ id: '1' }, { id: '2' }] }) // spaces
        .mockResolvedValueOnce({ data: [{ id: 'a1' }] }) // agents
        .mockResolvedValueOnce({ data: [{ id: 'w1' }, { id: 'w2' }] }) // workflows

      const stats = await dashboardService.getStats(false)
      expect(stats.spaceCount).toBe(2)
      expect(stats.agentCount).toBe(1)
      expect(stats.workflowCount).toBe(2)
    })

    it('returns 0 for agents/workflows when student', async () => {
      vi.mocked(api.get)
        .mockResolvedValueOnce({ data: [{ id: '1' }] }) // spaces

      const stats = await dashboardService.getStats(true)
      expect(stats.spaceCount).toBe(1)
      expect(stats.agentCount).toBe(0)
      expect(stats.workflowCount).toBe(0)
    })
  })
})
