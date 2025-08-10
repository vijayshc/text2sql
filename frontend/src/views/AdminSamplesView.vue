<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useToast } from '@/stores/toast'
import { apiRequest } from '@/services/api'

interface Sample {
  id: string
  name: string
  description: string
  category: string
  sql_query: string
  natural_language: string
  database_schema: string
  tags: string[]
  difficulty: 'beginner' | 'intermediate' | 'advanced'
  is_active: boolean
  created_at: string
  updated_at: string
}

const toast = useToast()

// Reactive state
const samples = ref<Sample[]>([])
const loading = ref(true)
const searchQuery = ref('')
const selectedCategory = ref('')
const selectedDifficulty = ref('')
const showActiveOnly = ref(true)

// Modal states
const showCreateModal = ref(false)
const showViewModal = ref(false)
const editingSample = ref<Sample | null>(null)
const selectedSample = ref<Sample | null>(null)

// Form data
const sampleForm = ref({
  name: '',
  description: '',
  category: '',
  sql_query: '',
  natural_language: '',
  database_schema: '',
  tags: '',
  difficulty: 'beginner' as 'beginner' | 'intermediate' | 'advanced',
  is_active: true
})

// Computed
const categories = computed(() => {
  const categorySet = new Set(samples.value.map(sample => sample.category))
  return Array.from(categorySet).sort()
})

const filteredSamples = computed(() => {
  let filtered = samples.value

  if (showActiveOnly.value) {
    filtered = filtered.filter(sample => sample.is_active)
  }

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(sample => 
      sample.name.toLowerCase().includes(query) ||
      sample.description.toLowerCase().includes(query) ||
      sample.natural_language.toLowerCase().includes(query) ||
      sample.tags.some(tag => tag.toLowerCase().includes(query))
    )
  }

  if (selectedCategory.value) {
    filtered = filtered.filter(sample => sample.category === selectedCategory.value)
  }

  if (selectedDifficulty.value) {
    filtered = filtered.filter(sample => sample.difficulty === selectedDifficulty.value)
  }

  return filtered.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
})

// API calls
const loadSamples = async () => {
  try {
    loading.value = true
    const response = await apiRequest('/api/v1/admin/samples')
    samples.value = response.samples
  } catch (error) {
    toast.error('Failed to load samples: ' + (error as Error).message)
  } finally {
    loading.value = false
  }
}

const saveSample = async () => {
  try {
    const sampleData = {
      ...sampleForm.value,
      tags: sampleForm.value.tags.split(',').map(t => t.trim()).filter(t => t.length > 0)
    }

    // Validation
    if (!sampleData.name || !sampleData.sql_query || !sampleData.natural_language) {
      toast.error('Please fill in all required fields')
      return
    }

    const isEdit = editingSample.value !== null
    const url = isEdit ? `/api/v1/admin/samples/${editingSample.value!.id}` : '/api/v1/admin/samples'
    const method = isEdit ? 'PUT' : 'POST'

    const response = await apiRequest(url, {
      method,
      body: JSON.stringify(sampleData)
    })

    toast.success(response.message)
    showCreateModal.value = false
    resetForm()
    await loadSamples()
  } catch (error) {
    toast.error('Error saving sample: ' + (error as Error).message)
  }
}

const editSample = (sample: Sample) => {
  editingSample.value = sample
  sampleForm.value = {
    name: sample.name,
    description: sample.description,
    category: sample.category,
    sql_query: sample.sql_query,
    natural_language: sample.natural_language,
    database_schema: sample.database_schema,
    tags: sample.tags.join(', '),
    difficulty: sample.difficulty,
    is_active: sample.is_active
  }
  showCreateModal.value = true
}

const viewSample = (sample: Sample) => {
  selectedSample.value = sample
  showViewModal.value = true
}

const deleteSample = async (sample: Sample) => {
  if (!confirm(`Are you sure you want to delete the sample "${sample.name}"? This action cannot be undone.`)) {
    return
  }

  try {
    const response = await apiRequest(`/api/v1/admin/samples/${sample.id}`, {
      method: 'DELETE'
    })
    toast.success(response.message)
    await loadSamples()
  } catch (error) {
    toast.error('Error deleting sample: ' + (error as Error).message)
  }
}

