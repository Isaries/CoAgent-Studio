import axios from 'axios'
import { API_ENDPOINTS, HTTP_STATUS } from './constants/api'
import { useToastStore } from './stores/toast'

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json'
  },
  withCredentials: true
})

// Response interceptor to handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    // Access store inside interceptor to avoid circular dependency during init
    const toast = useToastStore()
    const originalRequest = error.config

    if (!originalRequest) {
      return Promise.reject(error)
    }

    // Prevent infinite loop: if the failed request was the refresh attempt, don't retry
    if (originalRequest.url?.includes(API_ENDPOINTS.REFRESH)) {
      return Promise.reject(error)
    }

    // Handle 500 Server Errors
    if (error.response?.status && error.response.status >= HTTP_STATUS.SERVER_ERROR) {
      const detail = error.response.data?.detail
      const message = detail
        ? `Server Error: ${detail}`
        : `Server Error: ${error.response.statusText || 'Internal Server Error'}`
      toast.error(message)
    }

    // Handle 403 Forbidden (Permission)
    if (error.response?.status === HTTP_STATUS.FORBIDDEN) {
      toast.warning('Access Denied: You do not have permission.')
    }

    // Handle 401 Unauthorized (Token Expiry)
    if (error.response?.status === HTTP_STATUS.UNAUTHORIZED && !originalRequest._retry) {
      originalRequest._retry = true
      try {
        await api.post(API_ENDPOINTS.REFRESH)
        return api(originalRequest)
      } catch (refreshError) {
        // Refresh failed - force logout via Router
        const { default: router } = await import('./router')
        const currentPath = router.currentRoute.value.path

        if (currentPath !== API_ENDPOINTS.LOGIN) {
          toast.info('Session expired, please login again.')
          await router.push(API_ENDPOINTS.LOGIN)
        }
        return Promise.reject(refreshError)
      }
    }
    return Promise.reject(error)
  }
)

export default api
