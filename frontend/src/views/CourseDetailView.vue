<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api'
import { AxiosError } from 'axios'

interface Course {
    id: string
    title: string
    description: string
    owner_id: string
}

interface Room {
    id: string
    name: string
    is_ai_active: boolean
}

interface CourseMember {
    user_id: string
    email: string
    full_name?: string
    avatar_url?: string
    role: 'student' | 'ta'
}

const route = useRoute()
const router = useRouter()
const courseId = route.params.id as string
const course = ref<Course | null>(null)
const rooms = ref<Room[]>([])
const members = ref<CourseMember[]>([])
const activeTab = ref<'rooms' | 'members'>('rooms')
const loading = ref(true)

// Enroll State
interface UserResult {
    id: string
    email: string
    full_name?: string
    username?: string
}
const enrollEmail = ref('')
const enrollLoading = ref(false)
const searchQuery = ref('')
const searchResults = ref<UserResult[]>([])
const searchLoading = ref(false)
const activeSearchContext = ref<'enroll' | 'assign'>('enroll')
let searchTimeout: any = null

const handleSearch = () => {
    if (searchTimeout) clearTimeout(searchTimeout)
    if (!searchQuery.value) {
        searchResults.value = []
        return
    }
    
    searchTimeout = setTimeout(async () => {
        searchLoading.value = true
        try {
            const res = await api.get('/users/search', { params: { q: searchQuery.value } })
            searchResults.value = res.data
        } catch (e) {
            console.error(e)
        } finally {
            searchLoading.value = false
        }
    }, 300)
}

const selectUser = (user: UserResult) => {
    if (activeSearchContext.value === 'enroll') {
        enrollEmail.value = user.email
    } else {
        assignEmail.value = user.email
    }
    searchQuery.value = ''
    searchResults.value = []
}

const resetSearch = () => {
    searchQuery.value = ''
    searchResults.value = []
}

const openEnrollModal = () => {
    activeSearchContext.value = 'enroll'
    enrollEmail.value = ''
    resetSearch()
    const modal = document.getElementById('enroll_modal') as HTMLDialogElement
    if (modal) modal.showModal()
}

const assignEmail = ref('')
const assignLoading = ref(false)
const activeRoomId = ref('')

// Create Room State
const newRoom = ref({
    name: '',
    loading: false
})



// ... imports

const fetchCourseData = async () => {
    try {
        const [courseRes, roomsRes] = await Promise.all([
            api.get<Course>(`/courses/${courseId}`),
            api.get<Room[]>(`/rooms/`, { params: { course_id: courseId } })
        ])
        course.value = courseRes.data
        rooms.value = roomsRes.data
    } catch (e) {
        console.error(e)
    } finally {
        loading.value = false
    }
}

const enrollUser = async () => {
    if (!enrollEmail.value) return
    enrollLoading.value = true
    try {
        await api.post(`/courses/${courseId}/enroll`, {
           user_email: enrollEmail.value,
           role: 'student'
        })
        alert(`User ${enrollEmail.value} enrolled successfully!`)
        enrollEmail.value = ''
        // Close modal
         const modal = document.getElementById('enroll_modal') as HTMLDialogElement
        if (modal) modal.close()
    } catch (e: unknown) {
        if (e instanceof AxiosError && e.response) {
             alert('Enrollment failed: ' + (e.response.data?.detail || e.message))
        } else {
             alert('Enrollment failed: ' + String(e))
        }
    } finally {
        enrollLoading.value = false
    }
}

const deleteRoom = async (roomId: string) => {
    if (!confirm("Are you sure you want to delete this room?")) return;
    try {
        await api.delete(`/rooms/${roomId}`)
        await fetchCourseData()
    } catch (e) {
        alert("Failed to delete room")
    }
}

const deleteCourse = async () => {
    if (!confirm("DANGER: Are you sure you want to delete this ENTIRE course? All rooms and messages will be lost.")) return;
    try {
        await api.delete(`/courses/${courseId}`)
        router.push('/courses')
    } catch (e) {
        alert("Failed to delete course")
    }
}

const openCreateRoomModal = () => {
    newRoom.value = { name: '', loading: false }
    const modal = document.getElementById('create_room_modal') as HTMLDialogElement
    if (modal) modal.showModal()
}

