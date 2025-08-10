import axios, { type AxiosInstance, type AxiosResponse, type AxiosError } from 'axios'
import { useAuthStore } from '@/stores/auth'
import type { 
  LoginResponse, 
  RefreshResponse, 
  QuerySubmitResponse, 
  QueryProgressResponse,
  WorkspacesResponse,
  SchemaResponse,
  SuggestionsResponse
} from '@/types/api'

// API configuration
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'
const API_VERSION = '/api/v1'

// Create axios instance
const apiClient: AxiosInstance = axios.create({
  baseURL: `${API_BASE_URL}${API_VERSION}`,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config) => {
    const authStore = useAuthStore()
    if (authStore.accessToken) {
      config.headers.Authorization = `Bearer ${authStore.accessToken}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  },
)

// Response interceptor for error handling and token refresh
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    return response
  },
  async (error: AxiosError) => {
    const authStore = useAuthStore()
    const originalRequest = error.config

    // Handle 401 errors (unauthorized)
    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        // Try to refresh the token
        await authStore.refreshTokens()

        // Retry the original request with the new token
        if (authStore.accessToken) {
          originalRequest.headers = originalRequest.headers || {}
          originalRequest.headers.Authorization = `Bearer ${authStore.accessToken}`
          return apiClient(originalRequest)
        }
      } catch (refreshError) {
        // Refresh failed, redirect to login
        authStore.logout()
        window.location.href = '/login'
        return Promise.reject(refreshError)
      }
    }

    return Promise.reject(error)
  },
)

// API response types
export interface ApiResponse<T = any> {
  data: T
  message?: string
  success?: boolean
}

export interface ApiError {
  error: string
  message: string
  status_code: number
}

// API service class
export class ApiService {
  // Generic API methods
  static async get<T>(url: string, params?: any): Promise<T> {
    const response = await apiClient.get<T>(url, { params })
    return response.data
  }

  static async post<T>(url: string, data?: any): Promise<T> {
    const response = await apiClient.post<T>(url, data)
    return response.data
  }

  static async put<T>(url: string, data?: any): Promise<T> {
    const response = await apiClient.put<T>(url, data)
    return response.data
  }

  static async delete<T>(url: string): Promise<T> {
    const response = await apiClient.delete<T>(url)
    return response.data
  }

  // Authentication endpoints
  static async login(username: string, password: string): Promise<LoginResponse> {
    return this.post<LoginResponse>('/auth/login', { username, password })
  }

  static async logout() {
    return this.post('/auth/logout')
  }

  static async refreshToken(refreshToken: string): Promise<RefreshResponse> {
    return this.post<RefreshResponse>('/auth/refresh', { refresh_token: refreshToken })
  }

  static async changePassword(currentPassword: string, newPassword: string) {
    return this.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    })
  }

  static async getProfile() {
    return this.get('/auth/profile')
  }

  static async verifyToken() {
    return this.get('/auth/verify')
  }

  // Query endpoints
  static async submitQuery(query: string, workspace?: string, tables?: string[]): Promise<QuerySubmitResponse> {
    return this.post<QuerySubmitResponse>('/query/submit', { query, workspace, tables })
  }

  static async getQueryProgress(queryId: string): Promise<QueryProgressResponse> {
    return this.get<QueryProgressResponse>(`/query/progress/${queryId}`)
  }

  static async getSchema(workspace?: string): Promise<SchemaResponse> {
    return this.get<SchemaResponse>('/query/schema', { workspace })
  }

  static async getWorkspaces(): Promise<WorkspacesResponse> {
    return this.get<WorkspacesResponse>('/query/workspaces')
  }

  static async getTables(workspace?: string) {
    return this.get('/query/tables', { workspace })
  }

  static async getTableSuggestions(workspace?: string, query?: string): Promise<SuggestionsResponse> {
    return this.get<SuggestionsResponse>('/query/suggestions', { workspace, query })
  }

  // Feedback endpoints
  static async submitFeedback(feedback: {
    query_text: string
    sql_query: string
    feedback_rating: number
    results_summary?: string
    workspace?: string
    tables_used?: string[]
  }) {
    return this.post('/feedback/submit', feedback)
  }

  static async getFeedbackStats() {
    return this.get('/feedback/stats')
  }

  static async getSamples(page = 1, limit = 10, query?: string) {
    return this.get('/feedback/samples', { page, limit, query })
  }

  static async createSample(sample: {
    query_text: string
    sql_query: string
    results_summary?: string
    workspace?: string
    tables_used?: string[]
  }) {
    return this.post('/feedback/samples', sample)
  }

  static async getSample(id: number) {
    return this.get(`/feedback/samples/${id}`)
  }

  static async updateSample(id: number, sample: any) {
    return this.put(`/feedback/samples/${id}`, sample)
  }

  static async deleteSample(id: number) {
    return this.delete(`/feedback/samples/${id}`)
  }
}

export default ApiService
