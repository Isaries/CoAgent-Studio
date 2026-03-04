import api from '../api'

export interface DashboardStats {
  spaceCount: number
  agentCount: number
  workflowCount: number
}

export const dashboardService = {
  async getStats(isStudent: boolean): Promise<DashboardStats> {
    const requests: Promise<any>[] = [
      api.get('/spaces/'),
    ]

    if (!isStudent) {
      requests.push(
        api.get('/agents/configs/').catch(() => ({ data: [] })),
        api.get('/workflows/').catch(() => ({ data: [] })),
      )
    }

    const results = await Promise.all(requests)

    return {
      spaceCount: results[0]?.data?.length ?? 0,
      agentCount: isStudent ? 0 : (results[1]?.data?.length ?? 0),
      workflowCount: isStudent ? 0 : (results[2]?.data?.length ?? 0),
    }
  },

  async getRecentRooms(): Promise<any[]> {
    try {
      const spacesRes = await api.get('/spaces/')
      const spaces = spacesRes.data || []
      const roomPromises = spaces.slice(0, 3).map((space: any) =>
        api.get(`/spaces/${space.id}/overview`).catch(() => ({ data: { rooms: [] } }))
      )
      const roomResults = await Promise.all(roomPromises)
      const allRooms: any[] = []
      for (const result of roomResults) {
        const rooms = result.data?.rooms || []
        allRooms.push(...rooms)
      }
      return allRooms.slice(0, 6)
    } catch {
      return []
    }
  },
}
