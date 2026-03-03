import api from '../api'
import type { Space, SpaceMember } from '../types/space'
import type { SpacePreset } from '../types/enums'

export const spaceService = {
  async getSpaces() {
    return api.get<Space[]>('/spaces/')
  },

  async createSpace(data: { title: string; description: string; preset?: SpacePreset }) {
    return api.post<Space>('/spaces/', data)
  },

  async getSpace(id: string) {
    return api.get<Space>(`/spaces/${id}`)
  },

  async deleteSpace(id: string) {
    return api.delete(`/spaces/${id}`)
  },

  async getOverview(spaceId: string) {
    return api.get(`/spaces/${spaceId}/overview`)
  },

  // Members
  async getMembers(spaceId: string) {
    return api.get<SpaceMember[]>(`/spaces/${spaceId}/members`)
  },

  async updateMemberRole(spaceId: string, userId: string, role: string) {
    return api.put(`/spaces/${spaceId}/members/${userId}`, { role })
  },

  async removeMember(spaceId: string, userId: string) {
    return api.delete(`/spaces/${spaceId}/members/${userId}`)
  }
}

// Named exports for tree-shaking and backward-compat re-exports
export const getSpaces = spaceService.getSpaces
export const createSpace = spaceService.createSpace
export const getSpace = spaceService.getSpace
export const deleteSpace = spaceService.deleteSpace
export const getOverview = spaceService.getOverview
export const getMembers = spaceService.getMembers
export const updateMemberRole = spaceService.updateMemberRole
export const removeMember = spaceService.removeMember
