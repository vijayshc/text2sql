import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import ApiService from '@/services/api'
import type { 
  QuerySubmitResponse, 
  QueryProgressResponse, 
  WorkspacesResponse, 
  SchemaResponse,
  SuggestionsResponse 
} from '@/types/api'

export interface QueryProgress {
  status: string
  current_step: number
  steps: string[]
  result?: any
  error?: string
  start_time?: number
}

export interface Workspace {
  name: string
  description?: string
}

export interface Table {
  name: string
  description?: string
  columns?: Column[]
}

export interface Column {
  name: string
  datatype: string
  description?: string
  is_primary_key?: boolean
}

export const useQueryStore = defineStore('query', () => {
  // State
  const currentQuery = ref<string>('')
  const selectedWorkspace = ref<string>('Default')
  const selectedTables = ref<string[]>([])
  const queryProgress = ref<QueryProgress | null>(null)
  const currentQueryId = ref<string | null>(null)
  const isSubmitting = ref(false)
  const error = ref<string | null>(null)

  // Schema data
  const workspaces = ref<Workspace[]>([])
  const schema = ref<Table[]>([])
  const isLoadingSchema = ref(false)

  // Results
  const queryResults = ref<any>(null)
  const querySteps = ref<string[]>([])
  const generatedSQL = ref<string>('')
  const explanation = ref<string>('')

  // Computed
  const isQueryInProgress = computed(() => {
    return queryProgress.value?.status === 'processing'
  })

  const hasResults = computed(() => {
    return !!queryResults.value
  })

  // Actions
  async function submitQuery() {
    try {
      isSubmitting.value = true
      error.value = null

      const response: QuerySubmitResponse = await ApiService.submitQuery(
        currentQuery.value,
        selectedWorkspace.value,
        selectedTables.value.length > 0 ? selectedTables.value : undefined,
      )

      currentQueryId.value = response.query_id
      queryProgress.value = {
        status: 'processing',
        current_step: 0,
        steps: [],
      }

      // Start polling for progress
      pollQueryProgress()

      return response
    } catch (err: any) {
      error.value = err.response?.data?.message || 'Query submission failed'
      throw err
    } finally {
      isSubmitting.value = false
    }
  }

  async function pollQueryProgress() {
    if (!currentQueryId.value) return

    try {
      const progress: QueryProgressResponse = await ApiService.getQueryProgress(currentQueryId.value)
      queryProgress.value = progress

      if (progress.status === 'completed') {
        // Extract results
        if (progress.result) {
          queryResults.value = progress.result.data
          generatedSQL.value = progress.result.sql
          explanation.value = progress.result.explanation
          querySteps.value = progress.steps
        }
      } else if (progress.status === 'error') {
        error.value = progress.error || 'Query processing failed'
      } else if (progress.status === 'processing') {
        // Continue polling
        setTimeout(pollQueryProgress, 1000)
      }
    } catch (err: any) {
      error.value = err.response?.data?.message || 'Failed to get query progress'
      queryProgress.value = null
    }
  }

  async function loadWorkspaces() {
    try {
      const response: WorkspacesResponse = await ApiService.getWorkspaces()
      workspaces.value = response.workspaces
    } catch (err: any) {
      error.value = err.response?.data?.message || 'Failed to load workspaces'
    }
  }

  async function loadSchema(workspace?: string) {
    try {
      isLoadingSchema.value = true
      const response: SchemaResponse = await ApiService.getSchema(workspace || selectedWorkspace.value)
      schema.value = response.schema
    } catch (err: any) {
      error.value = err.response?.data?.message || 'Failed to load schema'
    } finally {
      isLoadingSchema.value = false
    }
  }

  async function getTableSuggestions(query?: string): Promise<string[]> {
    try {
      const response: SuggestionsResponse = await ApiService.getTableSuggestions(selectedWorkspace.value, query)
      return response.suggestions
    } catch (err: any) {
      console.warn('Failed to get table suggestions:', err)
      return []
    }
  }

  function clearResults() {
    queryResults.value = null
    querySteps.value = []
    generatedSQL.value = ''
    explanation.value = ''
    queryProgress.value = null
    currentQueryId.value = null
    error.value = null
  }

  function setWorkspace(workspace: string) {
    selectedWorkspace.value = workspace
    clearResults()
    loadSchema(workspace)
  }

  return {
    // State
    currentQuery,
    selectedWorkspace,
    selectedTables,
    queryProgress,
    currentQueryId,
    isSubmitting,
    error,
    workspaces,
    schema,
    isLoadingSchema,
    queryResults,
    querySteps,
    generatedSQL,
    explanation,

    // Computed
    isQueryInProgress,
    hasResults,

    // Actions
    submitQuery,
    pollQueryProgress,
    loadWorkspaces,
    loadSchema,
    getTableSuggestions,
    clearResults,
    setWorkspace,
  }
})
