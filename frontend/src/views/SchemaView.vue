<template>
  <div class="schema-view">
    <!-- Header -->
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white flex items-center">
          <i class="fas fa-table mr-3 text-blue-600"></i>
          Schema Browser
        </h1>
        <p class="text-gray-600 dark:text-gray-400 mt-1">
          Explore and manage database schema and table structures
        </p>
      </div>
      
      <!-- Action Buttons -->
      <div class="flex items-center space-x-3">
        <button
          @click="showImportModal = true"
          class="inline-flex items-center px-3 py-2 border border-gray-300 dark:border-gray-600 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          <i class="fas fa-upload mr-2"></i>
          Import Schema
        </button>
        <button
          @click="exportSchema"
          :disabled="!selectedWorkspace"
          class="inline-flex items-center px-3 py-2 border border-gray-300 dark:border-gray-600 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <i class="fas fa-download mr-2"></i>
          Export Schema
        </button>
        <button
          @click="showCreateWorkspaceModal = true"
          class="inline-flex items-center px-3 py-2 border border-transparent shadow-sm text-sm leading-4 font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          <i class="fas fa-plus mr-2"></i>
          New Workspace
        </button>
      </div>
    </div>

    <!-- Workspace Selector -->
    <div class="mb-6">
      <label for="workspaceSelect" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
        Select Workspace:
      </label>
      <select
        id="workspaceSelect"
        v-model="selectedWorkspace"
        @change="onWorkspaceChange"
        class="block w-full max-w-sm rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
      >
        <option value="">Select a workspace...</option>
        <option v-for="workspace in workspaces" :key="workspace.name" :value="workspace.name">
          {{ workspace.name }} {{ workspace.description ? `- ${workspace.description}` : '' }}
        </option>
      </select>
    </div>

    <!-- Main Content -->
    <div v-if="selectedWorkspace" class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Tables List -->
      <div class="lg:col-span-1">
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg">
          <div class="px-4 py-3 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
            <h3 class="text-lg font-medium text-gray-900 dark:text-white">Tables</h3>
            <button
              @click="showCreateTableModal = true"
              class="inline-flex items-center px-2 py-1 border border-transparent text-xs font-medium rounded text-blue-700 dark:text-blue-400 bg-blue-100 dark:bg-blue-900/20 hover:bg-blue-200 dark:hover:bg-blue-900/40 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              <i class="fas fa-plus mr-1"></i>
              Add Table
            </button>
          </div>
          
          <div class="max-h-96 overflow-y-auto">
            <div v-if="isLoadingTables" class="p-4 text-center">
              <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 mx-auto"></div>
              <p class="text-sm text-gray-500 dark:text-gray-400 mt-2">Loading tables...</p>
            </div>
            
            <div v-else-if="tables.length === 0" class="p-4 text-center">
              <p class="text-sm text-gray-500 dark:text-gray-400">No tables found in this workspace.</p>
            </div>
            
            <div v-else class="divide-y divide-gray-200 dark:divide-gray-700">
              <div
                v-for="table in tables"
                :key="table.name"
                @click="selectTable(table)"
                class="p-4 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer transition-colors"
                :class="selectedTable?.name === table.name ? 'bg-blue-50 dark:bg-blue-900/20' : ''"
              >
                <div class="flex items-center justify-between">
                  <div>
                    <h4 class="font-medium text-gray-900 dark:text-white">{{ table.name }}</h4>
                    <p v-if="table.description" class="text-sm text-gray-500 dark:text-gray-400 mt-1">
                      {{ table.description }}
                    </p>
                    <p class="text-xs text-gray-400 dark:text-gray-500 mt-1">
                      {{ table.columns?.length || 0 }} columns
                    </p>
                  </div>
                  <div class="flex items-center space-x-2">
                    <button
                      @click.stop="editTable(table)"
                      class="text-gray-400 hover:text-blue-600 dark:hover:text-blue-400"
                    >
                      <i class="fas fa-edit text-sm"></i>
                    </button>
                    <button
                      @click.stop="deleteTable(table)"
                      class="text-gray-400 hover:text-red-600 dark:hover:text-red-400"
                    >
                      <i class="fas fa-trash text-sm"></i>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Table Details -->
      <div class="lg:col-span-2">
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg">
          <div v-if="selectedTable" class="p-6">
            <div class="flex justify-between items-center mb-4">
              <div>
                <h3 class="text-lg font-medium text-gray-900 dark:text-white">
                  {{ selectedTable.name }}
                </h3>
                <p v-if="selectedTable.description" class="text-sm text-gray-500 dark:text-gray-400 mt-1">
                  {{ selectedTable.description }}
                </p>
              </div>
              <button
                @click="refreshTableDetails"
                class="inline-flex items-center px-3 py-2 border border-gray-300 dark:border-gray-600 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                <i class="fas fa-refresh mr-2"></i>
                Refresh
              </button>
            </div>

            <!-- Columns Table -->
            <div class="overflow-hidden shadow ring-1 ring-black ring-opacity-5 md:rounded-lg">
              <table class="min-w-full divide-y divide-gray-300 dark:divide-gray-600">
                <thead class="bg-gray-50 dark:bg-gray-700">
                  <tr>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Column Name
                    </th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Data Type
                    </th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Constraints
                    </th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Description
                    </th>
                  </tr>
                </thead>
                <tbody class="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                  <tr v-for="column in selectedTable.columns" :key="column.name">
                    <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                      {{ column.name }}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                      {{ column.datatype || column.type }}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                      <div class="flex space-x-1">
                        <span v-if="column.primary_key" class="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 dark:bg-blue-900/20 text-blue-800 dark:text-blue-200">
                          PK
                        </span>
                        <span v-if="column.foreign_key" class="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-green-100 dark:bg-green-900/20 text-green-800 dark:text-green-200">
                          FK
                        </span>
                        <span v-if="column.nullable === false" class="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-red-100 dark:bg-red-900/20 text-red-800 dark:text-red-200">
                          NOT NULL
                        </span>
                      </div>
                    </td>
                    <td class="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                      {{ column.description || '-' }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- Relationships -->
            <div v-if="selectedTable.relationships && selectedTable.relationships.length > 0" class="mt-6">
              <h4 class="text-md font-medium text-gray-900 dark:text-white mb-3">Relationships</h4>
              <div class="space-y-2">
                <div
                  v-for="relationship in selectedTable.relationships"
                  :key="`${relationship.from_table}.${relationship.from_column}`"
                  class="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg"
                >
                  <div class="text-sm">
                    <span class="font-medium text-gray-900 dark:text-white">{{ relationship.from_column }}</span>
                    <span class="text-gray-500 dark:text-gray-400 mx-2">→</span>
                    <span class="font-medium text-gray-900 dark:text-white">{{ relationship.to_table }}.{{ relationship.to_column }}</span>
                  </div>
                  <span class="text-xs text-gray-500 dark:text-gray-400 bg-gray-200 dark:bg-gray-600 px-2 py-1 rounded">
                    {{ relationship.type || 'FK' }}
                  </span>
                </div>
              </div>
            </div>
          </div>
          
          <div v-else class="p-8 text-center">
            <i class="fas fa-table text-4xl text-gray-300 dark:text-gray-600 mb-4"></i>
            <p class="text-gray-500 dark:text-gray-400">
              Select a table from the list to view its details
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="text-center py-12">
      <i class="fas fa-database text-6xl text-gray-300 dark:text-gray-600 mb-4"></i>
      <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-2">No Workspace Selected</h3>
      <p class="text-gray-500 dark:text-gray-400 mb-6">
        Select a workspace from the dropdown above to view its schema, or create a new workspace.
      </p>
    </div>

    <!-- Create Workspace Modal -->
    <div
      v-if="showCreateWorkspaceModal"
      class="fixed inset-0 z-50 overflow-y-auto"
      aria-labelledby="modal-title"
      role="dialog"
      aria-modal="true"
    >
      <div class="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" aria-hidden="true" @click="showCreateWorkspaceModal = false"></div>
        <span class="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>
        <div class="relative inline-block align-bottom bg-white dark:bg-gray-800 rounded-lg px-4 pt-5 pb-4 text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full sm:p-6">
          <div>
            <h3 class="text-lg leading-6 font-medium text-gray-900 dark:text-white mb-4">Create New Workspace</h3>
            <div class="space-y-4">
              <div>
                <label for="workspaceName" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Workspace Name
                </label>
                <input
                  id="workspaceName"
                  v-model="newWorkspace.name"
                  type="text"
                  class="block w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                  placeholder="Enter workspace name"
                >
              </div>
              <div>
                <label for="workspaceDescription" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Description (Optional)
                </label>
                <textarea
                  id="workspaceDescription"
                  v-model="newWorkspace.description"
                  rows="3"
                  class="block w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                  placeholder="Enter workspace description"
                ></textarea>
              </div>
            </div>
          </div>
          <div class="mt-5 sm:mt-6 sm:grid sm:grid-cols-2 sm:gap-3 sm:grid-flow-row-dense">
            <button
              @click="createWorkspace"
              :disabled="!newWorkspace.name.trim()"
              type="button"
              class="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-blue-600 text-base font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:col-start-2 sm:text-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Create
            </button>
            <button
              @click="showCreateWorkspaceModal = false"
              type="button"
              class="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 dark:border-gray-600 shadow-sm px-4 py-2 bg-white dark:bg-gray-700 text-base font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:mt-0 sm:col-start-1 sm:text-sm"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Import Schema Modal -->
    <div
      v-if="showImportModal"
      class="fixed inset-0 z-50 overflow-y-auto"
      aria-labelledby="modal-title"
      role="dialog"
      aria-modal="true"
    >
      <div class="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" aria-hidden="true" @click="showImportModal = false"></div>
        <span class="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>
        <div class="relative inline-block align-bottom bg-white dark:bg-gray-800 rounded-lg px-4 pt-5 pb-4 text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full sm:p-6">
          <div>
            <h3 class="text-lg leading-6 font-medium text-gray-900 dark:text-white mb-4">Import Schema</h3>
            <div class="space-y-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Import Type</label>
                <select
                  v-model="importData.sourceType"
                  class="block w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                >
                  <option value="json">JSON Schema</option>
                  <option value="database">Database Connection</option>
                </select>
              </div>
              
              <div v-if="importData.sourceType === 'json'">
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  JSON Schema Data
                </label>
                <textarea
                  v-model="importData.schemaData"
                  rows="6"
                  class="block w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm font-mono"
                  placeholder="Paste your JSON schema here..."
                ></textarea>
              </div>
              
              <div v-if="importData.sourceType === 'database'">
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Database Connection String
                </label>
                <input
                  v-model="importData.connectionString"
                  type="text"
                  class="block w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                  placeholder="postgresql://user:pass@host:port/db"
                >
              </div>
              
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Target Workspace
                </label>
                <input
                  v-model="importData.workspace"
                  type="text"
                  class="block w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                  placeholder="Enter workspace name"
                >
              </div>
            </div>
          </div>
          <div class="mt-5 sm:mt-6 sm:grid sm:grid-cols-2 sm:gap-3 sm:grid-flow-row-dense">
            <button
              @click="importSchema"
              :disabled="!canImport"
              type="button"
              class="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-blue-600 text-base font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:col-start-2 sm:text-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Import
            </button>
            <button
              @click="showImportModal = false"
              type="button"
              class="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 dark:border-gray-600 shadow-sm px-4 py-2 bg-white dark:bg-gray-700 text-base font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:mt-0 sm:col-start-1 sm:text-sm"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useToast } from '@/composables/useToast'
