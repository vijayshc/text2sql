<template>
  <div class="metadata-search-view">
    <!-- Header -->
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white flex items-center">
          <i class="fas fa-search mr-3 text-indigo-600"></i>
          Metadata Search
        </h1>
        <p class="text-gray-600 dark:text-gray-400 mt-1">
          AI-powered semantic search of database schema and metadata
        </p>
      </div>
      
      <!-- Action Buttons -->
      <div class="flex items-center space-x-3">
        <div class="min-w-0 flex-1">
          <label for="workspaceSelect" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Workspace
          </label>
          <select
            id="workspaceSelect"
            v-model="selectedWorkspace"
            class="block w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
          >
            <option value="default">Default</option>
            <!-- Add more workspaces as needed -->
          </select>
        </div>
        
        <button
          @click="clearConversation"
          class="inline-flex items-center px-3 py-2 border border-gray-300 dark:border-gray-600 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
        >
          <i class="fas fa-broom mr-2"></i>
          Clear Chat
        </button>
        
        <button
          @click="reindexMetadata"
          class="inline-flex items-center px-3 py-2 border border-gray-300 dark:border-gray-600 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
        >
          <i class="fas fa-sync mr-2"></i>
          Reindex
        </button>
      </div>
    </div>

    <!-- Search Interface -->
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg flex flex-col h-[calc(100vh-16rem)]">
      <!-- Messages Area -->
      <div class="flex-1 overflow-y-auto p-4 space-y-4" ref="messagesContainer">
        <!-- Welcome Message -->
        <div v-if="messages.length === 0" class="flex items-start space-x-3">
          <div class="flex-shrink-0">
            <div class="w-8 h-8 bg-indigo-600 rounded-full flex items-center justify-center">
              <i class="fas fa-search text-white text-sm"></i>
            </div>
          </div>
          <div class="flex-1">
            <div class="bg-gray-50 dark:bg-gray-700 rounded-lg p-3">
              <p class="text-gray-900 dark:text-white">
                Welcome to Metadata Search! I can help you explore your database schema and find information about tables, columns, and relationships.
              </p>
              <p class="text-gray-600 dark:text-gray-400 mt-2">
                Try asking questions like:
              </p>
              <ul class="text-gray-600 dark:text-gray-400 mt-1 text-sm list-disc list-inside">
                <li>"Show me all user tables"</li>
                <li>"What columns contain customer information?"</li>
                <li>"Find tables related to orders"</li>
                <li>"Describe the user_profile table"</li>
              </ul>
            </div>
          </div>
        </div>

        <!-- Chat Messages -->
        <div
          v-for="(message, index) in messages"
          :key="index"
          class="flex items-start space-x-3"
          :class="message.type === 'user' ? 'flex-row-reverse space-x-reverse' : ''"
        >
          <div class="flex-shrink-0">
            <div
              class="w-8 h-8 rounded-full flex items-center justify-center"
              :class="message.type === 'user' 
                ? 'bg-green-600' 
                : message.type === 'error' 
                  ? 'bg-red-600' 
                  : 'bg-indigo-600'"
            >
              <i
                :class="message.type === 'user' 
                  ? 'fas fa-user text-white text-sm' 
                  : message.type === 'error'
                    ? 'fas fa-exclamation text-white text-sm'
                    : 'fas fa-search text-white text-sm'"
              ></i>
            </div>
          </div>
          <div class="flex-1 min-w-0">
            <div
              class="rounded-lg p-3"
              :class="message.type === 'user' 
                ? 'bg-green-50 dark:bg-green-900/20' 
                : message.type === 'error'
                  ? 'bg-red-50 dark:bg-red-900/20'
                  : 'bg-gray-50 dark:bg-gray-700'"
            >
              <div
                v-if="message.type === 'assistant' && message.markdown"
                v-html="message.content"
                class="prose prose-sm dark:prose-invert max-w-none text-gray-900 dark:text-white"
              ></div>
              <p
                v-else
                class="text-gray-900 dark:text-white whitespace-pre-wrap"
                :class="message.type === 'error' ? 'text-red-900 dark:text-red-200' : ''"
              >
                {{ message.content }}
              </p>
              
              <!-- Search Results -->
              <div v-if="message.results && message.results.length > 0" class="mt-4">
                <h4 class="text-sm font-medium text-gray-900 dark:text-white mb-2">
                  Related Schema Elements ({{ message.results.length }} found)
                </h4>
                <div class="space-y-2 max-h-64 overflow-y-auto">
                  <div
                    v-for="(result, resultIndex) in message.results"
                    :key="resultIndex"
                    class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded p-3 text-sm"
                  >
                    <div class="flex items-center justify-between mb-2">
                      <span class="font-medium text-gray-900 dark:text-white">
                        {{ result.table_name || result.name }}
                      </span>
                      <span class="text-xs text-indigo-600 dark:text-indigo-400 bg-indigo-100 dark:bg-indigo-900/20 px-2 py-1 rounded">
                        {{ result.type || 'Table' }}
                      </span>
                    </div>
                    <p v-if="result.description" class="text-gray-600 dark:text-gray-400 text-xs mb-2">
                      {{ result.description }}
                    </p>
                    <div v-if="result.columns" class="text-xs text-gray-500 dark:text-gray-500">
                      Columns: {{ result.columns.join(', ') }}
                    </div>
                    <div v-if="result.similarity" class="text-xs text-gray-400 dark:text-gray-500 mt-1">
                      Relevance: {{ Math.round(result.similarity * 100) }}%
                    </div>
                  </div>
                </div>
              </div>
              
              <div v-if="message.timestamp" class="text-xs text-gray-500 dark:text-gray-400 mt-2">
                {{ formatTime(message.timestamp) }}
                <span v-if="message.duration" class="ml-2">
                  ({{ message.duration.toFixed(2) }}s)
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- Processing Indicator -->
        <div v-if="isSearching" class="flex items-start space-x-3">
          <div class="flex-shrink-0">
            <div class="w-8 h-8 bg-indigo-600 rounded-full flex items-center justify-center">
              <i class="fas fa-search text-white text-sm"></i>
            </div>
          </div>
          <div class="flex-1">
            <div class="bg-gray-50 dark:bg-gray-700 rounded-lg p-3">
              <div class="flex items-center space-x-2">
                <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-indigo-600"></div>
                <span class="text-gray-600 dark:text-gray-400">{{ searchStatus || 'Searching metadata...' }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Input Area -->
      <div class="border-t border-gray-200 dark:border-gray-600 p-4">
        <div class="flex space-x-3">
          <div class="flex-1">
            <textarea
              v-model="inputQuery"
              @keydown.enter.meta.prevent="searchMetadata"
              @keydown.enter.ctrl.prevent="searchMetadata"
              @keydown.enter.exact="handleEnter"
              placeholder="Ask about your database schema... (Ctrl+Enter or Cmd+Enter to search)"
              rows="2"
              class="block w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm resize-none"
              :disabled="isSearching"
            ></textarea>
            <div class="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Press Ctrl+Enter (Cmd+Enter on Mac) to search, or Enter for new line
            </div>
          </div>
          <button
            @click="searchMetadata"
            :disabled="!inputQuery.trim() || isSearching"
            class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <i class="fas fa-search mr-2"></i>
            Search
          </button>
        </div>
      </div>
    </div>

    <!-- Reindex Progress Modal -->
    <div
      v-if="showReindexModal"
      class="fixed inset-0 z-50 overflow-y-auto"
      aria-labelledby="modal-title"
      role="dialog"
      aria-modal="true"
    >
      <div class="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" aria-hidden="true"></div>
        <span class="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>
        <div class="relative inline-block align-bottom bg-white dark:bg-gray-800 rounded-lg px-4 pt-5 pb-4 text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full sm:p-6">
          <div class="sm:flex sm:items-start">
            <div class="mx-auto flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-full bg-indigo-100 dark:bg-indigo-900/20 sm:mx-0 sm:h-10 sm:w-10">
              <i class="fas fa-sync-alt text-indigo-600 dark:text-indigo-400"></i>
            </div>
            <div class="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left flex-1">
              <h3 class="text-lg leading-6 font-medium text-gray-900 dark:text-white" id="modal-title">
                Reindexing Metadata
              </h3>
              <div class="mt-2">
                <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
                  {{ reindexStatus || 'Reindexing database metadata for improved search performance...' }}
                </p>
                <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                  <div class="bg-indigo-600 h-2 rounded-full transition-all duration-300 animate-pulse" style="width: 70%"></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import { useToast } from '@/composables/useToast'
import { apiService } from '@/services/api'
import { formatDistanceToNow } from 'date-fns'
import DOMPurify from 'dompurify'
import { marked } from 'marked'

// Reactive state
const inputQuery = ref('')
const messages = ref<Array<{
  type: 'user' | 'assistant' | 'error'
  content: string
  timestamp: Date
  duration?: number
  results?: any[]
  markdown?: boolean
}>>([])
const isSearching = ref(false)
const searchStatus = ref('')
const selectedWorkspace = ref('default')
const messagesContainer = ref<HTMLElement>()

// Reindex modal
const showReindexModal = ref(false)
const reindexStatus = ref('')

// Composables
const { showToast } = useToast()

// Methods
const scrollToBottom = async () => {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

const handleEnter = (event: KeyboardEvent) => {
  // Allow Enter for new line in textarea
  if (!event.ctrlKey && !event.metaKey) {
    return // Let the default behavior happen (new line)
  }
  event.preventDefault()
  searchMetadata()
}

const searchMetadata = async () => {
  if (!inputQuery.value.trim() || isSearching.value) return

  const query = inputQuery.value.trim()
  inputQuery.value = ''

  // Add user message
  messages.value.push({
    type: 'user',
    content: query,
    timestamp: new Date()
  })

  scrollToBottom()

  // Start searching
  isSearching.value = true
  searchStatus.value = 'Searching metadata...'

  try {
    // Create SSE connection
    const url = new URL('/api/v1/metadata-search/search', window.location.origin)
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify({
        query: query,
        workspace: selectedWorkspace.value,
        streaming: true,
        conversation_history: messages.value.slice(0, -1).map(msg => ({
          role: msg.type === 'user' ? 'user' : 'assistant',
          content: msg.content
        }))
      })
    })

    if (!response.body) {
      throw new Error('No response body')
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let currentMessage = ''
    let messageAdded = false
    let searchResults: any[] = []
    let searchDuration = 0

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      const chunk = decoder.decode(value)
      const lines = chunk.split('\n')

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            
            switch (data.type) {
              case 'status':
                searchStatus.value = data.message || 'Processing...'
                break
                
              case 'text':
                if (data.content) {
                  currentMessage += data.content
                  
                  // Add or update assistant message
                  if (!messageAdded) {
                    messages.value.push({
                      type: 'assistant',
                      content: currentMessage,
                      timestamp: new Date(),
                      markdown: true
                    })
                    messageAdded = true
                  } else {
                    // Update the last message
                    const lastMessage = messages.value[messages.value.length - 1]
                    if (lastMessage.type === 'assistant') {
                      lastMessage.content = currentMessage
                    }
                  }
                  scrollToBottom()
                }
                break
                
              case 'results':
                searchResults = data.data || []
                searchDuration = data.duration || 0
                break
                
              case 'error':
                messages.value.push({
                  type: 'error',
                  content: data.message || 'An error occurred',
                  timestamp: new Date()
                })
                scrollToBottom()
                break
                
              case 'complete':
                isSearching.value = false
                searchStatus.value = ''
                
                // Process markdown and add results for the final message
                if (messageAdded && currentMessage) {
                  const lastMessage = messages.value[messages.value.length - 1]
                  if (lastMessage.type === 'assistant') {
                    try {
                      const html = marked(currentMessage)
                      lastMessage.content = DOMPurify.sanitize(html)
                      lastMessage.results = searchResults
                      lastMessage.duration = searchDuration
                    } catch (e) {
                      // Fallback to plain text
                      lastMessage.markdown = false
                      lastMessage.results = searchResults
                      lastMessage.duration = searchDuration
                    }
                  }
                  scrollToBottom()
                }
                break
            }
          } catch (e) {
            console.error('Error parsing SSE data:', e)
          }
        }
      }
    }
  } catch (error) {
    console.error('Error in metadata search:', error)
    isSearching.value = false
    searchStatus.value = ''
    
    messages.value.push({
      type: 'error',
      content: `Error: ${error instanceof Error ? error.message : 'Unknown error occurred'}`,
      timestamp: new Date()
    })
    scrollToBottom()
    showToast('Failed to search metadata', 'error')
  }
}

