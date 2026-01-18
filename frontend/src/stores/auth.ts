import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authService } from '../services/authService'
import { cookies } from '../utils/cookies'
import { UserRole } from '../types/enums'
import type { User } from '../types/user'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const isImpersonating = ref(false)
  const isAuthenticated = computed(() => !!user.value)
  const isAdmin = computed(() => [UserRole.ADMIN, UserRole.SUPER_ADMIN].includes((user.value?.role as UserRole) || ''))
  const isSuperAdmin = computed(() => user.value?.role === UserRole.SUPER_ADMIN)
  const isStudent = computed(() => user.value?.role === UserRole.STUDENT)

  // Helper to check impersonation cookie status
  function checkImpersonationStatus() {
    const allCookies = cookies.getAll()
    isImpersonating.value = allCookies['is_impersonating'] === 'true'
  }

  // NOTE: Login action in Store only updates STATE. 
  // Routing should be handled by useAuth or the View.
  async function fetchUser() {
    try {
      const res = await authService.fetchUser()
      user.value = res.data
      checkImpersonationStatus()
    } catch {
      user.value = null
      isImpersonating.value = false
    }
  }

  async function impersonateUser(userId: string) {
    try {
      await authService.impersonateUser(userId)
      await fetchUser()
      // Manually set true to handle cases where cookie might be delayed
      isImpersonating.value = true
      return true
    } catch (e) {
      console.error(e)
      return false
    }
  }

  async function stopImpersonating() {
    try {
      await authService.stopImpersonating()
      await fetchUser()
      return true
    } catch (e) {
      console.error('Failed to stop impersonating', e)
      return false
    }
  }

  async function logout() {
    try {
      await authService.logout()
    } catch (e) {
      console.error('Logout failed', e)
    }
    // Clean local state
    user.value = null
    isImpersonating.value = false
  }

  return {
    user,
    isAuthenticated,
    isAdmin,
    isSuperAdmin,
    isStudent,
    isImpersonating,
    // Actions now only mutate state, no routing!
    logout,
    fetchUser,
    impersonateUser,
    stopImpersonating
  }
})
