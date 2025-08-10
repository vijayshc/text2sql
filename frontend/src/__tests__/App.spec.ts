import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import { setActivePinia, createPinia } from 'pinia'
import App from '../App.vue'

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

// Mock auth store
vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    isAuthenticated: false,
    user: null,
    initializeAuth: vi.fn()
  })
}))

// Mock UI store
vi.mock('@/stores/ui', () => ({
  useUIStore: () => ({
    sidebarOpen: true,
    initializeTheme: vi.fn()
  })
}))

// Mock router for testing
const mockRouter = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: { template: '<div>Home</div>' } },
    { path: '/login', component: { template: '<div>Login</div>' } }
  ]
})

describe('App', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders properly', () => {
    const wrapper = mount(App, {
      global: {
        plugins: [mockRouter]
      }
    })
    expect(wrapper.find('#app').exists()).toBe(true)
  })

  it('has router-view for SPA routing', () => {
    const wrapper = mount(App, {
      global: {
        plugins: [mockRouter]
      }
    })
    expect(wrapper.findComponent({ name: 'RouterView' }).exists()).toBe(true)
  })
})
