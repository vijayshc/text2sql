<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useUIStore } from '@/stores/ui'

const authStore = useAuthStore()
const uiStore = useUIStore()

const isLoading = ref(false)

// User information display
const user = computed(() => authStore.user)
const userRoles = computed(() => user.value?.roles.join(', ') || 'No roles assigned')
const userPermissions = computed(() => user.value?.permissions || [])

// Group permissions by category for better display
const groupedPermissions = computed(() => {
  if (!userPermissions.value.length) return {}
  
  const groups: Record<string, string[]> = {}
  
  userPermissions.value.forEach(permission => {
    // Extract category from permission name (e.g., "ADMIN_ACCESS" -> "Admin")
    const parts = permission.split('_')
    const category = parts.length > 1 ? parts[0] : 'General'
    const categoryName = category.charAt(0).toUpperCase() + category.slice(1).toLowerCase()
    
    if (!groups[categoryName]) {
      groups[categoryName] = []
    }
    
    // Format permission name for display
    const displayName = permission
      .split('_')
      .map(part => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
      .join(' ')
    
    groups[categoryName].push(displayName)
  })
  
  return groups
})

const refreshProfile = async () => {
  try {
    isLoading.value = true
    await authStore.fetchProfile()
    uiStore.showSuccess('Profile Updated', 'Your profile information has been refreshed')
  } catch (error: any) {
    uiStore.showError('Refresh Failed', error.message)
  } finally {
    isLoading.value = false
  }
}

const formatJoinDate = (dateString?: string) => {
  if (!dateString) return 'Unknown'
  try {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    })
  } catch {
    return 'Invalid date'
  }
}

const getPermissionIcon = (permission: string) => {
  if (permission.includes('Admin')) return 'fas fa-crown'
  if (permission.includes('User')) return 'fas fa-users'
  if (permission.includes('Query') || permission.includes('Run')) return 'fas fa-search'
  if (permission.includes('Manage')) return 'fas fa-cog'
  if (permission.includes('View')) return 'fas fa-eye'
  if (permission.includes('Edit')) return 'fas fa-edit'
  if (permission.includes('Delete')) return 'fas fa-trash'
  return 'fas fa-check'
}

onMounted(() => {
  // Ensure we have the latest profile data
  if (!user.value) {
    refreshProfile()
  }
})
</script>