const createRoom = async () => {
    if (!newRoom.value.name) return
    newRoom.value.loading = true
    
    try {
        await api.post('/rooms/', {
            name: newRoom.value.name,
            course_id: courseId
        })
        
        const modal = document.getElementById('create_room_modal') as HTMLDialogElement
        if (modal) modal.close()
        
        await fetchCourseData()
    } catch (e: unknown) {
        console.error(e)
        if (e instanceof AxiosError && e.response) {
            alert('Failed to create room: ' + (e.response.data?.detail || e.message))
        } else {
             alert('Failed to create room: ' + String(e))
        }
    } finally {
        newRoom.value.loading = false
    }
}

const openAssignModal = (roomId: string) => {
    activeRoomId.value = roomId
    activeSearchContext.value = 'assign'
    assignEmail.value = ''
    resetSearch()
    const modal = document.getElementById('assign_modal') as HTMLDialogElement
    if (modal) modal.showModal()
}

const assignUser = async () => {
    if (!assignEmail.value || !activeRoomId.value) return
    assignLoading.value = true
    try {
        await api.post(`/rooms/${activeRoomId.value}/assign`, {
            user_email: assignEmail.value
        })
        alert(`User assigned successfully!`)
        assignEmail.value = ''
         const modal = document.getElementById('assign_modal') as HTMLDialogElement
        if (modal) modal.close()
    } catch (e: unknown) {
        if (e instanceof AxiosError && e.response) {
             alert('Assignment failed: ' + (e.response.data?.detail || e.message))
        } else {
             alert('Assignment failed: ' + String(e))
        }
    } finally {
        assignLoading.value = false
    }
}

const fetchMembers = async () => {
    try {
        const res = await api.get<CourseMember[]>(`/courses/${courseId}/members`)
        members.value = res.data
    } catch (e) {
        console.error("Failed to fetch members", e)
    }
}

const updateMemberRole = async (member: CourseMember, newRole: string) => {
    const originalRole = member.role
    try {
        // Optimistic update
        member.role = newRole as 'student' | 'ta'
        await api.put(`/courses/${courseId}/members/${member.user_id}`, { role: newRole })
    } catch (e) {
        console.error(e)
        alert("Failed to update role")
        member.role = originalRole // Revert on failure
    }
}

