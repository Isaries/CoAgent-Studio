import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '../stores/auth'
import { authService } from '../services/authService'

/**
 * useAuth Composable
 * Bridges the gap between State (Pinia) and Routing (Vue Router)
 * Ensures consistent behavior across the app without polluting the Store.
 */
export function useAuth() {
    const router = useRouter()
    const authStore = useAuthStore()
    const { user, isAuthenticated, isAdmin, isSuperAdmin, isStudent, isImpersonating } = storeToRefs(authStore)

    const login = async (formData: FormData) => {
        // 1. Call Service (Pure API)
        const success = await authService.login(formData)

        if (success) {
            // 2. Update Store (Pure State)
            await authStore.fetchUser()

            // 3. Handle Routing (Side Effect)
            if (isAdmin.value) {
                router.push('/dashboard')
            } else {
                router.push('/courses')
            }
            return true
        }
        return false
    }

    const logout = async () => {
        await authStore.logout() // Store clears state
        router.push('/login')
    }

    const impersonate = async (userId: string) => {
        const success = await authStore.impersonateUser(userId)
        if (success) {
            router.push('/courses')
        }
    }

    const stopImpersonating = async () => {
        await authStore.stopImpersonating()
        router.push('/admin/users')
    }

    return {
        login,
        logout,
        impersonate,
        stopImpersonating,
        // Refs
        user,
        isAuthenticated,
        isAdmin,
        isSuperAdmin,
        isStudent,
        isImpersonating
    }
}
