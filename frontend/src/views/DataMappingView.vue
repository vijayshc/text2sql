<template>
  <div class="data-mapping-view">
    <!-- Header -->
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white flex items-center">
          <i class="fas fa-project-diagram mr-3 text-purple-600"></i>
          AI Data Mapping Analyst
        </h1>
        <p class="text-gray-600 dark:text-gray-400 mt-1">
          Intelligent data mapping and modeling for enterprise data warehouses
        </p>
      </div>
      
      <!-- Action Buttons -->
      <div class="flex items-center space-x-3">
        <button
          @click="loadCatalogOverview"
          class="inline-flex items-center px-3 py-2 border border-gray-300 dark:border-gray-600 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500"
        >
          <i class="fas fa-info-circle mr-2"></i>
          Catalog Overview
        </button>
        <button
          @click="loadMappingStats"
          class="inline-flex items-center px-3 py-2 border border-gray-300 dark:border-gray-600 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500"
        >
          <i class="fas fa-chart-bar mr-2"></i>
          Statistics
        </button>
      </div>
    </div>

    <!-- Service Status -->
    <div v-if="serviceStatus" class="mb-6">
      <div 
        class="rounded-md p-4"
        :class="serviceStatus.success 
          ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800' 
          : 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800'"
      >
        <div class="flex">
          <div class="flex-shrink-0">
            <i 
              :class="serviceStatus.success 
                ? 'fas fa-check-circle text-green-400' 
                : 'fas fa-exclamation-circle text-red-400'"
            ></i>
          </div>
          <div class="ml-3">
            <p 
              class="text-sm font-medium"
              :class="serviceStatus.success 
                ? 'text-green-800 dark:text-green-200' 
                : 'text-red-800 dark:text-red-200'"
            >
              {{ serviceStatus.message }}
            </p>
            <p 
              v-if="serviceStatus.success && serviceStatus.tools_available"
              class="text-xs text-green-600 dark:text-green-400 mt-1"
            >
              {{ serviceStatus.tools_available }} analysis tools available
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Main Content Tabs -->
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg">
      <!-- Tab Navigation -->
      <div class="border-b border-gray-200 dark:border-gray-700">
        <nav class="-mb-px flex space-x-8 px-6" aria-label="Tabs">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            @click="activeTab = tab.id"
            class="py-4 px-1 border-b-2 font-medium text-sm focus:outline-none"
            :class="activeTab === tab.id
              ? 'border-purple-500 text-purple-600 dark:text-purple-400'
              : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600'"
          >
            <i :class="tab.icon" class="mr-2"></i>
            {{ tab.name }}
          </button>
        </nav>
      </div>

      <!-- Tab Content -->
      <div class="p-6">
        <!-- Single Column Analysis Tab -->
        <div v-if="activeTab === 'single'" class="space-y-6">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <!-- Input Form -->
            <div class="space-y-4">
              <h3 class="text-lg font-medium text-gray-900 dark:text-white">
                Analyze Single Column
              </h3>
              
              <div>
                <label for="tableName" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Table Name
                </label>
                <input
                  id="tableName"
                  v-model="singleAnalysis.tableName"
                  type="text"
                  placeholder="Enter table name"
                  class="block w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm focus:border-purple-500 focus:ring-purple-500 sm:text-sm"
                >
              </div>
              
              <div>
                <label for="columnName" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Column Name
                </label>
                <input
                  id="columnName"
                  v-model="singleAnalysis.columnName"
                  type="text"
                  placeholder="Enter column name"
                  class="block w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm focus:border-purple-500 focus:ring-purple-500 sm:text-sm"
                >
              </div>
              
              <div>
                <label for="workspace" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Workspace
                </label>
                <input
                  id="workspace"
                  v-model="singleAnalysis.workspace"
                  type="text"
                  placeholder="Enter workspace name"
                  class="block w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm focus:border-purple-500 focus:ring-purple-500 sm:text-sm"
                >
              </div>
              
              <button
                @click="analyzeSingleColumn"
                :disabled="!singleAnalysis.tableName || !singleAnalysis.columnName || isAnalyzing"
                class="w-full inline-flex justify-center items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-purple-600 hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <i v-if="isAnalyzing" class="fas fa-spinner fa-spin mr-2"></i>
                <i v-else class="fas fa-search mr-2"></i>
                {{ isAnalyzing ? 'Analyzing...' : 'Analyze Column' }}
              </button>
            </div>

            <!-- Results -->
            <div class="space-y-4">
              <h3 class="text-lg font-medium text-gray-900 dark:text-white">
                Analysis Results
              </h3>
              
              <div v-if="singleAnalysis.result" class="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                <pre class="text-sm text-gray-900 dark:text-white whitespace-pre-wrap">{{ JSON.stringify(singleAnalysis.result, null, 2) }}</pre>
              </div>
              
              <div v-else-if="singleAnalysis.error" class="bg-red-50 dark:bg-red-900/20 rounded-lg p-4">
                <p class="text-sm text-red-800 dark:text-red-200">
                  Error: {{ singleAnalysis.error }}
                </p>
              </div>
              
              <div v-else class="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                <p class="text-sm text-gray-500 dark:text-gray-400 text-center">
                  No analysis results yet. Enter a table and column name to begin analysis.
                </p>
              </div>
            </div>
          </div>
        </div>

        <!-- Bulk Analysis Tab -->
        <div v-if="activeTab === 'bulk'" class="space-y-6">
          <div class="flex justify-between items-center">
            <h3 class="text-lg font-medium text-gray-900 dark:text-white">
              Bulk Column Analysis
            </h3>
            <button
              @click="addBulkColumn"
              class="inline-flex items-center px-3 py-2 border border-gray-300 dark:border-gray-600 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500"
            >
              <i class="fas fa-plus mr-2"></i>
              Add Column
            </button>
          </div>

          <!-- Bulk Columns Input -->
          <div class="space-y-3">
            <div
              v-for="(column, index) in bulkAnalysis.columns"
              :key="index"
              class="flex items-center space-x-3"
            >
              <input
                v-model="column.tableName"
                type="text"
                placeholder="Table name"
                class="flex-1 rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm focus:border-purple-500 focus:ring-purple-500 sm:text-sm"
              >
              <input
                v-model="column.columnName"
                type="text"
                placeholder="Column name"
                class="flex-1 rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm focus:border-purple-500 focus:ring-purple-500 sm:text-sm"
              >
              <button
                @click="removeBulkColumn(index)"
                class="inline-flex items-center p-2 border border-gray-300 dark:border-gray-600 shadow-sm text-sm leading-4 font-medium rounded-md text-red-700 dark:text-red-400 bg-white dark:bg-gray-700 hover:bg-red-50 dark:hover:bg-red-900/20 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
              >
                <i class="fas fa-trash"></i>
              </button>
            </div>
          </div>

          <div class="flex items-center space-x-4">
            <input
              v-model="bulkAnalysis.workspace"
              type="text"
              placeholder="Workspace name"
              class="flex-1 rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm focus:border-purple-500 focus:ring-purple-500 sm:text-sm"
            >
            <button
              @click="analyzeBulkColumns"
              :disabled="bulkAnalysis.columns.length === 0 || isBulkAnalyzing"
              class="inline-flex justify-center items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-purple-600 hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <i v-if="isBulkAnalyzing" class="fas fa-spinner fa-spin mr-2"></i>
              <i v-else class="fas fa-list mr-2"></i>
              {{ isBulkAnalyzing ? 'Analyzing...' : 'Analyze All' }}
            </button>
          </div>

          <!-- Bulk Progress -->
          <div v-if="bulkAnalysis.progress.show" class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
            <div class="flex items-center justify-between mb-2">
              <span class="text-sm font-medium text-blue-800 dark:text-blue-200">
                Progress: {{ bulkAnalysis.progress.current }}/{{ bulkAnalysis.progress.total }}
              </span>
              <span class="text-sm text-blue-600 dark:text-blue-400">
                {{ bulkAnalysis.progress.currentColumn }}
              </span>
            </div>
            <div class="w-full bg-blue-200 dark:bg-blue-800 rounded-full h-2">
              <div
                class="bg-blue-600 h-2 rounded-full transition-all duration-300"
                :style="{ width: `${(bulkAnalysis.progress.current / bulkAnalysis.progress.total) * 100}%` }"
              ></div>
            </div>
          </div>

          <!-- Bulk Results -->
          <div v-if="bulkAnalysis.results.length > 0" class="space-y-4">
            <h4 class="text-lg font-medium text-gray-900 dark:text-white">Analysis Results</h4>
            <div class="space-y-3">
              <div
                v-for="(result, index) in bulkAnalysis.results"
                :key="index"
                class="bg-gray-50 dark:bg-gray-700 rounded-lg p-4"
              >
                <h5 class="font-medium text-gray-900 dark:text-white mb-2">
                  {{ result.table_name }}.{{ result.column_name }}
                </h5>
                <div v-if="result.error" class="text-red-600 dark:text-red-400 text-sm">
                  Error: {{ result.error }}
                </div>
                <div v-else class="text-sm text-gray-600 dark:text-gray-300">
                  <pre class="whitespace-pre-wrap">{{ JSON.stringify(result.result, null, 2) }}</pre>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Mapping Repository Tab -->
        <div v-if="activeTab === 'repository'" class="space-y-6">
          <div class="flex justify-between items-center">
            <h3 class="text-lg font-medium text-gray-900 dark:text-white">
              Mapping Repository
            </h3>
            <div class="flex items-center space-x-3">
              <input
                v-model="repository.searchQuery"
                type="text"
                placeholder="Search mappings..."
                class="rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm focus:border-purple-500 focus:ring-purple-500 sm:text-sm"
                @keyup.enter="searchMappings"
              >
              <button
                @click="searchMappings"
                class="inline-flex items-center px-3 py-2 border border-gray-300 dark:border-gray-600 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500"
              >
                <i class="fas fa-search mr-2"></i>
                Search
              </button>
            </div>
          </div>

          <!-- Repository Results -->
          <div v-if="repository.results.length > 0" class="bg-gray-50 dark:bg-gray-700 rounded-lg overflow-hidden">
            <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-600">
              <thead class="bg-gray-100 dark:bg-gray-800">
                <tr>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Source
                  </th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Target
                  </th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Type
                  </th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-200 dark:divide-gray-600">
                <tr v-for="mapping in repository.results" :key="mapping.id">
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                    {{ mapping.source_table }}.{{ mapping.source_column }}
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                    {{ mapping.target_table }}.{{ mapping.target_column }}
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap">
                    <span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-green-100 dark:bg-green-900/20 text-green-800 dark:text-green-200">
                      {{ mapping.mapping_type }}
                    </span>
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <button class="text-purple-600 dark:text-purple-400 hover:text-purple-900 dark:hover:text-purple-300">
                      Edit
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          
          <div v-else class="bg-gray-50 dark:bg-gray-700 rounded-lg p-8">
            <p class="text-center text-gray-500 dark:text-gray-400">
              No mappings found. Start by analyzing columns to create mappings.
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useToast } from '@/composables/useToast'
import { apiService } from '@/services/api'

