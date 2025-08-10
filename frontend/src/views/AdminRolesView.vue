<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-900">
    <!-- Header -->
    <div class="bg-white dark:bg-gray-800 shadow">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="py-6">
          <div class="flex justify-between items-center">
            <div>
              <h1 class="text-3xl font-bold text-gray-900 dark:text-white">
                Role Management
              </h1>
              <p class="mt-2 text-gray-600 dark:text-gray-400">
                Manage user roles and permissions
              </p>
            </div>
            <button
              @click="showCreateRole = true"
              class="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors"
            >
              Create Role
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Content -->
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <!-- Roles Table -->
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow">
        <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Roles</h2>
        </div>
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead class="bg-gray-50 dark:bg-gray-700">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Role
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Description
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Users Count
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
              <tr v-else-if="roles.length === 0">
                <td colspan="5" class="px-6 py-4 text-center text-gray-500 dark:text-gray-400">
                  No roles found
                </td>
              </tr>
              <tr v-else v-for="role in roles" :key="role.id" class="hover:bg-gray-50 dark:hover:bg-gray-700">
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="flex items-center">
                    <div class="flex-shrink-0 h-10 w-10">
                      <div class="h-10 w-10 rounded-full bg-purple-100 dark:bg-purple-900 flex items-center justify-center">
                        <svg class="w-5 h-5 text-purple-600 dark:text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                        </svg>
                      </div>
                    </div>
                    <div class="ml-4">
                      <div class="text-sm font-medium text-gray-900 dark:text-white">
                        {{ role.name }}
                      </div>
                      <div class="text-sm text-gray-500 dark:text-gray-400">
                        ID: {{ role.id }}
                      </div>
                    </div>
                  </div>
                </td>
                <td class="px-6 py-4 text-sm text-gray-900 dark:text-white">
                  <div class="max-w-xs truncate">
                    {{ role.description || 'No description' }}
                  </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                  <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                    {{ role.user_count || 0 }} users
                  </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                  {{ formatDate(role.created_at) }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                  <div class="flex space-x-2">
                    <button
                      @click="editRole(role)"
                      class="text-blue-600 hover:text-blue-900 dark:text-blue-400 dark:hover:text-blue-300"
                    >
                      Edit
                    </button>
                    <button
                      @click="deleteRole(role)"
                      :disabled="role.user_count > 0"
                      :class="[
                        'transition-colors',
                        role.user_count > 0
                          ? 'text-gray-400 cursor-not-allowed'
                          : 'text-red-600 hover:text-red-900 dark:text-red-400 dark:hover:text-red-300'
                      ]"
                      :title="role.user_count > 0 ? 'Cannot delete role with assigned users' : 'Delete role'"
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

    <!-- Create Role Modal -->
    <div
      v-if="showCreateRole"
      class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50"
      @click="showCreateRole = false"
    >
      <div class="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white dark:bg-gray-800" @click.stop>
        <div class="mt-3">
          <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-4">Create New Role</h3>
          <form @submit.prevent="createRole">
            <div class="mb-4">
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Role Name
              </label>
              <input
                v-model="newRole.name"
                type="text"
                required
                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                placeholder="Enter role name"
              />
            </div>
            <div class="mb-6">
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Description
              </label>
              <textarea
                v-model="newRole.description"
                rows="3"
                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                placeholder="Enter role description (optional)"
              ></textarea>
            </div>
            <div class="flex justify-end space-x-3">
              <button
                type="button"
                @click="showCreateRole = false"
                class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-600 rounded-md hover:bg-gray-200 dark:hover:bg-gray-700"
              >
                Cancel
              </button>
              <button
                type="submit"
                :disabled="creatingRole"
                class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {{ creatingRole ? 'Creating...' : 'Create Role' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- Edit Role Modal -->
    <div
      v-if="showEditRole"
      class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50"
      @click="showEditRole = false"
    >
      <div class="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white dark:bg-gray-800" @click.stop>
        <div class="mt-3">
          <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-4">Edit Role</h3>
          <form @submit.prevent="updateRole">
            <div class="mb-4">
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Role Name
              </label>
              <input
                v-model="editingRole.name"
                type="text"
                required
                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
              />
            </div>
            <div class="mb-6">
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Description
              </label>
              <textarea
                v-model="editingRole.description"
                rows="3"
                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
              ></textarea>
            </div>
            <div class="flex justify-end space-x-3">
              <button
                type="button"
                @click="showEditRole = false"
                class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-600 rounded-md hover:bg-gray-200 dark:hover:bg-gray-700"
              >
                Cancel
              </button>
              <button
                type="submit"
                :disabled="updatingRole"
                class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {{ updatingRole ? 'Updating...' : 'Update Role' }}
              </button>
            </div>
          </form>
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
const roles = ref<any[]>([])
const showCreateRole = ref(false)
const showEditRole = ref(false)
const creatingRole = ref(false)
const updatingRole = ref(false)

const newRole = ref({
  name: '',
  description: ''
})

const editingRole = ref({
  id: 0,
  name: '',
  description: ''
})

// Fetch roles
const fetchRoles = async () => {
  try {
    loading.value = true
    const response = await apiService.get('/admin/roles')
    
    if (response.success) {
      roles.value = response.roles
    } else {
      toast.error('Failed to load roles')
    }
  } catch (error) {
    console.error('Error fetching roles:', error)
    toast.error('Failed to load roles')
  } finally {
    loading.value = false
  }
}

// Create role
const createRole = async () => {
  try {
    creatingRole.value = true
    const response = await apiService.post('/admin/roles', newRole.value)
    
    if (response.success) {
      toast.success('Role created successfully')
      showCreateRole.value = false
      newRole.value = { name: '', description: '' }
      await fetchRoles()
    } else {
      toast.error(response.error || 'Failed to create role')
    }
  } catch (error) {
    console.error('Error creating role:', error)
    toast.error('Failed to create role')
  } finally {
    creatingRole.value = false
  }
}

// Edit role
const editRole = (role: any) => {
  editingRole.value = {
    id: role.id,
    name: role.name,
    description: role.description || ''
  }
  showEditRole.value = true
}

// Update role
const updateRole = async () => {
  try {
    updatingRole.value = true
    const response = await apiService.put(`/admin/roles/${editingRole.value.id}`, {
      name: editingRole.value.name,
      description: editingRole.value.description
    })
    
    if (response.success) {
      toast.success('Role updated successfully')
      showEditRole.value = false
      await fetchRoles()
    } else {
      toast.error(response.error || 'Failed to update role')
    }
  } catch (error) {
    console.error('Error updating role:', error)
    toast.error('Failed to update role')
  } finally {
    updatingRole.value = false
  }
}

// Delete role
const deleteRole = async (role: any) => {
  if (role.user_count > 0) {
    toast.error('Cannot delete role with assigned users')
    return
  }
  
  if (!confirm(`Are you sure you want to delete role "${role.name}"?`)) {
    return
  }
  
  try {
    const response = await apiService.delete(`/admin/roles/${role.id}`)
    
    if (response.success) {
      toast.success('Role deleted successfully')
      await fetchRoles()
    } else {
      toast.error(response.error || 'Failed to delete role')
    }
  } catch (error) {
    console.error('Error deleting role:', error)
    toast.error('Failed to delete role')
  }
}

// Format date
const formatDate = (date: string) => {
  if (!date) return ''
  return new Date(date).toLocaleDateString()
}

// Load data on mount
onMounted(() => {
  fetchRoles()
})
</script>