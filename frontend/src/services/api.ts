import axios from 'axios'
import type { Document, DocumentTextResponse, UploadResponse } from '../types/document'
import type { DocumentType } from '../types/document'

/**
 * Axios instance pointing at the FastAPI backend.
 * In development the Vite proxy rewrites /api → http://localhost:8000/api.
 * In production set VITE_API_BASE_URL to the deployed backend URL.
 */
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: {
    Accept: 'application/json',
  },
})

// ─── Health ─────────────────────────────────────────────────────────────────

export async function checkHealth(): Promise<{ status: string }> {
  const res = await apiClient.get<{ status: string }>('/api/health')
  return res.data
}

// ─── Documents ──────────────────────────────────────────────────────────────

/**
 * Upload a PDF or TXT file to the backend.
 * Returns the new document's ID and initial status.
 */
export async function uploadDocument(
  file: File,
  documentType: DocumentType,
  onUploadProgress?: (percent: number) => void
): Promise<UploadResponse> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('document_type', documentType)

  const res = await apiClient.post<UploadResponse>('/api/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (event) => {
      if (onUploadProgress && event.total) {
        onUploadProgress(Math.round((event.loaded / event.total) * 100))
      }
    },
  })
  return res.data
}

/**
 * Fetch document metadata and processing status.
 */
export async function getDocument(documentId: string): Promise<Document> {
  const res = await apiClient.get<Document>(`/api/documents/${documentId}`)
  return res.data
}

/**
 * Fetch page-level extracted text for a document.
 */
export async function getDocumentText(documentId: string): Promise<DocumentTextResponse> {
  const res = await apiClient.get<DocumentTextResponse>(`/api/documents/${documentId}/text`)
  return res.data
}

// ─── Phase 2 & 3: AI Analysis & Clauses ──────────────────────────────────────

import type {
  AnalysisResponse,
  AnalysisSummary,
  Clause,
  PaginatedClausesResponse,
} from '../types/clause'

/**
 * Triggers AI clause extraction and risk analysis.
 */
export async function analyzeDocument(documentId: string): Promise<AnalysisResponse> {
  const res = await apiClient.post<AnalysisResponse>(`/api/documents/${documentId}/analyze`)
  return res.data
}

/**
 * Fetch aggregated risk summary for a document.
 */
export async function getDocumentSummary(documentId: string): Promise<AnalysisSummary> {
  const res = await apiClient.get<AnalysisSummary>(`/api/documents/${documentId}/summary`)
  return res.data
}

/**
 * Fetch analyzed clauses with risk level filtering, search query, and pagination.
 */
export async function getDocumentClauses(
  documentId: string,
  params?: {
    risk_level?: string
    search?: string
    page?: number
    page_size?: number
  }
): Promise<PaginatedClausesResponse> {
  const res = await apiClient.get<PaginatedClausesResponse>(
    `/api/documents/${documentId}/clauses`,
    { params }
  )
  return res.data
}

/**
 * Fetch a single clause details by ID.
 */
export async function getClause(documentId: string, clauseId: string): Promise<Clause> {
  const res = await apiClient.get<Clause>(
    `/api/documents/${documentId}/clauses/${clauseId}`
  )
  return res.data
}

// ─── Phase 4: Document-Grounded Chat ─────────────────────────────────────────

import type { ChatHistoryResponse, ChatResponse } from '../types/chat'

/**
 * Ask a document-grounded question via RAG.
 */
export async function sendChatMessage(
  documentId: string,
  question: string,
  sessionId?: string
): Promise<ChatResponse> {
  const res = await apiClient.post<ChatResponse>(
    `/api/documents/${documentId}/chat`,
    {
      question,
      session_id: sessionId || undefined,
    }
  )
  return res.data
}

/**
 * Fetch chat message history and source citations for a document session.
 */
export async function getChatHistory(
  documentId: string,
  sessionId?: string
): Promise<ChatHistoryResponse> {
  const res = await apiClient.get<ChatHistoryResponse>(
    `/api/documents/${documentId}/chat/history`,
    {
      params: sessionId ? { session_id: sessionId } : undefined,
    }
  )
  return res.data
}

/**
 * Triggers executive PDF report download in browser.
 */
export async function downloadDocumentReport(documentId: string, filename: string = 'Contract_Report.pdf') {
  const res = await apiClient.get(`/api/documents/${documentId}/report`, {
    responseType: 'blob',
  })
  const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', `Risk_Report_${filename.replace(/\s+/g, '_')}.pdf`)
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

/**
 * Delete a document and all associated analysis records.
 */
export async function deleteDocument(documentId: string): Promise<void> {
  await apiClient.delete(`/api/documents/${documentId}`)
}

// ─── SRS-S02: Standard Clause Comparison ─────────────────────────────────────

import type { DocumentComparisonResponse, StandardTemplate } from '../types/comparison'

/**
 * Executes or re-runs standard benchmark clause comparison.
 */
export async function runDocumentComparison(documentId: string): Promise<DocumentComparisonResponse> {
  const res = await apiClient.post<DocumentComparisonResponse>(`/api/documents/${documentId}/compare`)
  return res.data
}

/**
 * Fetch standard clause comparisons for a document with optional deviation filtering.
 */
export async function getDocumentComparisons(
  documentId: string,
  deviationLevel?: string
): Promise<DocumentComparisonResponse> {
  const res = await apiClient.get<DocumentComparisonResponse>(
    `/api/documents/${documentId}/comparisons`,
    {
      params: deviationLevel && deviationLevel !== 'ALL' ? { deviation_level: deviationLevel } : undefined,
    }
  )
  return res.data
}

/**
 * List all standard benchmark templates and archetype clauses.
 */
export async function listBenchmarkTemplates(): Promise<StandardTemplate[]> {
  const res = await apiClient.get<StandardTemplate[]>('/api/benchmarks/templates')
  return res.data
}


