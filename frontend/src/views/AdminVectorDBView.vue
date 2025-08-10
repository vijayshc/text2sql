<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useToast } from '@/stores/toast'
import { apiRequest } from '@/services/api'

interface Collection {
  name: string
  vector_dimension: number
  record_count: number
  description?: string
}

interface Record {
  id: string | number
  [key: string]: any
}

interface SearchResult {
  id: string | number
  distance: number
  [key: string]: any
}

const toast = useToast()

// Reactive state
const collections = ref<Collection[]>([])
const selectedCollection = ref<string>('')
const selectedCollectionInfo = ref<Collection | null>(null)
const records = ref<Record[]>([])
const recordColumns = ref<string[]>([])
const loading = ref(true)
const recordsLoading = ref(false)

// Pagination
const currentPage = ref(1)
const recordsPerPage = ref(50)
const totalRecords = ref(0)
const filterExpression = ref('')

// Modals
const showCreateModal = ref(false)
const showRecordModal = ref(false)
const selectedRecord = ref<Record | null>(null)

// Forms
const createForm = ref({
  name: '',
  vector_dimension: 384,
  description: ''
})

const uploadForm = ref({
  file: null as File | null,
  textField: ''
})

const searchForm = ref({
  text: '',
  limit: 50
})

const searchResults = ref<SearchResult[]>([])

// Computed
const paginatedRecords = computed(() => {
  const start = (currentPage.value - 1) * recordsPerPage.value
  const end = start + recordsPerPage.value
  return records.value.slice(start, end)
})

const totalPages = computed(() => {
  return Math.ceil(totalRecords.value / recordsPerPage.value)
})

// API calls
const loadCollections = async () => {
  try {
    loading.value = true
    const response = await apiRequest('/api/v1/admin/vector-db/collections')
    collections.value = response.collections
  } catch (error) {
    toast.error('Failed to load collections: ' + (error as Error).message)
  } finally {
    loading.value = false
  }
}

const loadCollectionData = async (collectionName: string) => {
  try {
    recordsLoading.value = true
    
    // Load collection info
    const infoResponse = await apiRequest(`/api/v1/admin/vector-db/collections/${collectionName}`)
    selectedCollectionInfo.value = infoResponse.collection
    
    // Load records
    const params = new URLSearchParams({
      page: currentPage.value.toString(),
      limit: recordsPerPage.value.toString()
    })
    
    if (filterExpression.value) {
      params.append('filter', filterExpression.value)
    }
    
    const recordsResponse = await apiRequest(`/api/v1/admin/vector-db/collections/${collectionName}/records?${params}`)
    records.value = recordsResponse.records
    totalRecords.value = recordsResponse.total
    recordColumns.value = recordsResponse.columns || []
  } catch (error) {
    toast.error('Failed to load collection data: ' + (error as Error).message)
  } finally {
    recordsLoading.value = false
  }
}

const createCollection = async () => {
  try {
    const response = await apiRequest('/api/v1/admin/vector-db/collections', {
      method: 'POST',
      body: JSON.stringify(createForm.value)
    })
    
    toast.success(response.message)
    showCreateModal.value = false
    resetCreateForm()
    await loadCollections()
  } catch (error) {
    toast.error('Failed to create collection: ' + (error as Error).message)
  }
}

const deleteCollection = async (collectionName: string) => {
  if (!confirm(`Are you sure you want to delete the collection "${collectionName}"? This action cannot be undone.`)) {
    return
  }

  try {
    const response = await apiRequest(`/api/v1/admin/vector-db/collections/${collectionName}`, {
      method: 'DELETE'
    })
    
    toast.success(response.message)
    
    if (selectedCollection.value === collectionName) {
      selectedCollection.value = ''
      selectedCollectionInfo.value = null
      records.value = []
    }
    
    await loadCollections()
  } catch (error) {
    toast.error('Failed to delete collection: ' + (error as Error).message)
  }
}

const uploadData = async () => {
  if (!uploadForm.value.file || !uploadForm.value.textField) {
    toast.error('Please select a file and specify the text field name')
    return
  }

  try {
    const formData = new FormData()
    formData.append('file', uploadForm.value.file)
    formData.append('text_field', uploadForm.value.textField)

    const response = await apiRequest(`/api/v1/admin/vector-db/collections/${selectedCollection.value}/upload`, {
      method: 'POST',
      body: formData
    })

    toast.success(response.message)
    resetUploadForm()
    await loadCollectionData(selectedCollection.value)
  } catch (error) {
    toast.error('Failed to upload data: ' + (error as Error).message)
  }
}

