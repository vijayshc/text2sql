<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useUIStore } from '@/stores/ui'
import AppSidebar from '@/components/AppSidebar.vue'
import AppHeader from '@/components/AppHeader.vue'
import ToastNotification from '@/components/ToastNotification.vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const uiStore = useUIStore()

const sidebarOpen = ref(true)

const toggleSidebar = () => {
  sidebarOpen.value = !sidebarOpen.value
}

// Check authentication on mount
onMounted(async () => {
  await authStore.initialize()
  if (!authStore.isAuthenticated) {
    router.push('/login')
  }
})
</script>

<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-900">
    <!-- App Header -->
    <AppHeader @toggle-sidebar="toggleSidebar" />
    
    <!-- Main Content Area -->
    <div class="flex">
      <!-- Sidebar -->
      <AppSidebar 
        :is-open="sidebarOpen" 
        @close="sidebarOpen = false" 
      />
      
      <!-- Main Content -->
      <main 
        class="flex-1 transition-all duration-300"
        :class="{ 'ml-64': sidebarOpen, 'ml-0': !sidebarOpen }"
      >
        <div class="pt-16"> <!-- Account for fixed header -->
          <div class="p-6">
            <router-view />
          </div>
        </div>
      </main>
    </div>
    
    <!-- Toast Notifications -->
    <ToastNotification />
  </div>
</template>

<style scoped>
@media (max-width: 768px) {
  main {
    margin-left: 0 !important;
  }
}
</style>