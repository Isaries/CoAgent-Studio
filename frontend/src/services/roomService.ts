import api from '../api'
import type { Room } from '../types/course'
import type { RoomAgentLinkSettings, ScheduleConfig, TriggerConfig } from '../types/agent'

export const roomService = {
  async getRooms(courseId: string) {
    return api.get<Room[]>('/rooms/', { params: { course_id: courseId } })
  },

  async createRoom(payload: Partial<Room>) {
    return api.post<Room>('/rooms/', payload)
  },

  async deleteRoom(id: string) {
    return api.delete(`/rooms/${id}`)
  },

  async getRoomAgents(roomId: string) {
    return api.get<any[]>(`/rooms/${roomId}/agents`)
  },

  async assignAgentToRoom(roomId: string, agentId: string) {
    return api.post(`/rooms/${roomId}/agents/${agentId}`)
  },

  async removeAgentFromRoom(roomId: string, agentId: string) {
    return api.delete(`/rooms/${roomId}/agents/${agentId}`)
  },

  // --- Room Agent Link Settings ---

  async getRoomAgentSettings(roomId: string, agentId: string) {
    return api.get<RoomAgentLinkSettings>(`/rooms/${roomId}/agents/${agentId}/settings`)
  },

  async updateRoomAgentSettings(
    roomId: string,
    agentId: string,
    data: {
      is_active?: boolean
      schedule_config?: ScheduleConfig | null
      trigger_config?: TriggerConfig | null
    }
  ) {
    return api.put(`/rooms/${roomId}/agents/${agentId}/settings`, data)
  },

  async syncSettingsToCourse(roomId: string, agentId: string) {
    return api.post(`/rooms/${roomId}/agents/${agentId}/sync-to-course`)
  },
}
