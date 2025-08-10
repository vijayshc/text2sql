<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useQueryStore } from '@/stores/query'
import { useUIStore } from '@/stores/ui'

const queryStore = useQueryStore()
const uiStore = useUIStore()

// Editor state
const sqlQuery = ref('')
const isExecuting = ref(false)
const results = ref<any[]>([])
const executionError = ref<string | null>(null)
const executionTime = ref<number | null>(null)

// Editor features
const showLineNumbers = ref(true)
const fontSize = ref(14)
const theme = ref('vs-dark')

// AI assistance
const showAIHelp = ref(false)
const aiSuggestion = ref('')
const isGeneratingAI = ref(false)

// SQL Templates
const sqlTemplates = [
  {
    name: 'Basic SELECT',
    sql: 'SELECT column1, column2\nFROM table_name\nWHERE condition;'
  },
  {
    name: 'JOIN Query',
    sql: 'SELECT t1.column1, t2.column2\nFROM table1 t1\nINNER JOIN table2 t2 ON t1.id = t2.table1_id\nWHERE condition;'
  },
  {
    name: 'GROUP BY with COUNT',
    sql: 'SELECT column1, COUNT(*) as count\nFROM table_name\nGROUP BY column1\nORDER BY count DESC;'
  },
  {
    name: 'Subquery',
    sql: 'SELECT column1\nFROM table_name\nWHERE column2 IN (\n  SELECT column2\n  FROM other_table\n  WHERE condition\n);'
  },
  {
    name: 'Window Function',
    sql: 'SELECT column1,\n       ROW_NUMBER() OVER (PARTITION BY column2 ORDER BY column3) as row_num\nFROM table_name;'
  }
]

const formatSQL = () => {
  // Simple SQL formatting
  if (!sqlQuery.value.trim()) return
  
  let formatted = sqlQuery.value
    .replace(/\s+/g, ' ') // Normalize whitespace
    .replace(/\s*,\s*/g, ',\n       ') // Format commas
    .replace(/\s+(FROM|WHERE|GROUP BY|ORDER BY|HAVING|LIMIT|OFFSET)\s+/gi, '\n$1 ')
    .replace(/\s+(INNER|LEFT|RIGHT|FULL)\s+JOIN\s+/gi, '\n$1 JOIN ')
    .replace(/\s+(AND|OR)\s+/gi, '\n   $1 ')
    .trim()
  
  sqlQuery.value = formatted
}

const executeSQL = async () => {
  if (!sqlQuery.value.trim()) {
    uiStore.showWarning('Empty Query', 'Please enter a SQL query to execute')
    return
  }

  try {
    isExecuting.value = true
    executionError.value = null
    const startTime = Date.now()

    // This would typically call an API endpoint for SQL execution
    // For now, we'll simulate the API call
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    // Mock results for demonstration
    results.value = [
      { id: 1, name: 'John Doe', email: 'john@example.com', created_at: '2024-01-15' },
      { id: 2, name: 'Jane Smith', email: 'jane@example.com', created_at: '2024-01-16' },
      { id: 3, name: 'Bob Johnson', email: 'bob@example.com', created_at: '2024-01-17' }
    ]
    
    executionTime.value = Date.now() - startTime
    uiStore.showSuccess('Query Executed', `Query completed in ${executionTime.value}ms`)
    
  } catch (error: any) {
    executionError.value = error.message || 'Failed to execute query'
    uiStore.showError('Execution Failed', executionError.value || 'Unknown error')
  } finally {
    isExecuting.value = false
  }
}

const generateAIAssistance = async () => {
  if (!sqlQuery.value.trim()) {
    uiStore.showInfo('AI Help', 'Enter a SQL query or describe what you want to do')
    return
  }

  try {
    isGeneratingAI.value = true
    
    // Simulate AI suggestion generation
    await new Promise(resolve => setTimeout(resolve, 1500))
    
    aiSuggestion.value = `
**Query Analysis:**
Your query appears to be a ${sqlQuery.value.toLowerCase().includes('select') ? 'SELECT' : 'data manipulation'} operation.

**Suggestions:**
- Consider adding appropriate indexes for better performance
- Use LIMIT clause to avoid large result sets
- Ensure proper WHERE conditions to filter data effectively

**Optimization Tips:**
- Use specific column names instead of SELECT *
- Consider using EXISTS instead of IN for subqueries
- Add proper JOIN conditions to avoid cartesian products
    `.trim()
    
    showAIHelp.value = true
    
  } catch (error: any) {
    uiStore.showError('AI Help Failed', 'Could not generate AI assistance')
  } finally {
    isGeneratingAI.value = false
  }
}

const insertTemplate = (template: { name: string, sql: string }) => {
  sqlQuery.value = template.sql
}

const clearEditor = () => {
  sqlQuery.value = ''
  results.value = []
  executionError.value = null
  executionTime.value = null
  aiSuggestion.value = ''
  showAIHelp.value = false
}

