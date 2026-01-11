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
        // Refresh failed - let the store handle logout or catch block in component handle it
        // Ideally, we should redirect to login if we know it's a session expiry
        // import router is available
        // router.push('/login') // Moved to catch block in store usually, but global handler is safer
        return Promise.reject(refreshError)
      }
    }
    return Promise.reject(error)
  }
)

export default api
