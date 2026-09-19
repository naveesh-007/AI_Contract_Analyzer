export interface ChatSource {
  clause_id: string | null
  section: string | null
  page_number: number | null
  relevance_score: number | null
  snippet?: string | null
}

export interface ChatMessage {
  id: string
  session_id: string
  role: 'user' | 'assistant' | 'system'
  message: string
  grounded: boolean
  sources: ChatSource[]
  created_at: string
}

export interface ChatResponse {
  answer: string
  grounded: boolean
  sources: ChatSource[]
  session_id: string
  message_id: string
}

export interface ChatHistoryResponse {
  session_id: string
  document_id: string
  messages: ChatMessage[]
}
