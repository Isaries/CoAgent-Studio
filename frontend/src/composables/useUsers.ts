import { ref } from 'vue'
import { userService } from '../services/userService'
import type { User, CreateUserPayload, UpdateUserPayload } from '../types/user'
import { useToastStore } from '../stores/toast'
import { useConfirm } from '../composables/useConfirm'

export function useUsers() {
    const users = ref<User[]>([])
    const loading = ref(false)
    const error = ref<string | null>(null)
    const toast = useToastStore()
    const { confirm } = useConfirm()

    const fetchUsers = async (params?: { skip?: number; limit?: number }) => {
        loading.value = true
        error.value = null
        try {
            const res = await userService.getUsers(params)
            users.value = res.data
        } catch (e: any) {
            console.error(e)
            error.value = e.response?.data?.detail || 'Failed to fetch users'
            toast.error(error.value || 'Failed to fetch users')
        } finally {
            loading.value = false
        }
    }

    const createUser = async (payload: CreateUserPayload) => {
        loading.value = true
        error.value = null
        try {
            await userService.createUser(payload)
            // Refresh list
            await fetchUsers()
            return true
        } catch (e: any) {
            error.value = e.response?.data?.detail || 'Failed to create user'
            throw e // Re-throw to let component handle specific UI actions like closing modal
        } finally {
            loading.value = false
        }
    }

    const updateUser = async (id: string, payload: UpdateUserPayload) => {
        loading.value = true
        error.value = null
        try {
            await userService.updateUser(id, payload)
            // Optimistic update or refresh
            const index = users.value.findIndex(u => u.id === id)
            if (index !== -1) {
                // We partial update local state for speed, assuming success returns updated object usually, 
                // but here we just update fields we changed or fetch again.
                // Let's just fetch again for simplicity or manual update
                // users.value[index] = { ...users.value[index], ...payload } as User 
                // Actually payload might not have all fields. 
                await fetchUsers()
            }
            return true
        } catch (e: any) {
            error.value = e.response?.data?.detail || 'Failed to update user'
            throw e
        } finally {
            loading.value = false
        }
    }

    const deleteUser = async (id: string) => {
        if (!await confirm("Delete User", "Are you sure you want to delete this user?")) return

        loading.value = true
        try {
            await userService.deleteUser(id)
            users.value = users.value.filter(u => u.id !== id)
            toast.success('User deleted successfully')
        } catch (e: any) {
            error.value = e.response?.data?.detail || 'Failed to delete user'
            toast.error(error.value || 'Failed to delete user')
        } finally {
            loading.value = false
        }
    }

    return {
        users,
        loading,
        error,
        fetchUsers,
        createUser,
        updateUser,
        deleteUser
    }
}
