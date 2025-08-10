<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { useUIStore } from '@/stores/ui'

const uiStore = useUIStore()

// Chat state
const messages = ref<Array<{
  id: string
  type: 'user' | 'assistant'
  content: string
  timestamp: Date
  isStreaming?: boolean
}>>([])

const currentInput = ref('')
const isWaitingForResponse = ref(false)
const conversationHistory = ref<Array<{ role: string, content: string }>>([])

// File upload
const selectedFiles = ref<File[]>([])
const uploadProgress = ref<Record<string, number>>({})
const isUploading = ref(false)

// Knowledge base management
const documents = ref<Array<{
  id: string
  filename: string
  size: number
  uploadedAt: Date
  status: 'processing' | 'ready' | 'error'
}>>([])

// Text input for direct text addition
const showTextInput = ref(false)
const directTextInput = ref('')
const textInputTitle = ref('')

// Search and filtering
const searchQuery = ref('')
const documentFilter = ref('all') // all, ready, processing, error

const filteredDocuments = computed(() => {
  let filtered = documents.value
  
  if (documentFilter.value !== 'all') {
    filtered = filtered.filter(doc => doc.status === documentFilter.value)
  }
  
  if (searchQuery.value) {
    filtered = filtered.filter(doc => 
      doc.filename.toLowerCase().includes(searchQuery.value.toLowerCase())
    )
  }
  
  return filtered
})

const canSendMessage = computed(() => {
  return currentInput.value.trim().length > 0 && !isWaitingForResponse.value
})

const handleFileUpload = async (event: Event) => {
  const target = event.target as HTMLInputElement
  if (!target.files) return

  const files = Array.from(target.files)
  selectedFiles.value = files
  
  await uploadFiles(files)
  target.value = '' // Reset input
}

const uploadFiles = async (files: File[]) => {
  if (files.length === 0) return

  try {
    isUploading.value = true
    
    for (const file of files) {
      // Simulate upload progress
      uploadProgress.value[file.name] = 0
      
      // Add to documents list immediately with processing status
      const docId = `doc_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      documents.value.unshift({
        id: docId,
        filename: file.name,
        size: file.size,
        uploadedAt: new Date(),
        status: 'processing'
      })
      
      // Simulate upload progress
      for (let progress = 0; progress <= 100; progress += 10) {
        uploadProgress.value[file.name] = progress
        await new Promise(resolve => setTimeout(resolve, 100))
      }
      
      // Mark as ready after upload
      const doc = documents.value.find(d => d.id === docId)
      if (doc) {
        doc.status = 'ready'
      }
      
      delete uploadProgress.value[file.name]
    }
    
    uiStore.showSuccess('Upload Complete', `${files.length} file(s) uploaded successfully`)
    
  } catch (error: any) {
    uiStore.showError('Upload Failed', error.message)
  } finally {
    isUploading.value = false
    selectedFiles.value = []
  }
}

const addDirectText = async () => {
  if (!directTextInput.value.trim() || !textInputTitle.value.trim()) {
    uiStore.showWarning('Missing Information', 'Please provide both title and content')
    return
  }

  try {
    const docId = `text_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    
    documents.value.unshift({
      id: docId,
      filename: `${textInputTitle.value}.txt`,
      size: directTextInput.value.length,
      uploadedAt: new Date(),
      status: 'processing'
    })
    
    // Simulate processing
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    const doc = documents.value.find(d => d.id === docId)
    if (doc) {
      doc.status = 'ready'
    }
    
    uiStore.showSuccess('Text Added', 'Content added to knowledge base')
    
    // Reset form
    directTextInput.value = ''
    textInputTitle.value = ''
    showTextInput.value = false
    
  } catch (error: any) {
    uiStore.showError('Failed to Add Text', error.message)
  }
}

const deleteDocument = async (docId: string) => {
  try {
    const index = documents.value.findIndex(d => d.id === docId)
    if (index !== -1) {
      documents.value.splice(index, 1)
      uiStore.showSuccess('Document Deleted', 'Document removed from knowledge base')
    }
  } catch (error: any) {
    uiStore.showError('Delete Failed', error.message)
  }
}

const sendMessage = async () => {
  if (!canSendMessage.value) return

  const userMessage = currentInput.value.trim()
  const messageId = `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  
  // Add user message
  messages.value.push({
    id: messageId,
    type: 'user',
    content: userMessage,
    timestamp: new Date()
  })
  
  // Add to conversation history
  conversationHistory.value.push({ role: 'user', content: userMessage })
  
  // Clear input
  currentInput.value = ''
  isWaitingForResponse.value = true
  
  // Scroll to bottom
  await nextTick()
  scrollToBottom()
  
  try {
    // Simulate streaming response
    const assistantMessageId = `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    
    messages.value.push({
      id: assistantMessageId,
      type: 'assistant',
      content: '',
      timestamp: new Date(),
      isStreaming: true
    })
    
    // Simulate streaming response
    const responses = [
      "Based on your knowledge base documents, I can help you with that. ",
      "Let me search through the uploaded documents for relevant information. ",
      "Here's what I found:\n\n",
      "• Document 1 mentions relevant information about your query\n",
      "• Document 2 provides additional context\n",
      "• The overall analysis suggests...\n\n",
      "Would you like me to provide more details from any specific document?"
    ]
    
    for (const chunk of responses) {
      await new Promise(resolve => setTimeout(resolve, 200 + Math.random() * 300))
      
      const assistantMessage = messages.value.find(m => m.id === assistantMessageId)
      if (assistantMessage) {
        assistantMessage.content += chunk
        scrollToBottom()
      }
    }
    
    // Mark streaming as complete
    const finalMessage = messages.value.find(m => m.id === assistantMessageId)
    if (finalMessage) {
      finalMessage.isStreaming = false
      conversationHistory.value.push({ role: 'assistant', content: finalMessage.content })
    }
    
  } catch (error: any) {
    uiStore.showError('Query Failed', error.message)
  } finally {
    isWaitingForResponse.value = false
  }
}

