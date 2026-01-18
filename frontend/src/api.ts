import axios from 'axios'

const REFRESH_URL = '/login/refresh'

const api = axios.create({
  baseURL: '/api/v1', // Proxy will handle this in dev, or env var
  headers: {
    'Content-Type': 'application/json'
  },
  withCredentials: true
})

// Response interceptor to handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    // Dynamic import to avoid circular dependency if store imports api
    // But usually store uses API. To be safe, we can import store here if pinia is active.
    // However, pinia instance must be active. This api.ts is imported by components.
    // Better: use direct store import but inside the interceptor or ensure app setup
    const { useToastStore } = await import('./stores/toast')
    const toast = useToastStore()

    const originalRequest = error.config

    // Prevent infinite loop: if the failed request was the refresh attempt, don't retry
    if (originalRequest.url.includes(REFRESH_URL)) {
      return Promise.reject(error)
    }

    // Handle 500 Server Errors
    if (error.response?.status >= 500) {
      const detail = error.response.data?.detail
      const message = detail ? `Server Error: ${detail}` : `Server Error: ${error.response.statusText || 'Internal Server Error'}`
      toast.error(message)
    }

    // Handle 403 Forbidden (Permission)
    if (error.response?.status === 403) {
      toast.warning('Access Denied: You do not have permission.')
    }

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      try {
        await api.post(REFRESH_URL)
        return api(originalRequest)
      } catch (refreshError) {
        // Refresh failed - force logout
        if (window.location.pathname !== '/login') {
          toast.info('Session expired, please login again.')
          window.location.href = '/login'
        }
        return Promise.reject(refreshError)
      }
    }
    return Promise.reject(error)
  }
)

export default api
