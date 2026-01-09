import { storeToRefs } from 'pinia'
import { useAuthStore } from '../stores/auth'
import type { User } from '../types/user'

export function usePermissions() {
  const authStore = useAuthStore()
  const { user: currentUser } = storeToRefs(authStore)

  const isSuperAdmin = () => authStore.isSuperAdmin

  const canEditUser = (targetUser: User) => {
    if (!currentUser.value) return false

    // Self edit: usually allowed (but role might be restricted, handled in UI)
    // Here we focus on admin vs admin rules
    if (targetUser.id === currentUser.value.id) return true

    // Admin/SuperAdmin target Check
    if (
      (targetUser.role === 'admin' || targetUser.role === 'super_admin') &&
      !authStore.isSuperAdmin
    ) {
      return false
    }

    return true
  }

  const canDeleteUser = (targetUser: User) => {
    if (!currentUser.value) return false

    // Cannot delete self
    if (targetUser.id === currentUser.value.id) return false

    // Admin/SuperAdmin target Check
    if (
      (targetUser.role === 'admin' || targetUser.role === 'super_admin') &&
      !authStore.isSuperAdmin
    ) {
      return false
    }

    return true
  }

  return {
    currentUser,
    isSuperAdmin,
    canEditUser,
    canDeleteUser
  }
}