const clearConversation = () => {
  messages.value = []
  conversationHistory.value = []
  uiStore.showInfo('Conversation Cleared', 'Chat history has been reset')
}

const scrollToBottom = () => {
  nextTick(() => {
    const chatContainer = document.getElementById('chat-messages')
    if (chatContainer) {
      chatContainer.scrollTop = chatContainer.scrollHeight
    }
  })
}

const formatFileSize = (bytes: number) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

onMounted(() => {
  // Add welcome message
  messages.value.push({
    id: 'welcome',
    type: 'assistant',
    content: 'Hello! I\'m your knowledge base assistant. Upload documents or add text content, then ask me questions about your knowledge base. I can search through your documents and provide relevant answers.',
    timestamp: new Date()
  })
  
  // Load existing documents (mock data)
  documents.value = [
    {
      id: 'doc1',
      filename: 'company_policies.pdf',
      size: 1024567,
      uploadedAt: new Date(Date.now() - 86400000),
      status: 'ready'
    },
    {
      id: 'doc2',
      filename: 'user_manual.docx',
      size: 2048123,
      uploadedAt: new Date(Date.now() - 172800000),
      status: 'ready'
    },
    {
      id: 'doc3',
      filename: 'meeting_notes.txt',
      size: 15432,
      uploadedAt: new Date(Date.now() - 259200000),
      status: 'processing'
    }
  ]
})
</script>

