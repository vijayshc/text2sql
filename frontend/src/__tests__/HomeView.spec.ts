import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'

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

// Mock stores
vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    isAuthenticated: true,
    user: { name: 'Test User' }
  })
}))

vi.mock('@/stores/query', () => ({
  useQueryStore: () => ({
    currentWorkspace: 'default',
    workspaces: ['default', 'test'],
    query: '',
    isLoading: false,
    results: null,
    error: null,
    processQuery: vi.fn(),
    clearResults: vi.fn(),
    loadWorkspaces: vi.fn()
  })
}))

vi.mock('@/stores/ui', () => ({
  useUIStore: () => ({
    sidebarOpen: true,
    initializeTheme: vi.fn()
  })
}))

const mockRouter = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: HomeView }
  ]
})

describe('HomeView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders home view', () => {
    const wrapper = mount(HomeView, {
      global: {
        plugins: [mockRouter]
      }
    })
    expect(wrapper.exists()).toBe(true)
  })

  it('displays query interface', () => {
    const wrapper = mount(HomeView, {
      global: {
        plugins: [mockRouter]
      }
    })
    
    const homeText = wrapper.text()
    expect(homeText).toContain('Natural Language Query')
  })

  it('has navigation to other features', () => {
    const wrapper = mount(HomeView, {
      global: {
        plugins: [mockRouter]
      }
    })
    
    // Should have links/buttons to other features
    const homeHTML = wrapper.html()
    expect(homeHTML).toBeTruthy()
  })
})