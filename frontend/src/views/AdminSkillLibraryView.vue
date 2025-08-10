<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useToast } from '@/stores/toast'
import { apiRequest } from '@/services/api'

interface Skill {
  skill_id: string
  name: string
  description: string
  category: string
  status: 'active' | 'draft' | 'deprecated'
  version: string
  tags: string[]
  prerequisites: string[]
  steps: string[]
  examples: string[]
  created_at: string
  updated_at: string
}

interface Category {
  value: string
  label: string
  count: number
}

const toast = useToast()

// Reactive state
const skills = ref<Skill[]>([])
const categories = ref<Category[]>([])
const loading = ref(true)
const searchQuery = ref('')
const selectedCategory = ref('')
const selectedStatus = ref('active')

// Modal states
const showCreateModal = ref(false)
const showDetailModal = ref(false)
const showImportModal = ref(false)
const editingSkill = ref<Skill | null>(null)
const selectedSkill = ref<Skill | null>(null)

// Form data
const skillForm = reactive({
  name: '',
  description: '',
  category: '',
  status: 'active' as 'active' | 'draft' | 'deprecated',
  version: '1.0',
  tags: '',
  prerequisites: '',
  steps: '',
  examples: ''
})

const importData = ref('')

// Computed
const filteredSkills = computed(() => {
  let filtered = skills.value

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(skill => 
      skill.name.toLowerCase().includes(query) ||
      skill.description.toLowerCase().includes(query) ||
      skill.tags.some(tag => tag.toLowerCase().includes(query))
    )
  }

  if (selectedCategory.value) {
    filtered = filtered.filter(skill => skill.category === selectedCategory.value)
  }

  if (selectedStatus.value) {
    filtered = filtered.filter(skill => skill.status === selectedStatus.value)
  }

  return filtered
})

// API calls
const loadCategories = async () => {
  try {
    const response = await apiRequest('/api/v1/admin/skills/categories')
    categories.value = response.categories
  } catch (error) {
    console.error('Error loading categories:', error)
  }
}

const loadSkills = async () => {
  try {
    loading.value = true
    const params = new URLSearchParams()
    if (selectedCategory.value) params.append('category', selectedCategory.value)
    if (selectedStatus.value) params.append('status', selectedStatus.value)
    
    const url = `/api/v1/admin/skills${params.toString() ? '?' + params.toString() : ''}`
    const response = await apiRequest(url)
    skills.value = response.skills
  } catch (error) {
    toast.error('Failed to load skills: ' + (error as Error).message)
  } finally {
    loading.value = false
  }
}

const searchSkills = async () => {
  if (!searchQuery.value.trim()) {
    await loadSkills()
    return
  }

  try {
    loading.value = true
    const response = await apiRequest('/api/v1/admin/skills/search', {
      method: 'POST',
      body: JSON.stringify({
        query: searchQuery.value,
        category: selectedCategory.value,
        limit: 50
      })
    })
    skills.value = response.results
    if (response.total > 0) {
      toast.info(`Found ${response.total} skills`)
    }
  } catch (error) {
    toast.error('Search failed: ' + (error as Error).message)
  } finally {
    loading.value = false
  }
}

const saveSkill = async () => {
  try {
    const skillData = {
      name: skillForm.name.trim(),
      description: skillForm.description.trim(),
      category: skillForm.category,
      status: skillForm.status,
      version: skillForm.version.trim(),
      tags: skillForm.tags.split(',').map(t => t.trim()).filter(t => t.length > 0),
      prerequisites: skillForm.prerequisites.split('\n').map(p => p.trim()).filter(p => p.length > 0),
      steps: skillForm.steps.split('\n').map(s => s.trim()).filter(s => s.length > 0),
      examples: skillForm.examples.split('\n').map(e => e.trim()).filter(e => e.length > 0)
    }

    // Validation
    if (!skillData.name || !skillData.description || !skillData.category || skillData.steps.length === 0) {
      toast.error('Please fill in all required fields')
      return
    }

    const isEdit = editingSkill.value !== null
    const url = isEdit ? `/api/v1/admin/skills/${editingSkill.value!.skill_id}` : '/api/v1/admin/skills'
    const method = isEdit ? 'PUT' : 'POST'

    const response = await apiRequest(url, {
      method,
      body: JSON.stringify(skillData)
    })

    toast.success(response.message)
    showCreateModal.value = false
    resetForm()
    await loadSkills()
  } catch (error) {
    toast.error('Error saving skill: ' + (error as Error).message)
  }
}