const switchTab = (tab: 'rooms' | 'members') => {
    activeTab.value = tab
    if (tab === 'members') fetchMembers()
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
        <div class="mb-8 flex justify-between items-start">
            <div>
                <h1 class="text-3xl font-bold">{{ course.title }}</h1>
                <p class="text-gray-600 mt-2">{{ course.description }}</p>
            </div>
            <div class="flex gap-2">
                <router-link :to="`/courses/${course.id}/settings`" class="btn btn-outline gap-2">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>
                    Brain
                </router-link>
                <router-link :to="`/courses/${course.id}/analytics`" class="btn btn-outline gap-2">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line></svg>
                    Analytics
                </router-link>
            </div>
        </div>
        
        <!-- Management Toolbar -->
        <div class="flex flex-wrap gap-2 mb-6">
            <button @click="openCreateRoomModal" class="btn btn-primary btn-sm">Create Room</button>
            <button @click="openEnrollModal" class="btn btn-secondary btn-sm">Enroll Student</button>
            <button @click="deleteCourse" class="btn btn-error btn-sm btn-outline ml-auto">Delete Course</button>
        </div>

        <!-- Tabs -->
        <div role="tablist" class="tabs tabs-lifted mb-6">
            <a role="tab" class="tab" :class="{ 'tab-active': activeTab === 'rooms' }" @click="switchTab('rooms')">Rooms</a>
            <a role="tab" class="tab" :class="{ 'tab-active': activeTab === 'members' }" @click="switchTab('members')">Members</a>
        </div>

        <!-- Rooms Content -->
        <div v-show="activeTab === 'rooms'" class="grid grid-cols-1 md:grid-cols-2 gap-4">
             <div v-if="rooms.length === 0" class="col-span-full text-center py-4 opacity-70">
                No rooms created yet.
            </div>
            <div v-for="room in rooms" :key="room.id" class="card bg-base-100 shadow border border-base-300">
                <div class="card-body">
                    <div class="flex justify-between items-start">
                        <h3 class="card-title">
                            {{ room.name }}
                            <div v-if="room.is_ai_active" class="badge badge-secondary badge-outline text-xs">AI Active</div>
                        </h3>
                        <div class="dropdown dropdown-end">
                            <label tabindex="0" class="btn btn-ghost btn-xs btn-circle">
                                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="1"></circle><circle cx="12" cy="5" r="1"></circle><circle cx="12" cy="19" r="1"></circle></svg>
                            </label>
                            <ul tabindex="0" class="dropdown-content z-[1] menu p-2 shadow bg-base-100 rounded-box w-52">
                                <li><a @click="deleteRoom(room.id)" class="text-error">Delete Room</a></li>
                                <li><a @click="openAssignModal(room.id)">Assign Student</a></li>
                            </ul>
                        </div>
                    </div>
                    
                    <div class="card-actions justify-end mt-4">
                        <router-link :to="`/rooms/${room.id}`" class="btn btn-primary btn-sm">Enter Room</router-link>
                    </div>
                </div>
            </div>
        </div>

        <!-- Members Content -->
        <div v-show="activeTab === 'members'">
             <div v-if="members.length === 0" class="text-center py-4 opacity-70">
                No members found.
            </div>

            <!-- Desktop View (Table) -->
            <div class="hidden md:block overflow-x-auto">
                <table class="table w-full">
                    <!-- head -->
                    <thead>
                    <tr>
                        <th>Name</th>
                        <th>Email</th>
                        <th>Role</th>
                        <th>Actions</th>
                    </tr>
                    </thead>
                    <tbody>
                    <tr v-for="member in members" :key="member.user_id + '_desktop'">
                        <td>
                            <div class="flex items-center gap-3">
                                <div class="avatar">
                                    <div class="mask mask-squircle w-12 h-12">
                                        <img :src="member.avatar_url || 'https://ui-avatars.com/api/?name=' + member.email" alt="Avatar" />
                                    </div>
                                </div>
                                <div>
                                    <div class="font-bold">{{ member.full_name || 'No Name' }}</div>
                                </div>
                            </div>
                        </td>
                        <td>{{ member.email }}</td>
                        <td>
                            <span class="badge" :class="member.role === 'ta' ? 'badge-accent' : 'badge-ghost'">{{ member.role.toUpperCase() }}</span>
                        </td>
                        <td>
                            <div class="join">
                                <button 
                                    v-if="member.role !== 'ta'" 
                                    @click="updateMemberRole(member, 'ta')" 
                                    class="btn btn-xs btn-outline btn-accent join-item">
                                    Make TA
                                </button>
                                <button 
                                    v-if="member.role === 'ta'" 
                                    @click="updateMemberRole(member, 'student')" 
                                    class="btn btn-xs btn-outline join-item">
                                    Revoke TA
                                </button>
                            </div>
                        </td>
                    </tr>
                    </tbody>
                </table>
            </div>

            <!-- Mobile View (Cards) -->
            <div class="block md:hidden space-y-4">
                <div v-for="member in members" :key="member.user_id + '_mobile'" class="card bg-base-100 shadow-sm border border-base-200 transition-all active:scale-[0.98]">
                    <div class="card-body p-4 flex flex-row items-center gap-4">
                        <div class="avatar">
                            <div class="mask mask-squircle w-12 h-12">
                                <img :src="member.avatar_url || 'https://ui-avatars.com/api/?name=' + member.email" alt="Avatar" />
                            </div>
                        </div>
                        <div class="flex-1 min-w-0">
                            <div class="flex justify-between items-start">
                                <h3 class="font-bold truncate">{{ member.full_name || 'No Name' }}</h3>
                                <span class="badge badge-sm" :class="member.role === 'ta' ? 'badge-accent' : 'badge-ghost'">{{ member.role.toUpperCase() }}</span>
                            </div>
                            <p class="text-xs text-gray-500 truncate">{{ member.email }}</p>
                        </div>
                    </div>
                     <div class="card-actions px-4 pb-4">
                         <button 
                            v-if="member.role !== 'ta'" 
                            @click="updateMemberRole(member, 'ta')" 
                            class="btn btn-sm btn-outline btn-accent w-full">
                            Make TA
                         </button>
                         <button 
                            v-if="member.role === 'ta'" 
                            @click="updateMemberRole(member, 'student')" 
                            class="btn btn-sm btn-outline w-full">
                            Revoke TA
                         </button>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <div v-else class="text-center text-error">Course not found.</div>

        <!-- Create Room Modal -->
        <dialog id="create_room_modal" class="modal">
          <div class="modal-box">
            <h3 class="font-bold text-lg">Create New Room</h3>
            <p class="py-4">Create a new discussion space.</p>
            <div class="form-control w-full mb-4">
              <label class="label"><span class="label-text">Room Name</span></label>
              <input type="text" v-model="newRoom.name" placeholder="e.g. Group A Discussion" class="input input-bordered w-full" />
            </div>
            <div class="modal-action">
              <form method="dialog"><button class="btn btn-ghost mr-2">Cancel</button></form>
              <button @click="createRoom" class="btn btn-primary" :disabled="newRoom.loading">Create</button>
            </div>
          </div>
        </dialog>

        <!-- Enroll Modal -->
        <dialog id="enroll_modal" class="modal">
          <div class="modal-box overflow-visible">
             <h3 class="font-bold text-lg">Enroll Student</h3>
             <p class="py-4">Search for a user to add to this course.</p>
             
             <!-- Search Input -->
             <div class="form-control w-full mb-4 relative">
               <label class="label"><span class="label-text">Search User (Name, Email, Username)</span></label>
               <input 
                    type="text" 
                    v-model="searchQuery" 
                    @input="handleSearch"
                    placeholder="Type to search..." 
                    class="input input-bordered w-full" 
               />
               
               <!-- Dropdown Results -->
               <ul v-if="searchResults.length > 0 && searchQuery && activeSearchContext === 'enroll'" class="absolute top-full left-0 w-full bg-base-100 shadow-xl rounded-box z-50 p-2 mt-1 border border-base-200 max-h-60 overflow-y-auto">
                    <li v-for="user in searchResults" :key="user.id">
                        <a @click="selectUser(user)" class="block p-2 hover:bg-base-200 rounded cursor-pointer">
                            <div class="font-bold">{{ user.full_name || 'No Name' }}</div>
                            <div class="text-xs opacity-70">{{ user.email }} <span v-if="user.username">({{ user.username }})</span></div>
                        </a>
                    </li>
               </ul>
               <div v-else-if="searchQuery && !searchLoading && searchResults.length === 0 && activeSearchContext === 'enroll'" class="absolute top-full left-0 w-full bg-base-100 p-2 mt-1 text-sm text-center opacity-50 z-50">
                    No users found.
               </div>
             </div>
             
             <!-- Selected User Display -->
             <div v-if="enrollEmail" class="alert alert-success shadow-sm mb-4">
                <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                <span>Selected: {{ enrollEmail }}</span>
             </div>

             <div class="modal-action">
               <form method="dialog"><button class="btn btn-ghost mr-2" @click="resetSearch">Cancel</button></form>
               <button @click="enrollUser" class="btn btn-secondary" :disabled="enrollLoading || !enrollEmail">Enroll</button>
             </div>
          </div>
        </dialog>

        <!-- Assign Modal -->
        <dialog id="assign_modal" class="modal">
          <div class="modal-box overflow-visible">
             <h3 class="font-bold text-lg">Assign Student to Room</h3>
             <p class="py-4">Search for a user to link to this room.</p>
             
             <!-- Search Input -->
             <div class="form-control w-full mb-4 relative">
               <label class="label"><span class="label-text">Search User</span></label>
               <input 
                    type="text" 
                    v-model="searchQuery" 
                    @input="handleSearch"
                    placeholder="Type to search..." 
                    class="input input-bordered w-full" 
               />
                <!-- Dropdown Results -->
               <ul v-if="searchResults.length > 0 && searchQuery && activeSearchContext === 'assign'" class="absolute top-full left-0 w-full bg-base-100 shadow-xl rounded-box z-50 p-2 mt-1 border border-base-200 max-h-60 overflow-y-auto">
                    <li v-for="user in searchResults" :key="user.id">
                        <a @click="selectUser(user)" class="block p-2 hover:bg-base-200 rounded cursor-pointer">
                            <div class="font-bold">{{ user.full_name || 'No Name' }}</div>
                            <div class="text-xs opacity-70">{{ user.email }} <span v-if="user.username">({{ user.username }})</span></div>
                        </a>
                    </li>
               </ul>
               <div v-else-if="searchQuery && !searchLoading && searchResults.length === 0 && activeSearchContext === 'assign'" class="absolute top-full left-0 w-full bg-base-100 p-2 mt-1 text-sm text-center opacity-50 z-50">
                    No users found.
               </div>
             </div>

             <div v-if="assignEmail" class="alert alert-success shadow-sm mb-4">
                <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                <span>Selected: {{ assignEmail }}</span>
             </div>

             <div class="modal-action">
               <form method="dialog"><button class="btn btn-ghost mr-2" @click="resetSearch">Cancel</button></form>
               <button @click="assignUser" class="btn btn-secondary" :disabled="assignLoading || !assignEmail">Assign</button>
             </div>
          </div>
        </dialog>
   <!-- End of Modals -->
  </div>
</template>
