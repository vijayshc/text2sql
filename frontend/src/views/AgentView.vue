<template>
  <div class="agent-view">
    <!-- Header -->
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white flex items-center">
          <i class="fas fa-robot mr-3 text-blue-600"></i>
          Agent Mode
        </h1>
        <p class="text-gray-600 dark:text-gray-400 mt-1">
          Intelligent task execution with MCP server integration
        </p>
      </div>
      
      <!-- Server Selection -->
      <div class="flex items-center space-x-4">
        <div class="min-w-0 flex-1">
          <label for="serverSelect" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            MCP Server
          </label>
          <select
            id="serverSelect"
            v-model="selectedServer"
            class="block w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
          >
            <option value="">Auto-select best server</option>
            <option v-for="server in availableServers" :key="server.id" :value="server.id">
              {{ server.name }} - {{ server.description }}
            </option>
          </select>
        </div>
        
        <button
          @click="clearConversation"
          class="inline-flex items-center px-3 py-2 border border-gray-300 dark:border-gray-600 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          <i class="fas fa-broom mr-2"></i>
          Clear Chat
        </button>
      </div>
    </div>

    <!-- Chat Container -->
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg flex flex-col h-[calc(100vh-16rem)]">
      <!-- Messages Area -->
      <div class="flex-1 overflow-y-auto p-4 space-y-4" ref="messagesContainer">
        <!-- Welcome Message -->
        <div v-if="messages.length === 0" class="flex items-start space-x-3">
          <div class="flex-shrink-0">
            <div class="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
              <i class="fas fa-robot text-white text-sm"></i>
            </div>
          </div>
          <div class="flex-1">
            <div class="bg-gray-50 dark:bg-gray-700 rounded-lg p-3">
              <p class="text-gray-900 dark:text-white">
                Hello! I'm your agent assistant. I can help you with various tasks using available MCP servers.
              </p>
              <p class="text-gray-600 dark:text-gray-400 mt-2">
                What would you like me to help you with today?
              </p>
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
                  : 'bg-blue-600'"
            >
              <i
                :class="message.type === 'user' 
                  ? 'fas fa-user text-white text-sm' 
                  : message.type === 'error'
                    ? 'fas fa-exclamation text-white text-sm'
                    : 'fas fa-robot text-white text-sm'"
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
              <div v-if="message.timestamp" class="text-xs text-gray-500 dark:text-gray-400 mt-1">
                {{ formatTime(message.timestamp) }}
              </div>
            </div>
          </div>
        </div>

        <!-- Processing Indicator -->
        <div v-if="isProcessing" class="flex items-start space-x-3">
          <div class="flex-shrink-0">
            <div class="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
              <i class="fas fa-robot text-white text-sm"></i>
            </div>
          </div>
          <div class="flex-1">
            <div class="bg-gray-50 dark:bg-gray-700 rounded-lg p-3">
              <div class="flex items-center space-x-2">
                <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                <span class="text-gray-600 dark:text-gray-400">{{ processingStatus || 'Processing your request...' }}</span>
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
              v-model="inputMessage"
              @keydown.enter.meta.prevent="sendMessage"
              @keydown.enter.ctrl.prevent="sendMessage"
              @keydown.enter.exact="handleEnter"
              placeholder="Enter your instructions for the agent... (Ctrl+Enter or Cmd+Enter to send)"
              rows="2"
              class="block w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm resize-none"
              :disabled="isProcessing"
            ></textarea>
            <div class="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Press Ctrl+Enter (Cmd+Enter on Mac) to send, or Enter for new line
            </div>
          </div>
          <button
            @click="sendMessage"
            :disabled="!inputMessage.trim() || isProcessing"
            class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <i class="fas fa-paper-plane mr-2"></i>
            Send
          </button>
        </div>
      </div>
    </div>

    <!-- Tool Confirmation Modal -->
    <div
      v-if="toolConfirmation"
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
            <div class="mx-auto flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-full bg-yellow-100 dark:bg-yellow-900/20 sm:mx-0 sm:h-10 sm:w-10">
              <i class="fas fa-exclamation-triangle text-yellow-600 dark:text-yellow-400"></i>
            </div>
            <div class="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left">
              <h3 class="text-lg leading-6 font-medium text-gray-900 dark:text-white" id="modal-title">
                Tool Execution Confirmation
              </h3>
              <div class="mt-2">
                <p class="text-sm text-gray-500 dark:text-gray-400">
                  The agent wants to execute a potentially sensitive tool:
                </p>
                <div class="mt-2 p-3 bg-gray-100 dark:bg-gray-700 rounded-md">
                  <p class="text-sm font-mono text-gray-900 dark:text-white">
                    <strong>Tool:</strong> {{ toolConfirmation.tool_name }}
                  </p>
                  <p class="text-sm font-mono text-gray-900 dark:text-white mt-1">
                    <strong>Arguments:</strong> {{ JSON.stringify(toolConfirmation.arguments, null, 2) }}
                  </p>
                </div>
              </div>
            </div>
          </div>
          <div class="mt-5 sm:mt-4 sm:flex sm:flex-row-reverse">
            <button
              @click="confirmTool(true)"
              type="button"
              class="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-green-600 text-base font-medium text-white hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 sm:ml-3 sm:w-auto sm:text-sm"
            >
              Allow Execution
            </button>
            <button
              @click="confirmTool(false)"
              type="button"
              class="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 dark:border-gray-600 shadow-sm px-4 py-2 bg-white dark:bg-gray-700 text-base font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:mt-0 sm:w-auto sm:text-sm"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, computed } from 'vue'
