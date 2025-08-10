<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useQueryStore } from '@/stores/query'
import { useUIStore } from '@/stores/ui'
import ApiService from '@/services/api'

const queryStore = useQueryStore()
const uiStore = useUIStore()

// Query input
const queryInput = ref('')
const selectedTables = ref<string[]>([])
const tableSearch = ref('')

// UI state
const showTableSelector = ref(false)
const showSQLModal = ref(false)
const showExplanationModal = ref(false)

// Feedback state
const showFeedbackModal = ref(false)
const feedbackRating = ref(5)
const feedbackComment = ref('')

// Table suggestions
const tableSuggestions = ref<string[]>([])

const filteredTables = computed(() => {
  if (!tableSearch.value) {
    return queryStore.schema.map(table => table.name).slice(0, 10)
  }
  return queryStore.schema
    .filter(table => 
      table.name.toLowerCase().includes(tableSearch.value.toLowerCase()) ||
      table.description?.toLowerCase().includes(tableSearch.value.toLowerCase())
    )
    .map(table => table.name)
    .slice(0, 10)
})

const canSubmitQuery = computed(() => {
  return queryInput.value.trim().length > 0 && !queryStore.isSubmitting && !queryStore.isQueryInProgress
})

const progressPercentage = computed(() => {
  if (!queryStore.queryProgress?.steps) return 0
  const totalSteps = queryStore.queryProgress.steps.length
  const currentStep = queryStore.queryProgress.current_step || 0
  return totalSteps > 0 ? (currentStep / totalSteps) * 100 : 0
})

const handleSubmitQuery = async () => {
  if (!canSubmitQuery.value) return

  try {
    queryStore.currentQuery = queryInput.value
    queryStore.selectedTables = selectedTables.value
    await queryStore.submitQuery()
    
    uiStore.showSuccess('Query Submitted', 'Processing your request...')
  } catch (error: any) {
    uiStore.showError('Query Failed', error.message)
  }
}

const handleTableToggle = (tableName: string) => {
  const index = selectedTables.value.indexOf(tableName)
  if (index === -1) {
    selectedTables.value.push(tableName)
  } else {
    selectedTables.value.splice(index, 1)
  }
}

const clearResults = () => {
  queryStore.clearResults()
  queryInput.value = ''
  selectedTables.value = []
}

const submitFeedback = async () => {
  try {
    await ApiService.submitFeedback({
      query_text: queryStore.currentQuery,
      sql_query: queryStore.generatedSQL,
      feedback_rating: feedbackRating.value,
      results_summary: feedbackComment.value,
      workspace: queryStore.selectedWorkspace,
      tables_used: queryStore.selectedTables
    })
    
    uiStore.showSuccess('Feedback Submitted', 'Thank you for your feedback!')
    showFeedbackModal.value = false
    feedbackComment.value = ''
    feedbackRating.value = 5
  } catch (error: any) {
    uiStore.showError('Feedback Failed', error.message)
  }
}

const formatResults = (results: any) => {
  if (!results || !Array.isArray(results)) return []
  return results.slice(0, 100) // Limit to first 100 rows
}

// Load table suggestions when query changes
let timeoutId: ReturnType<typeof setTimeout>
watch(queryInput, async (newQuery) => {
  clearTimeout(timeoutId)
  if (newQuery.length > 3) {
    timeoutId = setTimeout(async () => {
      try {
        tableSuggestions.value = await queryStore.getTableSuggestions(newQuery)
      } catch (error) {
        console.warn('Failed to get table suggestions:', error)
      }
    }, 500)
  }
})

onMounted(async () => {
  await queryStore.loadWorkspaces()
  await queryStore.loadSchema()
})
</script>

