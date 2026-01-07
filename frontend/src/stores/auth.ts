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
    const isAuthenticated = computed(() => !!token.value)
    const isAdmin = computed(() => user.value?.role === 'admin')

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
            logout()
        }
    }

    function logout() {
        user.value = null
        token.value = null
        localStorage.removeItem('token')
        router.push('/login')
    }

    return {
        user,
        token,
        isAuthenticated,
        isAdmin,
        login,
        logout,
        fetchUser
    }
})
