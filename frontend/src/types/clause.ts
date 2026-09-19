export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH'

export interface Clause {
  id: string
  document_id: string
  section_number: string | null
  section_title: string | null
  clause_text: string
  risk_level: RiskLevel
  explanation: string
  reason: string
  page_number: number | null
  char_start: number | null
  char_end: number | null
  created_at?: string
}

export interface AnalysisSummary {
  total_clauses: number
  high: number
  medium: number
  low: number
  overall_summary: string
}

export interface AnalysisResponse {
  document_id: string
  status: string
  summary: AnalysisSummary
  clauses: Clause[]
}

export interface PaginatedClausesResponse {
  items: Clause[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export type RiskFilter = 'ALL' | 'HIGH' | 'MEDIUM' | 'LOW'