const clearConversation = async () => {
  try {
    await apiService.post('/api/v1/metadata-search/conversation/clear')
    messages.value = []
    showToast('Conversation cleared', 'success')
  } catch (error) {
    console.error('Error clearing conversation:', error)
    showToast('Failed to clear conversation', 'error')
  }
}

const reindexMetadata = async () => {
  showReindexModal.value = true
  reindexStatus.value = 'Starting reindexing process...'

  try {
    const url = new URL('/api/v1/metadata-search/reindex', window.location.origin)
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify({
        workspace: selectedWorkspace.value
      })
    })

    if (!response.body) {
      throw new Error('No response body')
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      const chunk = decoder.decode(value)
      const lines = chunk.split('\n')

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            
            switch (data.type) {
              case 'status':
                reindexStatus.value = data.message || 'Processing...'
                break
                
              case 'result':
                reindexStatus.value = 'Reindexing completed successfully!'
                setTimeout(() => {
                  showReindexModal.value = false
                  showToast('Metadata reindexed successfully', 'success')
                }, 2000)
                break
                
              case 'error':
                reindexStatus.value = `Error: ${data.message}`
                setTimeout(() => {
                  showReindexModal.value = false
                  showToast('Failed to reindex metadata', 'error')
                }, 2000)
                break
                
              case 'complete':
                if (reindexStatus.value.includes('Error')) {
                  // Error already handled
                } else if (!reindexStatus.value.includes('completed')) {
                  reindexStatus.value = 'Reindexing completed!'
                  setTimeout(() => {
                    showReindexModal.value = false
                    showToast('Metadata reindexed successfully', 'success')
                  }, 1000)
                }
                break
            }
          } catch (e) {
            console.error('Error parsing SSE data:', e)
          }
        }
      }
    }
  } catch (error) {
    console.error('Error reindexing metadata:', error)
    reindexStatus.value = `Error: ${error instanceof Error ? error.message : 'Unknown error'}`
    setTimeout(() => {
      showReindexModal.value = false
      showToast('Failed to reindex metadata', 'error')
    }, 2000)
  }
}

const formatTime = (timestamp: Date) => {
  return formatDistanceToNow(timestamp, { addSuffix: true })
}

// Lifecycle
onMounted(() => {
  // Auto-focus on input when component mounts
  // No additional initialization needed
})
</script>

<style scoped>
.metadata-search-view {
  @apply p-6;
}

.prose {
  @apply text-gray-900;
}

.dark .prose {
  @apply text-white;
}

.prose h1, .prose h2, .prose h3, .prose h4, .prose h5, .prose h6 {
  @apply text-gray-900;
}

.dark .prose h1, .dark .prose h2, .dark .prose h3, .dark .prose h4, .dark .prose h5, .dark .prose h6 {
  @apply text-white;
}

.prose code {
  @apply bg-gray-100 text-gray-900 px-1 py-0.5 rounded text-sm;
}

.dark .prose code {
  @apply bg-gray-700 text-white;
}

.prose pre {
  @apply bg-gray-100 text-gray-900 p-4 rounded;
}

.dark .prose pre {
  @apply bg-gray-700 text-white;
}
</style>