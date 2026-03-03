import api from '../api'
import type { Announcement } from '../types/space'

export const announcementService = {
  async getAnnouncements(spaceId: string) {
    return api.get<Announcement[]>('/announcements/', {
      params: { space_id: spaceId }
    })
  },

  async createAnnouncement(data: { space_id: string; title: string; content: string }) {
    return api.post<Announcement>('/announcements/', data)
  }
}
