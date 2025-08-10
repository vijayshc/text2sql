<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useUIStore } from '@/stores/ui'
import { useRouter } from 'vue-router'

defineEmits<{
  toggleSidebar: []
}>()

const authStore = useAuthStore()
const uiStore = useUIStore()
const router = useRouter()

const userMenuOpen = ref(false)

const handleLogout = async () => {
  try {
    await authStore.logout()
    router.push('/login')
  } catch (error) {
    console.error('Logout failed:', error)
  }
  userMenuOpen.value = false
}

const toggleTheme = () => {
  uiStore.toggleTheme()
}
</script>

<template>
  <header class="fixed top-0 left-0 right-0 z-50 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
    <div class="flex items-center justify-between px-4 py-3">
      <!-- Left side: Logo and menu toggle -->
      <div class="flex items-center space-x-4">
        <!-- Mobile menu button -->
        <button
          @click="$emit('toggleSidebar')"
          class="p-2 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg md:hidden"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
        
        <!-- Desktop menu button -->
        <button
          @click="$emit('toggleSidebar')"
          class="hidden md:block p-2 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>

        <!-- Logo -->
        <div class="flex items-center space-x-2">
          <div class="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
            <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
            </svg>
          </div>
          <span class="text-xl font-bold text-gray-900 dark:text-white">Text2SQL Assistant</span>
        </div>
      </div>

      <!-- Right side: Theme toggle and user menu -->
      <div class="flex items-center space-x-3">
        <!-- Theme toggle -->
        <button
          @click="toggleTheme"
          class="p-2 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
          title="Toggle theme"
        >
          <svg v-if="uiStore.theme === 'light'" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
          </svg>
          <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
          </svg>
        </button>

        <!-- User menu -->
        <div class="relative">
          <button
            @click="userMenuOpen = !userMenuOpen"
            class="flex items-center space-x-2 p-2 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
          >
            <div class="w-8 h-8 bg-primary-100 dark:bg-primary-900 rounded-full flex items-center justify-center">
              <span class="text-sm font-medium text-primary-600 dark:text-primary-300">
                {{ authStore.user?.username?.charAt(0).toUpperCase() }}
              </span>
            </div>
            <span class="hidden md:block text-sm font-medium">{{ authStore.user?.username }}</span>
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          <!-- Dropdown menu -->
          <div
            v-if="userMenuOpen"
            class="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 py-1"
            @click.away="userMenuOpen = false"
          >
            <div class="px-4 py-2 border-b border-gray-200 dark:border-gray-700">
              <p class="text-sm font-medium text-gray-900 dark:text-white">{{ authStore.user?.username }}</p>
              <p class="text-xs text-gray-500 dark:text-gray-400">{{ authStore.user?.email }}</p>
            </div>
            
            <router-link
              to="/profile"
              class="block px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
              @click="userMenuOpen = false"
            >
              <i class="fas fa-user w-4 mr-2"></i>
              Profile
            </router-link>
            
            <router-link
              to="/change-password"
              class="block px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
              @click="userMenuOpen = false"
            >
              <i class="fas fa-key w-4 mr-2"></i>
              Change Password
            </router-link>
            
            <button
              @click="handleLogout"
              class="w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
            >
              <i class="fas fa-sign-out-alt w-4 mr-2"></i>
              Logout
            </button>
          </div>
        </div>
      </div>
    </div>
  </header>
</template>

<style scoped>
/* Custom dropdown styling */
.dropdown-enter-active,
.dropdown-leave-active {
  transition: all 0.2s ease;
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>