const searchVectors = async () => {
  if (!searchForm.value.text.trim()) {
    toast.error('Please enter search text')
    return
  }

  try {
    const response = await apiRequest(`/api/v1/admin/vector-db/collections/${selectedCollection.value}/search`, {
      method: 'POST',
      body: JSON.stringify({
        text: searchForm.value.text,
        limit: searchForm.value.limit
      })
    })

    searchResults.value = response.results
    toast.success(`Found ${response.results.length} similar records`)
  } catch (error) {
    toast.error('Search failed: ' + (error as Error).message)
  }
}

const applyFilter = async () => {
  currentPage.value = 1
  await loadCollectionData(selectedCollection.value)
}

const viewRecord = (record: Record) => {
  selectedRecord.value = record
  showRecordModal.value = true
}

const deleteRecord = async (recordId: string | number) => {
  if (!confirm('Are you sure you want to delete this record?')) {
    return
  }

  try {
    const response = await apiRequest(`/api/v1/admin/vector-db/collections/${selectedCollection.value}/records/${recordId}`, {
      method: 'DELETE'
    })

    toast.success(response.message)
    await loadCollectionData(selectedCollection.value)
  } catch (error) {
    toast.error('Failed to delete record: ' + (error as Error).message)
  }
}

const onCollectionChange = async () => {
  if (selectedCollection.value) {
    currentPage.value = 1
    await loadCollectionData(selectedCollection.value)
  } else {
    selectedCollectionInfo.value = null
    records.value = []
  }
}

const onPageChange = async (page: number) => {
  currentPage.value = page
  await loadCollectionData(selectedCollection.value)
}

const resetCreateForm = () => {
  createForm.value = {
    name: '',
    vector_dimension: 384,
    description: ''
  }
}

const resetUploadForm = () => {
  uploadForm.value = {
    file: null,
    textField: ''
  }
  const fileInput = document.getElementById('uploadFile') as HTMLInputElement
  if (fileInput) fileInput.value = ''
}

const onFileChange = (event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    uploadForm.value.file = target.files[0]
  }
}

const formatNumber = (num: number) => {
  return new Intl.NumberFormat().format(num)
}

// Lifecycle
onMounted(async () => {
  await loadCollections()
})
</script>

