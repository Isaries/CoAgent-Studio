import api from '../api'
import type { Announcement } from '../types/course'

export const announcementService = {
  async getAnnouncements(courseId: string) {
    return api.get<Announcement[]>('/announcements/', {
      params: { course_id: courseId }
    })
  },

  async createAnnouncement(data: { course_id: string; title: string; content: string }) {
    return api.post<Announcement>('/announcements/', data)
  }
}
