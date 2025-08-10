<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useToast } from '@/stores/toast'
import { apiRequest } from '@/services/api'

interface Config {
  id: string
  key: string
  value: string
  value_type: 'string' | 'integer' | 'float' | 'boolean' | 'text'
  category: string
  description: string
  is_sensitive: boolean
  created_at: string
  updated_at: string
}

interface Category {
  name: string
  count: number
}

const toast = useToast()

// Reactive state
const configs = ref<Config[]>([])
const categories = ref<Category[]>([])
const loading = ref(true)
const selectedCategory = ref('')
const searchQuery = ref('')

// Modal states
const showCreateModal = ref(false)
const showDeleteModal = ref(false)
const editingConfig = ref<Config | null>(null)
const deletingConfig = ref<Config | null>(null)

// Form data
const configForm = ref({
  key: '',
  value: '',
  value_type: 'string' as 'string' | 'integer' | 'float' | 'boolean' | 'text',
  category: '',
  description: '',
  is_sensitive: false
})

// Computed
const filteredConfigs = computed(() => {
  let filtered = configs.value

  if (selectedCategory.value) {
    filtered = filtered.filter(config => config.category === selectedCategory.value)
  }

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(config => 
      config.key.toLowerCase().includes(query) ||
      config.description.toLowerCase().includes(query) ||
      config.category.toLowerCase().includes(query) ||
      (!config.is_sensitive && config.value.toLowerCase().includes(query))
    )
  }

  return filtered.sort((a, b) => a.key.localeCompare(b.key))
})

// API calls
const loadConfigs = async () => {
  try {
    loading.value = true
    const response = await apiRequest('/api/v1/admin/config')
    configs.value = response.configs
    
    // Extract categories
    const categoryMap = new Map<string, number>()
    configs.value.forEach(config => {
      const count = categoryMap.get(config.category) || 0
      categoryMap.set(config.category, count + 1)
    })
    
    categories.value = Array.from(categoryMap.entries()).map(([name, count]) => ({
      name,
      count
    })).sort((a, b) => a.name.localeCompare(b.name))
  } catch (error) {
    toast.error('Failed to load configurations: ' + (error as Error).message)
  } finally {
    loading.value = false
  }
}

const saveConfig = async () => {
  try {
    // Validate form
    if (!configForm.value.key || !configForm.value.category) {
      toast.error('Please fill in all required fields')
      return
    }

    // Type validation and conversion
    let convertedValue = configForm.value.value
    if (configForm.value.value_type === 'integer') {
      const intValue = parseInt(configForm.value.value)
      if (isNaN(intValue)) {
        toast.error('Invalid integer value')
        return
      }
      convertedValue = intValue.toString()
    } else if (configForm.value.value_type === 'float') {
      const floatValue = parseFloat(configForm.value.value)
      if (isNaN(floatValue)) {
        toast.error('Invalid float value')
        return
      }
      convertedValue = floatValue.toString()
    } else if (configForm.value.value_type === 'boolean') {
      convertedValue = configForm.value.value.toLowerCase() === 'true' ? 'true' : 'false'
    }

    const configData = {
      ...configForm.value,
      value: convertedValue
    }

    const isEdit = editingConfig.value !== null
    const url = isEdit ? `/api/v1/admin/config/${editingConfig.value!.id}` : '/api/v1/admin/config'
    const method = isEdit ? 'PUT' : 'POST'

    const response = await apiRequest(url, {
      method,
      body: JSON.stringify(configData)
    })

    toast.success(response.message)
    showCreateModal.value = false
    resetForm()
    await loadConfigs()
  } catch (error) {
    toast.error('Error saving configuration: ' + (error as Error).message)
  }
}

const editConfig = (config: Config) => {
  editingConfig.value = config
  configForm.value = {
    key: config.key,
    value: config.value,
    value_type: config.value_type,
    category: config.category,
    description: config.description,
    is_sensitive: config.is_sensitive
  }
  showCreateModal.value = true
}

const confirmDelete = (config: Config) => {
  deletingConfig.value = config
  showDeleteModal.value = true
}

const deleteConfig = async () => {
  if (!deletingConfig.value) return

  try {
    const response = await apiRequest(`/api/v1/admin/config/${deletingConfig.value.id}`, {
      method: 'DELETE'
    })

    toast.success(response.message)
    showDeleteModal.value = false
    deletingConfig.value = null
    await loadConfigs()
  } catch (error) {
    toast.error('Error deleting configuration: ' + (error as Error).message)
  }
}

