<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { useToast } from '@/stores/toast'
import { apiRequest } from '@/services/api'

interface SchemaObject {
  name: string
  type: 'table' | 'view' | 'index'
  columns?: Column[]
  expanded?: boolean
}

interface Column {
  name: string
  type: string
  nullable: boolean
  primary_key: boolean
}

interface QueryResult {
  columns: string[]
  rows: any[]
  rowCount: number
  executionTime: number
  message?: string
}

const toast = useToast()

// Reactive state
const sqlQuery = ref('')
const queryResults = ref<QueryResult | null>(null)
const schemaObjects = ref<SchemaObject[]>([])
const schemaLoading = ref(true)
const queryExecuting = ref(false)
const schemaSearchQuery = ref('')

// Editor state
const editorElement = ref<HTMLElement | null>(null)
const editorInitialized = ref(false)

// Computed
const filteredSchemaObjects = ref<SchemaObject[]>([])

// Watch schema search
const filterSchema = () => {
  if (!schemaSearchQuery.value.trim()) {
    filteredSchemaObjects.value = schemaObjects.value
  } else {
    const query = schemaSearchQuery.value.toLowerCase()
    filteredSchemaObjects.value = schemaObjects.value.filter(obj =>
      obj.name.toLowerCase().includes(query) ||
      obj.columns?.some(col => col.name.toLowerCase().includes(query))
    )
  }
}

// API calls
const loadSchema = async () => {
  try {
    schemaLoading.value = true
    const response = await apiRequest('/api/v1/admin/database/schema')
    schemaObjects.value = response.objects.map((obj: SchemaObject) => ({
      ...obj,
      expanded: false
    }))
    filteredSchemaObjects.value = schemaObjects.value
  } catch (error) {
    toast.error('Failed to load database schema: ' + (error as Error).message)
  } finally {
    schemaLoading.value = false
  }
}

const executeQuery = async () => {
  if (!sqlQuery.value.trim()) {
    toast.error('Please enter a SQL query')
    return
  }

  try {
    queryExecuting.value = true
    queryResults.value = null

    const response = await apiRequest('/api/v1/admin/database/execute', {
      method: 'POST',
      body: JSON.stringify({
        query: sqlQuery.value
      })
    })

    queryResults.value = response.result
    
    if (response.result.message) {
      toast.success(response.result.message)
    } else {
      toast.success(`Query executed successfully. ${response.result.rowCount} rows returned in ${response.result.executionTime}ms.`)
    }
  } catch (error) {
    toast.error('Query execution failed: ' + (error as Error).message)
  } finally {
    queryExecuting.value = false
  }
}

const clearQuery = () => {
  sqlQuery.value = ''
  queryResults.value = null
}

const formatSql = () => {
  // Basic SQL formatting - in a real app, you'd use a proper SQL formatter
  if (!sqlQuery.value.trim()) return
  
  const formatted = sqlQuery.value
    .replace(/\s+/g, ' ')
    .replace(/\b(SELECT|FROM|WHERE|JOIN|INNER JOIN|LEFT JOIN|RIGHT JOIN|GROUP BY|ORDER BY|HAVING|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER)\b/gi, '\n$1')
    .replace(/,/g, ',\n  ')
    .trim()
  
  sqlQuery.value = formatted
}

const insertTableName = (tableName: string) => {
  const currentPos = sqlQuery.value.length
  sqlQuery.value = sqlQuery.value.substring(0, currentPos) + tableName + ' '
}

const generateSelectQuery = (table: SchemaObject) => {
  if (!table.columns || table.columns.length === 0) {
    sqlQuery.value = `SELECT * FROM ${table.name};`
  } else {
    const columns = table.columns.slice(0, 5).map(col => col.name).join(',\n  ')
    sqlQuery.value = `SELECT ${columns}\nFROM ${table.name}\nLIMIT 100;`
  }
}

const expandTable = async (table: SchemaObject) => {
  if (table.columns) {
    table.expanded = !table.expanded
    return
  }

  try {
    const response = await apiRequest(`/api/v1/admin/database/schema/${table.name}`)
    table.columns = response.columns
    table.expanded = true
  } catch (error) {
    toast.error('Failed to load table columns: ' + (error as Error).message)
  }
}

const copyToClipboard = async () => {
  try {
    await navigator.clipboard.writeText(sqlQuery.value)
    toast.success('Query copied to clipboard')
  } catch (error) {
    toast.error('Failed to copy to clipboard')
  }
}

const exportResults = () => {
  if (!queryResults.value || queryResults.value.rows.length === 0) {
    toast.error('No results to export')
    return
  }

  // Convert results to CSV
  const headers = queryResults.value.columns.join(',')
  const rows = queryResults.value.rows.map(row => 
    queryResults.value!.columns.map(col => {
      const value = row[col]
      // Escape commas and quotes in CSV
      if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
        return `"${value.replace(/"/g, '""')}"`
      }
      return value
    }).join(',')
  )
  
  const csvContent = [headers, ...rows].join('\n')
  
  // Download CSV file
  const blob = new Blob([csvContent], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `query_results_${new Date().toISOString().split('T')[0]}.csv`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
  
  toast.success('Results exported to CSV')
}

