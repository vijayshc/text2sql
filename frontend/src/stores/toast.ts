import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface Toast {
  id: string
  message: string
  type: 'success' | 'error' | 'warning' | 'info'
  timeout?: number
}

export const useToastStore = defineStore('toast', () => {
  const toasts = ref<Toast[]>([])

  const addToast = (toast: Omit<Toast, 'id'>) => {
    const id = Math.random().toString(36).substr(2, 9)
    const newToast: Toast = { ...toast, id }
    
    toasts.value.push(newToast)

    // Auto-remove toast after timeout
    if (toast.timeout !== 0) {
      setTimeout(() => {
        removeToast(id)
      }, toast.timeout || 5000)
    }

    return id
  }

  const removeToast = (id: string) => {
    const index = toasts.value.findIndex(toast => toast.id === id)
    if (index > -1) {
      toasts.value.splice(index, 1)
    }
  }

  const success = (message: string, timeout?: number) => 
    addToast({ message, type: 'success', timeout })

  const error = (message: string, timeout?: number) => 
    addToast({ message, type: 'error', timeout })

  const warning = (message: string, timeout?: number) => 
    addToast({ message, type: 'warning', timeout })

  const info = (message: string, timeout?: number) => 
    addToast({ message, type: 'info', timeout })

  const clear = () => {
    toasts.value = []
  }

  return {
    toasts,
    addToast,
    removeToast,
    success,
    error,
    warning,
    info,
    clear
  }
})