const resetForm = () => {
  editingConfig.value = null
  configForm.value = {
    key: '',
    value: '',
    value_type: 'string',
    category: '',
    description: '',
    is_sensitive: false
  }
}

const openCreateModal = () => {
  resetForm()
  showCreateModal.value = true
}

const getValueTypeDisplay = (type: string) => {
  const types = {
    string: 'String',
    integer: 'Integer',
    float: 'Float',
    boolean: 'Boolean',
    text: 'Text (Multi-line)'
  }
  return types[type as keyof typeof types] || type
}

const formatValue = (config: Config) => {
  if (config.is_sensitive) {
    return '••••••••'
  }
  
  if (config.value_type === 'text' && config.value.length > 50) {
    return config.value.substring(0, 50) + '...'
  }
  
  return config.value
}

const getCategoryBadgeClass = (category: string) => {
  const hash = category.split('').reduce((a, b) => {
    a = ((a << 5) - a) + b.charCodeAt(0)
    return a & a
  }, 0)
  
  const colors = [
    'bg-blue-100 text-blue-800',
    'bg-green-100 text-green-800',
    'bg-yellow-100 text-yellow-800',
    'bg-red-100 text-red-800',
    'bg-purple-100 text-purple-800',
    'bg-pink-100 text-pink-800',
    'bg-indigo-100 text-indigo-800'
  ]
  
  return colors[Math.abs(hash) % colors.length]
}

// Lifecycle
onMounted(async () => {
  await loadConfigs()
})
</script>