const handleKeydown = (event: KeyboardEvent) => {
  if (event.ctrlKey && event.key === 'Enter') {
    event.preventDefault()
    executeQuery()
  }
}

// Lifecycle
onMounted(async () => {
  await loadSchema()
  
  // Set up keyboard listener
  document.addEventListener('keydown', handleKeydown)
  
  // Initialize SQL editor (basic textarea for now)
  nextTick(() => {
    editorInitialized.value = true
  })
})

// Cleanup
onMounted(() => {
  return () => {
    document.removeEventListener('keydown', handleKeydown)
  }
})
</script>

<template>
  <div class="p-6 max-w-full">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6">
      <div class="flex items-center mb-4 sm:mb-0">
        <i class="fas fa-terminal text-2xl text-green-600 mr-3"></i>
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Database Query Editor</h1>
      </div>
      <div class="flex flex-wrap gap-2">
        <button 
          @click="executeQuery"
          :disabled="queryExecuting || !sqlQuery.trim()"
          class="btn btn-primary"
        >
          <i v-if="queryExecuting" class="fas fa-spinner fa-spin mr-2"></i>
          <i v-else class="fas fa-play mr-2"></i>
          {{ queryExecuting ? 'Executing...' : 'Execute Query' }}
        </button>
        <button 
          @click="clearQuery"
          class="btn btn-outline-secondary"
        >
          <i class="fas fa-eraser mr-2"></i>Clear
        </button>
      </div>
    </div>

    <div class="grid grid-cols-1 xl:grid-cols-4 gap-6">
      <!-- Schema Browser -->
      <div class="xl:col-span-1">
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
          <div class="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
            <div class="flex justify-between items-center">
              <h3 class="text-lg font-medium text-gray-900 dark:text-white">Database Objects</h3>
              <button
                @click="loadSchema"
                class="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                title="Refresh Schema"
              >
                <i class="fas fa-sync-alt"></i>
              </button>
            </div>
          </div>
          
          <!-- Schema Search -->
          <div class="px-4 py-2 border-b border-gray-200 dark:border-gray-700">
            <div class="relative">
              <input
                v-model="schemaSearchQuery"
                @input="filterSchema"
                type="text"
                placeholder="Search objects..."
                class="input-primary text-sm pl-8"
              >
              <i class="fas fa-search absolute left-2 top-2.5 text-gray-400"></i>
            </div>
          </div>
          
          <!-- Schema Tree -->
          <div class="p-2 max-h-96 overflow-y-auto">
            <div v-if="schemaLoading" class="p-4 text-center">
              <div class="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-green-600"></div>
              <p class="mt-2 text-sm text-gray-600 dark:text-gray-400">Loading schema...</p>
            </div>
            
            <div v-else-if="filteredSchemaObjects.length === 0" class="p-4 text-center text-gray-500 dark:text-gray-400">
              <i class="fas fa-database text-2xl mb-2"></i>
              <p class="text-sm">No objects found</p>
            </div>
            
            <div v-else class="space-y-1">
              <div 
                v-for="object in filteredSchemaObjects" 
                :key="object.name"
                class="group"
              >
                <!-- Object Header -->
                <div 
                  class="flex items-center justify-between p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded cursor-pointer"
                  @click="expandTable(object)"
                >
                  <div class="flex items-center">
                    <i 
                      :class="[
                        'fas fa-sm mr-2',
                        object.type === 'table' ? 'fa-table text-blue-600' :
                        object.type === 'view' ? 'fa-eye text-green-600' :
                        'fa-list text-gray-600'
                      ]"
                    ></i>
                    <span class="text-sm font-medium text-gray-900 dark:text-white">{{ object.name }}</span>
                    <i 
                      v-if="object.columns"
                      :class="[
                        'fas fa-chevron-right ml-2 text-xs text-gray-400 transition-transform',
                        { 'transform rotate-90': object.expanded }
                      ]"
                    ></i>
                  </div>
                  <div class="opacity-0 group-hover:opacity-100 flex space-x-1">
                    <button
                      @click.stop="insertTableName(object.name)"
                      class="text-xs text-blue-600 hover:text-blue-800"
                      title="Insert table name"
                    >
                      <i class="fas fa-plus"></i>
                    </button>
                    <button
                      @click.stop="generateSelectQuery(object)"
                      class="text-xs text-green-600 hover:text-green-800"
                      title="Generate SELECT query"
                    >
                      <i class="fas fa-code"></i>
                    </button>
                  </div>
                </div>
                
                <!-- Columns -->
                <div v-if="object.expanded && object.columns" class="ml-6 space-y-1">
                  <div 
                    v-for="column in object.columns" 
                    :key="column.name"
                    class="flex items-center justify-between p-1 text-xs hover:bg-gray-50 dark:hover:bg-gray-600 rounded"
                  >
                    <div class="flex items-center">
                      <i 
                        :class="[
                          'fas fa-sm mr-2',
                          column.primary_key ? 'fa-key text-yellow-600' : 'fa-columns text-gray-400'
                        ]"
                      ></i>
                      <span class="text-gray-700 dark:text-gray-300">{{ column.name }}</span>
                    </div>
                    <div class="flex items-center space-x-1">
                      <span class="text-gray-500 dark:text-gray-400">{{ column.type }}</span>
                      <span v-if="!column.nullable" class="text-red-500 text-xs">*</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Main Content -->
      <div class="xl:col-span-3 space-y-6">
        <!-- SQL Editor -->
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
          <div class="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
            <div class="flex justify-between items-center">
              <h3 class="text-lg font-medium text-gray-900 dark:text-white">SQL Editor</h3>
              <div class="flex space-x-2">
                <button
                  @click="formatSql"
                  class="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                  title="Format SQL"
                >
                  <i class="fas fa-indent"></i>
                </button>
                <button
                  @click="copyToClipboard"
                  class="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                  title="Copy to Clipboard"
                >
                  <i class="fas fa-copy"></i>
                </button>
              </div>
            </div>
          </div>
          
          <div class="relative">
            <textarea
              v-model="sqlQuery"
              ref="editorElement"
              placeholder="Enter your SQL query here..."
              class="w-full h-64 p-4 font-mono text-sm border-0 resize-none focus:outline-none bg-transparent text-gray-900 dark:text-white"
              style="tab-size: 4;"
            ></textarea>
            <div class="px-4 py-2 bg-gray-50 dark:bg-gray-700 border-t border-gray-200 dark:border-gray-600 text-xs text-gray-500 dark:text-gray-400">
              Press Ctrl+Enter to execute query
            </div>
          </div>
        </div>
        
        <!-- Results -->
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
          <div class="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
            <div class="flex justify-between items-center">
              <h3 class="text-lg font-medium text-gray-900 dark:text-white">Results</h3>
              <div v-if="queryResults && queryResults.rows.length > 0" class="flex items-center space-x-4">
                <span class="text-sm text-gray-600 dark:text-gray-400">
                  {{ queryResults.rowCount }} rows in {{ queryResults.executionTime }}ms
                </span>
                <button
                  @click="exportResults"
                  class="btn btn-outline-secondary btn-sm"
                >
                  <i class="fas fa-download mr-1"></i>Export CSV
                </button>
              </div>
            </div>
          </div>
          
          <div class="p-4">
            <div v-if="queryExecuting" class="text-center py-8">
              <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-green-600"></div>
              <p class="mt-2 text-gray-600 dark:text-gray-400">Executing query...</p>
            </div>
            
            <div v-else-if="!queryResults" class="text-center py-8 text-gray-500 dark:text-gray-400">
              <i class="fas fa-database text-4xl mb-4"></i>
              <p class="text-lg">Execute a query to see results</p>
            </div>
            
            <div v-else-if="queryResults.message" class="text-center py-8">
              <div class="text-green-600">
                <i class="fas fa-check-circle text-4xl mb-4"></i>
                <p class="text-lg">{{ queryResults.message }}</p>
              </div>
            </div>
            
            <div v-else-if="queryResults.rows.length === 0" class="text-center py-8 text-gray-500 dark:text-gray-400">
              <i class="fas fa-table text-4xl mb-4"></i>
              <p class="text-lg">No rows returned</p>
            </div>
            
            <div v-else class="overflow-x-auto">
              <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead class="bg-gray-50 dark:bg-gray-700">
                  <tr>
                    <th 
                      v-for="column in queryResults.columns" 
                      :key="column"
                      class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider"
                    >
                      {{ column }}
                    </th>
                  </tr>
                </thead>
                <tbody class="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                  <tr v-for="(row, index) in queryResults.rows.slice(0, 100)" :key="index" class="hover:bg-gray-50 dark:hover:bg-gray-700">
                    <td 
                      v-for="column in queryResults.columns" 
                      :key="column"
                      class="px-6 py-4 text-sm text-gray-900 dark:text-white"
                    >
                      <div class="max-w-xs truncate" :title="String(row[column])">
                        {{ row[column] }}
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
              
              <div v-if="queryResults.rows.length > 100" class="p-4 text-center text-gray-500 dark:text-gray-400">
                Showing first 100 rows of {{ queryResults.rowCount }} total rows
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* SQL Editor custom styling */
textarea {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
}

/* Schema tree styling */
.group {
  transition: all 0.2s ease;
}

/* Results table styling */
.overflow-x-auto {
  scrollbar-width: thin;
  scrollbar-color: #cbd5e0 transparent;
}

.overflow-x-auto::-webkit-scrollbar {
  height: 6px;
}

.overflow-x-auto::-webkit-scrollbar-track {
  background: transparent;
}

.overflow-x-auto::-webkit-scrollbar-thumb {
  background-color: #cbd5e0;
  border-radius: 3px;
}

.overflow-x-auto::-webkit-scrollbar-thumb:hover {
  background-color: #a0aec0;
}
</style>