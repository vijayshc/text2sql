import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import AdminDashboardView from '../views/AdminDashboardView.vue'

// Mock window.matchMedia for UI store
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Mock API service
vi.mock('@/services/api', () => ({
  api: {
    get: vi.fn(() => Promise.resolve({
      data: {
        stats: {
          total_users: 10,
          total_queries: 100,
          total_samples: 50,
          active_sessions: 5
        }
      }
    }))
  }
}))

// Mock auth store
vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    isAuthenticated: true,
    isAdmin: true,
    user: { name: 'Admin User' }
  })
}))

// Mock toast store
vi.mock('@/stores/toast', () => ({
  useToastStore: () => ({
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn()
  })
}))

// Mock UI store
vi.mock('@/stores/ui', () => ({
  useUIStore: () => ({
    sidebarOpen: true,
    initializeTheme: vi.fn()
  })
}))

// Mock useToast composable
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn()
  })
}))

const mockRouter = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/admin', component: AdminDashboardView }
  ]
})

describe('AdminDashboardView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders dashboard title', () => {
    const wrapper = mount(AdminDashboardView, {
      global: {
        plugins: [mockRouter]
      }
    })
    expect(wrapper.text()).toContain('Admin Dashboard')
  })

  it('displays stats cards', async () => {
    const wrapper = mount(AdminDashboardView, {
      global: {
        plugins: [mockRouter]
      }
    })
    
    // Wait for async data loading
    await wrapper.vm.$nextTick()
    
    // Check for stats display
    expect(wrapper.text()).toContain('Users')
    expect(wrapper.text()).toContain('Queries')
    expect(wrapper.text()).toContain('Samples')
  })

  it('has quick action buttons', () => {
    const wrapper = mount(AdminDashboardView, {
      global: {
        plugins: [mockRouter]
      }
    })
    
    const actionText = wrapper.text()
    expect(actionText).toContain('Quick Actions')
  })
})