import { apiService } from '@/services/api'

// Reactive state
const workspaces = ref<Array<{ name: string; description?: string }>>([])
const selectedWorkspace = ref('')
const tables = ref<Array<any>>([])
const selectedTable = ref<any>(null)
const isLoadingTables = ref(false)

// Modal states
const showCreateWorkspaceModal = ref(false)
const showImportModal = ref(false)
const showCreateTableModal = ref(false)

// Form data
const newWorkspace = ref({
  name: '',
  description: ''
})

const importData = ref({
  sourceType: 'json',
  schemaData: '',
  connectionString: '',
  workspace: ''
})

// Computed
const canImport = computed(() => {
  if (importData.value.sourceType === 'json') {
    return importData.value.schemaData.trim() && importData.value.workspace.trim()
  } else {
    return importData.value.connectionString.trim() && importData.value.workspace.trim()
  }
})

// Composables
const { showToast } = useToast()

// Methods
const loadWorkspaces = async () => {
  try {
    const response = await apiService.get('/api/v1/schema/workspaces')
    if (response.success) {
      workspaces.value = response.workspaces
    }
  } catch (error) {
    console.error('Error loading workspaces:', error)
    showToast('Failed to load workspaces', 'error')
  }
}

const onWorkspaceChange = async () => {
  if (selectedWorkspace.value) {
    await loadTables()
  } else {
    tables.value = []
    selectedTable.value = null
  }
}