<template>
  <div class="p-6 max-w-7xl mx-auto">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6">
      <div class="flex items-center mb-4 sm:mb-0">
        <i class="fas fa-database text-2xl text-purple-600 mr-3"></i>
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Vector Database Management</h1>
      </div>
      <button 
        @click="showCreateModal = true"
        class="btn btn-primary"
      >
        <i class="fas fa-plus mr-2"></i>Create Collection
      </button>
    </div>

    <!-- Collections Table -->
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 mb-6">
      <div class="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
        <h3 class="text-lg font-medium text-gray-900 dark:text-white">Vector Collections</h3>
      </div>
      
      <div v-if="loading" class="p-8 text-center">
        <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
        <p class="mt-2 text-gray-600 dark:text-gray-400">Loading collections...</p>
      </div>

      <div v-else-if="collections.length === 0" class="p-8 text-center">
        <div class="text-gray-400">
          <i class="fas fa-database text-4xl mb-4"></i>
          <p class="text-lg">No collections found</p>
          <p class="text-sm">Create your first vector collection</p>
        </div>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead class="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                Collection Name
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                Vector Dimension
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                Record Count
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                Description
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody class="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
            <tr 
              v-for="collection in collections" 
              :key="collection.name" 
              class="hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer"
              :class="{ 'bg-blue-50 dark:bg-blue-900': selectedCollection === collection.name }"
              @click="selectedCollection = collection.name; onCollectionChange()"
            >
              <td class="px-6 py-4">
                <div class="text-sm font-medium text-gray-900 dark:text-white">{{ collection.name }}</div>
              </td>
              <td class="px-6 py-4 text-sm text-gray-900 dark:text-white">
                {{ formatNumber(collection.vector_dimension) }}
              </td>
              <td class="px-6 py-4 text-sm text-gray-900 dark:text-white">
                {{ formatNumber(collection.record_count) }}
              </td>
              <td class="px-6 py-4">
                <div class="text-sm text-gray-900 dark:text-white">{{ collection.description || 'No description' }}</div>
              </td>
              <td class="px-6 py-4">
                <div class="flex space-x-2">
                  <button
                    @click.stop="deleteCollection(collection.name)"
                    class="text-red-600 hover:text-red-900 dark:text-red-400 dark:hover:text-red-300"
                    title="Delete Collection"
                  >
                    <i class="fas fa-trash"></i>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Collection Detail Section -->
    <div v-if="selectedCollection && selectedCollectionInfo" class="space-y-6">
      <!-- Collection Info & Tools -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Collection Details -->
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
          <div class="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
            <h3 class="text-lg font-medium text-gray-900 dark:text-white">
              Collection: {{ selectedCollection }}
            </h3>
          </div>
          <div class="p-4">
            <div class="space-y-3">
              <div class="flex justify-between">
                <span class="text-sm font-medium text-gray-500 dark:text-gray-400">Dimension:</span>
                <span class="text-sm text-gray-900 dark:text-white">{{ formatNumber(selectedCollectionInfo.vector_dimension) }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-sm font-medium text-gray-500 dark:text-gray-400">Records:</span>
                <span class="text-sm text-gray-900 dark:text-white">{{ formatNumber(selectedCollectionInfo.record_count) }}</span>
              </div>
              <div v-if="selectedCollectionInfo.description">
                <span class="text-sm font-medium text-gray-500 dark:text-gray-400">Description:</span>
                <p class="text-sm text-gray-900 dark:text-white mt-1">{{ selectedCollectionInfo.description }}</p>
              </div>
            </div>

            <!-- Upload Data -->
            <div class="mt-6">
              <h4 class="text-base font-medium text-gray-900 dark:text-white mb-3">Upload Data</h4>
              <div class="space-y-3">
                <div>
                  <label class="form-label">CSV/JSON File</label>
                  <input
                    id="uploadFile"
                    type="file"
                    @change="onFileChange"
                    accept=".csv,.json"
                    class="input-primary"
                  >
                  <p class="text-xs text-gray-600 dark:text-gray-400 mt-1">
                    Upload CSV or JSON file with data to add to this collection.
                  </p>
                </div>
                <div>
                  <label class="form-label">Text Field Name</label>
                  <input
                    v-model="uploadForm.textField"
                    type="text"
                    placeholder="Field name for generating embeddings"
                    class="input-primary"
                  >
                  <p class="text-xs text-gray-600 dark:text-gray-400 mt-1">
                    Specify which field contains text for generating vector embeddings.
                  </p>
                </div>
                <button 
                  @click="uploadData"
                  :disabled="!uploadForm.file || !uploadForm.textField"
                  class="btn btn-success btn-sm"
                >
                  <i class="fas fa-upload mr-2"></i>Upload & Generate Embeddings
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Vector Search -->
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
          <div class="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
            <h3 class="text-lg font-medium text-gray-900 dark:text-white">Vector Search</h3>
          </div>
          <div class="p-4">
            <div class="space-y-3">
              <div>
                <label class="form-label">Search Text</label>
                <input
                  v-model="searchForm.text"
                  type="text"
                  placeholder="Enter text to search for similar records"
                  class="input-primary"
                >
              </div>
              <div>
                <label class="form-label">Result Limit</label>
                <input
                  v-model.number="searchForm.limit"
                  type="number"
                  min="1"
                  max="1000"
                  class="input-primary"
                >
              </div>
              <button 
                @click="searchVectors"
                :disabled="!searchForm.text.trim()"
                class="btn btn-primary btn-sm"
              >
                <i class="fas fa-search mr-2"></i>Search
              </button>
            </div>

            <!-- Search Results -->
            <div v-if="searchResults.length > 0" class="mt-4">
              <h5 class="text-sm font-medium text-gray-900 dark:text-white mb-2">Search Results</h5>
              <div class="space-y-2 max-h-64 overflow-y-auto">
                <div 
                  v-for="result in searchResults" 
                  :key="result.id"
                  class="p-2 border border-gray-200 dark:border-gray-600 rounded text-sm"
                >
                  <div class="flex justify-between items-start">
                    <span class="font-medium">ID: {{ result.id }}</span>
                    <span class="text-xs text-gray-500">Distance: {{ result.distance.toFixed(4) }}</span>
                  </div>
                  <div class="text-xs text-gray-600 dark:text-gray-400 truncate">
                    {{ JSON.stringify(result).substring(0, 100) }}...
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Records Table -->
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
        <div class="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
          <div class="flex justify-between items-center">
            <h3 class="text-lg font-medium text-gray-900 dark:text-white">Collection Records</h3>
            <div class="flex items-center space-x-2">
              <input
                v-model="filterExpression"
                type="text"
                placeholder="Filter expression (e.g. id > 100)"
                class="input-primary text-sm"
                style="max-width: 300px;"
              >
              <button 
                @click="applyFilter"
                class="btn btn-primary btn-sm"
              >
                <i class="fas fa-filter mr-1"></i>Apply Filter
              </button>
            </div>
          </div>
        </div>
        
        <div v-if="recordsLoading" class="p-8 text-center">
          <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
          <p class="mt-2 text-gray-600 dark:text-gray-400">Loading records...</p>
        </div>

        <div v-else-if="records.length === 0" class="p-8 text-center">
          <div class="text-gray-400">
            <i class="fas fa-table text-4xl mb-4"></i>
            <p class="text-lg">No records found</p>
            <p class="text-sm">Upload data to populate this collection</p>
          </div>
        </div>

        <div v-else>
          <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead class="bg-gray-50 dark:bg-gray-700">
                <tr>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    ID
                  </th>
                  <th 
                    v-for="column in recordColumns.slice(0, 5)" 
                    :key="column"
                    class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider"
                  >
                    {{ column }}
                  </th>
                  <th class="px-6 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody class="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                <tr v-for="record in paginatedRecords" :key="record.id" class="hover:bg-gray-50 dark:hover:bg-gray-700">
                  <td class="px-6 py-4 text-sm font-mono text-gray-900 dark:text-white">
                    {{ record.id }}
                  </td>
                  <td 
                    v-for="column in recordColumns.slice(0, 5)" 
                    :key="column"
                    class="px-6 py-4 text-sm text-gray-900 dark:text-white"
                  >
                    <div class="max-w-xs truncate" :title="String(record[column])">
                      {{ record[column] }}
                    </div>
                  </td>
                  <td class="px-6 py-4 text-center">
                    <div class="flex justify-center space-x-2">
                      <button
                        @click="viewRecord(record)"
                        class="text-blue-600 hover:text-blue-900 dark:text-blue-400 dark:hover:text-blue-300"
                        title="View Record"
                      >
                        <i class="fas fa-eye"></i>
                      </button>
                      <button
                        @click="deleteRecord(record.id)"
                        class="text-red-600 hover:text-red-900 dark:text-red-400 dark:hover:text-red-300"
                        title="Delete Record"
                      >
                        <i class="fas fa-trash"></i>
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Pagination -->
          <div class="px-4 py-3 border-t border-gray-200 dark:border-gray-700 flex justify-between items-center">
            <div class="text-sm text-gray-700 dark:text-gray-300">
              Showing {{ formatNumber(paginatedRecords.length) }} of {{ formatNumber(totalRecords) }} records
            </div>
            <div class="flex items-center space-x-2">
              <button
                @click="onPageChange(currentPage - 1)"
                :disabled="currentPage === 1"
                class="btn btn-outline-secondary btn-sm"
              >
                <i class="fas fa-chevron-left mr-1"></i>Previous
              </button>
              <span class="text-sm text-gray-700 dark:text-gray-300">
                Page {{ currentPage }} of {{ totalPages }}
              </span>
              <button
                @click="onPageChange(currentPage + 1)"
                :disabled="currentPage === totalPages"
                class="btn btn-outline-secondary btn-sm"
              >
                Next<i class="fas fa-chevron-right ml-1"></i>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Create Collection Modal -->
    <div v-if="showCreateModal" class="modal-overlay" @click.self="showCreateModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h3 class="modal-title">Create New Collection</h3>
          <button @click="showCreateModal = false" class="modal-close">
            <i class="fas fa-times"></i>
          </button>
        </div>
        
        <div class="modal-body">
          <form @submit.prevent="createCollection" class="space-y-4">
            <div>
              <label class="form-label">Collection Name *</label>
              <input
                v-model="createForm.name"
                type="text"
                required
                placeholder="Enter collection name"
                class="input-primary"
              >
            </div>
            
            <div>
              <label class="form-label">Vector Dimension *</label>
              <input
                v-model.number="createForm.vector_dimension"
                type="number"
                required
                min="1"
                class="input-primary"
              >
              <p class="text-sm text-gray-600 dark:text-gray-400 mt-1">
                Dimension of vector embeddings (typically 384 for all-MiniLM-L6-v2)
              </p>
            </div>
            
            <div>
              <label class="form-label">Description (optional)</label>
              <textarea
                v-model="createForm.description"
                rows="3"
                placeholder="Enter description"
                class="input-primary"
              ></textarea>
            </div>
          </form>
        </div>
        
        <div class="modal-footer">
          <button @click="showCreateModal = false" class="btn btn-secondary">
            Cancel
          </button>
          <button @click="createCollection" class="btn btn-primary">
            Create
          </button>
        </div>
      </div>
    </div>

    <!-- Record Detail Modal -->
    <div v-if="showRecordModal" class="modal-overlay" @click.self="showRecordModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h3 class="modal-title">Record Details</h3>
          <button @click="showRecordModal = false" class="modal-close">
            <i class="fas fa-times"></i>
          </button>
        </div>
        
        <div class="modal-body" v-if="selectedRecord">
          <div class="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
            <pre class="text-sm text-gray-900 dark:text-white whitespace-pre-wrap">{{ JSON.stringify(selectedRecord, null, 2) }}</pre>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>