import api from '../api'
import type { User } from '../types/user'

export const authService = {
  async login(formData: FormData): Promise<boolean> {
    try {
      await api.post('/login/access-token', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      return true
    } catch {
      return false
    }
  },

  async fetchUser() {
    return api.post<User>('/login/test-token')
  },

  async logout() {
    return api.post('/login/logout')
  },

  async refreshToken() {
    return api.post('/login/refresh')
  },

  async impersonateUser(userId: string) {
    return api.post(`/login/impersonate/${userId}`)
  },

  async stopImpersonating() {
    return api.post('/login/stop-impersonate')
  }
}
