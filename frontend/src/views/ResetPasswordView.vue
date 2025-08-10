<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
    <div class="max-w-md w-full space-y-8">
      <div>
        <h2 class="mt-6 text-center text-3xl font-extrabold text-gray-900">
          Set new password
        </h2>
        <p class="mt-2 text-center text-sm text-gray-600">
          Enter your new password below
        </p>
      </div>
      
      <form class="mt-8 space-y-6" @submit.prevent="submitPasswordReset">
        <div class="space-y-4">
          <div>
            <label for="password" class="sr-only">New Password</label>
            <input
              id="password"
              v-model="form.password"
              name="password"
              type="password"
              required
              class="relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
              placeholder="New password (min 6 characters)"
              :disabled="loading"
            />
          </div>
          
          <div>
            <label for="password_confirm" class="sr-only">Confirm Password</label>
            <input
              id="password_confirm"
              v-model="form.password_confirm"
              name="password_confirm"
              type="password"
              required
              class="relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
              placeholder="Confirm new password"
              :disabled="loading"
            />
          </div>
        </div>

        <div v-if="validationErrors.length > 0" class="bg-red-50 border border-red-200 rounded-md p-4">
          <div class="flex">
            <div class="flex-shrink-0">
              <ExclamationTriangleIcon class="h-5 w-5 text-red-400" />
            </div>
            <div class="ml-3">
              <h3 class="text-sm font-medium text-red-800">
                Please fix the following errors:
              </h3>
              <div class="mt-2 text-sm text-red-700">
                <ul class="list-disc list-inside space-y-1">
                  <li v-for="error in validationErrors" :key="error">{{ error }}</li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        <div v-if="message" :class="messageClass" class="rounded-md p-4">
          <div class="flex">
            <div class="flex-shrink-0">
              <CheckCircleIcon v-if="success" class="h-5 w-5 text-green-400" />
              <ExclamationTriangleIcon v-else class="h-5 w-5 text-red-400" />
            </div>
            <div class="ml-3">
              <p class="text-sm font-medium">
                {{ message }}
              </p>
            </div>
          </div>
        </div>

        <div>
          <button
            type="submit"
            :disabled="loading || !isFormValid"
            class="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span v-if="loading" class="absolute inset-y-0 left-0 flex items-center pl-3">
              <svg class="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            </span>
            {{ loading ? 'Resetting...' : 'Reset Password' }}
          </button>
        </div>

        <div class="text-center">
          <router-link 
            to="/login" 
            class="font-medium text-blue-600 hover:text-blue-500"
          >
            Back to login
          </router-link>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { CheckCircleIcon, ExclamationTriangleIcon } from '@heroicons/vue/24/outline'
import { authService } from '@/services/api'

const route = useRoute()
const router = useRouter()

const form = ref({
  password: '',
  password_confirm: ''
})

const loading = ref(false)
const message = ref('')
const success = ref(false)
const token = ref('')

const validationErrors = computed(() => {
  const errors: string[] = []
  
  if (form.value.password && form.value.password.length < 6) {
    errors.push('Password must be at least 6 characters long')
  }
  
  if (form.value.password && form.value.password_confirm && form.value.password !== form.value.password_confirm) {
    errors.push('Passwords do not match')
  }
  
  return errors
})

const isFormValid = computed(() => {
  return form.value.password.length >= 6 && 
         form.value.password_confirm.length >= 6 && 
         form.value.password === form.value.password_confirm
})

const messageClass = computed(() => ({
  'bg-green-50 text-green-800': success.value,
  'bg-red-50 text-red-800': !success.value
}))

onMounted(() => {
  // Get token from route params
  token.value = route.params.token as string || ''
  
  if (!token.value) {
    message.value = 'Invalid reset link. Please request a new password reset.'
    success.value = false
  }
})

const submitPasswordReset = async () => {
  if (!isFormValid.value || !token.value) return
  
  loading.value = true
  message.value = ''
  
  try {
    const response = await authService.resetPassword({
      token: token.value,
      password: form.value.password,
      password_confirm: form.value.password_confirm
    })
    
    success.value = true
    message.value = response.message || 'Password has been reset successfully!'
    
    // Redirect to login after 3 seconds
    setTimeout(() => {
      router.push('/login')
    }, 3000)
    
  } catch (error: any) {
    success.value = false
    message.value = error.message || 'Failed to reset password. Please try again.'
  } finally {
    loading.value = false
  }
}
</script>