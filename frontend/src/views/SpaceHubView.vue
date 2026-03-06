<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useSpace } from '../composables/useSpace'
import { useToastStore } from '../stores/toast'
import { useConfirm } from '../composables/useConfirm'
import { spaceService } from '../services/spaceService'

import CreateRoomModal from '../components/space/modals/CreateRoomModal.vue'
import InviteMemberModal from '../components/space/modals/InviteMemberModal.vue'
import AssignMemberModal from '../components/space/modals/AssignMemberModal.vue'
import SpaceRoomList from '../components/space/SpaceRoomList.vue'
import SpaceMemberList from '../components/space/SpaceMemberList.vue'
import SpaceAnnouncementList from '../components/space/SpaceAnnouncementList.vue'

type TabKey = 'overview' | 'rooms' | 'members' | 'announcements' | 'knowledge' | 'analytics'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const toast = useToastStore()
const { confirm } = useConfirm()

const spaceId = route.params.id as string
const {
  space,
  rooms,
  members,
  announcements,
  loading,
  fetchSpaceData,
  fetchMembers,
  deleteSpace,
  deleteRoom,
  updateMemberRole,
  removeMember,
  createAnnouncement
} = useSpace(spaceId)

const activeTab = ref<TabKey>('overview')

// Overview data
const overview = ref<any>(null)
const overviewLoading = ref(false)

// Modal Refs
const createRoomModal = ref<InstanceType<typeof CreateRoomModal> | null>(null)
const inviteModal = ref<InstanceType<typeof InviteMemberModal> | null>(null)
const assignModal = ref<InstanceType<typeof AssignMemberModal> | null>(null)

// State for assignment
const activeRoomId = ref('')

const isStudent = computed(() => authStore.isStudent)
const currentUserRole = computed(() => authStore.user?.role)

const presetBadgeClass = computed(() => {
  switch (space.value?.preset) {
    case 'colearn':
      return 'badge-primary'
    case 'support':
      return 'badge-secondary'
    case 'research':
      return 'badge-accent'
    default:
      return 'badge-ghost'
  }
})

const tabs: { key: TabKey; label: string }[] = [
  { key: 'overview', label: 'Overview' },
  { key: 'rooms', label: 'Rooms' },
  { key: 'members', label: 'Members' },
  { key: 'announcements', label: 'Announcements' },
  { key: 'knowledge', label: 'Knowledge' },
  { key: 'analytics', label: 'Analytics' }
]

const switchTab = (tab: TabKey) => {
  activeTab.value = tab
  if (tab === 'members') fetchMembers()
  if (tab === 'overview') fetchOverview()
}

const fetchOverview = async () => {
  overviewLoading.value = true
  try {
    const res = await spaceService.getOverview(spaceId)
    overview.value = res.data
  } catch (e) {
    console.error(e)
  } finally {
    overviewLoading.value = false
  }
}

// Actions
const handleDeleteSpace = async () => {
  if (
    !(await confirm(
      'Delete Space',
      'DANGER: Are you sure you want to delete this ENTIRE space? All rooms and messages will be lost.'
    ))
  )
    return
  try {
    await deleteSpace()
    toast.success('Space deleted successfully')
    router.push('/spaces')
  } catch (e: any) {
    toast.error(e.response?.data?.detail || 'Failed to delete space')
  }
}

// Modal Handlers
const openCreateRoom = () => createRoomModal.value?.open()
const openInvite = () => inviteModal.value?.open()
const openAssign = (roomId: string) => {
  activeRoomId.value = roomId
  assignModal.value?.open()
}

// Event Listeners
const onRoomCreated = () => {
  fetchSpaceData()
  if (activeTab.value === 'overview') fetchOverview()
}
const onInvited = () => {
  if (activeTab.value === 'members') fetchMembers()
}
const onAssigned = () => {
  // Toast handled in modal
}

const onCreateAnnouncement = async (data: { title: string; content: string }) => {
  try {
    await createAnnouncement(data.title, data.content)
    toast.success('Announcement posted')
  } catch (e: any) {
    toast.error(e.response?.data?.detail || 'Failed to post announcement')
  }
}

const formatTime = (dateStr: string) => {
  if (!dateStr) return 'N/A'
  const d = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  const diffHours = Math.floor(diffMins / 60)
  if (diffHours < 24) return `${diffHours}h ago`
  return d.toLocaleDateString()
}

onMounted(() => {
  fetchSpaceData()
  fetchOverview()
})
</script>

