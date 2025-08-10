<script setup lang="ts">
import { computed } from 'vue'
import { useUIStore } from '@/stores/ui'

const uiStore = useUIStore()

const toasts = computed(() => uiStore.toasts)

const getToastIcon = (type: string) => {
  switch (type) {
    case 'success':
      return 'fas fa-check-circle'
    case 'error':
      return 'fas fa-exclamation-circle'
    case 'warning':
      return 'fas fa-exclamation-triangle'
    case 'info':
    default:
      return 'fas fa-info-circle'
  }
}

const getToastClasses = (type: string) => {
  const baseClasses = 'p-4 rounded-lg shadow-lg border-l-4 transition-all duration-300'
  
  switch (type) {
    case 'success':
      return `${baseClasses} bg-green-50 dark:bg-green-900/30 border-green-400 text-green-800 dark:text-green-200`
    case 'error':
      return `${baseClasses} bg-red-50 dark:bg-red-900/30 border-red-400 text-red-800 dark:text-red-200`
    case 'warning':
      return `${baseClasses} bg-yellow-50 dark:bg-yellow-900/30 border-yellow-400 text-yellow-800 dark:text-yellow-200`
    case 'info':
    default:
      return `${baseClasses} bg-blue-50 dark:bg-blue-900/30 border-blue-400 text-blue-800 dark:text-blue-200`
  }
}

const closeToast = (id: string) => {
  uiStore.removeToast(id)
}
</script>

<template>
  <!-- Toast Container -->
  <div class="fixed bottom-4 right-4 z-50 space-y-2 max-w-sm">
    <transition-group
      name="toast"
      tag="div"
      class="space-y-2"
    >
      <div
        v-for="toast in toasts"
        :key="toast.id"
        :class="getToastClasses(toast.type)"
        class="relative"
      >
        <div class="flex items-start">
          <!-- Icon -->
          <div class="flex-shrink-0">
            <i :class="getToastIcon(toast.type)" class="text-lg"></i>
          </div>
          
          <!-- Message -->
          <div class="ml-3 flex-1">
            <h4 v-if="toast.title" class="font-medium mb-1">
              {{ toast.title }}
            </h4>
            <p class="text-sm" :class="{ 'font-medium': !toast.title }">
              {{ toast.message }}
            </p>
          </div>
          
          <!-- Close button -->
          <button
            @click="closeToast(toast.id)"
            class="ml-4 inline-flex text-sm rounded-md p-1.5 hover:bg-black hover:bg-opacity-10 dark:hover:bg-white dark:hover:bg-opacity-10 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-transparent focus:ring-gray-500"
          >
            <span class="sr-only">Dismiss</span>
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        
        <!-- Progress bar for auto-dismiss -->
        <div 
          v-if="toast.duration && toast.duration > 0"
          class="absolute bottom-0 left-0 h-1 bg-current opacity-30 rounded-bl-lg"
          :style="{ 
            width: '100%', 
            animation: `toast-progress ${toast.duration}ms linear` 
          }"
        ></div>
      </div>
    </transition-group>
  </div>
</template>

<style scoped>
/* Toast animations */
.toast-enter-active {
  transition: all 0.3s ease-out;
}

.toast-leave-active {
  transition: all 0.3s ease-in;
}

.toast-enter-from {
  transform: translateX(100%);
  opacity: 0;
}

.toast-leave-to {
  transform: translateX(100%);
  opacity: 0;
}

.toast-move {
  transition: transform 0.3s ease;
}

/* Progress bar animation */
@keyframes toast-progress {
  from {
    width: 100%;
  }
  to {
    width: 0%;
  }
}

/* Font Awesome icons */
.fas {
  font-family: 'Font Awesome 6 Free';
  font-weight: 900;
}
</style>