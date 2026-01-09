import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api'
import router from '../router'

interface User {
    id: string
    email: string
    role: string
    full_name?: string
    avatar_url?: string
}

export const useAuthStore = defineStore('auth', () => {
    const user = ref<User | null>(null)
    const isImpersonating = ref(false)
    const isAuthenticated = computed(() => !!user.value)
    const isAdmin = computed(() => ['admin', 'super_admin'].includes(user.value?.role || ''))
    const isSuperAdmin = computed(() => user.value?.role === 'super_admin')
    const isStudent = computed(() => user.value?.role === 'student')

    // Helper to check impersonation cookie status
    function checkImpersonationStatus() {
        isImpersonating.value = document.cookie.split('; ').some(row => row.startsWith('is_impersonating=true'))
    }

    async function login(username: string, password: string) {
        try {
            const formData = new FormData()
            formData.append('username', username)
            formData.append('password', password)

            await api.post('/login/access-token', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            })

            await fetchUser()

            if (isAdmin.value) {
                router.push('/dashboard')
            } else {
                router.push('/courses')
            }
            return true
        } catch (error) {
            console.error('Login failed', error)
            return false
        }
    }

    async function fetchUser() {
        try {
            const res = await api.post('/login/test-token')
            user.value = res.data
            checkImpersonationStatus()
        } catch (error) {
            user.value = null
            isImpersonating.value = false
            // If fetch user fails (401), we assume not logged in.
        }
    }

    async function impersonateUser(userId: string) {
        try {
            await api.post(`/login/impersonate/${userId}`)
            await fetchUser()
            router.push('/courses')
            return true
        } catch (e) {
            console.error(e)
            alert("Failed to impersonate user")
            return false
        }
    }

    async function stopImpersonating() {
        try {
            await api.post('/login/stop-impersonate')
            await fetchUser()
            router.push('/admin/users')
        } catch (e) {
            console.error("Failed to stop impersonating", e)
        }
    }

    async function logout() {
        try {
            await api.post('/login/logout')
        } catch (e) {
            console.error('Logout failed', e)
        }
        user.value = null
        isImpersonating.value = false
        router.push('/login')
    }

    return {
        user,
        token: user, // Alias for backward compatibility if needed, or remove. 
        // Actually, let's keep the return interface clean.
        // But invalidating `token` property usage in components might break things?
        // Let's check usage of `token`.
        // Ideally we remove it.
        isAuthenticated,
        isAdmin,
        isSuperAdmin,
        isStudent,
        isImpersonating,
        login,
        logout,
        fetchUser,
        impersonateUser,
        stopImpersonating
    }
})