<template>
  <div class="max-w-4xl mx-auto space-y-6">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white">
          User Profile
        </h1>
        <p class="text-gray-600 dark:text-gray-400 mt-1">
          View your account information and permissions
        </p>
      </div>
      
      <div class="flex items-center space-x-3">
        <router-link
          to="/change-password"
          class="btn btn-secondary"
        >
          <i class="fas fa-key mr-2"></i>
          Change Password
        </router-link>
        
        <button
          @click="refreshProfile"
          :disabled="isLoading"
          class="btn btn-primary"
        >
          <i v-if="isLoading" class="fas fa-spinner fa-spin mr-2"></i>
          <i v-else class="fas fa-sync mr-2"></i>
          {{ isLoading ? 'Refreshing...' : 'Refresh' }}
        </button>
      </div>
    </div>

    <!-- Profile Information -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- User Info Card -->
      <div class="lg:col-span-2">
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
          <div class="p-6">
            <div class="flex items-center space-x-6">
              <!-- Avatar -->
              <div class="w-20 h-20 bg-primary-100 dark:bg-primary-900 rounded-full flex items-center justify-center">
                <span class="text-2xl font-bold text-primary-600 dark:text-primary-300">
                  {{ user?.username?.charAt(0).toUpperCase() || 'U' }}
                </span>
              </div>
              
              <!-- User Details -->
              <div class="flex-1">
                <h2 class="text-xl font-bold text-gray-900 dark:text-white">
                  {{ user?.username || 'Unknown User' }}
                </h2>
                <p class="text-gray-600 dark:text-gray-400 mt-1">
                  {{ user?.email || 'No email provided' }}
                </p>
                
                <!-- Role Badge -->
                <div class="mt-3">
                  <span class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-primary-100 dark:bg-primary-900 text-primary-800 dark:text-primary-200">
                    <i class="fas fa-user-tag mr-2"></i>
                    {{ userRoles }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Quick Stats -->
      <div class="space-y-4">
        <!-- Account Status -->
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4">
          <h3 class="text-sm font-medium text-gray-900 dark:text-white mb-3">Account Status</h3>
          <div class="space-y-3">
            <div class="flex items-center justify-between">
              <span class="text-sm text-gray-600 dark:text-gray-400">Status</span>
              <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                <i class="fas fa-check-circle mr-1"></i>
                Active
              </span>
            </div>
            
            <div class="flex items-center justify-between">
              <span class="text-sm text-gray-600 dark:text-gray-400">User ID</span>
              <span class="text-sm font-medium text-gray-900 dark:text-white">
                #{{ user?.id || 'N/A' }}
              </span>
            </div>
            
            <div class="flex items-center justify-between">
              <span class="text-sm text-gray-600 dark:text-gray-400">Roles</span>
              <span class="text-sm font-medium text-gray-900 dark:text-white">
                {{ user?.roles?.length || 0 }}
              </span>
            </div>
            
            <div class="flex items-center justify-between">
              <span class="text-sm text-gray-600 dark:text-gray-400">Permissions</span>
              <span class="text-sm font-medium text-gray-900 dark:text-white">
                {{ userPermissions.length }}
              </span>
            </div>
          </div>
        </div>

        <!-- Session Info -->
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4">
          <h3 class="text-sm font-medium text-gray-900 dark:text-white mb-3">Session Information</h3>
          <div class="space-y-3">
            <div class="flex items-center justify-between">
              <span class="text-sm text-gray-600 dark:text-gray-400">Login Status</span>
              <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                <i class="fas fa-circle mr-1"></i>
                Online
              </span>
            </div>
            
            <div class="flex items-center justify-between">
              <span class="text-sm text-gray-600 dark:text-gray-400">Token Status</span>
              <span class="text-sm font-medium text-green-600 dark:text-green-400">
                <i class="fas fa-shield-alt mr-1"></i>
                Valid
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Permissions Panel -->
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
      <div class="p-6 border-b border-gray-200 dark:border-gray-700">
        <h3 class="text-lg font-medium text-gray-900 dark:text-white">User Permissions</h3>
        <p class="text-sm text-gray-600 dark:text-gray-400 mt-1">
          The following permissions are assigned to your account
        </p>
      </div>
      
      <div class="p-6">
        <div v-if="Object.keys(groupedPermissions).length === 0" class="text-center py-8">
          <i class="fas fa-ban text-4xl text-gray-400 mb-4"></i>
          <p class="text-gray-500 dark:text-gray-400">No permissions assigned</p>
        </div>
        
        <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div
            v-for="(permissions, category) in groupedPermissions"
            :key="category"
            class="space-y-3"
          >
            <h4 class="text-sm font-semibold text-gray-900 dark:text-white uppercase tracking-wider">
              {{ category }}
            </h4>
            
            <div class="space-y-2">
              <div
                v-for="permission in permissions"
                :key="permission"
                class="flex items-center space-x-3 p-2 bg-gray-50 dark:bg-gray-700 rounded-lg"
              >
                <i :class="getPermissionIcon(permission)" class="text-sm text-primary-600 dark:text-primary-400"></i>
                <span class="text-sm text-gray-700 dark:text-gray-300">{{ permission }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Security Information -->
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
      <div class="p-6 border-b border-gray-200 dark:border-gray-700">
        <h3 class="text-lg font-medium text-gray-900 dark:text-white">Security & Privacy</h3>
        <p class="text-sm text-gray-600 dark:text-gray-400 mt-1">
          Manage your account security settings
        </p>
      </div>
      
      <div class="p-6">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <!-- Password Security -->
          <div class="space-y-4">
            <h4 class="text-sm font-medium text-gray-900 dark:text-white">Password Security</h4>
            <div class="space-y-3">
              <div class="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                <div class="flex items-center space-x-3">
                  <i class="fas fa-key text-gray-500"></i>
                  <span class="text-sm text-gray-700 dark:text-gray-300">Password Protection</span>
                </div>
                <span class="text-sm text-green-600 dark:text-green-400">
                  <i class="fas fa-check"></i>
                  Enabled
                </span>
              </div>
              
              <router-link
                to="/change-password"
                class="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors"
              >
                <div class="flex items-center space-x-3">
                  <i class="fas fa-edit text-gray-500"></i>
                  <span class="text-sm text-gray-700 dark:text-gray-300">Change Password</span>
                </div>
                <i class="fas fa-chevron-right text-gray-400"></i>
              </router-link>
            </div>
          </div>

          <!-- Session Management -->
          <div class="space-y-4">
            <h4 class="text-sm font-medium text-gray-900 dark:text-white">Session Management</h4>
            <div class="space-y-3">
              <div class="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                <div class="flex items-center space-x-3">
                  <i class="fas fa-clock text-gray-500"></i>
                  <span class="text-sm text-gray-700 dark:text-gray-300">Auto-logout</span>
                </div>
                <span class="text-sm text-blue-600 dark:text-blue-400">
                  24 hours
                </span>
              </div>
              
              <div class="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                <div class="flex items-center space-x-3">
                  <i class="fas fa-shield-alt text-gray-500"></i>
                  <span class="text-sm text-gray-700 dark:text-gray-300">Token Refresh</span>
                </div>
                <span class="text-sm text-green-600 dark:text-green-400">
                  <i class="fas fa-check"></i>
                  Active
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Custom button styles */
.btn {
  @apply inline-flex items-center justify-center px-4 py-2 border rounded-lg text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed;
}

.btn-primary {
  @apply border-transparent text-white bg-primary-600 hover:bg-primary-700 focus:ring-primary-500;
}

.btn-secondary {
  @apply border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 focus:ring-primary-500;
}

/* Font Awesome icons */
.fas {
  font-family: 'Font Awesome 6 Free';
  font-weight: 900;
}
</style>