<template>
  <div class="w-full">
    <div v-if="loading" class="flex justify-center p-12">
      <span class="loading loading-spinner loading-lg"></span>
    </div>

    <div v-else-if="space">
      <!-- Header -->
      <div class="mb-8 flex justify-between items-start">
        <div>
          <div class="flex items-center gap-3 mb-2">
            <h1 class="text-3xl font-bold">{{ space.title }}</h1>
            <span class="badge" :class="presetBadgeClass">{{ space.preset }}</span>
          </div>
          <p class="text-base-content/60 mt-1">{{ space.description }}</p>
        </div>
        <div class="flex gap-2">
          <router-link
            v-if="!isStudent"
            :to="`/spaces/${space.id}/settings`"
            class="btn btn-outline btn-sm gap-2"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <circle cx="12" cy="12" r="3"></circle>
              <path
                d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"
              ></path>
            </svg>
            Settings
          </router-link>
          <button
            v-if="!isStudent && currentUserRole !== 'ta'"
            @click="handleDeleteSpace"
            class="btn btn-outline btn-error btn-sm"
          >
            Delete
          </button>
        </div>
      </div>

      <!-- Management Toolbar -->
      <div class="flex flex-wrap gap-2 mb-6" v-if="!isStudent">
        <button @click="openCreateRoom" class="btn btn-primary btn-sm">Create Room</button>
        <button @click="openInvite" class="btn btn-secondary btn-sm">Invite Member</button>
      </div>

      <!-- Tabs -->
      <div role="tablist" class="tabs tabs-lifted mb-6">
        <a
          v-for="tab in tabs"
          :key="tab.key"
          role="tab"
          class="tab"
          :class="{ 'tab-active': activeTab === tab.key }"
          @click="switchTab(tab.key)"
        >
          {{ tab.label }}
        </a>
      </div>

      <!-- Tab Content: Overview -->
      <div v-show="activeTab === 'overview'">
        <div v-if="overviewLoading" class="flex justify-center py-8">
          <span class="loading loading-spinner loading-md"></span>
        </div>
        <div v-else>
          <!-- Room Activity Grid -->
          <h3 class="font-bold text-lg mb-4">Room Activity</h3>
          <div v-if="rooms.length === 0" class="text-center py-8 opacity-50">
            No rooms yet. Create one to get started.
          </div>
          <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div
              v-for="room in rooms"
              :key="room.id"
              class="card bg-base-100 shadow-sm border border-base-300 hover:shadow-md transition-shadow"
            >
              <div class="card-body p-5">
                <div class="flex items-start justify-between">
                  <h4 class="card-title text-base">{{ room.name }}</h4>
                  <div
                    v-if="room.is_ai_active"
                    class="badge badge-secondary badge-outline badge-sm"
                  >
                    AI
                  </div>
                </div>
                <div class="mt-2 space-y-1 text-sm text-base-content/60">
                  <div class="flex items-center gap-2" v-if="overview?.rooms">
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      class="h-4 w-4"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"
                      />
                    </svg>
                    <span> {{ overview.rooms[room.id]?.active_users ?? 0 }} active </span>
                  </div>
                  <div class="flex items-center gap-2" v-if="overview?.rooms">
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      class="h-4 w-4"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                      />
                    </svg>
                    <span>
                      {{ formatTime(overview.rooms[room.id]?.last_message_at) }}
                    </span>
                  </div>
                </div>
                <div class="card-actions justify-end mt-3">
                  <router-link :to="`/rooms/${room.id}`" class="btn btn-primary btn-sm btn-outline">
                    Enter
                  </router-link>
                </div>
              </div>
            </div>
          </div>

          <!-- Quick Create -->
          <div v-if="!isStudent" class="mt-6">
            <button @click="openCreateRoom" class="btn btn-ghost btn-sm gap-2">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2"
              >
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
              </svg>
              Create Room
            </button>
          </div>
        </div>
      </div>

      <!-- Tab Content: Rooms -->
      <div v-show="activeTab === 'rooms'">
        <SpaceRoomList
          :rooms="rooms"
          :isStudent="isStudent"
          @delete-room="deleteRoom"
          @assign-member="openAssign"
        />
      </div>

      <!-- Tab Content: Members -->
      <div v-show="activeTab === 'members'">
        <SpaceMemberList
          :members="members"
          :spaceOwnerId="space.owner_id"
          :isStudent="isStudent"
          :currentUserRole="currentUserRole"
          @update-role="updateMemberRole"
          @remove-member="removeMember"
        />
      </div>

      <!-- Tab Content: Announcements -->
      <div v-show="activeTab === 'announcements'">
        <SpaceAnnouncementList
          :announcements="announcements"
          :spaceOwnerId="space?.owner_id || ''"
          @create="onCreateAnnouncement"
        />
      </div>

      <!-- Tab Content: Knowledge -->
      <div v-show="activeTab === 'knowledge'">
        <div class="card bg-base-100 shadow-sm border border-base-300 max-w-lg mx-auto mt-4">
          <div class="card-body items-center text-center">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-16 w-16 text-base-content/30 mb-2"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="1"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"
              />
            </svg>
            <h3 class="font-bold text-lg">Space Knowledge Base</h3>
            <p class="text-sm text-base-content/60">
              Configure your space-level knowledge engine for GraphRAG-powered insights.
            </p>
            <div class="card-actions mt-4">
              <router-link
                :to="`/platform/knowledge?space_id=${spaceId}`"
                class="btn btn-primary btn-sm"
              >
                Open Knowledge Engine
              </router-link>
            </div>
          </div>
        </div>
      </div>

      <!-- Tab Content: Analytics -->
      <div v-show="activeTab === 'analytics'">
        <div class="card bg-base-100 shadow-sm border border-base-300 max-w-lg mx-auto mt-4">
          <div class="card-body items-center text-center">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-16 w-16 text-base-content/30 mb-2"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="1"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
              />
            </svg>
            <h3 class="font-bold text-lg">Space Analytics</h3>
            <p class="text-sm text-base-content/60">
              View detailed analytics and reports for this space.
            </p>
            <div class="card-actions mt-4">
              <router-link :to="`/spaces/${spaceId}/analytics`" class="btn btn-primary btn-sm">
                View Analytics
              </router-link>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="text-center text-error py-12">Space not found.</div>

    <!-- Modals -->
    <CreateRoomModal ref="createRoomModal" :spaceId="spaceId" @created="onRoomCreated" />
    <InviteMemberModal ref="inviteModal" :spaceId="spaceId" @invited="onInvited" />
    <AssignMemberModal ref="assignModal" :roomId="activeRoomId" @assigned="onAssigned" />
  </div>
</template>
