<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
    <div class="max-w-md w-full space-y-8">
      <div>
        <h2 class="mt-6 text-center text-3xl font-extrabold text-gray-900">
          Reset your password
        </h2>
        <p class="mt-2 text-center text-sm text-gray-600">
          Enter your username to receive reset instructions
        </p>
      </div>
      
      <form class="mt-8 space-y-6" @submit.prevent="submitResetRequest">
        <div>
          <label for="username" class="sr-only">Username</label>
          <input
            id="username"
            v-model="form.username"
            name="username"
            type="text"
            required
            class="relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
            placeholder="Username"
            :disabled="loading"
          />
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
            :disabled="loading || !form.username.trim()"
            class="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span v-if="loading" class="absolute inset-y-0 left-0 flex items-center pl-3">
              <svg class="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            </span>
            {{ loading ? 'Sending...' : 'Send Reset Instructions' }}
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
import { ref, computed } from 'vue'
import { CheckCircleIcon, ExclamationTriangleIcon } from '@heroicons/vue/24/outline'
import { authService } from '@/services/api'

const form = ref({
  username: ''
})

const loading = ref(false)
const message = ref('')
const success = ref(false)

const messageClass = computed(() => ({
  'bg-green-50 text-green-800': success.value,
  'bg-red-50 text-red-800': !success.value
}))

const submitResetRequest = async () => {
  if (!form.value.username.trim()) return
  
  loading.value = true
  message.value = ''
  
  try {
    const response = await authService.resetPasswordRequest({
      username: form.value.username.trim()
    })
    
    success.value = true
    message.value = response.message || 'If the username exists, password reset instructions have been sent.'
    
  } catch (error: any) {
    success.value = false
    message.value = error.message || 'Failed to send reset instructions. Please try again.'
  } finally {
    loading.value = false
  }
}
</script>