const loadTables = async () => {
  if (!selectedWorkspace.value) return
  
  isLoadingTables.value = true
  try {
    const response = await apiService.get(`/api/v1/schema/tables?workspace=${selectedWorkspace.value}`)
    if (response.success) {
      tables.value = response.tables
    }
  } catch (error) {
    console.error('Error loading tables:', error)
    showToast('Failed to load tables', 'error')
  } finally {
    isLoadingTables.value = false
  }
}

const selectTable = async (table: any) => {
  selectedTable.value = table
  
  // Load detailed table information
  try {
    const response = await apiService.get(`/api/v1/schema/table-details?workspace=${selectedWorkspace.value}&table_name=${table.name}`)
    if (response.success) {
      selectedTable.value = response.table
    }
  } catch (error) {
    console.error('Error loading table details:', error)
    showToast('Failed to load table details', 'error')
  }
}

const refreshTableDetails = async () => {
  if (selectedTable.value) {
    await selectTable(selectedTable.value)
  }
}

const createWorkspace = async () => {
  try {
    const response = await apiService.post('/api/v1/schema/workspace', {
      name: newWorkspace.value.name,
      description: newWorkspace.value.description
    })
    
    if (response.success) {
      showToast(`Workspace "${newWorkspace.value.name}" created successfully`, 'success')
      showCreateWorkspaceModal.value = false
      newWorkspace.value = { name: '', description: '' }
      await loadWorkspaces()
      selectedWorkspace.value = response.workspace.name
      await onWorkspaceChange()
    }
  } catch (error) {
    console.error('Error creating workspace:', error)
    showToast('Failed to create workspace', 'error')
  }
}