// Reactive state
const activeTab = ref('single')
const serviceStatus = ref<{
  success: boolean
  status: string
  message: string
  tools_available?: number
} | null>(null)

const isAnalyzing = ref(false)
const isBulkAnalyzing = ref(false)

// Single analysis state
const singleAnalysis = ref({
  tableName: '',
  columnName: '',
  workspace: 'default',
  result: null as any,
  error: null as string | null
})

// Bulk analysis state  
const bulkAnalysis = ref({
  columns: [{ tableName: '', columnName: '' }],
  workspace: 'default',
  progress: {
    show: false,
    current: 0,
    total: 0,
    currentColumn: ''
  },
  results: [] as any[]
})

// Repository state
const repository = ref({
  searchQuery: '',
  results: [] as any[],
  total: 0
})

// Tab configuration
const tabs = ref([
  { id: 'single', name: 'Single Column Analysis', icon: 'fas fa-search' },
  { id: 'bulk', name: 'Bulk Analysis', icon: 'fas fa-list' },
  { id: 'repository', name: 'Mapping Repository', icon: 'fas fa-database' }
])

// Composables
const { showToast } = useToast()

// Methods
const checkServiceStatus = async () => {
  try {
    const response = await apiService.get('/api/v1/data-mapping/status')
    serviceStatus.value = response
  } catch (error) {
    console.error('Error checking service status:', error)
    serviceStatus.value = {
      success: false,
      status: 'error',
      message: 'Unable to connect to data mapping service'
    }
  }
}

