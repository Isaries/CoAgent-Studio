import { describe, it, expect, vi, beforeEach } from 'vitest'
import { authService } from '@/services/authService'

// ---------------------------------------------------------------------------
// Mock the api module (axios instance exported as default from @/api)
// ---------------------------------------------------------------------------
vi.mock('@/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn()
  }
}))

import api from '@/api'

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('authService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // --------------------------------------------------------------------------
  // login
  // --------------------------------------------------------------------------

  describe('login()', () => {
    it('calls POST /login/access-token with the FormData payload', async () => {
      vi.mocked(api.post).mockResolvedValue({ data: {} })

      const formData = new FormData()
      formData.append('username', 'alice@test.com')
      formData.append('password', 'secret')

      await authService.login(formData)

      expect(api.post).toHaveBeenCalledWith('/login/access-token', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
    })

    it('returns true when the API call succeeds', async () => {
      vi.mocked(api.post).mockResolvedValue({ data: {} })

      const result = await authService.login(new FormData())

      expect(result).toBe(true)
    })

    it('returns false when the API call throws an error', async () => {
      vi.mocked(api.post).mockRejectedValue(new Error('401 Unauthorized'))

      const result = await authService.login(new FormData())

      expect(result).toBe(false)
    })

    it('does not propagate the error thrown by the API', async () => {
      vi.mocked(api.post).mockRejectedValue(new Error('Network error'))

      await expect(authService.login(new FormData())).resolves.toBe(false)
    })
  })

  // --------------------------------------------------------------------------
  // fetchUser
  // --------------------------------------------------------------------------

  describe('fetchUser()', () => {
    it('calls POST /login/test-token', async () => {
      const fakeUser = { id: '1', email: 'alice@test.com', role: 'student' }
      vi.mocked(api.post).mockResolvedValue({ data: fakeUser })

      const response = await authService.fetchUser()

      expect(api.post).toHaveBeenCalledWith('/login/test-token')
      expect(response.data).toEqual(fakeUser)
    })

    it('returns the axios response object', async () => {
      const mockResponse = { data: { id: '2', email: 'bob@test.com' }, status: 200 }
      vi.mocked(api.post).mockResolvedValue(mockResponse)

      const result = await authService.fetchUser()

      expect(result).toEqual(mockResponse)
    })
  })

  // --------------------------------------------------------------------------
  // logout
  // --------------------------------------------------------------------------

  describe('logout()', () => {
    it('calls POST /login/logout', async () => {
      vi.mocked(api.post).mockResolvedValue({ data: {} })

      await authService.logout()

      expect(api.post).toHaveBeenCalledWith('/login/logout')
    })

    it('returns the axios response', async () => {
      const mockResponse = { data: { detail: 'Logged out' }, status: 200 }
      vi.mocked(api.post).mockResolvedValue(mockResponse)

      const result = await authService.logout()

      expect(result).toEqual(mockResponse)
    })
  })

  // --------------------------------------------------------------------------
  // refreshToken
  // --------------------------------------------------------------------------

  describe('refreshToken()', () => {
    it('calls POST /login/refresh', async () => {
      vi.mocked(api.post).mockResolvedValue({ data: {} })

      await authService.refreshToken()

      expect(api.post).toHaveBeenCalledWith('/login/refresh')
    })

    it('returns the axios response', async () => {
      const mockResponse = { data: {}, status: 200 }
      vi.mocked(api.post).mockResolvedValue(mockResponse)

      const result = await authService.refreshToken()

      expect(result).toEqual(mockResponse)
    })
  })

  // --------------------------------------------------------------------------
  // impersonateUser
  // --------------------------------------------------------------------------

  describe('impersonateUser()', () => {
    it('calls POST /login/impersonate/:userId with the correct user ID', async () => {
      vi.mocked(api.post).mockResolvedValue({ data: {} })

      await authService.impersonateUser('user-123')

      expect(api.post).toHaveBeenCalledWith('/login/impersonate/user-123')
    })

    it('uses the exact userId string in the URL path', async () => {
      vi.mocked(api.post).mockResolvedValue({ data: {} })

      await authService.impersonateUser('abc-xyz-789')

      expect(api.post).toHaveBeenCalledWith('/login/impersonate/abc-xyz-789')
    })
  })

  // --------------------------------------------------------------------------
  // stopImpersonating
  // --------------------------------------------------------------------------

  describe('stopImpersonating()', () => {
    it('calls POST /login/stop-impersonate', async () => {
      vi.mocked(api.post).mockResolvedValue({ data: {} })

      await authService.stopImpersonating()

      expect(api.post).toHaveBeenCalledWith('/login/stop-impersonate')
    })
  })
})
