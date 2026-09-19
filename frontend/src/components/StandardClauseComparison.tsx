import { useEffect, useState } from 'react'
import { getDocumentComparisons, runDocumentComparison } from '../services/api'
import type { Clause } from '../types/clause'
import type {
  ClauseComparison,
  DeviationFilter,
  DocumentComparisonResponse,
} from '../types/comparison'

interface StandardClauseComparisonProps {
  documentId: string
  clauses: Clause[]
  onSelectClause: (clause: Clause) => void
}

export function StandardClauseComparison({
  documentId,
  clauses,
  onSelectClause,
}: StandardClauseComparisonProps) {
  const [data, setData] = useState<DocumentComparisonResponse | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [comparing, setComparing] = useState<boolean>(false)
  const [activeFilter, setActiveFilter] = useState<DeviationFilter>('ALL')
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [error, setError] = useState<string | null>(null)

  const loadComparisons = async (showLoadingState = true) => {
    if (showLoadingState) setLoading(true)
    setError(null)
    try {
      const res = await getDocumentComparisons(documentId)
      setData(res)
    } catch (err: any) {
      console.warn('Failed to fetch comparisons:', err)
      setError(err?.response?.data?.detail || 'Failed to load standard comparisons.')
    } finally {
      if (showLoadingState) setLoading(false)
    }
  }

  const handleReRunComparison = async () => {
    setComparing(true)
    setError(null)
    try {
      const res = await runDocumentComparison(documentId)
      setData(res)
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to re-run benchmark comparison.')
    } finally {
      setComparing(false)
    }
  }

  useEffect(() => {
    loadComparisons()
  }, [documentId])

  const handleNavigate = (comp: ClauseComparison) => {
    const matched = clauses.find((c) => c.id === comp.clause_id)
    if (matched) {
      onSelectClause(matched)
    }
  }

  const filteredComparisons = (data?.comparisons || []).filter((comp) => {
    if (activeFilter !== 'ALL' && comp.deviation_level !== activeFilter) {
      return false
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      const inCat = comp.category.toLowerCase().includes(q)
      const inSec = (comp.section_title || '').toLowerCase().includes(q)
      const inActual = comp.actual_clause.toLowerCase().includes(q)
      const inBench = comp.benchmark_clause.toLowerCase().includes(q)
      const inSummary = comp.comparison_summary.toLowerCase().includes(q)
      const inDiffs = comp.differences.some((d) => d.toLowerCase().includes(q))
      return inCat || inSec || inActual || inBench || inSummary || inDiffs
    }
    return true
  })

  if (loading) {
    return (
      <div
        className="glass-card"
        style={{
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '32px',
          textAlign: 'center',
          gap: '12px',
        }}
      >
        <div style={{ fontSize: '32px' }} className="animate-pulse-slow">
          ⚖️
        </div>
        <p style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-text-primary)' }}>
          Evaluating against Standard Benchmark Clauses...
        </p>
        <p style={{ fontSize: '11px', color: 'var(--color-text-muted)', maxWidth: '300px' }}>
          Comparing your document provisions with typical industry standard templates.
        </p>
      </div>
    )
  }

  const summary = data?.summary || {
    total_comparisons: 0,
    high_deviation: 0,
    medium_deviation: 0,
    low_deviation: 0,
    average_similarity: 0,
  }

  return (
    <div
      className="glass-card"
      style={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        background: 'var(--color-bg-card)',
      }}
    >
      {/* Header with Benchmark info & Re-evaluate button */}
      <div
        style={{
          padding: '12px 16px',
          borderBottom: '1px solid var(--color-border)',
          background: 'var(--color-bg-secondary)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '8px',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '16px' }}>⚖️</span>
            <h2
              style={{
                fontSize: '13.5px',
                fontWeight: 800,
                color: 'var(--color-text-primary)',
                margin: 0,
              }}
            >
              Standard Clause Comparison
            </h2>
            <span
              className="badge"
              style={{
                background: 'rgba(108, 142, 245, 0.15)',
                color: 'var(--color-accent-light)',
                fontSize: '10px',
              }}
            >
              {data?.template_name || 'Standard Benchmark'}
            </span>
          </div>
          <p style={{ fontSize: '11px', color: 'var(--color-text-muted)', margin: '2px 0 0 0' }}>
            Informational comparison against typical {data?.document_type || 'contract'} patterns
          </p>
        </div>

        <button
          type="button"
          id="recompare-btn"
          disabled={comparing}
          onClick={handleReRunComparison}
          className="btn-secondary"
          style={{ padding: '4px 10px', fontSize: '11px' }}
          title="Re-run standard benchmark comparison"
        >
          {comparing ? 'Evaluating...' : '🔄 Re-compare'}
        </button>
      </div>

      {/* Summary Metrics Row */}
      <div
        style={{
          padding: '10px 16px',
          borderBottom: '1px solid var(--color-border)',
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '6px',
          background: 'rgba(10, 13, 20, 0.3)',
        }}
      >
        <div
          style={{
            padding: '6px 8px',
            borderRadius: '8px',
            background: 'var(--color-bg-secondary)',
            border: '1px solid var(--color-border)',
            textAlign: 'center',
          }}
        >
          <span style={{ fontSize: '14px', fontWeight: 800, color: 'var(--color-text-primary)' }}>
            {summary.total_comparisons}
          </span>
          <p style={{ fontSize: '9.5px', fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase', margin: 0 }}>
            Compared
          </p>
        </div>

        <div
          style={{
            padding: '6px 8px',
            borderRadius: '8px',
            background: 'rgba(248, 113, 113, 0.1)',
            border: '1px solid rgba(248, 113, 113, 0.25)',
            textAlign: 'center',
          }}
        >
          <span style={{ fontSize: '14px', fontWeight: 800, color: '#f87171' }}>
            {summary.high_deviation}
          </span>
          <p style={{ fontSize: '9.5px', fontWeight: 700, color: '#fca5a5', textTransform: 'uppercase', margin: 0 }}>
            High Dev.
          </p>
        </div>

        <div
          style={{
            padding: '6px 8px',
            borderRadius: '8px',
            background: 'rgba(251, 191, 36, 0.1)',
            border: '1px solid rgba(251, 191, 36, 0.25)',
            textAlign: 'center',
          }}
        >
          <span style={{ fontSize: '14px', fontWeight: 800, color: '#fbbf24' }}>
            {summary.medium_deviation}
          </span>
          <p style={{ fontSize: '9.5px', fontWeight: 700, color: '#fde68a', textTransform: 'uppercase', margin: 0 }}>
            Med Dev.
          </p>
        </div>

        <div
          style={{
            padding: '6px 8px',
            borderRadius: '8px',
            background: 'rgba(52, 211, 153, 0.1)',
            border: '1px solid rgba(52, 211, 153, 0.25)',
            textAlign: 'center',
          }}
        >
          <span style={{ fontSize: '14px', fontWeight: 800, color: '#34d399' }}>
            {Math.round(summary.average_similarity * 100)}%
          </span>
          <p style={{ fontSize: '9.5px', fontWeight: 700, color: '#a7f3d0', textTransform: 'uppercase', margin: 0 }}>
            Avg Match
          </p>
        </div>
      </div>

      {/* Filter Tabs & Search Bar */}
      <div
        style={{
          padding: '10px 16px',
          borderBottom: '1px solid var(--color-border)',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
        }}
      >
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '4px' }}>
          {[
            { key: 'ALL' as const, label: 'All', count: summary.total_comparisons },
            { key: 'HIGH' as const, label: 'High', count: summary.high_deviation, color: '#f87171' },
            { key: 'MEDIUM' as const, label: 'Med', count: summary.medium_deviation, color: '#fbbf24' },
            { key: 'LOW' as const, label: 'Low', count: summary.low_deviation, color: '#34d399' },
          ].map(({ key, label, count, color }) => {
            const active = activeFilter === key
            return (
              <button
                key={key}
                type="button"
                id={`dev-filter-${key.toLowerCase()}`}
                onClick={() => setActiveFilter(key)}
                style={{
                  padding: '5px 4px',
                  borderRadius: '6px',
                  background: active ? 'var(--color-bg-card-hover)' : 'transparent',
                  border: active ? '1px solid var(--color-border-hover)' : '1px solid transparent',
                  color: active ? 'var(--color-text-primary)' : 'var(--color-text-secondary)',
                  fontWeight: active ? 700 : 500,
                  fontSize: '11px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '4px',
                }}
              >
                <span>{label}</span>
                <span
                  style={{
                    fontSize: '9.5px',
                    fontWeight: 700,
                    padding: '1px 4px',
                    borderRadius: '8px',
                    background: color ? `${color}20` : 'rgba(108, 142, 245, 0.15)',
                    color: color || 'var(--color-accent-light)',
                  }}
                >
                  {count}
                </span>
              </button>
            )
          })}
        </div>

        <input
          type="text"
          className="input-field"
          placeholder="Filter comparisons by category or keyword..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          style={{ height: '34px', fontSize: '12px' }}
        />
      </div>

      {/* Comparisons Scrollable List */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '12px 16px',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
        }}
      >
        {error && (
          <div
            style={{
              padding: '8px 12px',
              borderRadius: '8px',
              background: 'rgba(248, 113, 113, 0.12)',
              border: '1px solid rgba(248, 113, 113, 0.3)',
              color: '#f87171',
              fontSize: '12px',
            }}
          >
            {error}
          </div>
        )}

        {filteredComparisons.length === 0 ? (
          <div
            style={{
              padding: '32px 16px',
              textAlign: 'center',
              color: 'var(--color-text-muted)',
              fontSize: '12px',
            }}
          >
            <p style={{ fontSize: '24px', marginBottom: '6px' }}>🔍</p>
            No comparisons match your current filter.
          </div>
        ) : (
          filteredComparisons.map((comp) => {
            const isHigh = comp.deviation_level === 'HIGH'
            const isMed = comp.deviation_level === 'MEDIUM'

            const devBadgeColor = isHigh ? '#f87171' : isMed ? '#fbbf24' : '#34d399'
            const devBadgeBg = isHigh
              ? 'rgba(248, 113, 113, 0.15)'
              : isMed
              ? 'rgba(251, 191, 36, 0.15)'
              : 'rgba(52, 211, 153, 0.15)'

            return (
              <div
                key={comp.id}
                style={{
                  background: 'var(--color-bg-secondary)',
                  border: `1px solid ${
                    isHigh
                      ? 'rgba(248, 113, 113, 0.3)'
                      : isMed
                      ? 'rgba(251, 191, 36, 0.3)'
                      : 'var(--color-border)'
                  }`,
                  borderRadius: '10px',
                  padding: '14px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '10px',
                }}
              >
                {/* Header: Category, Section, Deviation & Match % */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    justifyContent: 'space-between',
                    gap: '8px',
                  }}
                >
                  <div>
                    <span
                      style={{
                        fontSize: '10px',
                        fontWeight: 700,
                        color: 'var(--color-accent-light)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.06em',
                      }}
                    >
                      {comp.category}
                    </span>
                    <h3
                      style={{
                        fontSize: '13px',
                        fontWeight: 700,
                        color: 'var(--color-text-primary)',
                        margin: '2px 0 0 0',
                      }}
                    >
                      {comp.section_title || (comp.section_number ? `Section ${comp.section_number}` : 'Contract Provision')}
                    </h3>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
                    <span
                      className="badge"
                      style={{
                        background: devBadgeBg,
                        color: devBadgeColor,
                        border: `1px solid ${devBadgeColor}40`,
                        fontSize: '10px',
                        fontWeight: 700,
                      }}
                    >
                      {isHigh ? '⚠️' : isMed ? '⚡' : '✅'} {comp.deviation_level} DEVIATION
                    </span>
                    <span style={{ fontSize: '10.5px', color: 'var(--color-text-muted)' }}>
                      {Math.round(comp.similarity_score * 100)}% benchmark match
                    </span>
                  </div>
                </div>

                {/* Summary Explanation */}
                <div
                  style={{
                    background: 'rgba(15, 19, 32, 0.5)',
                    padding: '8px 10px',
                    borderRadius: '6px',
                    fontSize: '11.5px',
                    color: 'var(--color-text-secondary)',
                    lineHeight: 1.5,
                  }}
                >
                  <strong style={{ color: 'var(--color-text-primary)' }}>Benchmark Note: </strong>
                  {comp.comparison_summary}
                </div>

                {/* What is different bullet points */}
                {comp.differences && comp.differences.length > 0 && (
                  <div>
                    <p
                      style={{
                        fontSize: '10.5px',
                        fontWeight: 700,
                        color: 'var(--color-text-muted)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.04em',
                        marginBottom: '4px',
                        margin: 0,
                      }}
                    >
                      What is Different:
                    </p>
                    <ul
                      style={{
                        margin: '4px 0 0 0',
                        paddingLeft: '16px',
                        fontSize: '11.5px',
                        color: isHigh ? '#fca5a5' : isMed ? '#fde68a' : 'var(--color-text-secondary)',
                        lineHeight: 1.4,
                      }}
                    >
                      {comp.differences.map((diff, i) => (
                        <li key={i} style={{ marginBottom: '2px' }}>
                          {diff}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Dual Excerpt View: Your Clause vs Benchmark Clause */}
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr',
                    gap: '8px',
                    marginTop: '2px',
                  }}
                >
                  {/* Actual Clause */}
                  <div
                    style={{
                      background: 'rgba(0,0,0,0.25)',
                      padding: '8px',
                      borderRadius: '6px',
                      border: '1px solid rgba(255,255,255,0.05)',
                    }}
                  >
                    <span style={{ fontSize: '9.5px', fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
                      Your Clause
                    </span>
                    <p
                      style={{
                        fontSize: '11px',
                        color: 'var(--color-text-primary)',
                        fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
                        lineHeight: 1.4,
                        margin: '4px 0 0 0',
                        maxHeight: '70px',
                        overflowY: 'auto',
                      }}
                    >
                      {comp.actual_clause}
                    </p>
                  </div>

                  {/* Benchmark Clause */}
                  <div
                    style={{
                      background: 'rgba(108, 142, 245, 0.05)',
                      padding: '8px',
                      borderRadius: '6px',
                      border: '1px solid rgba(108, 142, 245, 0.15)',
                    }}
                  >
                    <span style={{ fontSize: '9.5px', fontWeight: 700, color: 'var(--color-accent-light)', textTransform: 'uppercase' }}>
                      Benchmark Pattern
                    </span>
                    <p
                      style={{
                        fontSize: '11px',
                        color: 'var(--color-text-secondary)',
                        fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
                        lineHeight: 1.4,
                        margin: '4px 0 0 0',
                        maxHeight: '70px',
                        overflowY: 'auto',
                      }}
                    >
                      {comp.benchmark_clause}
                    </p>
                  </div>
                </div>

                {/* Jump to Document Action */}
                <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '2px' }}>
                  <button
                    type="button"
                    onClick={() => handleNavigate(comp)}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: 'var(--color-accent-light)',
                      fontSize: '11.5px',
                      fontWeight: 600,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      padding: 0,
                    }}
                  >
                    View in Document (Page {comp.page_number || 1}) ↗
                  </button>
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
