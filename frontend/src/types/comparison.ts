export type DeviationLevel = 'LOW' | 'MEDIUM' | 'HIGH'

export type DeviationFilter = 'ALL' | 'HIGH' | 'MEDIUM' | 'LOW'

export interface StandardClause {
  id: string
  template_id: string
  category: string
  title: string
  benchmark_text: string
  description?: string
}

export interface StandardTemplate {
  id: string
  document_type: string
  name: string
  description: string
  version: string
  clauses: StandardClause[]
}

export interface ClauseComparison {
  id: string
  document_id: string
  clause_id: string
  standard_clause_id?: string | null
  category: string
  section_title?: string | null
  section_number?: string | null
  actual_clause: string
  benchmark_clause: string
  benchmark_title?: string | null
  deviation_level: DeviationLevel
  similarity_score: number
  comparison_summary: string
  differences: string[]
  page_number?: number
  created_at: string
}

export interface ComparisonSummaryStats {
  total_comparisons: number
  high_deviation: number
  medium_deviation: number
  low_deviation: number
  average_similarity: number
}

export interface DocumentComparisonResponse {
  document_id: string
  document_type: string
  template_name: string
  summary: ComparisonSummaryStats
  comparisons: ClauseComparison[]
}
