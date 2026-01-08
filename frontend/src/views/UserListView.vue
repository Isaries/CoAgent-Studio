<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../api'
import { useAuthStore } from '../stores/auth' // Import store

const authStore = useAuthStore() // Use store

interface User {
    id: string
    email: string
    username?: string
    full_name: string
    role: string
    is_active: boolean
}

const users = ref<User[]>([])
const loading = ref(true)

const fetchUsers = async () => {
    loading.value = true
    try {
        const res = await api.get('/users/', {
            params: { skip: 0, limit: 100 } 
        })
        users.value = res.data
    } catch (e) {
        console.error(e)
        alert('Failed to fetch users')
    } finally {
        loading.value = false
    }
}

const toggleRole = async (user: User) => {
    // Permission Check:
    // 1. Super Admin cannot change own role
    if (user.role === 'super_admin' && user.id === authStore.user?.id) {
         alert("Super Admins cannot change their own role.")
         return
    }

    // 2. If target is Admin/Super Admin, and NOT self, only Super Admin can modify
    if (user.id !== authStore.user?.id) {
        if ((user.role === 'admin' || user.role === 'super_admin') && !authStore.isSuperAdmin) {
            alert("You do not have permission to modify this user.")
            return
        }
    }

    let newRole = user.role === 'admin' ? 'teacher' : 'admin' 
    
    // If Super Admin modifing Admin, allow toggle to/from admin?
    // Simplified logic: If admin -> teacher. If teacher/student -> admin.
    
    if (!confirm(`Change role of ${user.email} to ${newRole}?`)) return
    
    try {
        await api.put(`/users/${user.id}`, { role: newRole })
        user.role = newRole
    } catch (e: any) {
        alert(e.response?.data?.detail || 'Failed to update role')
    }
}

const deleteUser = async (user: User) => {
    // Permission Check
    // 1. Cannot delete self
    if (user.id === authStore.user?.id) {
        alert("You cannot delete your own account.")
        return
    }

    // 2. If target is Admin/Super Admin, only Super Admin can delete
    if ((user.role === 'admin' || user.role === 'super_admin') && !authStore.isSuperAdmin) {
        alert("You do not have permission to delete this user.")
        return
    }

    if (!confirm(`Are you sure you want to DELETE user ${user.email}? This action cannot be undone.`)) return
    
    try {
        await api.delete(`/users/${user.id}`)
        // Remove from list
        users.value = users.value.filter(u => u.id !== user.id)
        alert('User deleted successfully')
    } catch (e: any) {
        alert(e.response?.data?.detail || 'Failed to delete user')
    }
}

// Create User State
const showCreateModal = ref(false)
const createLoading = ref(false)
const newUser = ref({
    email: '',
    username: '',
    password: '',
    full_name: '',
    role: 'student' as 'student' | 'teacher' | 'admin' | 'ta' | 'guest'
})

const createUser = async () => {
    createLoading.value = true
    try {
        const payload = { ...newUser.value }
        // Determine which fields to send based on input (Email OR Username is required)
        // Ideally both or one.
        
        await api.post('/users/', payload)
        
        // Reset and refresh
        showCreateModal.value = false
        newUser.value = { email: '', username: '', password: '', full_name: '', role: 'student' }
        fetchUsers()
        alert('User created successfully')
    } catch (e: any) {
        alert(e.response?.data?.detail || 'Failed to create user')
    } finally {
        createLoading.value = false
    }
}

onMounted(() => {
    fetchUsers()
})
</script>

<template>
  <div class="p-6">
    <div class="flex justify-between items-center mb-6">
        <h1 class="text-3xl font-bold">User Management</h1>
        <button class="btn btn-primary" @click="showCreateModal = true">Create User</button>
    </div>
    
    <div v-if="loading" class="flex justify-center">
        <span class="loading loading-spinner loading-lg"></span>
    </div>

    <div v-else class="overflow-x-auto">
      <table class="table">
        <!-- head -->
        <thead>
          <tr>
            <th>Name (Username)</th>
            <th>Email</th>
            <th>Role</th>
            <th>Active</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in users" :key="user.id">
            <td>
              <div class="font-bold">{{ user.full_name || 'N/A' }}</div>
              <div v-if="user.username" class="text-xs opacity-50">{{ user.username }}</div>
            </td>
            <td>{{ user.email }}</td>
            <td>
                <span class="badge" :class="{
                    'badge-primary': user.role === 'admin' || user.role === 'super_admin',
                    'badge-secondary': user.role === 'teacher',
                    'badge-accent': user.role === 'ta',
                    'badge-ghost': user.role === 'student' || user.role === 'guest'
                }">
                    {{ user.role }}
                </span>
            </td>
            <td>
                <input type="checkbox" class="checkbox" :checked="user.is_active" disabled />
            </td>
            <td>
              <button 
                @click="toggleRole(user)" 
                class="btn btn-xs mr-2"
                :disabled="
                    (user.role === 'super_admin' && user.id === authStore.user?.id) || 
                    ((user.role === 'admin' || user.role === 'super_admin') && !authStore.isSuperAdmin && user.id !== authStore.user?.id)
                "
              >Change Role</button>
              
              <button 
                @click="deleteUser(user)" 
                class="btn btn-xs btn-error btn-outline"
                :disabled="
                   user.id === authStore.user?.id ||
                    ((user.role === 'admin' || user.role === 'super_admin') && !authStore.isSuperAdmin)
                "
              >Delete</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Create User Modal -->
    <dialog :class="{ 'modal-open': showCreateModal }" class="modal">
      <div class="modal-box">
        <h3 class="font-bold text-lg">Create New User</h3>
        <div class="py-4 flex flex-col gap-3">
            <div class="form-control">
                <label class="label"><span class="label-text">Email</span></label>
                <input type="email" v-model="newUser.email" placeholder="user@example.com" class="input input-bordered" />
            </div>
            
            <div class="form-control">
                <label class="label"><span class="label-text">Username (For Guest Login)</span></label>
                <input type="text" v-model="newUser.username" placeholder="johndoe" class="input input-bordered" />
            </div>

            <div class="form-control">
                <label class="label"><span class="label-text">Full Name</span></label>
                <input type="text" v-model="newUser.full_name" placeholder="John Doe" class="input input-bordered" />
            </div>

            <div class="form-control">
                <label class="label"><span class="label-text">Password</span></label>
                <input type="password" v-model="newUser.password" placeholder="********" class="input input-bordered" />
            </div>

            <div class="form-control">
                <label class="label"><span class="label-text">Role</span></label>
                <select v-model="newUser.role" class="select select-bordered" required>
                    <option value="guest">Guest</option>
                    <option value="student">Student</option>
                    <option value="ta">TA</option>
                    <option value="teacher">Teacher</option>
                    <option value="admin">Admin</option>
                </select>
            </div>
        </div>
        <div class="modal-action">
          <button class="btn btn-ghost" @click="showCreateModal = false">Cancel</button>
          <button class="btn btn-primary" @click="createUser" :disabled="createLoading">Create</button>
        </div>
      </div>
    </dialog>
  </div>
</template>