const editSkill = (skill: Skill) => {
  editingSkill.value = skill
  skillForm.name = skill.name
  skillForm.description = skill.description
  skillForm.category = skill.category
  skillForm.status = skill.status
  skillForm.version = skill.version
  skillForm.tags = skill.tags.join(', ')
  skillForm.prerequisites = skill.prerequisites.join('\n')
  skillForm.steps = skill.steps.join('\n')
  skillForm.examples = skill.examples.join('\n')
  showCreateModal.value = true
}

const viewSkill = async (skillId: string) => {
  try {
    const response = await apiRequest(`/api/v1/admin/skills/${skillId}`)
    selectedSkill.value = response.skill
    showDetailModal.value = true
  } catch (error) {
    toast.error('Error loading skill details: ' + (error as Error).message)
  }
}

const deleteSkill = async (skill: Skill) => {
  if (!confirm(`Are you sure you want to delete the skill "${skill.name}"? This action cannot be undone.`)) {
    return
  }

  try {
    const response = await apiRequest(`/api/v1/admin/skills/${skill.skill_id}`, {
      method: 'DELETE'
    })
    toast.success(response.message)
    await loadSkills()
  } catch (error) {
    toast.error('Error deleting skill: ' + (error as Error).message)
  }
}

const vectorizeSkills = async () => {
  if (!confirm('This will reprocess all skills into the vector store. This may take a few minutes. Continue?')) {
    return
  }

  try {
    toast.info('Processing skills... This may take a few minutes.')
    const response = await apiRequest('/api/v1/admin/skills/vectorize', {
      method: 'POST'
    })
    toast.success(response.message)
  } catch (error) {
    toast.error('Error vectorizing skills: ' + (error as Error).message)
  }
}

const importSkills = async () => {
  if (!importData.value.trim()) {
    toast.error('Please enter JSON data')
    return
  }

  try {
    const data = JSON.parse(importData.value)
    if (!data.skills || !Array.isArray(data.skills)) {
      throw new Error('Invalid format: expected {"skills": [...]}')
    }

    const response = await apiRequest('/api/v1/admin/skills/import', {
      method: 'POST',
      body: JSON.stringify(data)
    })

    showImportModal.value = false
    importData.value = ''

    let message = response.message
    if (response.errors && response.errors.length > 0) {
      message += `\n\nErrors:\n${response.errors.join('\n')}`
      toast.warning(message)
    } else {
      toast.success(message)
    }

    await loadSkills()
  } catch (error) {
    if (error instanceof SyntaxError) {
      toast.error('Invalid JSON format: ' + error.message)
    } else {
      toast.error('Import error: ' + (error as Error).message)
    }
  }
}

const resetForm = () => {
  editingSkill.value = null
  skillForm.name = ''
  skillForm.description = ''
  skillForm.category = ''
  skillForm.status = 'active'
  skillForm.version = '1.0'
  skillForm.tags = ''
  skillForm.prerequisites = ''
  skillForm.steps = ''
  skillForm.examples = ''
}

const openCreateModal = () => {
  resetForm()
  showCreateModal.value = true
}

const getStatusBadgeClass = (status: string) => {
  switch (status) {
    case 'active': return 'bg-green-100 text-green-800'
    case 'draft': return 'bg-yellow-100 text-yellow-800'
    case 'deprecated': return 'bg-red-100 text-red-800'
    default: return 'bg-gray-100 text-gray-800'
  }
}

// Lifecycle
onMounted(async () => {
  await Promise.all([loadCategories(), loadSkills()])
})
</script>