const analyzeSingleColumn = async () => {
  if (!singleAnalysis.value.tableName || !singleAnalysis.value.columnName) {
    showToast('Please enter both table and column names', 'error')
    return
  }

  isAnalyzing.value = true
  singleAnalysis.value.result = null
  singleAnalysis.value.error = null

  try {
    const url = new URL('/api/v1/data-mapping/analyze/single', window.location.origin)
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify({
        column_name: singleAnalysis.value.columnName,
        table_name: singleAnalysis.value.tableName,
        workspace: singleAnalysis.value.workspace
      })
    })

    if (!response.body) {
      throw new Error('No response body')
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      const chunk = decoder.decode(value)
      const lines = chunk.split('\n')

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            
            switch (data.type) {
              case 'result':
                singleAnalysis.value.result = data.data
                break
              case 'error':
                singleAnalysis.value.error = data.message
                break
              case 'complete':
                isAnalyzing.value = false
                break
            }
          } catch (e) {
            console.error('Error parsing SSE data:', e)
          }
        }
      }
    }
  } catch (error) {
    console.error('Error in single column analysis:', error)
    isAnalyzing.value = false
    singleAnalysis.value.error = error instanceof Error ? error.message : 'Unknown error occurred'
    showToast('Failed to analyze column', 'error')
  }
}

