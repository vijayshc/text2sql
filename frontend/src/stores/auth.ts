import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import ApiService from '@/services/api'

export interface User {
  id: number
  username: string
  email?: string
  roles: string[]
  permissions: string[]
}

export interface AuthTokens {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref<User | null>(null)
  const accessToken = ref<string | null>(localStorage.getItem('access_token'))
  const refreshToken = ref<string | null>(localStorage.getItem('refresh_token'))
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // Computed
  const isAuthenticated = computed(() => {
    return !!accessToken.value && !!user.value
  })

  const hasRole = computed(() => {
    return (role: string) => {
      return user.value?.roles.includes(role) ?? false
    }
  })

  const hasPermission = computed(() => {
    return (permission: string) => {
      return user.value?.permissions.includes(permission) ?? false
    }
  })

  const isAdmin = computed(() => {
    return hasRole.value('admin')
  })

  // Actions
  async function login(username: string, password: string) {
    try {
      isLoading.value = true
      error.value = null

      const response = await ApiService.login(username, password)

      // Store tokens
      accessToken.value = response.tokens.access_token
      refreshToken.value = response.tokens.refresh_token
      localStorage.setItem('access_token', response.tokens.access_token)
      localStorage.setItem('refresh_token', response.tokens.refresh_token)

      // Store user info
      user.value = response.user

      return response
    } catch (err: any) {
      error.value = err.response?.data?.message || 'Login failed'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function logout() {
    try {
      if (accessToken.value) {
        await ApiService.logout()
      }
    } catch (err) {
      // Ignore logout errors
      console.warn('Logout API call failed:', err)
    } finally {
      // Clear local state regardless of API call result
      user.value = null
      accessToken.value = null
      refreshToken.value = null
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      error.value = null
    }
  }

  async function refreshTokens() {
    try {
      if (!refreshToken.value) {
        throw new Error('No refresh token available')
      }

      const response = await ApiService.refreshToken(refreshToken.value)

      // Update tokens
      accessToken.value = response.access_token
      localStorage.setItem('access_token', response.access_token)

      return response
    } catch (err) {
      // Refresh failed, clear tokens
      await logout()
      throw err
    }
  }

  async function fetchProfile() {
    try {
      if (!accessToken.value) {
        throw new Error('No access token')
      }

      const profile = await ApiService.getProfile()
      user.value = profile

      return profile
    } catch (err) {
      // If profile fetch fails, probably token is invalid
      await logout()
      throw err
    }
  }

  async function changePassword(currentPassword: string, newPassword: string) {
    try {
      isLoading.value = true
      error.value = null

      await ApiService.changePassword(currentPassword, newPassword)
    } catch (err: any) {
      error.value = err.response?.data?.message || 'Password change failed'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function verifyToken() {
    try {
      if (!accessToken.value) {
        return false
      }

      await ApiService.verifyToken()
      return true
    } catch (err) {
      // Token is invalid
      await logout()
      return false
    }
  }

  // Initialize auth state on store creation
  async function initialize() {
    if (accessToken.value) {
      try {
        await fetchProfile()
      } catch (err) {
        console.warn('Failed to fetch profile on initialization:', err)
        await logout()
      }
    }
  }

  return {
    // State
    user,
    accessToken,
    refreshToken,
    isLoading,
    error,

    // Computed
    isAuthenticated,
    hasRole,
    hasPermission,
    isAdmin,

    // Actions
    login,
    logout,
    refreshToken: refreshTokens, // Rename to avoid conflict
    fetchProfile,
    changePassword,
    verifyToken,
    initialize,
  }
})