const importSchema = async () => {
  try {
    const response = await apiService.post('/api/v1/schema/import', {
      source_type: importData.value.sourceType,
      workspace: importData.value.workspace,
      ...(importData.value.sourceType === 'json' 
        ? { schema_data: JSON.parse(importData.value.schemaData) }
        : { connection_string: importData.value.connectionString }
      )
    })
    
    if (response.success) {
      showToast('Schema imported successfully', 'success')
      showImportModal.value = false
      importData.value = { sourceType: 'json', schemaData: '', connectionString: '', workspace: '' }
      await loadWorkspaces()
      
      // Switch to the imported workspace if it exists
      if (workspaces.value.find(w => w.name === response.result?.workspace)) {
        selectedWorkspace.value = response.result.workspace
        await onWorkspaceChange()
      }
    }
  } catch (error) {
    console.error('Error importing schema:', error)
    showToast('Failed to import schema', 'error')
  }
}

const exportSchema = async () => {
  if (!selectedWorkspace.value) return
  
  try {
    const response = await apiService.get(`/api/v1/schema/export?workspace=${selectedWorkspace.value}&format=json`)
    if (response.success) {
      // Create and download file
      const blob = new Blob([JSON.stringify(response.data, null, 2)], { type: 'application/json' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${selectedWorkspace.value}_schema.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
      
      showToast('Schema exported successfully', 'success')
    }
  } catch (error) {
    console.error('Error exporting schema:', error)
    showToast('Failed to export schema', 'error')
  }
}

const editTable = (table: any) => {
  // TODO: Implement table editing
  showToast('Table editing not yet implemented', 'info')
}

const deleteTable = async (table: any) => {
  if (!confirm(`Are you sure you want to delete table "${table.name}"?`)) {
    return
  }
  
  try {
    const response = await apiService.delete(`/api/v1/schema/table?workspace=${selectedWorkspace.value}&table_name=${table.name}`)
    if (response.success) {
      showToast(`Table "${table.name}" deleted successfully`, 'success')
      await loadTables()
      if (selectedTable.value?.name === table.name) {
        selectedTable.value = null
      }
    }
  } catch (error) {
    console.error('Error deleting table:', error)
    showToast('Failed to delete table', 'error')
  }
}

// Lifecycle
onMounted(() => {
  loadWorkspaces()
})
</script>

<style scoped>
.schema-view {
  @apply p-6;
}
</style>