<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white">
          Natural Language Query
        </h1>
        <p class="text-gray-600 dark:text-gray-400 mt-1">
          Ask questions about your data in plain English
        </p>
      </div>
      
      <button
        v-if="queryStore.hasResults"
        @click="clearResults"
        class="btn btn-secondary"
      >
        <i class="fas fa-plus mr-2"></i>
        New Query
      </button>
    </div>

    <!-- Query Input Section -->
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
      <div class="space-y-4">
        <!-- Query Input -->
        <div>
          <label for="query" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Your Question
          </label>
          <div class="relative">
            <textarea
              id="query"
              v-model="queryInput"
              rows="4"
              class="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 resize-none"
              placeholder="e.g., Show me all customers who made purchases in the last month"
              :disabled="queryStore.isQueryInProgress"
            ></textarea>
            
            <!-- Character count -->
            <div class="absolute bottom-2 right-2 text-xs text-gray-400">
              {{ queryInput.length }}/500
            </div>
          </div>
        </div>

        <!-- Table Selection -->
        <div>
          <div class="flex items-center justify-between mb-2">
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Focus Tables (Optional)
            </label>
            <button
              @click="showTableSelector = !showTableSelector"
              class="text-sm text-primary-600 dark:text-primary-400 hover:text-primary-800 dark:hover:text-primary-300"
            >
              {{ showTableSelector ? 'Hide' : 'Select Tables' }}
            </button>
          </div>
          
          <!-- Selected Tables Display -->
          <div v-if="selectedTables.length > 0" class="flex flex-wrap gap-2 mb-3">
            <span
              v-for="table in selectedTables"
              :key="table"
              class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-primary-100 dark:bg-primary-900 text-primary-800 dark:text-primary-200"
            >
              {{ table }}
              <button
                @click="handleTableToggle(table)"
                class="ml-1 text-primary-600 dark:text-primary-400 hover:text-primary-800 dark:hover:text-primary-300"
              >
                <i class="fas fa-times text-xs"></i>
              </button>
            </span>
          </div>

          <!-- Table Selector -->
          <div v-if="showTableSelector" class="border border-gray-200 dark:border-gray-600 rounded-lg p-4 bg-gray-50 dark:bg-gray-700">
            <!-- Search Tables -->
            <div class="mb-3">
              <input
                v-model="tableSearch"
                type="text"
                placeholder="Search tables..."
                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
            
            <!-- Table List -->
            <div class="max-h-32 overflow-y-auto space-y-1">
              <label
                v-for="table in filteredTables"
                :key="table"
                class="flex items-center p-2 rounded hover:bg-gray-100 dark:hover:bg-gray-600 cursor-pointer"
              >
                <input
                  type="checkbox"
                  :checked="selectedTables.includes(table)"
                  @change="handleTableToggle(table)"
                  class="mr-3 h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 dark:border-gray-600 rounded"
                />
                <span class="text-sm text-gray-700 dark:text-gray-300">{{ table }}</span>
              </label>
            </div>
          </div>
        </div>

        <!-- Submit Button -->
        <button
          @click="handleSubmitQuery"
          :disabled="!canSubmitQuery"
          class="w-full btn btn-primary py-3"
        >
          <i v-if="queryStore.isSubmitting" class="fas fa-spinner fa-spin mr-2"></i>
          <i v-else class="fas fa-search mr-2"></i>
          {{ queryStore.isSubmitting ? 'Submitting...' : 'Submit Query' }}
        </button>
      </div>
    </div>

    <!-- Query Progress -->
    <div
      v-if="queryStore.isQueryInProgress"
      class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6"
    >
      <div class="space-y-4">
        <div class="flex items-center justify-between">
          <h3 class="text-lg font-medium text-gray-900 dark:text-white">Processing Query</h3>
          <span class="text-sm text-gray-500 dark:text-gray-400">{{ Math.round(progressPercentage) }}%</span>
        </div>
        
        <!-- Progress Bar -->
        <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
          <div
            class="bg-primary-600 h-2 rounded-full transition-all duration-300"
            :style="{ width: `${progressPercentage}%` }"
          ></div>
        </div>
        
        <!-- Current Step -->
        <div v-if="queryStore.queryProgress?.current_step !== undefined" class="text-sm text-gray-600 dark:text-gray-400">
          Step {{ queryStore.queryProgress.current_step + 1 }} of {{ queryStore.queryProgress.steps?.length || 0 }}:
          {{ queryStore.queryProgress.steps?.[queryStore.queryProgress.current_step] || 'Processing...' }}
        </div>
      </div>
    </div>

    <!-- Results Section -->
    <div v-if="queryStore.hasResults" class="space-y-6">
      <!-- Action Buttons -->
      <div class="flex flex-wrap gap-3">
        <button
          @click="showSQLModal = true"
          class="btn btn-secondary"
        >
          <i class="fas fa-code mr-2"></i>
          View SQL
        </button>
        
        <button
          v-if="queryStore.explanation"
          @click="showExplanationModal = true"
          class="btn btn-secondary"
        >
          <i class="fas fa-lightbulb mr-2"></i>
          Explanation
        </button>
        
        <button
          @click="showFeedbackModal = true"
          class="btn btn-secondary"
        >
          <i class="fas fa-star mr-2"></i>
          Rate Result
        </button>
      </div>

      <!-- Results Table -->
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 class="text-lg font-medium text-gray-900 dark:text-white">Query Results</h3>
          <p class="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Showing {{ formatResults(queryStore.queryResults).length }} 
            {{ formatResults(queryStore.queryResults).length === 100 ? '(first 100)' : '' }} results
          </p>
        </div>
        
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead class="bg-gray-50 dark:bg-gray-700">
              <tr>
                <th
                  v-for="(column, index) in Object.keys(formatResults(queryStore.queryResults)[0] || {})"
                  :key="index"
                  class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
                >
                  {{ column }}
                </th>
              </tr>
            </thead>
            <tbody class="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
              <tr
                v-for="(row, rowIndex) in formatResults(queryStore.queryResults)"
                :key="rowIndex"
                class="hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                <td
                  v-for="(value, colIndex) in Object.values(row)"
                  :key="colIndex"
                  class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white"
                >
                  {{ value }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- SQL Modal -->
    <div
      v-if="showSQLModal"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-50"
      @click.self="showSQLModal = false"
    >
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-4xl w-full max-h-[80vh] overflow-hidden">
        <div class="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <h3 class="text-lg font-medium text-gray-900 dark:text-white">Generated SQL Query</h3>
          <button
            @click="showSQLModal = false"
            class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <i class="fas fa-times"></i>
          </button>
        </div>
        <div class="p-6 overflow-y-auto">
          <pre class="bg-gray-100 dark:bg-gray-900 p-4 rounded-lg text-sm overflow-x-auto"><code>{{ queryStore.generatedSQL }}</code></pre>
        </div>
      </div>
    </div>

    <!-- Explanation Modal -->
    <div
      v-if="showExplanationModal"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-50"
      @click.self="showExplanationModal = false"
    >
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-hidden">
        <div class="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <h3 class="text-lg font-medium text-gray-900 dark:text-white">Query Explanation</h3>
          <button
            @click="showExplanationModal = false"
            class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <i class="fas fa-times"></i>
          </button>
        </div>
        <div class="p-6 overflow-y-auto">
          <div class="prose dark:prose-invert max-w-none" v-html="queryStore.explanation"></div>
        </div>
      </div>
    </div>

    <!-- Feedback Modal -->
    <div
      v-if="showFeedbackModal"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-50"
      @click.self="showFeedbackModal = false"
    >
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full">
        <div class="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <h3 class="text-lg font-medium text-gray-900 dark:text-white">Rate This Result</h3>
          <button
            @click="showFeedbackModal = false"
            class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <i class="fas fa-times"></i>
          </button>
        </div>
        <div class="p-6 space-y-4">
          <!-- Rating -->
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Rating (1-5)
            </label>
            <div class="flex space-x-1">
              <button
                v-for="star in 5"
                :key="star"
                @click="feedbackRating = star"
                class="text-2xl transition-colors"
                :class="{
                  'text-yellow-400': star <= feedbackRating,
                  'text-gray-300 dark:text-gray-600': star > feedbackRating
                }"
              >
                <i class="fas fa-star"></i>
              </button>
            </div>
          </div>
          
          <!-- Comment -->
          <div>
            <label for="feedbackComment" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Comments (Optional)
            </label>
            <textarea
              id="feedbackComment"
              v-model="feedbackComment"
              rows="3"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              placeholder="Any additional feedback..."
            ></textarea>
          </div>
          
          <!-- Submit -->
          <div class="flex justify-end space-x-3">
            <button
              @click="showFeedbackModal = false"
              class="btn btn-secondary"
            >
              Cancel
            </button>
            <button
              @click="submitFeedback"
              class="btn btn-primary"
            >
              Submit Feedback
            </button>
          </div>
        </div>
      </div>
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

/* Table styling */
table {
  border-collapse: collapse;
}

/* Prose styling for explanation */
.prose {
  max-width: none;
}

.prose h1,
.prose h2,
.prose h3 {
  color: inherit;
}

.prose p {
  color: inherit;
}
</style>