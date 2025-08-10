import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

// Views
import LoginView from '@/views/LoginView.vue'
import HomeView from '@/views/HomeView.vue'
import ChangePasswordView from '@/views/ChangePasswordView.vue'
import QueryEditorView from '@/views/QueryEditorView.vue'
import KnowledgeView from '@/views/KnowledgeView.vue'
import ProfileView from '@/views/ProfileView.vue'
import AgentView from '@/views/AgentView.vue'
import DataMappingView from '@/views/DataMappingView.vue'
import SchemaView from '@/views/SchemaView.vue'
import MetadataSearchView from '@/views/MetadataSearchView.vue'

// Admin Views
import AdminDashboardView from '@/views/AdminDashboardView.vue'
import AdminUsersView from '@/views/AdminUsersView.vue'
import AdminRolesView from '@/views/AdminRolesView.vue'
import AdminMCPServersView from '@/views/AdminMCPServersView.vue'
import AdminAuditView from '@/views/AdminAuditView.vue'
import AdminSamplesView from '@/views/AdminSamplesView.vue'
import AdminSkillLibraryView from '@/views/AdminSkillLibraryView.vue'
import AdminKnowledgeView from '@/views/AdminKnowledgeView.vue'
import AdminVectorDBView from '@/views/AdminVectorDBView.vue'
import AdminDatabaseQueryView from '@/views/AdminDatabaseQueryView.vue'
import AdminConfigView from '@/views/AdminConfigView.vue'

import AppLayout from '@/layouts/AppLayout.vue'

// Route guard for authentication
const requiresAuth = (to: any, from: any, next: any) => {
  const authStore = useAuthStore()
  if (authStore.isAuthenticated) {
    next()
  } else {
    next('/login')
  }
}

// Route guard for admin access
const requiresAdmin = (to: any, from: any, next: any) => {
  const authStore = useAuthStore()
  if (authStore.isAuthenticated) {
    // Check if user has admin permissions
    const user = authStore.user
    const isAdmin = user?.roles?.some((role: any) => role.name === 'admin') || 
                   user?.permissions?.includes('admin') ||
                   user?.is_admin === true
    
    if (isAdmin) {
      next()
    } else {
      next('/') // Redirect to home if not admin
    }
  } else {
    next('/login')
  }
}

