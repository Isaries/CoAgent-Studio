import { ref } from 'vue'
import { spaceService } from '../services/spaceService'
import { roomService } from '../services/roomService'
import { announcementService } from '../services/announcementService'
import type { Space, Room, SpaceMember, Announcement } from '../types/space'
import { useToastStore } from '../stores/toast'
import { useConfirm } from '../composables/useConfirm'

export function useSpace(spaceId: string) {
  const space = ref<Space | null>(null)
  const rooms = ref<Room[]>([])
  const members = ref<SpaceMember[]>([])
  const announcements = ref<Announcement[]>([])
  const loading = ref(true)
  const error = ref<string | null>(null)
  const toast = useToastStore()
  const { confirm } = useConfirm()

  const fetchSpaceData = async () => {
    loading.value = true
    try {
      const [spaceRes, roomsRes, announceRes] = await Promise.all([
        spaceService.getSpace(spaceId),
        roomService.getRooms(spaceId),
        announcementService.getAnnouncements(spaceId)
      ])
      space.value = spaceRes.data
      rooms.value = roomsRes.data
      announcements.value = announceRes.data
    } catch (e: any) {
      console.error(e)
      error.value = 'Failed to load space data'
    } finally {
      loading.value = false
    }
  }

  const fetchMembers = async () => {
    try {
      const res = await spaceService.getMembers(spaceId)
      members.value = res.data
    } catch (e) {
      console.error(e)
    }
  }

  const deleteSpace = async () => {
    await spaceService.deleteSpace(spaceId)
    return true
  }

  const deleteRoom = async (roomId: string) => {
    if (!(await confirm('Delete Room', 'Are you sure you want to delete this room?'))) return
    try {
      await roomService.deleteRoom(roomId)
      rooms.value = rooms.value.filter((r) => r.id !== roomId)
      toast.success('Room deleted')
    } catch (e) {
      toast.error('Failed to delete room')
    }
  }

  const updateMemberRole = async (member: SpaceMember, role: string) => {
    const originalRole = member.role
    try {
      member.role = role as 'student' | 'ta' // Optimistic
      await spaceService.updateMemberRole(spaceId, member.user_id, role)
      toast.success('Role updated')
    } catch (e) {
      console.error(e)
      toast.error('Failed to update role')
      member.role = originalRole
    }
  }

  const removeMember = async (memberId: string) => {
    if (!(await confirm('Remove Member', 'Are you sure you want to remove this member?'))) return
    try {
      await spaceService.removeMember(spaceId, memberId)
      members.value = members.value.filter((m) => m.user_id !== memberId)
      toast.success('Member removed')
    } catch (e: any) {
      console.error(e)
      toast.error(e.response?.data?.detail || 'Failed to remove member')
    }
  }

  const createAnnouncement = async (title: string, content: string) => {
    try {
      const res = await announcementService.createAnnouncement({
        space_id: spaceId,
        title,
        content
      })
      announcements.value.unshift(res.data)
      return res.data
    } catch (e: any) {
      console.error(e)
      throw e
    }
  }

  return {
    space,
    rooms,
    members,
    announcements,
    loading,
    error,
    fetchSpaceData,
    fetchMembers,
    updateMemberRole,
    removeMember,
    deleteSpace,
    deleteRoom,
    createAnnouncement
  }
}
