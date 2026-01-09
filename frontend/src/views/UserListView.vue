<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useUsers } from '../composables/useUsers'
import { usePermissions } from '../composables/usePermissions'

// Components
import UserCreateModal from '../components/user/UserCreateModal.vue'
import UserEditModal from '../components/user/UserEditModal.vue'

// Types
import type { User } from '../types/user'

const authStore = useAuthStore()
const { users, loading, fetchUsers, deleteUser } = useUsers()
const { canEditUser, canDeleteUser, isSuperAdmin, currentUser } = usePermissions()

// Modal Refs
const createModal = ref<InstanceType<typeof UserCreateModal> | null>(null)
const editModal = ref<InstanceType<typeof UserEditModal> | null>(null)

// Handlers
const openCreateModal = () => createModal.value?.open()
const openEditModal = (user: User) => {
    if (!canEditUser(user)) {
        alert("You do not have permission to edit this user.")
        return
    }
    editModal.value?.open(user)
}

const handleDelete = async (user: User) => {
    if (!canDeleteUser(user)) {
        alert("You do not have permission to delete this user.")
        return
    }
    await deleteUser(user.id)
}

const onUserCreated = () => fetchUsers()
const onUserUpdated = () => fetchUsers()

onMounted(() => {
    fetchUsers()
})
</script>

<template>
  <div class="p-6">
    <div class="flex justify-between items-center mb-6">
        <h1 class="text-3xl font-bold">User Management</h1>
        <button class="btn btn-primary" @click="openCreateModal">Create User</button>
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
                @click="openEditModal(user)" 
                class="btn btn-xs mr-2"
                :disabled="!canEditUser(user)"
              >Edit</button>

              <button 
                v-if="isSuperAdmin() && user.id !== currentUser?.id"
                @click="authStore.impersonateUser(user.id)" 
                class="btn btn-xs btn-warning btn-outline mr-2"
              >Impersonate</button>
              
              <button 
                @click="handleDelete(user)" 
                class="btn btn-xs btn-error btn-outline"
                :disabled="!canDeleteUser(user)"
              >Delete</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Modals -->
    <UserCreateModal 
        ref="createModal" 
        @created="onUserCreated" 
    />
    
    <UserEditModal 
        ref="editModal" 
        @updated="onUserUpdated" 
    />
  </div>
</template>