const toggleSampleStatus = async (sample: Sample) => {
  try {
    const response = await apiRequest(`/api/v1/admin/samples/${sample.id}/toggle`, {
      method: 'PUT'
    })
    toast.success(response.message)
    await loadSamples()
  } catch (error) {
    toast.error('Error updating sample status: ' + (error as Error).message)
  }
}

const resetForm = () => {
  editingSample.value = null
  sampleForm.value = {
    name: '',
    description: '',
    category: '',
    sql_query: '',
    natural_language: '',
    database_schema: '',
    tags: '',
    difficulty: 'beginner',
    is_active: true
  }
}

const openCreateModal = () => {
  resetForm()
  showCreateModal.value = true
}

const getDifficultyBadgeClass = (difficulty: string) => {
  switch (difficulty) {
    case 'beginner': return 'bg-green-100 text-green-800'
    case 'intermediate': return 'bg-yellow-100 text-yellow-800'
    case 'advanced': return 'bg-red-100 text-red-800'
    default: return 'bg-gray-100 text-gray-800'
  }
}

// Lifecycle
onMounted(async () => {
  await loadSamples()
})
</script>

<template>
  <div class="p-6 max-w-7xl mx-auto">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6">
      <div class="flex items-center mb-4 sm:mb-0">
        <i class="fas fa-flask text-2xl text-orange-600 mr-3"></i>
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Manage Samples</h1>
      </div>
      <button 
        @click="openCreateModal"
        class="btn btn-primary"
      >
        <i class="fas fa-plus mr-2"></i>Add Sample
      </button>
    </div>

    <!-- Filters -->
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4 mb-6">
      <div class="grid grid-cols-1 md:grid-cols-5 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Search Samples
          </label>
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search samples..."
            class="input-primary"
          >
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Category
          </label>
          <select
            v-model="selectedCategory"
            class="input-primary"
          >
            <option value="">All Categories</option>
            <option 
              v-for="category in categories" 
              :key="category" 
              :value="category"
            >
              {{ category }}
            </option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Difficulty
          </label>
          <select
            v-model="selectedDifficulty"
            class="input-primary"
          >
            <option value="">All Levels</option>
            <option value="beginner">Beginner</option>
            <option value="intermediate">Intermediate</option>
            <option value="advanced">Advanced</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Status
          </label>
          <div class="flex items-center mt-2">
            <input
              v-model="showActiveOnly"
              type="checkbox"
              id="showActiveOnly"
              class="w-4 h-4 text-orange-600 bg-gray-100 border-gray-300 rounded focus:ring-orange-500"
            >
            <label for="showActiveOnly" class="ml-2 text-sm text-gray-900 dark:text-white">
              Active only
            </label>
          </div>
        </div>
        <div class="flex items-end">
          <button 
            @click="loadSamples"
            class="btn btn-outline-secondary w-full"
          >
            <i class="fas fa-refresh mr-2"></i>Refresh
          </button>
        </div>
      </div>
    </div>

    <!-- Samples Table -->
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
      <div class="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
        <h3 class="text-lg font-medium text-gray-900 dark:text-white">
          Samples ({{ filteredSamples.length }})
        </h3>
      </div>
      
      <div v-if="loading" class="p-8 text-center">
        <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-orange-600"></div>
        <p class="mt-2 text-gray-600 dark:text-gray-400">Loading samples...</p>
      </div>

      <div v-else-if="filteredSamples.length === 0" class="p-8 text-center">
        <div class="text-gray-400">
          <i class="fas fa-flask text-4xl mb-4"></i>
          <p class="text-lg">No samples found</p>
          <p class="text-sm">Create your first sample or adjust your filters</p>
        </div>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead class="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                Name
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                Category
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                Natural Language
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                Difficulty
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                Status
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody class="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
            <tr v-for="sample in filteredSamples" :key="sample.id" class="hover:bg-gray-50 dark:hover:bg-gray-700">
              <td class="px-6 py-4">
                <div>
                  <div class="text-sm font-medium text-gray-900 dark:text-white">{{ sample.name }}</div>
                  <div class="text-sm text-gray-500 dark:text-gray-400 max-w-xs truncate">{{ sample.description }}</div>
                </div>
              </td>
              <td class="px-6 py-4">
                <span class="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded">
                  {{ sample.category }}
                </span>
              </td>
              <td class="px-6 py-4">
                <div class="text-sm text-gray-900 dark:text-white max-w-md truncate" :title="sample.natural_language">
                  {{ sample.natural_language }}
                </div>
              </td>
              <td class="px-6 py-4">
                <span :class="['px-2 py-1 text-xs font-medium rounded', getDifficultyBadgeClass(sample.difficulty)]">
                  {{ sample.difficulty }}
                </span>
              </td>
              <td class="px-6 py-4">
                <div class="flex items-center">
                  <button
                    @click="toggleSampleStatus(sample)"
                    :class="[
                      'relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-orange-500 focus:ring-offset-2',
                      sample.is_active ? 'bg-orange-600' : 'bg-gray-200'
                    ]"
                  >
                    <span
                      :class="[
                        'pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow transform ring-0 transition duration-200 ease-in-out',
                        sample.is_active ? 'translate-x-5' : 'translate-x-0'
                      ]"
                    ></span>
                  </button>
                  <span class="ml-2 text-sm text-gray-900 dark:text-white">
                    {{ sample.is_active ? 'Active' : 'Inactive' }}
                  </span>
                </div>
              </td>
              <td class="px-6 py-4">
                <div class="flex space-x-2">
                  <button
                    @click="viewSample(sample)"
                    class="text-blue-600 hover:text-blue-900 dark:text-blue-400 dark:hover:text-blue-300"
                    title="View Sample"
                  >
                    <i class="fas fa-eye"></i>
                  </button>
                  <button
                    @click="editSample(sample)"
                    class="text-indigo-600 hover:text-indigo-900 dark:text-indigo-400 dark:hover:text-indigo-300"
                    title="Edit"
                  >
                    <i class="fas fa-edit"></i>
                  </button>
                  <button
                    @click="deleteSample(sample)"
                    class="text-red-600 hover:text-red-900 dark:text-red-400 dark:hover:text-red-300"
                    title="Delete"
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

    <!-- Create/Edit Sample Modal -->
    <div v-if="showCreateModal" class="modal-overlay" @click.self="showCreateModal = false">
      <div class="modal-content modal-wide">
        <div class="modal-header">
          <h3 class="modal-title">
            {{ editingSample ? 'Edit Sample' : 'Create Sample' }}
          </h3>
          <button @click="showCreateModal = false" class="modal-close">
            <i class="fas fa-times"></i>
          </button>
        </div>
        
        <div class="modal-body">
          <form @submit.prevent="saveSample" class="space-y-4">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label class="form-label">Sample Name *</label>
                <input
                  v-model="sampleForm.name"
                  type="text"
                  required
                  class="input-primary"
                  placeholder="Basic SELECT query"
                >
              </div>
              <div>
                <label class="form-label">Category</label>
                <input
                  v-model="sampleForm.category"
                  type="text"
                  class="input-primary"
                  placeholder="SELECT, JOIN, AGGREGATE, etc."
                  list="categoryOptions"
                >
                <datalist id="categoryOptions">
                  <option v-for="category in categories" :key="category" :value="category">
                    {{ category }}
                  </option>
                </datalist>
              </div>
            </div>

            <div>
              <label class="form-label">Description</label>
              <textarea
                v-model="sampleForm.description"
                rows="2"
                class="input-primary"
                placeholder="Brief description of what this sample demonstrates"
              ></textarea>
            </div>

            <div>
              <label class="form-label">Natural Language Query *</label>
              <textarea
                v-model="sampleForm.natural_language"
                required
                rows="3"
                class="input-primary"
                placeholder="Show me all customers who have placed orders in the last 30 days"
              ></textarea>
            </div>

            <div>
              <label class="form-label">SQL Query *</label>
              <textarea
                v-model="sampleForm.sql_query"
                required
                rows="6"
                class="input-primary font-mono text-sm"
                placeholder="SELECT * FROM customers WHERE ..."
              ></textarea>
            </div>

            <div>
              <label class="form-label">Database Schema</label>
              <textarea
                v-model="sampleForm.database_schema"
                rows="3"
                class="input-primary font-mono text-sm"
                placeholder="customers(id, name, email), orders(id, customer_id, date), ..."
              ></textarea>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label class="form-label">Difficulty</label>
                <select
                  v-model="sampleForm.difficulty"
                  class="input-primary"
                >
                  <option value="beginner">Beginner</option>
                  <option value="intermediate">Intermediate</option>
                  <option value="advanced">Advanced</option>
                </select>
              </div>
              <div>
                <label class="form-label">Tags</label>
                <input
                  v-model="sampleForm.tags"
                  type="text"
                  class="input-primary"
                  placeholder="join, aggregation, window"
                >
              </div>
              <div class="flex items-center mt-6">
                <input
                  v-model="sampleForm.is_active"
                  type="checkbox"
                  id="is_active"
                  class="w-4 h-4 text-orange-600 bg-gray-100 border-gray-300 rounded focus:ring-orange-500"
                >
                <label for="is_active" class="ml-2 text-sm font-medium text-gray-900 dark:text-gray-300">
                  Active
                </label>
              </div>
            </div>
          </form>
        </div>
        
        <div class="modal-footer">
          <button @click="showCreateModal = false" class="btn btn-secondary">
            Cancel
          </button>
          <button @click="saveSample" class="btn btn-primary">
            {{ editingSample ? 'Update' : 'Create' }}
          </button>
        </div>
      </div>
    </div>

    <!-- View Sample Modal -->
    <div v-if="showViewModal" class="modal-overlay" @click.self="showViewModal = false">
      <div class="modal-content modal-wide">
        <div class="modal-header">
          <h3 class="modal-title">{{ selectedSample?.name }}</h3>
          <button @click="showViewModal = false" class="modal-close">
            <i class="fas fa-times"></i>
          </button>
        </div>
        
        <div class="modal-body" v-if="selectedSample">
          <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div class="lg:col-span-2 space-y-4">
              <div>
                <h5 class="text-lg font-medium text-gray-900 dark:text-white mb-2">Natural Language Query</h5>
                <p class="text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-700 p-3 rounded">
                  {{ selectedSample.natural_language }}
                </p>
              </div>
              
              <div>
                <h5 class="text-lg font-medium text-gray-900 dark:text-white mb-2">SQL Query</h5>
                <pre class="text-sm bg-gray-900 text-green-400 p-4 rounded overflow-x-auto"><code>{{ selectedSample.sql_query }}</code></pre>
              </div>
              
              <div v-if="selectedSample.database_schema">
                <h5 class="text-lg font-medium text-gray-900 dark:text-white mb-2">Database Schema</h5>
                <pre class="text-sm bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white p-3 rounded overflow-x-auto">{{ selectedSample.database_schema }}</pre>
              </div>
              
              <div v-if="selectedSample.description">
                <h5 class="text-lg font-medium text-gray-900 dark:text-white mb-2">Description</h5>
                <p class="text-gray-700 dark:text-gray-300">{{ selectedSample.description }}</p>
              </div>
            </div>
            
            <div>
              <h5 class="text-lg font-medium text-gray-900 dark:text-white mb-4">Metadata</h5>
              <div class="space-y-3">
                <div class="flex justify-between">
                  <span class="text-sm font-medium text-gray-500 dark:text-gray-400">Category:</span>
                  <span class="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded">
                    {{ selectedSample.category }}
                  </span>
                </div>
                <div class="flex justify-between">
                  <span class="text-sm font-medium text-gray-500 dark:text-gray-400">Difficulty:</span>
                  <span :class="['px-2 py-1 text-xs font-medium rounded', getDifficultyBadgeClass(selectedSample.difficulty)]">
                    {{ selectedSample.difficulty }}
                  </span>
                </div>
                <div class="flex justify-between">
                  <span class="text-sm font-medium text-gray-500 dark:text-gray-400">Status:</span>
                  <span :class="[
                    'px-2 py-1 text-xs font-medium rounded',
                    selectedSample.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                  ]">
                    {{ selectedSample.is_active ? 'Active' : 'Inactive' }}
                  </span>
                </div>
                <div class="flex justify-between">
                  <span class="text-sm font-medium text-gray-500 dark:text-gray-400">Created:</span>
                  <span class="text-sm text-gray-900 dark:text-white">
                    {{ new Date(selectedSample.created_at).toLocaleDateString() }}
                  </span>
                </div>
                
                <div v-if="selectedSample.tags.length > 0" class="pt-2">
                  <h6 class="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">Tags</h6>
                  <div class="flex flex-wrap gap-1">
                    <span 
                      v-for="tag in selectedSample.tags" 
                      :key="tag"
                      class="px-2 py-1 text-xs bg-gray-100 text-gray-800 rounded"
                    >
                      {{ tag }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-wide {
  max-width: 4xl;
}
</style>