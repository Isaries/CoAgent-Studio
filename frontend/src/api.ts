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
    const originalRequest = error.config

    // Prevent infinite loop: if the failed request was the refresh attempt, don't retry
    if (originalRequest.url.includes(REFRESH_URL)) {
      return Promise.reject(error)
    }

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      try {
        await api.post(REFRESH_URL)
        return api(originalRequest)
      } catch (refreshError) {
        // Refresh failed - force logout
        // Using window.location instead of router to ensure full state reset
        if (window.location.pathname !== '/login') {
          window.location.href = '/login'
        }
        return Promise.reject(refreshError)
      }
    }
    return Promise.reject(error)
  }
)

export default api
