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
    const token = ref<string | null>(localStorage.getItem('token'))
    const originalToken = ref<string | null>(localStorage.getItem('originalToken'))
    const isAuthenticated = computed(() => !!token.value)
    const isAdmin = computed(() => ['admin', 'super_admin'].includes(user.value?.role || ''))
    const isSuperAdmin = computed(() => user.value?.role === 'super_admin')
    const isStudent = computed(() => user.value?.role === 'student')
    const isImpersonating = computed(() => !!originalToken.value)

    async function login(username: string, password: string) {
        try {
            const formData = new FormData()
            formData.append('username', username)
            formData.append('password', password)

            const res = await api.post('/login/access-token', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            })

            token.value = res.data.access_token
            localStorage.setItem('token', token.value!)

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
        if (!token.value) return
        try {
            const res = await api.post('/login/test-token')
            user.value = res.data
        } catch (error) {
            // Only logout if not impersonating or if main token is invalid
            // But if impersonating, maybe we just want to validation fail?
            // For simplicity, regular logout logic is fine for now
            logout()
        }
    }

    async function impersonateUser(userId: string) {
        if (!token.value) return
        try {
            const res = await api.post(`/login/impersonate/${userId}`)
            const newToken = res.data.access_token

            // Save original token
            originalToken.value = token.value
            localStorage.setItem('originalToken', token.value!)

            // Set new token
            token.value = newToken
            localStorage.setItem('token', newToken)

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
        if (!originalToken.value) return

        // Restore original token
        token.value = originalToken.value
        localStorage.setItem('token', token.value!)

        // Clear original token
        originalToken.value = null
        localStorage.removeItem('originalToken')

        await fetchUser()
        router.push('/admin/users')
    }

    function logout() {
        user.value = null
        token.value = null
        originalToken.value = null
        localStorage.removeItem('token')
        localStorage.removeItem('originalToken')
        router.push('/login')
    }

    return {
        user,
        token,
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
