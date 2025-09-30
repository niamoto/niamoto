import axios from 'axios'

// Create axios instance with base configuration
export const apiClient = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json'
  },
  timeout: 60000 // 60 seconds
})

// Request interceptor for error handling
apiClient.interceptors.request.use(
  config => config,
  error => Promise.reject(error)
)

// Response interceptor for error handling
apiClient.interceptors.response.use(
  response => response,
  error => {
    // Handle common errors
    if (error.response?.status === 404) {
      console.error('Resource not found:', error.config?.url)
    } else if (error.response?.status === 500) {
      console.error('Server error:', error.response?.data?.detail || error.message)
    }
    return Promise.reject(error)
  }
)

export default apiClient
