<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useToast } from '@/stores/toast'
import { apiRequest } from '@/services/api'

interface Document {
  id: string
  filename: string
  content_type: string
  status: 'completed' | 'processing' | 'error' | 'pending'
  tags: string[]
  created_at: string
  chunk_count: number
  error_message?: string
}

const toast = useToast()

// Reactive state
const documents = ref<Document[]>([])
const loading = ref(true)
const showUploadModal = ref(false)
const showTextModal = ref(false)
const showViewerModal = ref(false)
const selectedDocument = ref<Document | null>(null)

// Form data
const uploadFile = ref<File | null>(null)
const uploadTags = ref('')
const textContent = ref({
  name: '',
  type: '',
  tags: '',
  text: ''
})

// Document viewer state
const documentContent = ref('')
const documentType = ref<'original' | 'processed'>('processed')
const viewerLoading = ref(false)

// File upload progress
const uploadProgress = ref(0)
const uploading = ref(false)

const filteredDocuments = computed(() => {
  return documents.value.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
})

// API calls
const loadDocuments = async () => {
  try {
    loading.value = true
    const response = await apiRequest('/api/v1/admin/knowledge/documents')
    documents.value = response.documents
  } catch (error) {
    toast.error('Failed to load documents: ' + (error as Error).message)
  } finally {
    loading.value = false
  }
}

const uploadDocument = async () => {
  if (!uploadFile.value) {
    toast.error('Please select a file')
    return
  }

  try {
    uploading.value = true
    uploadProgress.value = 0

    const formData = new FormData()
    formData.append('document', uploadFile.value)
    formData.append('tags', uploadTags.value)

    // Create XMLHttpRequest for progress tracking
    const xhr = new XMLHttpRequest()
    
    xhr.upload.addEventListener('progress', (event) => {
      if (event.lengthComputable) {
        uploadProgress.value = Math.round((event.loaded / event.total) * 100)
      }
    })

    const response = await new Promise<any>((resolve, reject) => {
      xhr.onload = () => {
        if (xhr.status === 200) {
          resolve(JSON.parse(xhr.responseText))
        } else {
          reject(new Error(xhr.statusText))
        }
      }
      xhr.onerror = () => reject(new Error('Upload failed'))
      
      xhr.open('POST', '/api/v1/admin/knowledge/upload')
      // Note: In a real app, you'd need to handle auth headers here
      xhr.send(formData)
    })

    toast.success(response.message)
    showUploadModal.value = false
    resetUploadForm()
    await loadDocuments()
  } catch (error) {
    toast.error('Upload failed: ' + (error as Error).message)
  } finally {
    uploading.value = false
    uploadProgress.value = 0
  }
}

const addTextContent = async () => {
  if (!textContent.value.name || !textContent.value.type || !textContent.value.text) {
    toast.error('Please fill in all required fields')
    return
  }

  try {
    const response = await apiRequest('/api/v1/admin/knowledge/text', {
      method: 'POST',
      body: JSON.stringify({
        name: textContent.value.name,
        content_type: textContent.value.type,
        tags: textContent.value.tags.split(',').map(t => t.trim()).filter(t => t.length > 0),
        content: textContent.value.text
      })
    })

    toast.success(response.message)
    showTextModal.value = false
    resetTextForm()
    await loadDocuments()
  } catch (error) {
    toast.error('Error adding content: ' + (error as Error).message)
  }
}

const viewDocument = async (document: Document) => {
  selectedDocument.value = document
  showViewerModal.value = true
  await loadDocumentContent(document, 'processed')
}

const loadDocumentContent = async (document: Document, type: 'original' | 'processed') => {
  try {
    viewerLoading.value = true
    documentType.value = type
    
    const response = await apiRequest(`/api/v1/admin/knowledge/documents/${document.id}/content?type=${type}`)
    documentContent.value = response.content
  } catch (error) {
    toast.error('Failed to load document content: ' + (error as Error).message)
    documentContent.value = 'Error loading content'
  } finally {
    viewerLoading.value = false
  }
}

