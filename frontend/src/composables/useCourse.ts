import { ref } from 'vue'
import { courseService } from '../services/courseService'
import { roomService } from '../services/roomService'
import type { Course, Room, CourseMember } from '../types/course'

export function useCourse(courseId: string) {
    const course = ref<Course | null>(null)
    const rooms = ref<Room[]>([])
    const members = ref<CourseMember[]>([])
    const loading = ref(true)
    const error = ref<string | null>(null)

    const fetchCourseData = async () => {
        loading.value = true
        try {
            const [courseRes, roomsRes] = await Promise.all([
                courseService.getCourse(courseId),
                roomService.getRooms(courseId)
            ])
            course.value = courseRes.data
            rooms.value = roomsRes.data
        } catch (e: any) {
            console.error(e)
            error.value = "Failed to load course data"
        } finally {
            loading.value = false
        }
    }

    const fetchMembers = async () => {
        try {
            const res = await courseService.getMembers(courseId)
            members.value = res.data
        } catch (e) {
            console.error(e)
        }
    }

    const deleteCourse = async () => {
        try {
            await courseService.deleteCourse(courseId)
            return true
        } catch (e) {
            throw e
        }
    }

    const deleteRoom = async (roomId: string) => {
        if (!confirm("Are you sure you want to delete this room?")) return
        try {
            await roomService.deleteRoom(roomId)
            rooms.value = rooms.value.filter(r => r.id !== roomId)
        } catch (e) {
            alert("Failed to delete room")
        }
    }

    const updateMemberRole = async (member: CourseMember, role: string) => {
        const originalRole = member.role
        try {
            member.role = role as 'student' | 'ta' // Optimistic
            await courseService.updateMemberRole(courseId, member.user_id, role)
        } catch (e) {
            console.error(e)
            alert("Failed to update role")
            member.role = originalRole
        }
    }

    const removeMember = async (memberId: string) => {
        if (!confirm("Are you sure you want to remove this member?")) return
        try {
            // Need to implement removeMember in courseService first
            await courseService.removeMember(courseId, memberId)
            members.value = members.value.filter(m => m.user_id !== memberId)
        } catch (e: any) {
            console.error(e)
            alert(e.response?.data?.detail || "Failed to remove member")
        }
    }

    return {
        course,
        rooms,
        members,
        loading,
        error,
        fetchCourseData,
        fetchMembers,
        updateMemberRole,
        removeMember,
        deleteCourse,
        deleteRoom
    }
}