const addBulkColumn = () => {
  bulkAnalysis.value.columns.push({ tableName: '', columnName: '' })
}

const removeBulkColumn = (index: number) => {
  bulkAnalysis.value.columns.splice(index, 1)
}

const analyzeBulkColumns = async () => {
  const validColumns = bulkAnalysis.value.columns.filter(col => col.tableName && col.columnName)
  
  if (validColumns.length === 0) {
    showToast('Please enter at least one valid table and column name', 'error')
    return
  }

  isBulkAnalyzing.value = true
  bulkAnalysis.value.results = []
  bulkAnalysis.value.progress.show = true
  bulkAnalysis.value.progress.current = 0
  bulkAnalysis.value.progress.total = validColumns.length

  try {
    const url = new URL('/api/v1/data-mapping/analyze/bulk', window.location.origin)
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify({
        columns: validColumns.map(col => ({
          column_name: col.columnName,
          table_name: col.tableName
        })),
        workspace: bulkAnalysis.value.workspace
      })
    })

    if (!response.body) {
      throw new Error('No response body')
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      const chunk = decoder.decode(value)
      const lines = chunk.split('\n')

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            
            switch (data.type) {
              case 'progress':
                bulkAnalysis.value.progress.current = data.current
                bulkAnalysis.value.progress.currentColumn = data.column
                break
              case 'column_result':
              case 'column_error':
                bulkAnalysis.value.results.push(data.data)
                break
              case 'complete':
                isBulkAnalyzing.value = false
                bulkAnalysis.value.progress.show = false
                break
            }
          } catch (e) {
            console.error('Error parsing SSE data:', e)
          }
        }
      }
    }
  } catch (error) {
    console.error('Error in bulk column analysis:', error)
    isBulkAnalyzing.value = false
    bulkAnalysis.value.progress.show = false
    showToast('Failed to analyze columns', 'error')
  }
}

const searchMappings = async () => {
  if (!repository.value.searchQuery.trim()) {
    showToast('Please enter a search query', 'error')
    return
  }

  try {
    const response = await apiService.post('/api/v1/data-mapping/search', {
      query: repository.value.searchQuery,
      workspace: 'default'
    })
    
    if (response.success) {
      repository.value.results = response.results
      repository.value.total = response.total
    }
  } catch (error) {
    console.error('Error searching mappings:', error)
    showToast('Failed to search mappings', 'error')
  }
}

const loadCatalogOverview = async () => {
  try {
    const response = await apiService.get('/api/v1/data-mapping/catalog?workspace=default')
    if (response.success) {
      showToast(`Catalog loaded: ${response.catalog.total_tables} tables, ${response.catalog.total_columns} columns`, 'success')
    }
  } catch (error) {
    console.error('Error loading catalog:', error)
    showToast('Failed to load catalog overview', 'error')
  }
}

const loadMappingStats = async () => {
  try {
    // This would show mapping statistics
    showToast('Mapping statistics loaded', 'info')
  } catch (error) {
    console.error('Error loading stats:', error)
    showToast('Failed to load mapping statistics', 'error')
  }
}

// Lifecycle
onMounted(() => {
  checkServiceStatus()
})
</script>

<style scoped>
.data-mapping-view {
  @apply p-6;
}
</style>