<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useCourse } from '../composables/useCourse'

// Components
import CreateRoomModal from '../components/course/modals/CreateRoomModal.vue'
import EnrollStudentModal from '../components/course/modals/EnrollStudentModal.vue'
import AssignStudentModal from '../components/course/modals/AssignStudentModal.vue'
import CourseRoomList from '../components/course/CourseRoomList.vue'
import CourseMemberList from '../components/course/CourseMemberList.vue'

// Types
// import type { CourseMember } from '../types/course'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const courseId = route.params.id as string
const { course, rooms, members, loading, fetchCourseData, fetchMembers, deleteCourse, deleteRoom, updateMemberRole, removeMember } = useCourse(courseId)

const activeTab = ref<'rooms' | 'members'>('rooms')

// Modal Refs
const createRoomModal = ref<InstanceType<typeof CreateRoomModal> | null>(null)
const enrollModal = ref<InstanceType<typeof EnrollStudentModal> | null>(null)
const assignModal = ref<InstanceType<typeof AssignStudentModal> | null>(null)

// State for assignment
const activeRoomId = ref('')

const isStudent = computed(() => authStore.isStudent)
const currentUserRole = computed(() => authStore.user?.role)

const switchTab = (tab: 'rooms' | 'members') => {
    activeTab.value = tab
    if (tab === 'members') fetchMembers()
}

// Actions
const handleDeleteCourse = async () => {
    if (!confirm("DANGER: Are you sure you want to delete this ENTIRE course? All rooms and messages will be lost.")) return;
    try {
        await deleteCourse()
        router.push('/courses')
    } catch (e) {
        alert("Failed to delete course")
    }
}

// Modal Handlers
const openCreateRoom = () => createRoomModal.value?.open()
const openEnroll = () => enrollModal.value?.open()
const openAssign = (roomId: string) => {
    activeRoomId.value = roomId
    assignModal.value?.open()
}

// Event Listeners
const onRoomCreated = () => fetchCourseData()
const onEnrolled = () => {
    if (activeTab.value === 'members') fetchMembers()
}
const onAssigned = () => {
    // Maybe show toast? Logic handled in modal.
}

onMounted(() => {
    fetchCourseData()
})
</script>

<template>
  <div class="w-full">
    <div v-if="loading" class="flex justify-center">
        <span class="loading loading-spinner loading-lg"></span>
    </div>
    
    <div v-else-if="course">
        <!-- Header -->
        <div class="mb-8 flex justify-between items-start">
            <div>
                <h1 class="text-3xl font-bold">{{ course.title }}</h1>
                <p class="text-gray-600 mt-2">{{ course.description }}</p>
            </div>
            <div class="flex gap-2">
                <router-link v-if="!isStudent" :to="`/courses/${course.id}/settings`" class="btn btn-outline gap-2">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>
                    Brain
                </router-link>
                <router-link v-if="!isStudent" :to="`/courses/${course.id}/analytics`" class="btn btn-outline gap-2">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line></svg>
                    Analytics
                </router-link>
            </div>
        </div>
        
        <!-- Management Toolbar -->
        <div class="flex flex-wrap gap-2 mb-6" v-if="!isStudent">
            <button @click="openCreateRoom" class="btn btn-primary btn-sm">Create Room</button>
            <button @click="openEnroll" class="btn btn-secondary btn-sm">Enroll Student</button>
            <button v-if="currentUserRole !== 'ta'" @click="handleDeleteCourse" class="btn btn-error btn-sm btn-outline ml-auto">Delete Course</button>
        </div>

        <!-- Tabs -->
        <div role="tablist" class="tabs tabs-lifted mb-6">
            <a role="tab" class="tab" :class="{ 'tab-active': activeTab === 'rooms' }" @click="switchTab('rooms')">Rooms</a>
            <a role="tab" class="tab" :class="{ 'tab-active': activeTab === 'members' }" @click="switchTab('members')">Members</a>
        </div>

        <!-- Tab Content -->
        <div v-show="activeTab === 'rooms'">
            <CourseRoomList 
                :rooms="rooms"
                :isStudent="isStudent"
                @delete-room="deleteRoom"
                @assign-student="openAssign"
            />
        </div>

        <div v-show="activeTab === 'members'">
            <CourseMemberList 
                :members="members"
                :courseOwnerId="course.owner_id"
                :isStudent="isStudent"
                :currentUserRole="currentUserRole"
                @update-role="updateMemberRole"
                @remove-member="removeMember"
            />
        </div>
    </div>
    
    <div v-else class="text-center text-error">Course not found.</div>

    <!-- Modals -->
    <CreateRoomModal 
        ref="createRoomModal" 
        :courseId="courseId" 
        @created="onRoomCreated" 
    />
    
    <EnrollStudentModal 
        ref="enrollModal" 
        :courseId="courseId" 
        @enrolled="onEnrolled" 
    />
    
    <AssignStudentModal 
        ref="assignModal" 
        :roomId="activeRoomId" 
        @assigned="onAssigned" 
    />
  </div>
</template>
