import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

// Views
import LoginView from '@/views/LoginView.vue'
import HomeView from '@/views/HomeView.vue'
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
        // Additional authenticated routes will be added here
        // {
        //   path: '/query-editor',
        //   name: 'QueryEditor',
        //   component: () => import('@/views/QueryEditorView.vue'),
        //   meta: {
        //     title: 'Query Editor - Text2SQL Assistant'
        //   }
        // },
        // {
        //   path: '/knowledge',
        //   name: 'Knowledge',
        //   component: () => import('@/views/KnowledgeView.vue'),
        //   meta: {
        //     title: 'Knowledge Finder - Text2SQL Assistant'
        //   }
        // },
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
