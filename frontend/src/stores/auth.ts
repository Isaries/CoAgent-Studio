import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authService } from '../services/authService' // Changed import
import router from '../router'
import type { User } from '../types/user'

export const useAuthStore = defineStore('auth', () => {
    const user = ref<User | null>(null)
    const isImpersonating = ref(false)
    const isAuthenticated = computed(() => !!user.value)
    const isAdmin = computed(() => ['admin', 'super_admin'].includes(user.value?.role || ''))
    const isSuperAdmin = computed(() => user.value?.role === 'super_admin')
    const isStudent = computed(() => user.value?.role === 'student')

    // Helper to check impersonation cookie status
    function checkImpersonationStatus() {
        if (!document.cookie) {
            isImpersonating.value = false
            return
        }
        const cookies = document.cookie.split('; ').reduce((acc, current) => {
            const [name, value] = current.split('=')
            if (name) acc[name.trim()] = value || ''
            return acc
        }, {} as Record<string, string>)
        isImpersonating.value = cookies['is_impersonating'] === 'true'
    }

    async function login(username: string, password: string) {
        try {
            const formData = new FormData()
            formData.append('username', username)
            formData.append('password', password)

            await authService.login(formData) // Service Call

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
            const res = await authService.fetchUser() // Service Call
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
            await authService.impersonateUser(userId) // Service Call
            await fetchUser()
            // Manually set true to handle cases where cookie might be delayed or rejected in dev
            isImpersonating.value = true
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
            await authService.stopImpersonating() // Service Call
            await fetchUser()
            router.push('/admin/users')
        } catch (e) {
            console.error("Failed to stop impersonating", e)
        }
    }

    async function logout() {
        try {
            await authService.logout() // Service Call
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
