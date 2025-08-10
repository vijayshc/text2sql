<script setup lang="ts">
import { onMounted } from 'vue'
import { useUIStore } from '@/stores/ui'

const uiStore = useUIStore()

// Initialize theme on app mount
onMounted(() => {
  uiStore.initializeTheme()
})
</script>

<template>
  <div id="app">
    <router-view />
  </div>
</template>

<style>
/* Global styles */
html {
  scroll-behavior: smooth;
}

body {
  margin: 0;
  padding: 0;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* Scrollbar styling */
::-webkit-scrollbar {
  width: 8px;
}

::-webkit-scrollbar-track {
  @apply bg-gray-100 dark:bg-gray-800;
}

::-webkit-scrollbar-thumb {
  @apply bg-gray-300 dark:bg-gray-600 rounded-full;
}

::-webkit-scrollbar-thumb:hover {
  @apply bg-gray-400 dark:bg-gray-500;
}

/* Focus styles */
button:focus,
input:focus,
textarea:focus,
select:focus {
  outline: 2px solid rgb(59 130 246);
  outline-offset: 2px;
}

/* Transition for theme switching */
* {
  transition: background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease;
}

/* Utility classes */
.glass {
  backdrop-filter: blur(10px);
  background-color: rgba(255, 255, 255, 0.8);
}

.dark .glass {
  background-color: rgba(31, 41, 55, 0.8);
}

/* Animation utilities */
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.fade-in {
  animation: fadeIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.slide-in {
  animation: slideIn 0.3s ease-out;
}

/* Loading spinner */
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.animate-spin {
  animation: spin 1s linear infinite;
}

/* Modal backdrop */
.modal-backdrop {
  backdrop-filter: blur(4px);
}
</style>
