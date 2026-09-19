// Document status enum matching backend
export type DocumentStatus = 'UPLOADED' | 'PROCESSING' | 'ANALYZED' | 'FAILED'

// Document type options
export type DocumentType =
  | 'Rental Agreement'
  | 'Freelance Contract'
  | 'Terms of Service'
  | 'Other'

export const DOCUMENT_TYPES: DocumentType[] = [
  'Rental Agreement',
  'Freelance Contract',
  'Terms of Service',
  'Other',
]

// Returned immediately after upload
export interface UploadResponse {
  document_id: string
  filename: string
  document_type: DocumentType
  status: DocumentStatus
}

// Full document metadata
export interface Document {
  id: string
  filename: string
  document_type: DocumentType
  file_type: string
  file_size: number
  status: DocumentStatus
  created_at: string
  updated_at: string
}

// A single extracted page
export interface DocumentPage {
  id: string
  document_id: string
  page_number: number
  text: string
  char_start: number | null
  char_end: number | null
}

// Response for GET /api/documents/{id}/text
export interface DocumentTextResponse {
  document_id: string
  total_pages: number
  pages: DocumentPage[]
}

// Upload state machine
export type UploadStage = 'idle' | 'uploading' | 'extracting' | 'completed' | 'failed'

export interface UploadState {
  stage: UploadStage
  progress: number // 0–100
  documentId?: string
  filename?: string
  error?: string
}