<template>
  <div class="p-6 max-w-7xl mx-auto">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6">
      <div class="flex items-center mb-4 sm:mb-0">
        <i class="fas fa-brain text-2xl text-blue-600 mr-3"></i>
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Skill Library Management</h1>
      </div>
      <div class="flex flex-wrap gap-2">
        <button 
          @click="openCreateModal"
          class="btn btn-primary"
        >
          <i class="fas fa-plus mr-2"></i>Add Skill
        </button>
        <button 
          @click="vectorizeSkills"
          class="btn btn-info"
        >
          <i class="fas fa-sync mr-2"></i>Reprocess Vector Store
        </button>
        <button 
          @click="showImportModal = true"
          class="btn btn-secondary"
        >
          <i class="fas fa-upload mr-2"></i>Import Skills
        </button>
      </div>
    </div>

    <!-- Filters -->
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4 mb-6">
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Search Skills
          </label>
          <div class="flex">
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Search skills..."
              class="input-primary flex-1"
              @keyup.enter="searchSkills"
            >
            <button 
              @click="searchSkills"
              class="ml-2 px-3 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              <i class="fas fa-search"></i>
            </button>
          </div>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Category
          </label>
          <select
            v-model="selectedCategory"
            @change="loadSkills"
            class="input-primary"
          >
            <option value="">All Categories</option>
            <option 
              v-for="category in categories" 
              :key="category.value" 
              :value="category.value"
            >
              {{ category.label }} ({{ category.count }})
            </option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Status
          </label>
          <select
            v-model="selectedStatus"
            @change="loadSkills"
            class="input-primary"
          >
            <option value="">All Status</option>
            <option value="active">Active</option>
            <option value="draft">Draft</option>
            <option value="deprecated">Deprecated</option>
          </select>
        </div>
        <div class="flex items-end">
          <button 
            @click="loadSkills"
            class="btn btn-outline-secondary w-full"
          >
            <i class="fas fa-refresh mr-2"></i>Refresh
          </button>
        </div>
      </div>
    </div>

    <!-- Skills Table -->
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
      <div class="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
        <h3 class="text-lg font-medium text-gray-900 dark:text-white">Skills</h3>
      </div>
      
      <div v-if="loading" class="p-8 text-center">
        <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <p class="mt-2 text-gray-600 dark:text-gray-400">Loading skills...</p>
      </div>

      <div v-else-if="filteredSkills.length === 0" class="p-8 text-center">
        <div class="text-gray-400">
          <i class="fas fa-brain text-4xl mb-4"></i>
          <p class="text-lg">No skills found</p>
          <p class="text-sm">Create your first skill or adjust your filters</p>
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
                Description
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                Tags
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                Status
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                Version
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody class="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
            <tr v-for="skill in filteredSkills" :key="skill.skill_id" class="hover:bg-gray-50 dark:hover:bg-gray-700">
              <td class="px-6 py-4">
                <div>
                  <div class="text-sm font-medium text-gray-900 dark:text-white">{{ skill.name }}</div>
                  <div class="text-sm text-gray-500 dark:text-gray-400">v{{ skill.version }}</div>
                </div>
              </td>
              <td class="px-6 py-4">
                <span class="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-full">
                  {{ skill.category.replace('_', ' ') }}
                </span>
              </td>
              <td class="px-6 py-4">
                <div class="text-sm text-gray-900 dark:text-white max-w-xs truncate" :title="skill.description">
                  {{ skill.description }}
                </div>
              </td>
              <td class="px-6 py-4">
                <div class="flex flex-wrap gap-1">
                  <span 
                    v-for="tag in skill.tags.slice(0, 3)" 
                    :key="tag"
                    class="px-2 py-1 text-xs bg-gray-100 text-gray-800 rounded"
                  >
                    {{ tag }}
                  </span>
                  <span v-if="skill.tags.length > 3" class="text-xs text-gray-500">
                    +{{ skill.tags.length - 3 }} more
                  </span>
                </div>
              </td>
              <td class="px-6 py-4">
                <span :class="['px-2 py-1 text-xs font-medium rounded-full', getStatusBadgeClass(skill.status)]">
                  {{ skill.status }}
                </span>
              </td>
              <td class="px-6 py-4 text-sm text-gray-900 dark:text-white">
                {{ skill.version }}
              </td>
              <td class="px-6 py-4">
                <div class="flex space-x-2">
                  <button
                    @click="viewSkill(skill.skill_id)"
                    class="text-blue-600 hover:text-blue-900 dark:text-blue-400 dark:hover:text-blue-300"
                    title="View Details"
                  >
                    <i class="fas fa-eye"></i>
                  </button>
                  <button
                    @click="editSkill(skill)"
                    class="text-indigo-600 hover:text-indigo-900 dark:text-indigo-400 dark:hover:text-indigo-300"
                    title="Edit"
                  >
                    <i class="fas fa-edit"></i>
                  </button>
                  <button
                    @click="deleteSkill(skill)"
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

    <!-- Create/Edit Skill Modal -->
    <div v-if="showCreateModal" class="modal-overlay" @click.self="showCreateModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h3 class="modal-title">
            {{ editingSkill ? 'Edit Skill' : 'Add New Skill' }}
          </h3>
          <button @click="showCreateModal = false" class="modal-close">
            <i class="fas fa-times"></i>
          </button>
        </div>
        
        <div class="modal-body">
          <form @submit.prevent="saveSkill" class="space-y-4">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div class="md:col-span-1">
                <label class="form-label">Skill Name *</label>
                <input
                  v-model="skillForm.name"
                  type="text"
                  required
                  class="input-primary"
                >
              </div>
              <div class="md:col-span-1">
                <label class="form-label">Version</label>
                <input
                  v-model="skillForm.version"
                  type="text"
                  class="input-primary"
                >
              </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label class="form-label">Category *</label>
                <select
                  v-model="skillForm.category"
                  required
                  class="input-primary"
                >
                  <option value="">Select Category</option>
                  <option 
                    v-for="category in categories" 
                    :key="category.value" 
                    :value="category.value"
                  >
                    {{ category.label }}
                  </option>
                </select>
              </div>
              <div>
                <label class="form-label">Status</label>
                <select
                  v-model="skillForm.status"
                  class="input-primary"
                >
                  <option value="active">Active</option>
                  <option value="draft">Draft</option>
                  <option value="deprecated">Deprecated</option>
                </select>
              </div>
            </div>

            <div>
              <label class="form-label">Description *</label>
              <textarea
                v-model="skillForm.description"
                required
                rows="3"
                class="input-primary"
              ></textarea>
            </div>

            <div>
              <label class="form-label">Tags (comma-separated)</label>
              <input
                v-model="skillForm.tags"
                type="text"
                placeholder="tag1, tag2, tag3"
                class="input-primary"
              >
            </div>

            <div>
              <label class="form-label">Prerequisites</label>
              <textarea
                v-model="skillForm.prerequisites"
                rows="2"
                placeholder="Enter prerequisites, one per line"
                class="input-primary"
              ></textarea>
            </div>

            <div>
              <label class="form-label">Technical Steps *</label>
              <textarea
                v-model="skillForm.steps"
                required
                rows="6"
                placeholder="Enter detailed technical steps, one per line"
                class="input-primary"
              ></textarea>
            </div>

            <div>
              <label class="form-label">Usage Examples</label>
              <textarea
                v-model="skillForm.examples"
                rows="3"
                placeholder="Enter usage examples, one per line"
                class="input-primary"
              ></textarea>
            </div>
          </form>
        </div>
        
        <div class="modal-footer">
          <button @click="showCreateModal = false" class="btn btn-secondary">
            Cancel
          </button>
          <button @click="saveSkill" class="btn btn-primary">
            Save Skill
          </button>
        </div>
      </div>
    </div>

    <!-- Skill Details Modal -->
    <div v-if="showDetailModal" class="modal-overlay" @click.self="showDetailModal = false">
      <div class="modal-content modal-wide">
        <div class="modal-header">
          <h3 class="modal-title">{{ selectedSkill?.name }}</h3>
          <button @click="showDetailModal = false" class="modal-close">
            <i class="fas fa-times"></i>
          </button>
        </div>
        
        <div class="modal-body" v-if="selectedSkill">
          <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div class="lg:col-span-2">
              <div class="space-y-6">
                <div>
                  <h5 class="text-lg font-medium text-gray-900 dark:text-white mb-2">Description</h5>
                  <p class="text-gray-700 dark:text-gray-300">{{ selectedSkill.description }}</p>
                </div>
                
                <div>
                  <h5 class="text-lg font-medium text-gray-900 dark:text-white mb-2">Technical Steps</h5>
                  <ol class="list-decimal list-inside space-y-1">
                    <li 
                      v-for="step in selectedSkill.steps" 
                      :key="step"
                      class="text-gray-700 dark:text-gray-300"
                    >
                      {{ step }}
                    </li>
                  </ol>
                </div>
                
                <div v-if="selectedSkill.prerequisites.length > 0">
                  <h5 class="text-lg font-medium text-gray-900 dark:text-white mb-2">Prerequisites</h5>
                  <ul class="list-disc list-inside space-y-1">
                    <li 
                      v-for="prereq in selectedSkill.prerequisites" 
                      :key="prereq"
                      class="text-gray-700 dark:text-gray-300"
                    >
                      {{ prereq }}
                    </li>
                  </ul>
                </div>
                
                <div v-if="selectedSkill.examples.length > 0">
                  <h5 class="text-lg font-medium text-gray-900 dark:text-white mb-2">Examples</h5>
                  <ul class="list-disc list-inside space-y-1">
                    <li 
                      v-for="example in selectedSkill.examples" 
                      :key="example"
                      class="text-gray-700 dark:text-gray-300"
                    >
                      {{ example }}
                    </li>
                  </ul>
                </div>
              </div>
            </div>
            
            <div>
              <h5 class="text-lg font-medium text-gray-900 dark:text-white mb-4">Metadata</h5>
              <div class="space-y-3">
                <div class="flex justify-between">
                  <span class="text-sm font-medium text-gray-500 dark:text-gray-400">ID:</span>
                  <code class="text-sm bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">{{ selectedSkill.skill_id }}</code>
                </div>
                <div class="flex justify-between">
                  <span class="text-sm font-medium text-gray-500 dark:text-gray-400">Category:</span>
                  <span class="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-full">
                    {{ selectedSkill.category.replace('_', ' ') }}
                  </span>
                </div>
                <div class="flex justify-between">
                  <span class="text-sm font-medium text-gray-500 dark:text-gray-400">Status:</span>
                  <span :class="['px-2 py-1 text-xs font-medium rounded-full', getStatusBadgeClass(selectedSkill.status)]">
                    {{ selectedSkill.status }}
                  </span>
                </div>
                <div class="flex justify-between">
                  <span class="text-sm font-medium text-gray-500 dark:text-gray-400">Version:</span>
                  <span class="text-sm text-gray-900 dark:text-white">{{ selectedSkill.version }}</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-sm font-medium text-gray-500 dark:text-gray-400">Created:</span>
                  <span class="text-sm text-gray-900 dark:text-white">{{ new Date(selectedSkill.created_at).toLocaleDateString() }}</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-sm font-medium text-gray-500 dark:text-gray-400">Updated:</span>
                  <span class="text-sm text-gray-900 dark:text-white">{{ new Date(selectedSkill.updated_at).toLocaleDateString() }}</span>
                </div>
                
                <div v-if="selectedSkill.tags.length > 0" class="pt-2">
                  <h6 class="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">Tags</h6>
                  <div class="flex flex-wrap gap-1">
                    <span 
                      v-for="tag in selectedSkill.tags" 
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

    <!-- Import Skills Modal -->
    <div v-if="showImportModal" class="modal-overlay" @click.self="showImportModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h3 class="modal-title">Import Skills</h3>
          <button @click="showImportModal = false" class="modal-close">
            <i class="fas fa-times"></i>
          </button>
        </div>
        
        <div class="modal-body">
          <div class="space-y-4">
            <div>
              <label class="form-label">Skills JSON Data</label>
              <textarea
                v-model="importData"
                rows="15"
                placeholder="Paste your skills JSON data here..."
                class="input-primary font-mono text-sm"
              ></textarea>
              <p class="text-sm text-gray-600 dark:text-gray-400 mt-1">
                Expected format: {"skills": [{"name": "...", "description": "...", "category": "...", "steps": [...], ...}]}
              </p>
            </div>
          </div>
        </div>
        
        <div class="modal-footer">
          <button @click="showImportModal = false" class="btn btn-secondary">
            Cancel
          </button>
          <button @click="importSkills" class="btn btn-primary">
            Import Skills
          </button>
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