// Route guard for guests (redirect authenticated users)
const guestOnly = (to: any, from: any, next: any) => {
  const authStore = useAuthStore()
  if (!authStore.isAuthenticated) {
    next()
  } else {
    next('/')
  }
}

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    // Guest routes (no authentication required)
    {
      path: '/login',
      name: 'Login',
      component: LoginView,
      beforeEnter: guestOnly,
      meta: {
        title: 'Login - Text2SQL Assistant'
      }
    },
    
    // Authenticated routes (require login)
    {
      path: '/',
      component: AppLayout,
      beforeEnter: requiresAuth,
      children: [
        {
          path: '',
          name: 'Home',
          component: HomeView,
          meta: {
            title: 'Home - Text2SQL Assistant'
          }
        },
        {
          path: '/profile',
          name: 'Profile',
          component: ProfileView,
          meta: {
            title: 'Profile - Text2SQL Assistant'
          }
        },
        {
          path: '/change-password',
          name: 'ChangePassword',
          component: ChangePasswordView,
          meta: {
            title: 'Change Password - Text2SQL Assistant'
          }
        },
        {
          path: '/query-editor',
          name: 'QueryEditor',
          component: QueryEditorView,
          meta: {
            title: 'Query Editor - Text2SQL Assistant'
          }
        },
        {
          path: '/knowledge',
          name: 'Knowledge',
          component: KnowledgeView,
          meta: {
            title: 'Knowledge Finder - Text2SQL Assistant'
          }
        },
        {
          path: '/agent',
          name: 'Agent',
          component: AgentView,
          meta: {
            title: 'Agent Mode - Text2SQL Assistant'
          }
        },
        {
          path: '/data-mapping',
          name: 'DataMapping',
          component: DataMappingView,
          meta: {
            title: 'Data Mapping - Text2SQL Assistant'
          }
        },
        {
          path: '/schema',
          name: 'Schema',
          component: SchemaView,
          meta: {
            title: 'Schema Browser - Text2SQL Assistant'
          }
        },
        {
          path: '/metadata-search',
          name: 'MetadataSearch',
          component: MetadataSearchView,
          meta: {
            title: 'Metadata Search - Text2SQL Assistant'
          }
        },
        
        // Admin routes (require admin permissions)
        {
          path: '/admin',
          name: 'AdminDashboard',
          component: AdminDashboardView,
          beforeEnter: requiresAdmin,
          meta: {
            title: 'Admin Dashboard - Text2SQL Assistant',
            requiresAdmin: true
          }
        },
        {
          path: '/admin/users',
          name: 'AdminUsers',
          component: AdminUsersView,
          beforeEnter: requiresAdmin,
          meta: {
            title: 'User Management - Text2SQL Assistant',
            requiresAdmin: true
          }
        },
        {
          path: '/admin/roles',
          name: 'AdminRoles',
          component: AdminRolesView,
          beforeEnter: requiresAdmin,
          meta: {
            title: 'Role Management - Text2SQL Assistant',
            requiresAdmin: true
          }
        },
        {
          path: '/admin/mcp-servers',
          name: 'AdminMCPServers',
          component: AdminMCPServersView,
          beforeEnter: requiresAdmin,
          meta: {
            title: 'MCP Server Management - Text2SQL Assistant',
            requiresAdmin: true
          }
        },
        {
          path: '/admin/audit',
          name: 'AdminAudit',
          component: AdminAuditView,
          beforeEnter: requiresAdmin,
          meta: {
            title: 'Audit Logs - Text2SQL Assistant',
            requiresAdmin: true
          }
        },
        {
          path: '/admin/samples',
          name: 'AdminSamples',
          component: AdminSamplesView,
          beforeEnter: requiresAdmin,
          meta: {
            title: 'Manage Samples - Text2SQL Assistant',
            requiresAdmin: true
          }
        },
        {
          path: '/admin/skill-library',
          name: 'AdminSkillLibrary',
          component: AdminSkillLibraryView,
          beforeEnter: requiresAdmin,
          meta: {
            title: 'Skill Library - Text2SQL Assistant',
            requiresAdmin: true
          }
        },
        {
          path: '/admin/knowledge',
          name: 'AdminKnowledge',
          component: AdminKnowledgeView,
          beforeEnter: requiresAdmin,
          meta: {
            title: 'Knowledge Management - Text2SQL Assistant',
            requiresAdmin: true
          }
        },
        {
          path: '/admin/vector-db',
          name: 'AdminVectorDB',
          component: AdminVectorDBView,
          beforeEnter: requiresAdmin,
          meta: {
            title: 'Vector Database - Text2SQL Assistant',
            requiresAdmin: true
          }
        },
        {
          path: '/admin/database-query',
          name: 'AdminDatabaseQuery',
          component: AdminDatabaseQueryView,
          beforeEnter: requiresAdmin,
          meta: {
            title: 'Database Query Editor - Text2SQL Assistant',
            requiresAdmin: true
          }
        },
        {
          path: '/admin/config',
          name: 'AdminConfig',
          component: AdminConfigView,
          beforeEnter: requiresAdmin,
          meta: {
            title: 'Configuration - Text2SQL Assistant',
            requiresAdmin: true
          }
        }
        // Additional authenticated routes will be added here
        // ... more routes
      ]
    },
    
    // Catch-all redirect
    {
      path: '/:pathMatch(.*)*',
      redirect: '/'
    }
  ],
})

// Global navigation guard for title updates
router.beforeEach((to, from, next) => {
  // Update page title
  if (to.meta?.title) {
    document.title = to.meta.title as string
  } else {
    document.title = 'Text2SQL Assistant'
  }
  
  next()
})

export default router
