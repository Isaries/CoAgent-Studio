import api from '../api'
import type { Course, CourseMember } from '../types/course'

export const courseService = {
    async getCourse(id: string) {
        return api.get<Course>(`/courses/${id}`)
    },

    async deleteCourse(id: string) {
        return api.delete(`/courses/${id}`)
    },

    // Members
    async getMembers(courseId: string) {
        return api.get<CourseMember[]>(`/courses/${courseId}/members`)
    },

    async updateMemberRole(courseId: string, userId: string, role: string) {
        return api.put(`/courses/${courseId}/members/${userId}`, { role })
    }
}