const deleteDocument = async (document: Document) => {
  if (!confirm(`Are you sure you want to delete "${document.filename}"? This will permanently remove the document and all associated chunks from the knowledge base.`)) {
    return
  }

  try {
    const response = await apiRequest(`/api/v1/admin/knowledge/documents/${document.id}`, {
      method: 'DELETE'
    })
    toast.success(response.message)
    await loadDocuments()
  } catch (error) {
    toast.error('Error deleting document: ' + (error as Error).message)
  }
}

const getStatusBadgeClass = (status: string) => {
  switch (status) {
    case 'completed': return 'bg-green-100 text-green-800'
    case 'processing': return 'bg-yellow-100 text-yellow-800'
    case 'error': return 'bg-red-100 text-red-800'
    case 'pending': return 'bg-blue-100 text-blue-800'
    default: return 'bg-gray-100 text-gray-800'
  }
}

const resetUploadForm = () => {
  uploadFile.value = null
  uploadTags.value = ''
  const fileInput = document.getElementById('documentFile') as HTMLInputElement
  if (fileInput) fileInput.value = ''
}

const resetTextForm = () => {
  textContent.value = {
    name: '',
    type: '',
    tags: '',
    text: ''
  }
}

const onFileChange = (event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    uploadFile.value = target.files[0]
  }
}

const formatFileSize = (bytes: number) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// Lifecycle
onMounted(async () => {
  await loadDocuments()
})
</script>

