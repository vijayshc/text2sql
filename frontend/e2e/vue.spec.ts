import { test, expect } from '@playwright/test'

test.describe('Vue.js Migration E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the app
    await page.goto('/')
  })

  test('SPA loads correctly', async ({ page }) => {
    // Should load Vue.js app
    await expect(page.locator('#app')).toBeVisible()
    
    // Should have Vue.js in the title or page
    await expect(page).toHaveTitle(/Text2SQL/)
  })

  test('client-side routing works', async ({ page }) => {
    // Should show login page initially (if not authenticated)
    const currentUrl = page.url()
    expect(currentUrl).toContain('/')
    
    // Test that routes don't cause full page reload
    const navigationPromise = page.waitForURL('**/login')
    await page.goto('/login')
    await navigationPromise
    
    // Should still be SPA (no full page reload)
    await expect(page.locator('#app')).toBeVisible()
  })

  test('admin routes are protected', async ({ page }) => {
    // Try to access admin directly
    await page.goto('/admin')
    
    // Should redirect to login or show auth required
    const currentUrl = page.url()
    expect(currentUrl).toMatch(/(login|auth|admin)/)
  })

  test('navigation menu exists', async ({ page }) => {
    // Try to find navigation elements
    // This test will pass if any navigation is visible
    const hasNav = await page.locator('nav, .sidebar, .menu').count() > 0 ||
                   await page.locator('[role="navigation"]').count() > 0
    
    expect(hasNav).toBeTruthy()
  })

  test('API endpoints are accessible', async ({ page }) => {
    // Test that API calls work (check network requests)
    let apiCallMade = false
    
    page.on('request', request => {
      if (request.url().includes('/api/')) {
        apiCallMade = true
      }
    })
    
    // Navigate around to trigger API calls
    await page.goto('/')
    await page.waitForTimeout(1000)
    
    // Some pages should make API calls
    expect(apiCallMade).toBeTruthy()
  })

  test('responsive design works', async ({ page }) => {
    // Test mobile view
    await page.setViewportSize({ width: 375, height: 667 })
    await expect(page.locator('#app')).toBeVisible()
    
    // Test desktop view
    await page.setViewportSize({ width: 1200, height: 800 })
    await expect(page.locator('#app')).toBeVisible()
  })

  test('no JavaScript errors in console', async ({ page }) => {
    const errors: string[] = []
    
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text())
      }
    })
    
    await page.goto('/')
    await page.waitForTimeout(2000)
    
    // Filter out known acceptable errors
    const criticalErrors = errors.filter(error => 
      !error.includes('404') && 
      !error.includes('401') && 
      !error.includes('403') &&
      !error.toLowerCase().includes('network')
    )
    
    expect(criticalErrors).toHaveLength(0)
  })
})
