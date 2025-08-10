<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-900">
    <!-- Header -->
    <div class="bg-white dark:bg-gray-800 shadow">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="py-6">
          <div class="flex justify-between items-center">
            <div>
              <h1 class="text-3xl font-bold text-gray-900 dark:text-white">
                MCP Server Management
              </h1>
              <p class="mt-2 text-gray-600 dark:text-gray-400">
                Manage Model Context Protocol servers and their configurations
              </p>
            </div>
            <button
              @click="showCreateServer = true"
              class="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors"
            >
              Add Server
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Content -->
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <!-- Servers Table -->
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow">
        <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white">MCP Servers</h2>
        </div>
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead class="bg-gray-50 dark:bg-gray-700">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Server
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Type
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Status
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Created
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody class="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
              <tr v-if="loading">
                <td colspan="5" class="px-6 py-4 text-center">
                  <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
                </td>
              </tr>
              <tr v-else-if="servers.length === 0">
                <td colspan="5" class="px-6 py-4 text-center text-gray-500 dark:text-gray-400">
                  No MCP servers found
                </td>
              </tr>
              <tr v-else v-for="server in servers" :key="server.id" class="hover:bg-gray-50 dark:hover:bg-gray-700">
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="flex items-center">
                    <div class="flex-shrink-0 h-10 w-10">
                      <div class="h-10 w-10 rounded-full bg-purple-100 dark:bg-purple-900 flex items-center justify-center">
                        <svg class="w-5 h-5 text-purple-600 dark:text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01"></path>
                        </svg>
                      </div>
                    </div>
                    <div class="ml-4">
                      <div class="text-sm font-medium text-gray-900 dark:text-white">
                        {{ server.name }}
                      </div>
                      <div class="text-sm text-gray-500 dark:text-gray-400">
                        {{ server.description || 'No description' }}
                      </div>
                    </div>
                  </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200">
                    {{ server.server_type }}
                  </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <span
                    :class="[
                      'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
                      getStatusColor(server.status)
                    ]"
                  >
                    <div class="w-1.5 h-1.5 rounded-full mr-1" :class="getStatusDotColor(server.status)"></div>
                    {{ server.status }}
                  </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                  {{ formatDate(server.created_at) }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                  <div class="flex space-x-2">
                    <button
                      v-if="server.status !== 'running'"
                      @click="startServer(server)"
                      :disabled="startingServer === server.id"
                      class="text-green-600 hover:text-green-900 dark:text-green-400 dark:hover:text-green-300 disabled:opacity-50"
                    >
                      {{ startingServer === server.id ? 'Starting...' : 'Start' }}
                    </button>
                    <button
                      v-if="server.status === 'running'"
                      @click="stopServer(server)"
                      :disabled="stoppingServer === server.id"
                      class="text-yellow-600 hover:text-yellow-900 dark:text-yellow-400 dark:hover:text-yellow-300 disabled:opacity-50"
                    >
                      {{ stoppingServer === server.id ? 'Stopping...' : 'Stop' }}
                    </button>
                    <button
                      @click="viewServerConfig(server)"
                      class="text-blue-600 hover:text-blue-900 dark:text-blue-400 dark:hover:text-blue-300"
                    >
                      Config
                    </button>
                    <button
                      @click="deleteServer(server)"
                      :disabled="server.status === 'running'"
                      :class="[
                        'transition-colors',
                        server.status === 'running'
                          ? 'text-gray-400 cursor-not-allowed'
                          : 'text-red-600 hover:text-red-900 dark:text-red-400 dark:hover:text-red-300'
                      ]"
                      :title="server.status === 'running' ? 'Stop server before deleting' : 'Delete server'"
                    >
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Create Server Modal -->
    <div
      v-if="showCreateServer"
      class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50"
      @click="showCreateServer = false"
    >
      <div class="relative top-20 mx-auto p-5 border w-[32rem] shadow-lg rounded-md bg-white dark:bg-gray-800" @click.stop>
        <div class="mt-3">
          <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-4">Add New MCP Server</h3>
          <form @submit.prevent="createServer">
            <div class="mb-4">
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Server Name
              </label>
              <input
                v-model="newServer.name"
                type="text"
                required
                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                placeholder="Enter server name"
              />
            </div>
            <div class="mb-4">
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Description
              </label>
              <textarea
                v-model="newServer.description"
                rows="2"
                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                placeholder="Enter server description (optional)"
              ></textarea>
            </div>
            <div class="mb-4">
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Server Type
              </label>
              <select
                v-model="newServer.server_type"
                required
                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
              >
                <option value="">Select server type</option>
                <option value="python">Python</option>
                <option value="nodejs">Node.js</option>
                <option value="executable">Executable</option>
                <option value="stdio">Standard I/O</option>
              </select>
            </div>
            <div class="mb-6">
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Configuration (JSON)
              </label>
              <textarea
                v-model="configJson"
                rows="6"
                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white font-mono text-sm"
                placeholder='{"command": ["python", "server.py"], "args": ["--port", "8080"]}'
              ></textarea>
              <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
                Enter server configuration as JSON
              </p>
            </div>
            <div class="flex justify-end space-x-3">
              <button
                type="button"
                @click="showCreateServer = false"
                class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-600 rounded-md hover:bg-gray-200 dark:hover:bg-gray-700"
              >
                Cancel
              </button>
              <button
                type="submit"
                :disabled="creatingServer"
                class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {{ creatingServer ? 'Creating...' : 'Create Server' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- Server Config Modal -->
    <div
      v-if="showServerConfig"
      class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50"
      @click="showServerConfig = false"
    >
      <div class="relative top-20 mx-auto p-5 border w-[32rem] shadow-lg rounded-md bg-white dark:bg-gray-800" @click.stop>
        <div class="mt-3">
          <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-4">
            Server Configuration - {{ selectedServer?.name }}
          </h3>
          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Server Type
              </label>
              <div class="text-sm text-gray-900 dark:text-white">{{ selectedServer?.server_type }}</div>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Configuration
              </label>
              <pre class="text-sm bg-gray-100 dark:bg-gray-700 p-3 rounded-md overflow-x-auto text-gray-900 dark:text-white">{{ formatConfig(selectedServer?.config) }}</pre>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Status
              </label>
              <span
                :class="[
                  'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
                  getStatusColor(selectedServer?.status)
                ]"
              >
                <div class="w-1.5 h-1.5 rounded-full mr-1" :class="getStatusDotColor(selectedServer?.status)"></div>
                {{ selectedServer?.status }}
              </span>
            </div>
          </div>
          <div class="flex justify-end mt-6">
            <button
              @click="showServerConfig = false"
              class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-600 rounded-md hover:bg-gray-200 dark:hover:bg-gray-700"
            >
              Close
            </button>
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
const servers = ref<any[]>([])
const showCreateServer = ref(false)
const showServerConfig = ref(false)
const creatingServer = ref(false)
const startingServer = ref<number | null>(null)
const stoppingServer = ref<number | null>(null)
const selectedServer = ref<any>(null)

const newServer = ref({
  name: '',
  description: '',
  server_type: '',
  config: {}
})

const configJson = ref('')

// Fetch servers
const fetchServers = async () => {
  try {
    loading.value = true
    const response = await apiService.get('/admin/mcp-servers')
    
    if (response.success) {
      servers.value = response.servers
    } else {
      toast.error('Failed to load MCP servers')
    }
  } catch (error) {
    console.error('Error fetching servers:', error)
    toast.error('Failed to load MCP servers')
  } finally {
    loading.value = false
  }
}

// Create server
const createServer = async () => {
  try {
    // Parse JSON config
    let config = {}
    if (configJson.value.trim()) {
      try {
        config = JSON.parse(configJson.value)
      } catch (e) {
        toast.error('Invalid JSON configuration')
        return
      }
    }
    
    creatingServer.value = true
    const response = await apiService.post('/admin/mcp-servers', {
      ...newServer.value,
      config
    })
    
    if (response.success) {
      toast.success('MCP server created successfully')
      showCreateServer.value = false
      newServer.value = { name: '', description: '', server_type: '', config: {} }
      configJson.value = ''
      await fetchServers()
    } else {
      toast.error(response.error || 'Failed to create MCP server')
    }
  } catch (error) {
    console.error('Error creating server:', error)
    toast.error('Failed to create MCP server')
  } finally {
    creatingServer.value = false
  }
}

// Start server
const startServer = async (server: any) => {
  try {
    startingServer.value = server.id
    const response = await apiService.post(`/admin/mcp-servers/${server.id}/start`)
    
    if (response.success) {
      toast.success(`Server ${server.name} started successfully`)
      await fetchServers()
    } else {
      toast.error(response.error || 'Failed to start server')
    }
  } catch (error) {
    console.error('Error starting server:', error)
    toast.error('Failed to start server')
  } finally {
    startingServer.value = null
  }
}

// Stop server
const stopServer = async (server: any) => {
  try {
    stoppingServer.value = server.id
    const response = await apiService.post(`/admin/mcp-servers/${server.id}/stop`)
    
    if (response.success) {
      toast.success(`Server ${server.name} stopped successfully`)
      await fetchServers()
    } else {
      toast.error(response.error || 'Failed to stop server')
    }
  } catch (error) {
    console.error('Error stopping server:', error)
    toast.error('Failed to stop server')
  } finally {
    stoppingServer.value = null
  }
}

// Delete server
const deleteServer = async (server: any) => {
  if (server.status === 'running') {
    toast.error('Stop the server before deleting')
    return
  }
  
  if (!confirm(`Are you sure you want to delete server "${server.name}"?`)) {
    return
  }
  
  try {
    const response = await apiService.delete(`/admin/mcp-servers/${server.id}`)
    
    if (response.success) {
      toast.success('Server deleted successfully')
      await fetchServers()
    } else {
      toast.error(response.error || 'Failed to delete server')
    }
  } catch (error) {
    console.error('Error deleting server:', error)
    toast.error('Failed to delete server')
  }
}

// View server config
const viewServerConfig = (server: any) => {
  selectedServer.value = server
  showServerConfig.value = true
}

// Get status color
const getStatusColor = (status: string) => {
  switch (status) {
    case 'running':
      return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
    case 'stopped':
      return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
    case 'error':
      return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
    default:
      return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
  }
}

// Get status dot color
const getStatusDotColor = (status: string) => {
  switch (status) {
    case 'running':
      return 'bg-green-400'
    case 'stopped':
      return 'bg-gray-400'
    case 'error':
      return 'bg-red-400'
    default:
      return 'bg-yellow-400'
  }
}

// Format config for display
const formatConfig = (config: any) => {
  if (!config) return 'No configuration'
  return JSON.stringify(config, null, 2)
}

// Format date
const formatDate = (date: string) => {
  if (!date) return ''
  return new Date(date).toLocaleDateString()
}

// Load data on mount
onMounted(() => {
  fetchServers()
})
</script>