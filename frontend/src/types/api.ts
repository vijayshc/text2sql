// API Response types
export interface LoginResponse {
  tokens: {
    access_token: string
    refresh_token: string
    token_type: string
    expires_in: number
  }
  user: {
    id: number
    username: string
    email?: string
    roles: string[]
    permissions: string[]
  }
}

export interface RefreshResponse {
  access_token: string
  token_type: string
  expires_in: number
}

export interface QuerySubmitResponse {
  query_id: string
  status: string
}

export interface QueryProgressResponse {
  status: string
  current_step: number
  steps: string[]
  result?: {
    data: any[]
    sql: string
    explanation: string
  }
  error?: string
  start_time?: number
}

export interface WorkspacesResponse {
  workspaces: Array<{
    name: string
    description?: string
  }>
}

export interface SchemaResponse {
  schema: Array<{
    name: string
    description?: string
    columns?: Array<{
      name: string
      datatype: string
      description?: string
      is_primary_key?: boolean
    }>
  }>
}

export interface SuggestionsResponse {
  suggestions: string[]
}

// Extend Axios config for retry functionality
declare module 'axios' {
  interface InternalAxiosRequestConfig {
    _retry?: boolean
  }
}