<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useQueryStore } from '@/stores/query'

interface MenuItem {
  name: string
  path: string
  icon: string
  permission?: string
}

interface MenuSection {
  title: string
  items: MenuItem[]
}

defineProps<{
  isOpen: boolean
}>()

defineEmits<{
  close: []
}>()

const route = useRoute()
const authStore = useAuthStore()
const queryStore = useQueryStore()

const selectedWorkspace = ref('')

const menuSections = computed<MenuSection[]>(() => [
  {
    title: 'Main',
    items: [
      { name: 'Home', path: '/', icon: 'fas fa-home' },
      { name: 'Query Editor', path: '/query-editor', icon: 'fas fa-code' },
      { name: 'Knowledge Finder', path: '/knowledge', icon: 'fas fa-book' },
      { name: 'Agent Mode', path: '/agent', icon: 'fas fa-robot' },
      { name: 'Data Mapping', path: '/data-mapping', icon: 'fas fa-project-diagram' },
      { name: 'Schema Viewer', path: '/schema', icon: 'fas fa-table' },
    ]
  },
  {
    title: 'Management',
    items: [
      { name: 'Samples', path: '/samples', icon: 'fas fa-flask', permission: 'MANAGE_SAMPLES' },
    ]
  },
  {
    title: 'Administration',
    items: [
      { name: 'Dashboard', path: '/admin', icon: 'fas fa-tachometer-alt', permission: 'ADMIN_ACCESS' },
      { name: 'Users', path: '/admin/users', icon: 'fas fa-users', permission: 'MANAGE_USERS' },
      { name: 'Roles', path: '/admin/roles', icon: 'fas fa-user-tag', permission: 'MANAGE_ROLES' },
      { name: 'Schema', path: '/admin/schema', icon: 'fas fa-database', permission: 'MANAGE_SCHEMA' },
      { name: 'Vector DB', path: '/admin/vector-db', icon: 'fas fa-vector-square', permission: 'ADMIN_ACCESS' },
      { name: 'MCP Servers', path: '/admin/mcp-servers', icon: 'fas fa-server', permission: 'ADMIN_ACCESS' },
      { name: 'Skills', path: '/admin/skills', icon: 'fas fa-brain', permission: 'ADMIN_ACCESS' },
      { name: 'Audit Logs', path: '/admin/audit', icon: 'fas fa-history', permission: 'VIEW_AUDIT_LOGS' },
      { name: 'Config', path: '/admin/config', icon: 'fas fa-cog', permission: 'ADMIN_ACCESS' },
    ]
  }
])

const filteredMenuSections = computed(() => {
  return menuSections.value.map(section => ({
    ...section,
    items: section.items.filter(item => 
      !item.permission || authStore.hasPermission(item.permission)
    )
  })).filter(section => section.items.length > 0)
})

const isActiveRoute = (path: string) => {
  if (path === '/') {
    return route.path === path
  }
  return route.path.startsWith(path)
}

const onWorkspaceChange = async () => {
  if (selectedWorkspace.value) {
    await queryStore.setWorkspace(selectedWorkspace.value)
  }
}

onMounted(async () => {
  // Load workspaces and set default
  await queryStore.loadWorkspaces()
  if (queryStore.workspaces.length > 0) {
    selectedWorkspace.value = queryStore.workspaces[0].name
    queryStore.setWorkspace(selectedWorkspace.value)
  }
})
</script>

<template>
  <!-- Mobile backdrop -->
  <div
    v-if="isOpen"
    class="fixed inset-0 z-40 bg-black bg-opacity-50 md:hidden"
    @click="$emit('close')"
  ></div>

  <!-- Sidebar -->
  <div
    class="fixed left-0 top-16 z-50 w-64 h-full bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 transform transition-transform duration-300 md:relative md:top-0 md:translate-x-0"
    :class="{
      'translate-x-0': isOpen,
      '-translate-x-full': !isOpen
    }"
  >
    <div class="flex flex-col h-full">
      <!-- Workspace Selector -->
      <div class="p-4 border-b border-gray-200 dark:border-gray-700">
        <label for="workspaceSelect" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Subject Area:
        </label>
        <select
          id="workspaceSelect"
          v-model="selectedWorkspace"
          @change="onWorkspaceChange"
          class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-primary-500 focus:border-primary-500"
        >
          <option v-for="workspace in queryStore.workspaces" :key="workspace.name" :value="workspace.name">
            {{ workspace.name }}
          </option>
        </select>
      </div>

      <!-- Navigation Menu -->
      <div class="flex-1 overflow-y-auto p-4">
        <nav class="space-y-6">
          <div v-for="section in filteredMenuSections" :key="section.title">
            <h3 class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">
              {{ section.title }}
            </h3>
            <div class="space-y-1">
              <router-link
                v-for="item in section.items"
                :key="item.path"
                :to="item.path"
                class="flex items-center px-3 py-2 rounded-lg text-sm font-medium transition-colors duration-200"
                :class="{
                  'bg-primary-100 dark:bg-primary-900 text-primary-700 dark:text-primary-300': isActiveRoute(item.path),
                  'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700': !isActiveRoute(item.path)
                }"
                @click="$emit('close')"
              >
                <i :class="item.icon" class="w-5 h-5 mr-3"></i>
                {{ item.name }}
              </router-link>
            </div>
          </div>
        </nav>
      </div>

      <!-- Footer -->
      <div class="p-4 border-t border-gray-200 dark:border-gray-700">
        <div class="text-xs text-gray-500 dark:text-gray-400 text-center">
          Text2SQL Assistant
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Ensure sidebar doesn't interfere with mobile layout */
@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    top: 4rem;
    left: 0;
    bottom: 0;
    z-index: 50;
  }
}

/* Font Awesome icons */
.fas {
  font-family: 'Font Awesome 6 Free';
  font-weight: 900;
}
</style>