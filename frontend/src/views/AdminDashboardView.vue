<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-900">
    <!-- Header -->
    <div class="bg-white dark:bg-gray-800 shadow">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="py-6">
          <h1 class="text-3xl font-bold text-gray-900 dark:text-white">
            Admin Dashboard
          </h1>
          <p class="mt-2 text-gray-600 dark:text-gray-400">
            Manage users, roles, MCP servers, and monitor system activity
          </p>
        </div>
      </div>
    </div>

    <!-- Content -->
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <!-- Stats Cards -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div class="flex items-center">
            <div class="flex-shrink-0">
              <div class="w-8 h-8 bg-blue-500 rounded-md flex items-center justify-center">
                <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z"></path>
                </svg>
              </div>
            </div>
            <div class="ml-4">
              <dt class="text-sm font-medium text-gray-500 dark:text-gray-400">Total Users</dt>
              <dd class="text-2xl font-semibold text-gray-900 dark:text-white">{{ stats.users?.total || 0 }}</dd>
            </div>
          </div>
        </div>

        <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div class="flex items-center">
            <div class="flex-shrink-0">
              <div class="w-8 h-8 bg-green-500 rounded-md flex items-center justify-center">
                <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
              </div>
            </div>
            <div class="ml-4">
              <dt class="text-sm font-medium text-gray-500 dark:text-gray-400">Active Users</dt>
              <dd class="text-2xl font-semibold text-gray-900 dark:text-white">{{ stats.users?.active || 0 }}</dd>
            </div>
          </div>
        </div>

        <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div class="flex items-center">
            <div class="flex-shrink-0">
              <div class="w-8 h-8 bg-purple-500 rounded-md flex items-center justify-center">
                <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01"></path>
                </svg>
              </div>
            </div>
            <div class="ml-4">
              <dt class="text-sm font-medium text-gray-500 dark:text-gray-400">MCP Servers</dt>
              <dd class="text-2xl font-semibold text-gray-900 dark:text-white">{{ stats.mcp_servers?.total || 0 }}</dd>
            </div>
          </div>
        </div>

        <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div class="flex items-center">
            <div class="flex-shrink-0">
              <div class="w-8 h-8 bg-yellow-500 rounded-md flex items-center justify-center">
                <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
                </svg>
              </div>
            </div>
            <div class="ml-4">
              <dt class="text-sm font-medium text-gray-500 dark:text-gray-400">Running Servers</dt>
              <dd class="text-2xl font-semibold text-gray-900 dark:text-white">{{ stats.mcp_servers?.running || 0 }}</dd>
            </div>
          </div>
        </div>
      </div>

      <!-- Quick Actions -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        <!-- Quick Actions -->
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow">
          <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Quick Actions</h2>
          </div>
          <div class="p-6">
            <div class="grid grid-cols-2 gap-4">
              <router-link
                to="/admin/users"
                class="flex items-center justify-center px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-md text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
              >
                <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z"></path>
                </svg>
                Manage Users
              </router-link>

              <router-link
                to="/admin/roles"
                class="flex items-center justify-center px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-md text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
              >
                <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                </svg>
                Manage Roles
              </router-link>

              <router-link
                to="/admin/mcp-servers"
                class="flex items-center justify-center px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-md text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
              >
                <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01"></path>
                </svg>
                MCP Servers
              </router-link>

              <router-link
                to="/admin/audit"
                class="flex items-center justify-center px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-md text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
              >
                <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                </svg>
                Audit Logs
              </router-link>
            </div>
          </div>
        </div>

        <!-- Recent Activity -->
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow">
          <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Recent Activity</h2>
          </div>
          <div class="p-6">
            <div v-if="loading" class="text-center py-4">
              <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
            </div>
            <div v-else-if="recentLogs && recentLogs.length > 0" class="space-y-4">
              <div v-for="log in recentLogs" :key="log.id" class="flex items-start space-x-3">
                <div class="flex-shrink-0">
                  <div class="w-8 h-8 bg-gray-200 dark:bg-gray-600 rounded-full flex items-center justify-center">
                    <svg class="w-4 h-4 text-gray-600 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>
                  </div>
                </div>
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-medium text-gray-900 dark:text-white">
                    {{ log.username }}
                  </p>
                  <p class="text-sm text-gray-500 dark:text-gray-400">
                    {{ log.action }}: {{ log.details }}
                  </p>
                  <p class="text-xs text-gray-400 dark:text-gray-500">
                    {{ formatTimestamp(log.timestamp) }}
                  </p>
                </div>
              </div>
            </div>
            <div v-else class="text-center py-4 text-gray-500 dark:text-gray-400">
              No recent activity
            </div>
          </div>
        </div>
      </div>

      <!-- System Status -->
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow">
        <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white">System Status</h2>
        </div>
        <div class="p-6">
          <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div class="text-center">
              <div class="text-2xl font-bold text-green-500">{{ stats.users?.active || 0 }}</div>
              <div class="text-sm text-gray-600 dark:text-gray-400">Active Users</div>
            </div>
            <div class="text-center">
              <div class="text-2xl font-bold text-blue-500">{{ stats.mcp_servers?.running || 0 }}</div>
              <div class="text-sm text-gray-600 dark:text-gray-400">Running Servers</div>
            </div>
            <div class="text-center">
              <div class="text-2xl font-bold text-purple-500">{{ stats.recent_activity || 0 }}</div>
              <div class="text-sm text-gray-600 dark:text-gray-400">Recent Activities</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useToast } from '@/stores/toast'
import { apiService } from '@/services/api'

const toast = useToast()

// Reactive data
const loading = ref(true)
const stats = ref<any>({})
const recentLogs = ref<any[]>([])

// Fetch dashboard data
const fetchDashboardData = async () => {
  try {
    loading.value = true
    const response = await apiService.get('/admin/dashboard')
    
    if (response.success) {
      stats.value = response.stats
      recentLogs.value = response.recent_logs
    } else {
      toast.error('Failed to load dashboard data')
    }
  } catch (error) {
    console.error('Error fetching dashboard data:', error)
    toast.error('Failed to load dashboard data')
  } finally {
    loading.value = false
  }
}

// Format timestamp
const formatTimestamp = (timestamp: string) => {
  if (!timestamp) return ''
  return new Date(timestamp).toLocaleString()
}

// Load data on mount
onMounted(() => {
  fetchDashboardData()
})
</script>