<template>
  <div class="p-6 max-w-7xl mx-auto">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6">
      <div class="flex items-center mb-4 sm:mb-0">
        <i class="fas fa-book text-2xl text-blue-600 mr-3"></i>
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Knowledge Management</h1>
      </div>
      <div class="flex flex-wrap gap-2">
        <button 
          @click="showUploadModal = true"
          class="btn btn-primary"
        >
          <i class="fas fa-upload mr-2"></i>Upload Document
        </button>
        <button 
          @click="showTextModal = true"
          class="btn btn-primary"
        >
          <i class="fas fa-paste mr-2"></i>Paste Text
        </button>
      </div>
    </div>

    <!-- Document Library -->
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
      <div class="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
        <h3 class="text-lg font-medium text-gray-900 dark:text-white">Document Library</h3>
      </div>
      
      <div v-if="loading" class="p-8 text-center">
        <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <p class="mt-2 text-gray-600 dark:text-gray-400">Loading documents...</p>
      </div>

      <div v-else-if="filteredDocuments.length === 0" class="p-8 text-center">
        <div class="text-gray-400">
          <i class="fas fa-book text-4xl mb-4"></i>
          <p class="text-lg">No documents found</p>
          <p class="text-sm">Upload your first document to get started</p>
        </div>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead class="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                Filename
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                Type
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                Status
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                Tags
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                Uploaded
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                Chunks
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody class="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
            <tr v-for="document in filteredDocuments" :key="document.id" class="hover:bg-gray-50 dark:hover:bg-gray-700">
              <td class="px-6 py-4">
                <div class="text-sm font-medium text-gray-900 dark:text-white">{{ document.filename }}</div>
              </td>
              <td class="px-6 py-4">
                <span class="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-800 rounded">
                  {{ document.content_type }}
                </span>
              </td>
              <td class="px-6 py-4">
                <span :class="['px-2 py-1 text-xs font-medium rounded-full', getStatusBadgeClass(document.status)]">
                  {{ document.status }}
                </span>
                <div v-if="document.error_message" class="text-xs text-red-600 mt-1">
                  {{ document.error_message }}
                </div>
              </td>
              <td class="px-6 py-4">
                <div class="flex flex-wrap gap-1">
                  <span 
                    v-for="tag in document.tags" 
                    :key="tag"
                    class="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded"
                  >
                    {{ tag }}
                  </span>
                </div>
              </td>
              <td class="px-6 py-4">
                <div class="text-sm text-gray-900 dark:text-white">
                  {{ new Date(document.created_at).toLocaleDateString() }}
                </div>
                <div class="text-xs text-gray-500 dark:text-gray-400">
                  {{ new Date(document.created_at).toLocaleTimeString() }}
                </div>
              </td>
              <td class="px-6 py-4 text-sm text-gray-900 dark:text-white">
                {{ document.chunk_count }}
              </td>
              <td class="px-6 py-4">
                <div class="flex space-x-2">
                  <button
                    @click="viewDocument(document)"
                    class="text-blue-600 hover:text-blue-900 dark:text-blue-400 dark:hover:text-blue-300"
                    title="View Document"
                  >
                    <i class="fas fa-eye"></i>
                  </button>
                  <button
                    @click="deleteDocument(document)"
                    class="text-red-600 hover:text-red-900 dark:text-red-400 dark:hover:text-red-300"
                    title="Delete Document"
                  >
                    <i class="fas fa-trash"></i>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Upload Document Modal -->
    <div v-if="showUploadModal" class="modal-overlay" @click.self="showUploadModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h3 class="modal-title">Upload Document</h3>
          <button @click="showUploadModal = false" class="modal-close">
            <i class="fas fa-times"></i>
          </button>
        </div>
        
        <div class="modal-body">
          <form @submit.prevent="uploadDocument" class="space-y-4">
            <div>
              <label class="form-label">Select Document</label>
              <input
                id="documentFile"
                type="file"
                @change="onFileChange"
                required
                class="input-primary"
                accept=".pdf,.docx,.xlsx,.pptx,.txt,.md"
              >
            </div>
            
            <div>
              <label class="form-label">Tags</label>
              <input
                v-model="uploadTags"
                type="text"
                placeholder="Enter tags separated by commas"
                class="input-primary"
              >
              <p class="text-sm text-gray-600 dark:text-gray-400 mt-1">
                Add tags to categorize your document (e.g. policy, manual, report)
              </p>
            </div>
            
            <div v-if="uploading" class="space-y-2">
              <div class="w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-700">
                <div 
                  class="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
                  :style="{ width: `${uploadProgress}%` }"
                ></div>
              </div>
              <p class="text-sm text-center text-gray-600 dark:text-gray-400">
                Uploading... {{ uploadProgress }}%
              </p>
            </div>
            
            <p class="text-sm text-gray-600 dark:text-gray-400">
              Supported file types: PDF, DOCX, XLSX, PPTX, TXT, MD
            </p>
          </form>
        </div>
        
        <div class="modal-footer">
          <button @click="showUploadModal = false" class="btn btn-secondary" :disabled="uploading">
            Cancel
          </button>
          <button @click="uploadDocument" class="btn btn-primary" :disabled="uploading || !uploadFile">
            <i v-if="uploading" class="fas fa-spinner fa-spin mr-2"></i>
            {{ uploading ? 'Uploading...' : 'Upload' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Paste Text Modal -->
    <div v-if="showTextModal" class="modal-overlay" @click.self="showTextModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h3 class="modal-title">Add Text Content</h3>
          <button @click="showTextModal = false" class="modal-close">
            <i class="fas fa-times"></i>
          </button>
        </div>
        
        <div class="modal-body">
          <form @submit.prevent="addTextContent" class="space-y-4">
            <div>
              <label class="form-label">Content Name *</label>
              <input
                v-model="textContent.name"
                type="text"
                required
                placeholder="Enter a name for this content"
                class="input-primary"
              >
            </div>
            
            <div>
              <label class="form-label">Content Type *</label>
              <select
                v-model="textContent.type"
                required
                class="input-primary"
              >
                <option value="">Select content type</option>
                <option value="policy">Policy</option>
                <option value="documentation">Documentation</option>
                <option value="procedure">Procedure</option>
                <option value="report">Report</option>
                <option value="article">Article</option>
                <option value="guide">Guide</option>
                <option value="notes">Notes</option>
                <option value="other">Other</option>
              </select>
            </div>
            
            <div>
              <label class="form-label">Tags</label>
              <input
                v-model="textContent.tags"
                type="text"
                placeholder="Enter tags separated by commas"
                class="input-primary"
              >
              <p class="text-sm text-gray-600 dark:text-gray-400 mt-1">
                Add tags to categorize your content (e.g. policy, manual, report)
              </p>
            </div>
            
            <div>
              <label class="form-label">Content Text *</label>
              <textarea
                v-model="textContent.text"
                required
                rows="10"
                placeholder="Paste your content here..."
                class="input-primary"
              ></textarea>
            </div>
          </form>
        </div>
        
        <div class="modal-footer">
          <button @click="showTextModal = false" class="btn btn-secondary">
            Cancel
          </button>
          <button @click="addTextContent" class="btn btn-primary">
            Add Content
          </button>
        </div>
      </div>
    </div>

    <!-- Document Viewer Modal -->
    <div v-if="showViewerModal" class="modal-overlay" @click.self="showViewerModal = false">
      <div class="modal-content modal-wide">
        <div class="modal-header">
          <h3 class="modal-title">Document Viewer</h3>
          <button @click="showViewerModal = false" class="modal-close">
            <i class="fas fa-times"></i>
          </button>
        </div>
        
        <div class="modal-body" v-if="selectedDocument">
          <!-- Document Info -->
          <div class="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 mb-4">
            <div class="flex justify-between items-start">
              <div>
                <h4 class="text-lg font-medium text-gray-900 dark:text-white">{{ selectedDocument.filename }}</h4>
                <div class="text-sm text-gray-600 dark:text-gray-400 space-x-4">
                  <span>{{ selectedDocument.content_type }}</span>
                  <span>{{ selectedDocument.chunk_count }} chunks</span>
                  <span>{{ new Date(selectedDocument.created_at).toLocaleDateString() }}</span>
                </div>
              </div>
              <div class="flex space-x-2">
                <button
                  @click="loadDocumentContent(selectedDocument!, 'original')"
                  :class="[
                    'px-3 py-1 text-sm rounded-md',
                    documentType === 'original' 
                      ? 'bg-blue-600 text-white' 
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  ]"
                >
                  <i class="fas fa-file mr-1"></i> Original
                </button>
                <button
                  @click="loadDocumentContent(selectedDocument!, 'processed')"
                  :class="[
                    'px-3 py-1 text-sm rounded-md',
                    documentType === 'processed' 
                      ? 'bg-green-600 text-white' 
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  ]"
                >
                  <i class="fas fa-cogs mr-1"></i> Processed
                </button>
              </div>
            </div>
          </div>
          
          <!-- Content Area -->
          <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4" style="max-height: 60vh; overflow-y: auto;">
            <div v-if="viewerLoading" class="text-center py-8">
              <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <p class="mt-2 text-gray-600 dark:text-gray-400">Loading document...</p>
            </div>
            
            <div v-else-if="documentContent" class="prose dark:prose-invert max-w-none">
              <pre v-if="documentType === 'original'" class="whitespace-pre-wrap font-sans">{{ documentContent }}</pre>
              <div v-else v-html="documentContent"></div>
            </div>
            
            <div v-else class="text-center py-8 text-gray-500 dark:text-gray-400">
              <i class="fas fa-exclamation-triangle text-4xl mb-2"></i>
              <p>Failed to load document content</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-wide {
  max-width: 6xl;
}

.prose {
  max-width: none;
}

.prose pre {
  background-color: transparent;
  padding: 0;
  margin: 0;
  border: none;
  border-radius: 0;
}
</style>