<template>
  <div class="h-full flex flex-col space-y-6">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white">
          Knowledge Base
        </h1>
        <p class="text-gray-600 dark:text-gray-400 mt-1">
          Upload documents and ask questions about your knowledge base
        </p>
      </div>
      
      <div class="flex items-center space-x-3">
        <button
          @click="showTextInput = true"
          class="btn btn-secondary"
        >
          <i class="fas fa-plus mr-2"></i>
          Add Text
        </button>
        
        <label class="btn btn-primary cursor-pointer">
          <i class="fas fa-upload mr-2"></i>
          Upload Files
          <input
            type="file"
            multiple
            accept=".pdf,.doc,.docx,.txt,.md"
            @change="handleFileUpload"
            class="hidden"
          />
        </label>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1">
      <!-- Chat Interface -->
      <div class="lg:col-span-2 flex flex-col">
        <!-- Chat Messages -->
        <div
          id="chat-messages"
          class="flex-1 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 overflow-y-auto space-y-4 min-h-96"
        >
          <div
            v-for="message in messages"
            :key="message.id"
            class="flex"
            :class="{ 'justify-end': message.type === 'user' }"
          >
            <div
              class="max-w-3xl rounded-lg p-4"
              :class="{
                'bg-primary-600 text-white': message.type === 'user',
                'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white': message.type === 'assistant'
              }"
            >
              <!-- Message Avatar -->
              <div class="flex items-start space-x-3">
                <div
                  class="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
                  :class="{
                    'bg-primary-700': message.type === 'user',
                    'bg-secondary-600': message.type === 'assistant'
                  }"
                >
                  <i :class="message.type === 'user' ? 'fas fa-user' : 'fas fa-robot'" class="text-white text-sm"></i>
                </div>
                
                <div class="flex-1 min-w-0">
                  <!-- Message Content -->
                  <div class="prose prose-sm dark:prose-invert max-w-none">
                    <div class="whitespace-pre-wrap">{{ message.content }}</div>
                    
                    <!-- Streaming indicator -->
                    <div v-if="message.isStreaming" class="inline-flex items-center mt-2">
                      <div class="flex space-x-1">
                        <div class="w-2 h-2 bg-current rounded-full animate-bounce" style="animation-delay: 0ms"></div>
                        <div class="w-2 h-2 bg-current rounded-full animate-bounce" style="animation-delay: 150ms"></div>
                        <div class="w-2 h-2 bg-current rounded-full animate-bounce" style="animation-delay: 300ms"></div>
                      </div>
                    </div>
                  </div>
                  
                  <!-- Timestamp -->
                  <div class="text-xs opacity-75 mt-2">
                    {{ message.timestamp.toLocaleTimeString() }}
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Waiting indicator -->
          <div v-if="isWaitingForResponse && !messages.some(m => m.isStreaming)" class="flex">
            <div class="bg-gray-100 dark:bg-gray-700 rounded-lg p-4 max-w-xs">
              <div class="flex items-center space-x-3">
                <div class="w-8 h-8 bg-secondary-600 rounded-full flex items-center justify-center">
                  <i class="fas fa-robot text-white text-sm"></i>
                </div>
                <div class="flex space-x-1">
                  <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0ms"></div>
                  <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 150ms"></div>
                  <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 300ms"></div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Chat Input -->
        <div class="mt-4 space-y-3">
          <div v-if="messages.length > 1" class="flex justify-end">
            <button
              @click="clearConversation"
              class="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
            >
              <i class="fas fa-trash mr-1"></i>
              Clear conversation
            </button>
          </div>
          
          <form @submit.prevent="sendMessage" class="flex space-x-3">
            <div class="flex-1">
              <textarea
                v-model="currentInput"
                rows="3"
                class="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 resize-none"
                placeholder="Ask a question about your knowledge base..."
                :disabled="isWaitingForResponse"
                @keydown.ctrl.enter="sendMessage"
              ></textarea>
            </div>
            
            <button
              type="submit"
              :disabled="!canSendMessage"
              class="btn btn-primary h-fit"
            >
              <i v-if="isWaitingForResponse" class="fas fa-spinner fa-spin mr-2"></i>
              <i v-else class="fas fa-paper-plane mr-2"></i>
              Send
            </button>
          </form>
          
          <p class="text-xs text-gray-500 dark:text-gray-400">
            Press Ctrl+Enter to send • Upload documents to enhance the knowledge base
          </p>
        </div>
      </div>

      <!-- Knowledge Base Management -->
      <div class="space-y-6">
        <!-- Document Search -->
        <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-4">Document Library</h3>
          
          <!-- Search and Filter -->
          <div class="space-y-3 mb-4">
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Search documents..."
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            />
            
            <select
              v-model="documentFilter"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            >
              <option value="all">All Documents</option>
              <option value="ready">Ready</option>
              <option value="processing">Processing</option>
              <option value="error">Error</option>
            </select>
          </div>
          
          <!-- Document List -->
          <div class="space-y-3 max-h-64 overflow-y-auto">
            <div
              v-for="doc in filteredDocuments"
              :key="doc.id"
              class="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg"
            >
              <div class="flex-1 min-w-0">
                <div class="flex items-center space-x-2">
                  <i
                    :class="{
                      'fas fa-file-pdf text-red-500': doc.filename.endsWith('.pdf'),
                      'fas fa-file-word text-blue-500': doc.filename.endsWith('.doc') || doc.filename.endsWith('.docx'),
                      'fas fa-file-alt text-gray-500': doc.filename.endsWith('.txt') || doc.filename.endsWith('.md'),
                      'fas fa-file text-gray-400': !doc.filename.match(/\.(pdf|doc|docx|txt|md)$/)
                    }"
                    class="text-sm"
                  ></i>
                  <span class="text-sm font-medium text-gray-900 dark:text-white truncate">
                    {{ doc.filename }}
                  </span>
                  
                  <!-- Status Badge -->
                  <span
                    class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
                    :class="{
                      'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200': doc.status === 'ready',
                      'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200': doc.status === 'processing',
                      'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200': doc.status === 'error'
                    }"
                  >
                    {{ doc.status }}
                  </span>
                </div>
                
                <div class="flex items-center space-x-4 mt-1 text-xs text-gray-500 dark:text-gray-400">
                  <span>{{ formatFileSize(doc.size) }}</span>
                  <span>{{ doc.uploadedAt.toLocaleDateString() }}</span>
                </div>
              </div>
              
              <button
                @click="deleteDocument(doc.id)"
                class="ml-3 text-gray-400 hover:text-red-500 transition-colors"
                title="Delete document"
              >
                <i class="fas fa-trash text-sm"></i>
              </button>
            </div>
            
            <div v-if="filteredDocuments.length === 0" class="text-center py-8 text-gray-500 dark:text-gray-400">
              <i class="fas fa-folder-open text-2xl mb-2"></i>
              <p class="text-sm">No documents found</p>
            </div>
          </div>
        </div>

        <!-- Upload Progress -->
        <div v-if="isUploading" class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-4">Upload Progress</h3>
          <div class="space-y-3">
            <div v-for="(progress, filename) in uploadProgress" :key="filename" class="space-y-2">
              <div class="flex justify-between text-sm">
                <span class="text-gray-700 dark:text-gray-300 truncate">{{ filename }}</span>
                <span class="text-gray-500 dark:text-gray-400">{{ progress }}%</span>
              </div>
              <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                <div
                  class="bg-primary-600 h-2 rounded-full transition-all duration-300"
                  :style="{ width: `${progress}%` }"
                ></div>
              </div>
            </div>
          </div>
        </div>

        <!-- Knowledge Base Stats -->
        <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-4">Statistics</h3>
          <div class="space-y-3">
            <div class="flex justify-between items-center">
              <span class="text-sm text-gray-600 dark:text-gray-400">Total Documents</span>
              <span class="text-sm font-medium text-gray-900 dark:text-white">{{ documents.length }}</span>
            </div>
            <div class="flex justify-between items-center">
              <span class="text-sm text-gray-600 dark:text-gray-400">Ready</span>
              <span class="text-sm font-medium text-green-600 dark:text-green-400">
                {{ documents.filter(d => d.status === 'ready').length }}
              </span>
            </div>
            <div class="flex justify-between items-center">
              <span class="text-sm text-gray-600 dark:text-gray-400">Processing</span>
              <span class="text-sm font-medium text-yellow-600 dark:text-yellow-400">
                {{ documents.filter(d => d.status === 'processing').length }}
              </span>
            </div>
            <div class="flex justify-between items-center">
              <span class="text-sm text-gray-600 dark:text-gray-400">Total Size</span>
              <span class="text-sm font-medium text-gray-900 dark:text-white">
                {{ formatFileSize(documents.reduce((sum, doc) => sum + doc.size, 0)) }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Text Input Modal -->
    <div
      v-if="showTextInput"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-50"
      @click.self="showTextInput = false"
    >
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-hidden">
        <div class="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <h3 class="text-lg font-medium text-gray-900 dark:text-white">Add Text Content</h3>
          <button
            @click="showTextInput = false"
            class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <i class="fas fa-times"></i>
          </button>
        </div>
        
        <div class="p-6 space-y-4">
          <div>
            <label for="textTitle" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Title
            </label>
            <input
              id="textTitle"
              v-model="textInputTitle"
              type="text"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              placeholder="Enter a title for this content..."
            />
          </div>
          
          <div>
            <label for="textContent" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Content
            </label>
            <textarea
              id="textContent"
              v-model="directTextInput"
              rows="12"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 resize-none"
              placeholder="Paste or type your content here..."
            ></textarea>
          </div>
        </div>
        
        <div class="flex justify-end space-x-3 p-6 border-t border-gray-200 dark:border-gray-700">
          <button
            @click="showTextInput = false"
            class="btn btn-secondary"
          >
            Cancel
          </button>
          <button
            @click="addDirectText"
            :disabled="!directTextInput.trim() || !textInputTitle.trim()"
            class="btn btn-primary"
          >
            <i class="fas fa-plus mr-2"></i>
            Add Content
          </button>
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

/* Custom scrollbar for chat */
#chat-messages::-webkit-scrollbar {
  width: 6px;
}

#chat-messages::-webkit-scrollbar-track {
  background: transparent;
}

#chat-messages::-webkit-scrollbar-thumb {
  @apply bg-gray-300 dark:bg-gray-600 rounded-full;
}

#chat-messages::-webkit-scrollbar-thumb:hover {
  @apply bg-gray-400 dark:bg-gray-500;
}

/* Bounce animation for loading dots */
@keyframes bounce {
  0%, 80%, 100% {
    transform: scale(0);
  }
  40% {
    transform: scale(1);
  }
}

.animate-bounce {
  animation: bounce 1.4s infinite ease-in-out both;
}
</style>