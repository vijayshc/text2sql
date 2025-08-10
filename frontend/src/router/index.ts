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
