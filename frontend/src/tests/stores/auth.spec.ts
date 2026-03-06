import { setActivePinia, createPinia } from 'pinia'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useAuthStore } from '@/stores/auth'
import { UserRole } from '@/types/enums'
import type { User } from '@/types/user'

vi.mock('@/services/authService', () => ({
  authService: {
    fetchUser: vi.fn(),
    logout: vi.fn(),
    impersonateUser: vi.fn(),
    stopImpersonating: vi.fn()
  }
}))

vi.mock('@/utils/cookies', () => ({
  cookies: {
    getAll: vi.fn(() => ({})),
    get: vi.fn(),
    set: vi.fn(),
    delete: vi.fn()
  }
}))

const mockStudent: User = {
  id: 'user-1',
  email: 'student@example.com',
  full_name: 'Student User',
  role: UserRole.STUDENT,
  is_active: true
}

const mockAdmin: User = {
  id: 'admin-1',
  email: 'admin@example.com',
  full_name: 'Admin User',
  role: UserRole.ADMIN,
  is_active: true
}

const mockSuperAdmin: User = {
  id: 'super-1',
  email: 'super@example.com',
  full_name: 'Super Admin',
  role: UserRole.SUPER_ADMIN,
  is_active: true
}

describe('Auth Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('initial state', () => {
    it('user is null', () => {
      const store = useAuthStore()
      expect(store.user).toBeNull()
    })

    it('isAuthenticated is false', () => {
      const store = useAuthStore()
      expect(store.isAuthenticated).toBe(false)
    })

    it('isImpersonating is false', () => {
      const store = useAuthStore()
      expect(store.isImpersonating).toBe(false)
    })
  })

  describe('fetchUser', () => {
    it('sets user when API succeeds', async () => {
      const { authService } = await import('@/services/authService')
      vi.mocked(authService.fetchUser).mockResolvedValueOnce({ data: mockStudent } as any)

      const store = useAuthStore()
      await store.fetchUser()

      expect(store.user).toEqual(mockStudent)
      expect(store.isAuthenticated).toBe(true)
    })

    it('clears user when API throws', async () => {
      const { authService } = await import('@/services/authService')
      vi.mocked(authService.fetchUser).mockRejectedValueOnce(new Error('Unauthorized'))

      const store = useAuthStore()
      store.user = mockStudent

      await store.fetchUser()

      expect(store.user).toBeNull()
      expect(store.isAuthenticated).toBe(false)
      expect(store.isImpersonating).toBe(false)
    })

    it('sets impersonating status from cookies', async () => {
      const { authService } = await import('@/services/authService')
      const { cookies } = await import('@/utils/cookies')
      vi.mocked(authService.fetchUser).mockResolvedValueOnce({ data: mockStudent } as any)
      vi.mocked(cookies.getAll).mockReturnValueOnce({ is_impersonating: 'true' })

      const store = useAuthStore()
      await store.fetchUser()

      expect(store.isImpersonating).toBe(true)
    })
  })

  describe('logout', () => {
    it('clears user and impersonating state', async () => {
      const { authService } = await import('@/services/authService')
      vi.mocked(authService.logout).mockResolvedValueOnce(undefined as any)

      const store = useAuthStore()
      store.user = mockStudent
      store.isImpersonating = true

      await store.logout()

      expect(store.user).toBeNull()
      expect(store.isImpersonating).toBe(false)
    })

    it('still clears state even when API throws', async () => {
      const { authService } = await import('@/services/authService')
      vi.mocked(authService.logout).mockRejectedValueOnce(new Error('Network error'))

      const store = useAuthStore()
      store.user = mockStudent

      await store.logout()

      expect(store.user).toBeNull()
      expect(store.isImpersonating).toBe(false)
    })
  })

  describe('computed properties', () => {
    it('isAuthenticated is true when user is set', () => {
      const store = useAuthStore()
      store.user = mockStudent
      expect(store.isAuthenticated).toBe(true)
    })

    it('isAdmin is true for admin role', () => {
      const store = useAuthStore()
      store.user = mockAdmin
      expect(store.isAdmin).toBe(true)
    })

    it('isAdmin is true for super_admin role', () => {
      const store = useAuthStore()
      store.user = mockSuperAdmin
      expect(store.isAdmin).toBe(true)
    })

    it('isAdmin is false for student role', () => {
      const store = useAuthStore()
      store.user = mockStudent
      expect(store.isAdmin).toBe(false)
    })

    it('isSuperAdmin is true for super_admin role', () => {
      const store = useAuthStore()
      store.user = mockSuperAdmin
      expect(store.isSuperAdmin).toBe(true)
    })

    it('isSuperAdmin is false for admin role', () => {
      const store = useAuthStore()
      store.user = mockAdmin
      expect(store.isSuperAdmin).toBe(false)
    })

    it('isStudent is true for student role', () => {
      const store = useAuthStore()
      store.user = mockStudent
      expect(store.isStudent).toBe(true)
    })

    it('isStudent is false for admin role', () => {
      const store = useAuthStore()
      store.user = mockAdmin
      expect(store.isStudent).toBe(false)
    })
  })

  describe('impersonateUser', () => {
    it('returns true and sets isImpersonating on success', async () => {
      const { authService } = await import('@/services/authService')
      vi.mocked(authService.impersonateUser).mockResolvedValueOnce(undefined as any)
      vi.mocked(authService.fetchUser).mockResolvedValueOnce({ data: mockStudent } as any)

      const store = useAuthStore()
      const result = await store.impersonateUser('user-2')

      expect(result).toBe(true)
      expect(store.isImpersonating).toBe(true)
    })

    it('returns false on API error', async () => {
      const { authService } = await import('@/services/authService')
      vi.mocked(authService.impersonateUser).mockRejectedValueOnce(new Error('Forbidden'))

      const store = useAuthStore()
      const result = await store.impersonateUser('user-2')

      expect(result).toBe(false)
    })
  })
})