import { useToast } from '@/composables/useToast'
import { apiService } from '@/services/api'
import { formatDistanceToNow } from 'date-fns'
import DOMPurify from 'dompurify'
import { marked } from 'marked'

// Reactive state
const inputMessage = ref('')
const messages = ref<Array<{
  type: 'user' | 'assistant' | 'error' | 'status'
  content: string
  timestamp: Date
  markdown?: boolean
}>>([])
const isProcessing = ref(false)
const processingStatus = ref('')
const selectedServer = ref('')
const availableServers = ref<Array<{
  id: string
  name: string
  description: string
  status: string
  server_type: string
  url?: string
}>>([])
const messagesContainer = ref<HTMLElement>()
const toolConfirmation = ref<{
  confirmation_id: string
  tool_name: string
  arguments: any
} | null>(null)

// Composables
const { showToast } = useToast()

// Methods
const loadServers = async () => {
  try {
    const response = await apiService.get('/api/v1/agent/servers')
    if (response.success) {
      availableServers.value = response.servers
    }
  } catch (error) {
    console.error('Error loading servers:', error)
    showToast('Failed to load available servers', 'error')
  }
}

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
  sendMessage()
}

const sendMessage = async () => {
  if (!inputMessage.value.trim() || isProcessing.value) return

  const message = inputMessage.value.trim()
  inputMessage.value = ''

  // Add user message
  messages.value.push({
    type: 'user',
    content: message,
    timestamp: new Date()
  })

  scrollToBottom()

  // Start processing
  isProcessing.value = true
  processingStatus.value = 'Connecting to agent...'

  try {
    // Create SSE connection
    const url = new URL('/api/v1/agent/chat', window.location.origin)
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify({
        query: message,
        server_id: selectedServer.value || null,
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
                processingStatus.value = data.message || 'Processing...'
                break
                
              case 'text':
              case 'final_answer':
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
                
              case 'tool_call':
                processingStatus.value = `Executing tool: ${data.tool_name}`
                break
                
              case 'tool_confirmation_required':
                toolConfirmation.value = {
                  confirmation_id: data.confirmation_id,
                  tool_name: data.tool_name,
                  arguments: data.arguments
                }
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
                isProcessing.value = false
                processingStatus.value = ''
                
                // Process markdown for the final message
                if (messageAdded && currentMessage) {
                  const lastMessage = messages.value[messages.value.length - 1]
                  if (lastMessage.type === 'assistant') {
                    try {
                      const html = marked(currentMessage)
                      lastMessage.content = DOMPurify.sanitize(html)
                    } catch (e) {
                      // Fallback to plain text
                      lastMessage.markdown = false
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
    console.error('Error in agent chat:', error)
    isProcessing.value = false
    processingStatus.value = ''
    
    messages.value.push({
      type: 'error',
      content: `Error: ${error instanceof Error ? error.message : 'Unknown error occurred'}`,
      timestamp: new Date()
    })
    scrollToBottom()
    showToast('Failed to process message', 'error')
  }
}

const confirmTool = async (confirmed: boolean) => {
  if (!toolConfirmation.value) return

  try {
    await apiService.post('/api/v1/agent/tool-confirm', {
      confirmation_id: toolConfirmation.value.confirmation_id,
      confirmed
    })

    if (confirmed) {
      processingStatus.value = `Executing ${toolConfirmation.value.tool_name}...`
    } else {
      processingStatus.value = 'Tool execution cancelled'
      isProcessing.value = false
    }
  } catch (error) {
    console.error('Error confirming tool:', error)
    showToast('Failed to confirm tool execution', 'error')
  } finally {
    toolConfirmation.value = null
  }
}

const clearConversation = async () => {
  try {
    await apiService.post('/api/v1/agent/conversation/clear')
    messages.value = []
    showToast('Conversation cleared', 'success')
  } catch (error) {
    console.error('Error clearing conversation:', error)
    showToast('Failed to clear conversation', 'error')
  }
}

const formatTime = (timestamp: Date) => {
  return formatDistanceToNow(timestamp, { addSuffix: true })
}

// Lifecycle
onMounted(() => {
  loadServers()
})
</script>

<style scoped>
.agent-view {
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