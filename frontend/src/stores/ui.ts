import { ref } from 'vue'
import { defineStore } from 'pinia'

export type ThemeMode = 'light' | 'dark'
export type ToastType = 'success' | 'error' | 'warning' | 'info'

export interface Toast {
  id: string
  type: ToastType
  title: string
  message?: string
  duration?: number
}

export const useUIStore = defineStore('ui', () => {
  // State
  const theme = ref<ThemeMode>('light')
  const sidebarCollapsed = ref(false)
  const toasts = ref<Toast[]>([])
  const modals = ref<Record<string, boolean>>({})
  const loading = ref<Record<string, boolean>>({})

  // Actions
  function setTheme(newTheme: ThemeMode) {
    theme.value = newTheme
    localStorage.setItem('theme', newTheme)

    // Apply theme to DOM
    if (newTheme === 'dark') {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }

  function toggleTheme() {
    setTheme(theme.value === 'light' ? 'dark' : 'light')
  }

  function initializeTheme() {
    const savedTheme = localStorage.getItem('theme') as ThemeMode
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches

    const initialTheme = savedTheme || (prefersDark ? 'dark' : 'light')
    setTheme(initialTheme)
  }

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function setSidebarCollapsed(collapsed: boolean) {
    sidebarCollapsed.value = collapsed
  }

  function showToast(toast: Omit<Toast, 'id'>) {
    const id = Date.now().toString()
    const duration = toast.duration ?? 5000

    const newToast: Toast = {
      id,
      ...toast,
    }

    toasts.value.push(newToast)

    // Auto-remove toast after duration
    if (duration > 0) {
      setTimeout(() => {
        removeToast(id)
      }, duration)
    }

    return id
  }

  function removeToast(id: string) {
    const index = toasts.value.findIndex((toast) => toast.id === id)
    if (index > -1) {
      toasts.value.splice(index, 1)
    }
  }

  function clearToasts() {
    toasts.value = []
  }

  function showModal(modalId: string) {
    modals.value[modalId] = true
  }

  function hideModal(modalId: string) {
    modals.value[modalId] = false
  }

  function isModalOpen(modalId: string): boolean {
    return modals.value[modalId] ?? false
  }

  function setLoading(key: string, isLoading: boolean) {
    if (isLoading) {
      loading.value[key] = true
    } else {
      delete loading.value[key]
    }
  }

  function isLoading(key: string): boolean {
    return loading.value[key] ?? false
  }

  // Utility toast methods
  function showSuccess(title: string, message?: string) {
    return showToast({ type: 'success', title, message })
  }

  function showError(title: string, message?: string) {
    return showToast({ type: 'error', title, message, duration: 0 }) // Don't auto-hide errors
  }

  function showWarning(title: string, message?: string) {
    return showToast({ type: 'warning', title, message })
  }

  function showInfo(title: string, message?: string) {
    return showToast({ type: 'info', title, message })
  }

  return {
    // State
    theme,
    sidebarCollapsed,
    toasts,
    modals,
    loading,

    // Actions
    setTheme,
    toggleTheme,
    initializeTheme,
    toggleSidebar,
    setSidebarCollapsed,
    showToast,
    removeToast,
    clearToasts,
    showModal,
    hideModal,
    isModalOpen,
    setLoading,
    isLoading,

    // Utility methods
    showSuccess,
    showError,
    showWarning,
    showInfo,
  }
})
