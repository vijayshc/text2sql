<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-900">
    <!-- Header -->
    <div class="bg-white dark:bg-gray-800 shadow">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="py-6">
          <div class="flex justify-between items-center">
            <div>
              <h1 class="text-3xl font-bold text-gray-900 dark:text-white">
                User Management
              </h1>
              <p class="mt-2 text-gray-600 dark:text-gray-400">
                Manage user accounts, roles, and permissions
              </p>
            </div>
            <button
              @click="showCreateUser = true"
              class="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors"
            >
              Create User
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Content -->
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <!-- Users Table -->
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow">
        <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Users</h2>
        </div>
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead class="bg-gray-50 dark:bg-gray-700">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  User
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Email
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Roles
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
                <td colspan="6" class="px-6 py-4 text-center">
                  <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
                </td>
              </tr>
              <tr v-else-if="users.length === 0">
                <td colspan="6" class="px-6 py-4 text-center text-gray-500 dark:text-gray-400">
                  No users found
                </td>
              </tr>
              <tr v-else v-for="user in users" :key="user.id" class="hover:bg-gray-50 dark:hover:bg-gray-700">
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="flex items-center">
                    <div class="flex-shrink-0 h-10 w-10">
                      <div class="h-10 w-10 rounded-full bg-gray-300 dark:bg-gray-600 flex items-center justify-center">
                        <span class="text-sm font-medium text-gray-700 dark:text-gray-300">
                          {{ user.username?.charAt(0).toUpperCase() }}
                        </span>
                      </div>
                    </div>
                    <div class="ml-4">
                      <div class="text-sm font-medium text-gray-900 dark:text-white">
                        {{ user.username }}
                      </div>
                      <div class="text-sm text-gray-500 dark:text-gray-400">
                        ID: {{ user.id }}
                      </div>
                    </div>
                  </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                  {{ user.email }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="flex flex-wrap gap-1">
                    <span
                      v-for="role in user.roles || []"
                      :key="role.id"
                      class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"
                    >
                      {{ role.name }}
                    </span>
                  </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <span
                    :class="[
                      'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
                      user.status === 'active'
                        ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                        : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                    ]"
                  >
                    {{ user.status || 'active' }}
                  </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                  {{ formatDate(user.created_at) }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                  <div class="flex space-x-2">
                    <button
                      @click="editUser(user)"
                      class="text-blue-600 hover:text-blue-900 dark:text-blue-400 dark:hover:text-blue-300"
                    >
                      Edit
                    </button>
                    <button
                      @click="deleteUser(user)"
                      class="text-red-600 hover:text-red-900 dark:text-red-400 dark:hover:text-red-300"
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

    <!-- Create User Modal -->
    <div
      v-if="showCreateUser"
      class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50"
      @click="showCreateUser = false"
    >
      <div class="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white dark:bg-gray-800" @click.stop>
        <div class="mt-3">
          <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-4">Create New User</h3>
          <form @submit.prevent="createUser">
            <div class="mb-4">
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Username
              </label>
              <input
                v-model="newUser.username"
                type="text"
                required
                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
              />
            </div>
            <div class="mb-4">
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Email
              </label>
              <input
                v-model="newUser.email"
                type="email"
                required
                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
              />
            </div>
            <div class="mb-4">
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Password
              </label>
              <input
                v-model="newUser.password"
                type="password"
                required
                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
              />
            </div>
            <div class="mb-6">
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Roles
              </label>
              <div class="space-y-2 max-h-32 overflow-y-auto">
                <label v-for="role in roles" :key="role.id" class="flex items-center">
                  <input
                    v-model="newUser.roles"
                    :value="role.id"
                    type="checkbox"
                    class="mr-2 text-blue-600 focus:ring-blue-500"
                  />
                  <span class="text-sm text-gray-700 dark:text-gray-300">{{ role.name }}</span>
                </label>
              </div>
            </div>
            <div class="flex justify-end space-x-3">
              <button
                type="button"
                @click="showCreateUser = false"
                class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-600 rounded-md hover:bg-gray-200 dark:hover:bg-gray-700"
              >
                Cancel
              </button>
              <button
                type="submit"
                :disabled="creatingUser"
                class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {{ creatingUser ? 'Creating...' : 'Create User' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- Edit User Modal -->
    <div
      v-if="showEditUser"
      class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50"
      @click="showEditUser = false"
    >
      <div class="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white dark:bg-gray-800" @click.stop>
        <div class="mt-3">
          <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-4">Edit User</h3>
          <form @submit.prevent="updateUser">
            <div class="mb-4">
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Username
              </label>
              <input
                :value="editingUser.username"
                type="text"
                disabled
                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-gray-100 dark:bg-gray-600 text-gray-500 dark:text-gray-400"
              />
            </div>
            <div class="mb-4">
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Email
              </label>
              <input
                v-model="editingUser.email"
                type="email"
                required
                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
              />
            </div>
            <div class="mb-4">
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Status
              </label>
              <select
                v-model="editingUser.status"
                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
              >
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
              </select>
            </div>
            <div class="mb-6">
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Roles
              </label>
              <div class="space-y-2 max-h-32 overflow-y-auto">
                <label v-for="role in roles" :key="role.id" class="flex items-center">
                  <input
                    v-model="editingUser.roles"
                    :value="role.id"
                    type="checkbox"
                    class="mr-2 text-blue-600 focus:ring-blue-500"
                  />
                  <span class="text-sm text-gray-700 dark:text-gray-300">{{ role.name }}</span>
                </label>
              </div>
            </div>
            <div class="flex justify-end space-x-3">
              <button
                type="button"
                @click="showEditUser = false"
                class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-600 rounded-md hover:bg-gray-200 dark:hover:bg-gray-700"
              >
                Cancel
              </button>
              <button
                type="submit"
                :disabled="updatingUser"
                class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {{ updatingUser ? 'Updating...' : 'Update User' }}
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
const users = ref<any[]>([])
const roles = ref<any[]>([])
const showCreateUser = ref(false)
const showEditUser = ref(false)
const creatingUser = ref(false)
const updatingUser = ref(false)

const newUser = ref({
  username: '',
  email: '',
  password: '',
  roles: [] as number[]
})

const editingUser = ref({
  id: 0,
  username: '',
  email: '',
  status: 'active',
  roles: [] as number[]
})

// Fetch users and roles
const fetchData = async () => {
  try {
    loading.value = true
    
    const [usersResponse, rolesResponse] = await Promise.all([
      apiService.get('/admin/users'),
      apiService.get('/admin/roles')
    ])
    
    if (usersResponse.success) {
      users.value = usersResponse.users
    }
    
    if (rolesResponse.success) {
      roles.value = rolesResponse.roles
    }
  } catch (error) {
    console.error('Error fetching data:', error)
    toast.error('Failed to load data')
  } finally {
    loading.value = false
  }
}

// Create user
const createUser = async () => {
  try {
    creatingUser.value = true
    const response = await apiService.post('/admin/users', newUser.value)
    
    if (response.success) {
      toast.success('User created successfully')
      showCreateUser.value = false
      newUser.value = { username: '', email: '', password: '', roles: [] }
      await fetchData()
    } else {
      toast.error(response.error || 'Failed to create user')
    }
  } catch (error) {
    console.error('Error creating user:', error)
    toast.error('Failed to create user')
  } finally {
    creatingUser.value = false
  }
}

// Edit user
const editUser = (user: any) => {
  editingUser.value = {
    id: user.id,
    username: user.username,
    email: user.email,
    status: user.status || 'active',
    roles: (user.roles || []).map((role: any) => role.id)
  }
  showEditUser.value = true
}

// Update user
const updateUser = async () => {
  try {
    updatingUser.value = true
    const response = await apiService.put(`/admin/users/${editingUser.value.id}`, {
      email: editingUser.value.email,
      status: editingUser.value.status,
      roles: editingUser.value.roles
    })
    
    if (response.success) {
      toast.success('User updated successfully')
      showEditUser.value = false
      await fetchData()
    } else {
      toast.error(response.error || 'Failed to update user')
    }
  } catch (error) {
    console.error('Error updating user:', error)
    toast.error('Failed to update user')
  } finally {
    updatingUser.value = false
  }
}

// Delete user
const deleteUser = async (user: any) => {
  if (!confirm(`Are you sure you want to delete user "${user.username}"?`)) {
    return
  }
  
  try {
    const response = await apiService.delete(`/admin/users/${user.id}`)
    
    if (response.success) {
      toast.success('User deleted successfully')
      await fetchData()
    } else {
      toast.error(response.error || 'Failed to delete user')
    }
  } catch (error) {
    console.error('Error deleting user:', error)
    toast.error('Failed to delete user')
  }
}

// Format date
const formatDate = (date: string) => {
  if (!date) return ''
  return new Date(date).toLocaleDateString()
}

// Load data on mount
onMounted(() => {
  fetchData()
})
</script>