const saveQuery = () => {
  if (!sqlQuery.value.trim()) {
    uiStore.showWarning('Empty Query', 'Please enter a SQL query to save')
    return
  }
  
  // This would typically save to the backend
  uiStore.showSuccess('Query Saved', 'Your SQL query has been saved')
}

const exportResults = () => {
  if (!results.value.length) {
    uiStore.showWarning('No Results', 'Execute a query first to export results')
    return
  }
  
  // Convert results to CSV
  const headers = Object.keys(results.value[0])
  const csvContent = [
    headers.join(','),
    ...results.value.map(row => headers.map(header => `"${row[header]}"`).join(','))
  ].join('\n')
  
  // Download CSV
  const blob = new Blob([csvContent], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `query_results_${new Date().toISOString().split('T')[0]}.csv`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  
  uiStore.showSuccess('Export Complete', 'Results exported as CSV')
}

onMounted(() => {
  // Initialize with a sample query
  sqlQuery.value = 'SELECT * FROM users WHERE created_at >= \'2024-01-01\' ORDER BY created_at DESC LIMIT 10;'
})
</script>

<template>
  <div class="h-full flex flex-col space-y-6">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white">
          SQL Query Editor
        </h1>
        <p class="text-gray-600 dark:text-gray-400 mt-1">
          Write, execute, and analyze SQL queries
        </p>
      </div>
      
      <div class="flex items-center space-x-3">
        <!-- Templates Dropdown -->
        <div class="relative group">
          <button class="btn btn-secondary">
            <i class="fas fa-file-code mr-2"></i>
            Templates
          </button>
          <div class="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-10">
            <div class="py-1">
              <button
                v-for="template in sqlTemplates"
                :key="template.name"
                @click="insertTemplate(template)"
                class="block w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
              >
                {{ template.name }}
              </button>
            </div>
          </div>
        </div>
        
        <button @click="formatSQL" class="btn btn-secondary">
          <i class="fas fa-magic mr-2"></i>
          Format
        </button>
        
        <button @click="clearEditor" class="btn btn-secondary">
          <i class="fas fa-trash mr-2"></i>
          Clear
        </button>
      </div>
    </div>

    <!-- Editor Section -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1">
      <!-- SQL Editor -->
      <div class="lg:col-span-2 space-y-4">
        <!-- Editor Toolbar -->
        <div class="flex items-center justify-between bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 px-4 py-2">
          <div class="flex items-center space-x-4">
            <label class="flex items-center">
              <input
                v-model="showLineNumbers"
                type="checkbox"
                class="mr-2 h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
              />
              <span class="text-sm text-gray-700 dark:text-gray-300">Line numbers</span>
            </label>
            
            <div class="flex items-center space-x-2">
              <label class="text-sm text-gray-700 dark:text-gray-300">Font size:</label>
              <select
                v-model="fontSize"
                class="text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              >
                <option :value="12">12px</option>
                <option :value="14">14px</option>
                <option :value="16">16px</option>
                <option :value="18">18px</option>
              </select>
            </div>
          </div>
          
          <div class="flex items-center space-x-2">
            <button
              @click="generateAIAssistance"
              :disabled="isGeneratingAI"
              class="btn btn-secondary text-xs"
            >
              <i v-if="isGeneratingAI" class="fas fa-spinner fa-spin mr-1"></i>
              <i v-else class="fas fa-robot mr-1"></i>
              AI Help
            </button>
            
            <button @click="saveQuery" class="btn btn-secondary text-xs">
              <i class="fas fa-save mr-1"></i>
              Save
            </button>
          </div>
        </div>

        <!-- SQL Editor Area -->
        <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
          <div class="bg-gray-50 dark:bg-gray-700 px-4 py-2 border-b border-gray-200 dark:border-gray-600">
            <h3 class="text-sm font-medium text-gray-900 dark:text-white">SQL Query</h3>
          </div>
          
          <!-- Monaco Editor would go here in a real implementation -->
          <div class="relative">
            <textarea
              v-model="sqlQuery"
              rows="15"
              class="w-full p-4 border-0 bg-gray-900 text-green-400 font-mono text-sm resize-none focus:ring-0 focus:outline-none"
              :style="{ fontSize: fontSize + 'px' }"
              placeholder="-- Enter your SQL query here..."
            ></textarea>
            
            <!-- Line numbers (if enabled) -->
            <div
              v-if="showLineNumbers"
              class="absolute left-0 top-0 bg-gray-800 text-gray-500 text-sm font-mono p-4 border-r border-gray-600 select-none pointer-events-none"
              :style="{ fontSize: fontSize + 'px' }"
            >
              <div v-for="n in (sqlQuery.split('\n').length)" :key="n" class="leading-6">
                {{ n }}
              </div>
            </div>
          </div>
          
          <!-- Execute Button -->
          <div class="bg-gray-50 dark:bg-gray-700 px-4 py-3 border-t border-gray-200 dark:border-gray-600">
            <button
              @click="executeSQL"
              :disabled="isExecuting || !sqlQuery.trim()"
              class="btn btn-primary"
            >
              <i v-if="isExecuting" class="fas fa-spinner fa-spin mr-2"></i>
              <i v-else class="fas fa-play mr-2"></i>
              {{ isExecuting ? 'Executing...' : 'Execute Query' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Sidebar -->
      <div class="space-y-4">
        <!-- Schema Browser -->
        <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <div class="bg-gray-50 dark:bg-gray-700 px-4 py-3 border-b border-gray-200 dark:border-gray-600">
            <h3 class="text-sm font-medium text-gray-900 dark:text-white">Schema Browser</h3>
          </div>
          <div class="p-4 max-h-64 overflow-y-auto">
            <div v-for="table in queryStore.schema.slice(0, 5)" :key="table.name" class="mb-3">
              <div class="flex items-center text-sm font-medium text-gray-900 dark:text-white mb-1">
                <i class="fas fa-table mr-2 text-gray-500"></i>
                {{ table.name }}
              </div>
              <div class="ml-6 space-y-1">
                <div
                  v-for="column in table.columns?.slice(0, 3)"
                  :key="column.name"
                  class="text-xs text-gray-600 dark:text-gray-400 flex items-center"
                >
                  <i :class="column.is_primary_key ? 'fas fa-key text-yellow-500' : 'fas fa-circle'" class="mr-2 text-xs"></i>
                  {{ column.name }} ({{ column.datatype }})
                </div>
                <div v-if="table.columns && table.columns.length > 3" class="text-xs text-gray-500 dark:text-gray-500 ml-4">
                  ... {{ table.columns.length - 3 }} more
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- AI Help Panel -->
        <div v-if="showAIHelp" class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <div class="bg-gray-50 dark:bg-gray-700 px-4 py-3 border-b border-gray-200 dark:border-gray-600 flex items-center justify-between">
            <h3 class="text-sm font-medium text-gray-900 dark:text-white">AI Assistant</h3>
            <button @click="showAIHelp = false" class="text-gray-400 hover:text-gray-600">
              <i class="fas fa-times"></i>
            </button>
          </div>
          <div class="p-4">
            <div class="prose prose-sm dark:prose-invert max-w-none">
              <div class="whitespace-pre-line text-sm text-gray-700 dark:text-gray-300">{{ aiSuggestion }}</div>
            </div>
          </div>
        </div>

        <!-- Query History (placeholder) -->
        <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <div class="bg-gray-50 dark:bg-gray-700 px-4 py-3 border-b border-gray-200 dark:border-gray-600">
            <h3 class="text-sm font-medium text-gray-900 dark:text-white">Recent Queries</h3>
          </div>
          <div class="p-4">
            <div class="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
              No recent queries
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Results Section -->
    <div v-if="results.length > 0 || executionError" class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
      <div class="bg-gray-50 dark:bg-gray-700 px-4 py-3 border-b border-gray-200 dark:border-gray-600 flex items-center justify-between">
        <div class="flex items-center space-x-4">
          <h3 class="text-sm font-medium text-gray-900 dark:text-white">Query Results</h3>
          <span v-if="executionTime" class="text-xs text-gray-500 dark:text-gray-400">
            Executed in {{ executionTime }}ms
          </span>
        </div>
        
        <button
          v-if="results.length > 0"
          @click="exportResults"
          class="btn btn-secondary text-xs"
        >
          <i class="fas fa-download mr-1"></i>
          Export CSV
        </button>
      </div>
      
      <!-- Error Display -->
      <div v-if="executionError" class="p-4">
        <div class="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <div class="flex items-center">
            <i class="fas fa-exclamation-triangle text-red-500 mr-2"></i>
            <span class="text-sm font-medium text-red-800 dark:text-red-200">Query Error</span>
          </div>
          <div class="mt-2 text-sm text-red-700 dark:text-red-300 font-mono">
            {{ executionError }}
          </div>
        </div>
      </div>
      
      <!-- Results Table -->
      <div v-else-if="results.length > 0" class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead class="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th
                v-for="(column, index) in Object.keys(results[0])"
                :key="index"
                class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
              >
                {{ column }}
              </th>
            </tr>
          </thead>
          <tbody class="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
            <tr
              v-for="(row, rowIndex) in results"
              :key="rowIndex"
              class="hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              <td
                v-for="(value, colIndex) in Object.values(row)"
                :key="colIndex"
                class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white"
              >
                {{ value }}
              </td>
            </tr>
          </tbody>
        </table>
        
        <div class="bg-gray-50 dark:bg-gray-700 px-4 py-3 border-t border-gray-200 dark:border-gray-600">
          <p class="text-sm text-gray-700 dark:text-gray-300">
            Showing {{ results.length }} {{ results.length === 1 ? 'row' : 'rows' }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Custom button styles */
.btn {
  @apply inline-flex items-center justify-center px-3 py-2 border rounded-lg text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed;
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

/* Editor styling */
textarea {
  tab-size: 2;
}

textarea:focus {
  outline: none;
  box-shadow: none;
}

/* Dropdown hover effect */
.group:hover .group-hover\:opacity-100 {
  opacity: 1;
}

.group:hover .group-hover\:visible {
  visibility: visible;
}
</style>