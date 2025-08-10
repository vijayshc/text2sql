<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useUIStore } from '@/stores/ui'

const router = useRouter()
const authStore = useAuthStore()
const uiStore = useUIStore()

const form = ref({
  currentPassword: '',
  newPassword: '',
  confirmPassword: ''
})

const isLoading = ref(false)
const showCurrentPassword = ref(false)
const showNewPassword = ref(false)
const showConfirmPassword = ref(false)

const passwordValidation = ref({
  minLength: false,
  hasUppercase: false,
  hasLowercase: false,
  hasNumber: false,
  hasSpecial: false
})

const validatePassword = (password: string) => {
  passwordValidation.value = {
    minLength: password.length >= 8,
    hasUppercase: /[A-Z]/.test(password),
    hasLowercase: /[a-z]/.test(password),
    hasNumber: /\d/.test(password),
    hasSpecial: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)
  }
}

const isPasswordValid = () => {
  return Object.values(passwordValidation.value).every(Boolean)
}

const passwordsMatch = () => {
  return form.value.newPassword === form.value.confirmPassword
}

const canSubmit = () => {
  return (
    form.value.currentPassword &&
    form.value.newPassword &&
    form.value.confirmPassword &&
    isPasswordValid() &&
    passwordsMatch() &&
    !isLoading.value
  )
}

const handleSubmit = async () => {
  if (!canSubmit()) return

  try {
    isLoading.value = true
    await authStore.changePassword(form.value.currentPassword, form.value.newPassword)
    
    uiStore.showSuccess('Password Changed', 'Your password has been updated successfully')
    router.push('/')
  } catch (error: any) {
    uiStore.showError('Password Change Failed', error.response?.data?.message || 'Failed to change password')
  } finally {
    isLoading.value = false
  }
}

// Watch new password for validation
watch(() => form.value.newPassword, validatePassword)
</script>

<template>
  <div class="max-w-md mx-auto">
    <!-- Page Header -->
    <div class="text-center mb-8">
      <h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-2">
        Change Password
      </h1>
      <p class="text-gray-600 dark:text-gray-400">
        Update your account password
      </p>
    </div>

    <!-- Change Password Form -->
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
      <form @submit.prevent="handleSubmit" class="space-y-6">
        <!-- Current Password -->
        <div>
          <label for="currentPassword" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Current Password
          </label>
          <div class="relative">
            <input
              id="currentPassword"
              v-model="form.currentPassword"
              :type="showCurrentPassword ? 'text' : 'password'"
              required
              autocomplete="current-password"
              class="w-full px-4 py-3 pr-12 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors"
              placeholder="Enter your current password"
            />
            <button
              type="button"
              @click="showCurrentPassword = !showCurrentPassword"
              class="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            >
              <i :class="showCurrentPassword ? 'fas fa-eye-slash' : 'fas fa-eye'"></i>
            </button>
          </div>
        </div>

        <!-- New Password -->
        <div>
          <label for="newPassword" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            New Password
          </label>
          <div class="relative">
            <input
              id="newPassword"
              v-model="form.newPassword"
              :type="showNewPassword ? 'text' : 'password'"
              required
              autocomplete="new-password"
              class="w-full px-4 py-3 pr-12 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors"
              placeholder="Enter your new password"
            />
            <button
              type="button"
              @click="showNewPassword = !showNewPassword"
              class="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            >
              <i :class="showNewPassword ? 'fas fa-eye-slash' : 'fas fa-eye'"></i>
            </button>
          </div>
          
          <!-- Password Requirements -->
          <div v-if="form.newPassword" class="mt-3 space-y-2">
            <p class="text-sm text-gray-600 dark:text-gray-400">Password requirements:</p>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
              <div class="flex items-center">
                <i :class="passwordValidation.minLength ? 'fas fa-check text-green-500' : 'fas fa-times text-red-500'" class="mr-2"></i>
                <span :class="passwordValidation.minLength ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'">
                  At least 8 characters
                </span>
              </div>
              <div class="flex items-center">
                <i :class="passwordValidation.hasUppercase ? 'fas fa-check text-green-500' : 'fas fa-times text-red-500'" class="mr-2"></i>
                <span :class="passwordValidation.hasUppercase ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'">
                  Uppercase letter
                </span>
              </div>
              <div class="flex items-center">
                <i :class="passwordValidation.hasLowercase ? 'fas fa-check text-green-500' : 'fas fa-times text-red-500'" class="mr-2"></i>
                <span :class="passwordValidation.hasLowercase ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'">
                  Lowercase letter
                </span>
              </div>
              <div class="flex items-center">
                <i :class="passwordValidation.hasNumber ? 'fas fa-check text-green-500' : 'fas fa-times text-red-500'" class="mr-2"></i>
                <span :class="passwordValidation.hasNumber ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'">
                  Number
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- Confirm Password -->
        <div>
          <label for="confirmPassword" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Confirm New Password
          </label>
          <div class="relative">
            <input
              id="confirmPassword"
              v-model="form.confirmPassword"
              :type="showConfirmPassword ? 'text' : 'password'"
              required
              autocomplete="new-password"
              class="w-full px-4 py-3 pr-12 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors"
              placeholder="Confirm your new password"
              :class="{
                'border-red-500 focus:border-red-500 focus:ring-red-500': form.confirmPassword && !passwordsMatch(),
                'border-green-500 focus:border-green-500 focus:ring-green-500': form.confirmPassword && passwordsMatch()
              }"
            />
            <button
              type="button"
              @click="showConfirmPassword = !showConfirmPassword"
              class="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            >
              <i :class="showConfirmPassword ? 'fas fa-eye-slash' : 'fas fa-eye'"></i>
            </button>
          </div>
          
          <!-- Password Match Indicator -->
          <div v-if="form.confirmPassword" class="mt-2">
            <div v-if="passwordsMatch()" class="flex items-center text-sm text-green-600 dark:text-green-400">
              <i class="fas fa-check mr-2"></i>
              Passwords match
            </div>
            <div v-else class="flex items-center text-sm text-red-600 dark:text-red-400">
              <i class="fas fa-times mr-2"></i>
              Passwords do not match
            </div>
          </div>
        </div>

        <!-- Submit Button -->
        <div class="flex justify-end space-x-3">
          <router-link
            to="/"
            class="btn btn-secondary"
          >
            Cancel
          </router-link>
          
          <button
            type="submit"
            :disabled="!canSubmit()"
            class="btn btn-primary"
          >
            <i v-if="isLoading" class="fas fa-spinner fa-spin mr-2"></i>
            <i v-else class="fas fa-key mr-2"></i>
            {{ isLoading ? 'Updating...' : 'Update Password' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
/* Custom button styles */
.btn {
  @apply inline-flex items-center justify-center px-4 py-2 border rounded-lg text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed;
}

.btn-primary {
  @apply border-transparent text-white bg-primary-600 hover:bg-primary-700 focus:ring-primary-500;
}

.btn-secondary {
  @apply border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 focus:ring-primary-500;
}

/* Font Awesome icons */
.fas {
  font-family: 'Font Awesome 6 Free';
  font-weight: 900;
}
</style>