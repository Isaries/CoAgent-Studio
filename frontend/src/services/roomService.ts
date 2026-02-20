import api from '../api'
import type { Room } from '../types/course'

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
  }
}