<template>
  <div class="p-6 max-w-7xl mx-auto">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6">
      <div class="flex items-center mb-4 sm:mb-0">
        <i class="fas fa-cogs text-2xl text-purple-600 mr-3"></i>
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Configuration Management</h1>
      </div>
      <button 
        @click="openCreateModal"
        class="btn btn-primary"
      >
        <i class="fas fa-plus mr-2"></i>New Configuration
      </button>
    </div>

    <!-- Filters -->
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4 mb-6">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Search Configurations
          </label>
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search by key, description, or category..."
            class="input-primary"
          >
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Filter by Category
          </label>
          <select
            v-model="selectedCategory"
            class="input-primary"
          >
            <option value="">All Categories</option>
            <option 
              v-for="category in categories" 
              :key="category.name" 
              :value="category.name"
            >
              {{ category.name }} ({{ category.count }})
            </option>
          </select>
        </div>
        <div class="flex items-end">
          <button 
            @click="loadConfigs"
            class="btn btn-outline-secondary w-full"
          >
            <i class="fas fa-refresh mr-2"></i>Refresh
          </button>
        </div>
      </div>
    </div>

    <!-- Configurations Table -->
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
      <div class="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
        <h3 class="text-lg font-medium text-gray-900 dark:text-white">System Configurations</h3>
      </div>
      
      <div v-if="loading" class="p-8 text-center">
        <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
        <p class="mt-2 text-gray-600 dark:text-gray-400">Loading configurations...</p>
      </div>

      <div v-else-if="filteredConfigs.length === 0" class="p-8 text-center">
        <div class="text-gray-400">
          <i class="fas fa-cogs text-4xl mb-4"></i>
          <p class="text-lg">No configurations found</p>
          <p class="text-sm">Create your first configuration or adjust your filters</p>
        </div>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead class="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                Key
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                Value
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                Type
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                Category
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
            <tr v-for="config in filteredConfigs" :key="config.id" class="hover:bg-gray-50 dark:hover:bg-gray-700">
              <td class="px-6 py-4">
                <div class="flex items-center">
                  <div class="text-sm font-medium text-gray-900 dark:text-white">{{ config.key }}</div>
                  <i v-if="config.is_sensitive" class="fas fa-lock text-yellow-500 ml-2" title="Sensitive"></i>
                </div>
              </td>
              <td class="px-6 py-4">
                <div class="text-sm text-gray-900 dark:text-white font-mono">
                  {{ formatValue(config) }}
                </div>
              </td>
              <td class="px-6 py-4">
                <span class="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-800 rounded">
                  {{ getValueTypeDisplay(config.value_type) }}
                </span>
              </td>
              <td class="px-6 py-4">
                <span :class="['px-2 py-1 text-xs font-medium rounded', getCategoryBadgeClass(config.category)]">
                  {{ config.category }}
                </span>
              </td>
              <td class="px-6 py-4">
                <div class="text-sm text-gray-900 dark:text-white max-w-xs truncate" :title="config.description">
                  {{ config.description }}
                </div>
              </td>
              <td class="px-6 py-4">
                <div class="flex space-x-2">
                  <button
                    @click="editConfig(config)"
                    class="text-indigo-600 hover:text-indigo-900 dark:text-indigo-400 dark:hover:text-indigo-300"
                    title="Edit"
                  >
                    <i class="fas fa-edit"></i>
                  </button>
                  <button
                    @click="confirmDelete(config)"
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

    <!-- Create/Edit Configuration Modal -->
    <div v-if="showCreateModal" class="modal-overlay" @click.self="showCreateModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h3 class="modal-title">
            {{ editingConfig ? 'Edit Configuration' : 'Create Configuration' }}
          </h3>
          <button @click="showCreateModal = false" class="modal-close">
            <i class="fas fa-times"></i>
          </button>
        </div>
        
        <div class="modal-body">
          <form @submit.prevent="saveConfig" class="space-y-4">
            <div>
              <label class="form-label">Key *</label>
              <input
                v-model="configForm.key"
                type="text"
                required
                :disabled="editingConfig !== null"
                class="input-primary"
                placeholder="configuration.key.name"
              >
            </div>
            
            <div>
              <label class="form-label">Value</label>
              <input
                v-if="configForm.value_type !== 'text'"
                v-model="configForm.value"
                type="text"
                class="input-primary"
                :placeholder="configForm.value_type === 'boolean' ? 'true or false' : 'Enter value'"
              >
              <textarea
                v-else
                v-model="configForm.value"
                rows="4"
                class="input-primary"
                placeholder="Enter multi-line text value"
              ></textarea>
            </div>
            
            <div>
              <label class="form-label">Value Type *</label>
              <select
                v-model="configForm.value_type"
                required
                class="input-primary"
              >
                <option value="string">String</option>
                <option value="integer">Integer</option>
                <option value="float">Float</option>
                <option value="boolean">Boolean</option>
                <option value="text">Text (Multi-line)</option>
              </select>
            </div>
            
            <div>
              <label class="form-label">Category *</label>
              <input
                v-model="configForm.category"
                type="text"
                required
                class="input-primary"
                placeholder="database, api, ui, security, etc."
                list="categoryOptions"
              >
              <datalist id="categoryOptions">
                <option v-for="category in categories" :key="category.name" :value="category.name">
                  {{ category.name }}
                </option>
              </datalist>
            </div>
            
            <div>
              <label class="form-label">Description</label>
              <textarea
                v-model="configForm.description"
                rows="3"
                class="input-primary"
                placeholder="Describe what this configuration controls"
              ></textarea>
            </div>
            
            <div class="flex items-center">
              <input
                v-model="configForm.is_sensitive"
                type="checkbox"
                id="is_sensitive"
                class="w-4 h-4 text-purple-600 bg-gray-100 border-gray-300 rounded focus:ring-purple-500 dark:focus:ring-purple-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
              >
              <label for="is_sensitive" class="ml-2 text-sm font-medium text-gray-900 dark:text-gray-300">
                Sensitive (mask value in display)
              </label>
            </div>
          </form>
        </div>
        
        <div class="modal-footer">
          <button @click="showCreateModal = false" class="btn btn-secondary">
            Cancel
          </button>
          <button @click="saveConfig" class="btn btn-primary">
            {{ editingConfig ? 'Update' : 'Create' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Delete Confirmation Modal -->
    <div v-if="showDeleteModal" class="modal-overlay" @click.self="showDeleteModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h3 class="modal-title">Confirm Deletion</h3>
          <button @click="showDeleteModal = false" class="modal-close">
            <i class="fas fa-times"></i>
          </button>
        </div>
        
        <div class="modal-body">
          <div class="flex items-center">
            <div class="flex-shrink-0">
              <i class="fas fa-exclamation-triangle text-red-500 text-2xl"></i>
            </div>
            <div class="ml-4">
              <h4 class="text-lg font-medium text-gray-900 dark:text-white">
                Delete Configuration
              </h4>
              <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
                Are you sure you want to delete the configuration "{{ deletingConfig?.key }}"?
                This action cannot be undone and may affect application functionality.
              </p>
            </div>
          </div>
        </div>
        
        <div class="modal-footer">
          <button @click="showDeleteModal = false" class="btn btn-secondary">
            Cancel
          </button>
          <button @click="deleteConfig" class="btn btn-danger">
            Delete
          </button>
        </div>
      </div>
    </div>
  </div>
</template>