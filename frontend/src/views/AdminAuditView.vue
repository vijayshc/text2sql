<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-900">
    <!-- Header -->
    <div class="bg-white dark:bg-gray-800 shadow">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="py-6">
          <div class="flex justify-between items-center">
            <div>
              <h1 class="text-3xl font-bold text-gray-900 dark:text-white">
                Audit Logs
              </h1>
              <p class="mt-2 text-gray-600 dark:text-gray-400">
                Monitor system activity and user actions
              </p>
            </div>
            <button
              @click="exportLogs"
              :disabled="exporting"
              class="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 transition-colors disabled:opacity-50"
            >
              {{ exporting ? 'Exporting...' : 'Export CSV' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Content -->
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <!-- Filters -->
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow mb-6 p-6">
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Filters</h2>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Action
            </label>
            <select
              v-model="filters.action"
              @change="applyFilters"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
            >
              <option value="">All Actions</option>
              <option value="login">Login</option>
              <option value="logout">Logout</option>
              <option value="create_user">Create User</option>
              <option value="update_user">Update User</option>
              <option value="delete_user">Delete User</option>
              <option value="create_role">Create Role</option>
              <option value="update_role">Update Role</option>
              <option value="delete_role">Delete Role</option>
              <option value="change_password">Change Password</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              User
            </label>
            <input
              v-model="filters.user_id"
              @input="applyFilters"
              type="number"
              placeholder="User ID"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Per Page
            </label>
            <select
              v-model="pagination.perPage"
              @change="applyFilters"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
            >
              <option value="25">25</option>
              <option value="50">50</option>
              <option value="100">100</option>
            </select>
          </div>
        </div>
      </div>

      <!-- Audit Logs Table -->
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow">
        <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Audit Logs</h2>
        </div>
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead class="bg-gray-50 dark:bg-gray-700">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Timestamp
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  User
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Action
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Details
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  IP Address
                </th>
              </tr>
            </thead>
            <tbody class="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
              <tr v-if="loading">
                <td colspan="5" class="px-6 py-4 text-center">
                  <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
                </td>
              </tr>
              <tr v-else-if="logs.length === 0">
                <td colspan="5" class="px-6 py-4 text-center text-gray-500 dark:text-gray-400">
                  No audit logs found
                </td>
              </tr>
              <tr v-else v-for="log in logs" :key="log.id" class="hover:bg-gray-50 dark:hover:bg-gray-700">
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                  {{ formatTimestamp(log.timestamp) }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="flex items-center">
                    <div class="flex-shrink-0 h-8 w-8">
                      <div class="h-8 w-8 rounded-full bg-gray-300 dark:bg-gray-600 flex items-center justify-center">
                        <span class="text-xs font-medium text-gray-700 dark:text-gray-300">
                          {{ log.username?.charAt(0).toUpperCase() || '?' }}
                        </span>
                      </div>
                    </div>
                    <div class="ml-3">
                      <div class="text-sm font-medium text-gray-900 dark:text-white">
                        {{ log.username || 'Unknown' }}
                      </div>
                      <div class="text-sm text-gray-500 dark:text-gray-400">
                        ID: {{ log.user_id }}
                      </div>
                    </div>
                  </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <span
                    :class="[
                      'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
                      getActionColor(log.action)
                    ]"
                  >
                    {{ formatAction(log.action) }}
                  </span>
                </td>
                <td class="px-6 py-4 text-sm text-gray-900 dark:text-white">
                  <div class="max-w-xs truncate" :title="log.details">
                    {{ log.details }}
                  </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                  {{ log.ip_address }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Pagination -->
        <div class="px-6 py-4 border-t border-gray-200 dark:border-gray-700">
          <div class="flex items-center justify-between">
            <div class="text-sm text-gray-700 dark:text-gray-300">
              Page {{ pagination.page }} ({{ logs.length }} {{ logs.length === 1 ? 'entry' : 'entries' }})
            </div>
            <div class="flex space-x-2">
              <button
                @click="goToPage(pagination.page - 1)"
                :disabled="pagination.page <= 1"
                class="px-3 py-1 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-600 rounded-md hover:bg-gray-200 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              <button
                @click="goToPage(pagination.page + 1)"
                :disabled="!pagination.hasNext"
                class="px-3 py-1 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-600 rounded-md hover:bg-gray-200 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
              </button>
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
const exporting = ref(false)
const logs = ref<any[]>([])

const filters = ref({
  action: '',
  user_id: ''
})

const pagination = ref({
  page: 1,
  perPage: 50,
  hasNext: false
})

// Fetch audit logs
const fetchLogs = async (page = 1) => {
  try {
    loading.value = true
    
    const params = new URLSearchParams({
      page: page.toString(),
      per_page: pagination.value.perPage.toString()
    })
    
    if (filters.value.action) {
      params.append('action', filters.value.action)
    }
    
    if (filters.value.user_id) {
      params.append('user_id', filters.value.user_id)
    }
    
    const response = await apiService.get(`/admin/audit-logs?${params}`)
    
    if (response.success) {
      logs.value = response.logs
      pagination.value.page = response.pagination.page
      pagination.value.hasNext = response.pagination.has_next
    } else {
      toast.error('Failed to load audit logs')
    }
  } catch (error) {
    console.error('Error fetching logs:', error)
    toast.error('Failed to load audit logs')
  } finally {
    loading.value = false
  }
}

// Apply filters
const applyFilters = () => {
  pagination.value.page = 1
  fetchLogs(1)
}

// Go to page
const goToPage = (page: number) => {
  if (page >= 1) {
    fetchLogs(page)
  }
}

// Export logs
const exportLogs = async () => {
  try {
    exporting.value = true
    
    const response = await fetch('/api/v1/admin/audit-logs/export', {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      }
    })
    
    if (response.ok) {
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `audit_logs_${new Date().toISOString().split('T')[0]}.csv`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
      toast.success('Audit logs exported successfully')
    } else {
      toast.error('Failed to export audit logs')
    }
  } catch (error) {
    console.error('Error exporting logs:', error)
    toast.error('Failed to export audit logs')
  } finally {
    exporting.value = false
  }
}

// Get action color
const getActionColor = (action: string) => {
  if (action.includes('login')) {
    return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
  } else if (action.includes('logout')) {
    return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
  } else if (action.includes('create')) {
    return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
  } else if (action.includes('update')) {
    return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
  } else if (action.includes('delete')) {
    return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
  } else {
    return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200'
  }
}

// Format action for display
const formatAction = (action: string) => {
  return action.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

// Format timestamp
const formatTimestamp = (timestamp: string) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleString()
}

// Load data on mount
onMounted(() => {
  fetchLogs()
})
</script>