import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import AppSidebar from '../components/AppSidebar.vue'

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

// Mock the auth store
vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    user: { 
      name: 'Test User',
      roles: [{ name: 'admin' }]
    },
    isAuthenticated: true,
    isAdmin: true,
    hasPermission: vi.fn(() => true),
    hasRole: vi.fn(() => true)
  })
}))

// Mock the query store
vi.mock('@/stores/query', () => ({
  useQueryStore: () => ({
    workspaces: ['default', 'test'],
    currentWorkspace: 'default',
    setWorkspace: vi.fn()
  })
}))

// Mock the UI store
vi.mock('@/stores/ui', () => ({
  useUIStore: () => ({
    sidebarOpen: true,
    initializeTheme: vi.fn()
  })
}))

const mockRouter = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: { template: '<div>Home</div>' } },
    { path: '/admin', component: { template: '<div>Admin</div>' } }
  ]
})

describe('AppSidebar', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders navigation menu', () => {
    const wrapper = mount(AppSidebar, {
      props: {
        isOpen: true
      },
      global: {
        plugins: [mockRouter]
      }
    })
    expect(wrapper.exists()).toBe(true)
  })

  it('shows admin navigation for admin users', () => {
    const wrapper = mount(AppSidebar, {
      props: {
        isOpen: true
      },
      global: {
        plugins: [mockRouter]
      }
    })
    
    // Check if admin menu items exist
    const adminItems = wrapper.text()
    expect(adminItems).toContain('Administration')
    expect(adminItems).toContain('Admin Dashboard')
    expect(adminItems).toContain('Manage Samples')
    expect(adminItems).toContain('User Management')
    expect(adminItems).toContain('Skill Library')
    expect(adminItems).toContain('Knowledge Management')
    expect(adminItems).toContain('Vector Database')
    expect(adminItems).toContain('Database Query Editor')
    expect(adminItems).toContain('Configuration')
    expect(adminItems).toContain('Audit Logs')
  })

  it('shows workspace selector', () => {
    const wrapper = mount(AppSidebar, {
      props: {
        isOpen: true
      },
      global: {
        plugins: [mockRouter]
      }
    })
    expect(wrapper.find('select').exists()).toBe(true)
  })
})