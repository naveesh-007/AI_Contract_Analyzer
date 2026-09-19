import { ClauseCard } from './ClauseCard'
import type { Clause, RiskFilter } from '../types/clause'

interface ClauseListProps {
  clauses: Clause[]
  selectedClauseId: string | null
  onSelectClause: (clause: Clause) => void
  activeFilter: RiskFilter
  onFilterChange: (filter: RiskFilter) => void
  searchQuery: string
  onSearchChange: (query: string) => void
}

export function ClauseList({
  clauses,
  selectedClauseId,
  onSelectClause,
  activeFilter,
  onFilterChange,
  searchQuery,
  onSearchChange,
}: ClauseListProps) {
  // Count by risk for badges
  const highCount = clauses.filter((c) => c.risk_level === 'HIGH').length
  const medCount = clauses.filter((c) => c.risk_level === 'MEDIUM').length
  const lowCount = clauses.filter((c) => c.risk_level === 'LOW').length

  const filterTabs: { key: RiskFilter; label: string; count: number; color?: string }[] = [
    { key: 'ALL', label: 'All', count: clauses.length },
    { key: 'HIGH', label: 'High', count: highCount, color: '#f87171' },
    { key: 'MEDIUM', label: 'Med', count: medCount, color: '#fbbf24' },
    { key: 'LOW', label: 'Low', count: lowCount, color: '#34d399' },
  ]

  // Filter clauses by risk level and search text
  const filteredClauses = clauses.filter((clause) => {
    // 1. Risk Level Filter
    if (activeFilter !== 'ALL' && clause.risk_level !== activeFilter) {
      return false
    }

    // 2. Search Query Filter
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      const inText = clause.clause_text.toLowerCase().includes(q)
      const inTitle = (clause.section_title || '').toLowerCase().includes(q)
      const inNumber = (clause.section_number || '').toLowerCase().includes(q)
      const inExplanation = clause.explanation.toLowerCase().includes(q)
      const inReason = clause.reason.toLowerCase().includes(q)
      return inText || inTitle || inNumber || inExplanation || inReason
    }

    return true
  })

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        gap: '12px',
      }}
    >
      {/* Search Input */}
      <div style={{ position: 'relative' }}>
        <input
          id="clause-search-input"
          type="text"
          className="input-field"
          placeholder="Search clauses, terms, or risk factors..."
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          style={{
            paddingLeft: '36px',
            fontSize: '13px',
            height: '40px',
          }}
        />
        <span
          style={{
            position: 'absolute',
            left: '12px',
            top: '50%',
            transform: 'translateY(-50%)',
            fontSize: '14px',
            color: 'var(--color-text-muted)',
            pointerEvents: 'none',
          }}
        >
          🔍
        </span>
        {searchQuery && (
          <button
            type="button"
            onClick={() => onSearchChange('')}
            style={{
              position: 'absolute',
              right: '10px',
              top: '50%',
              transform: 'translateY(-50%)',
              background: 'transparent',
              border: 'none',
              color: 'var(--color-text-muted)',
              cursor: 'pointer',
              fontSize: '14px',
            }}
          >
            ✕
          </button>
        )}
      </div>

      {/* Filter Tabs */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '4px',
          background: 'var(--color-bg-secondary)',
          padding: '4px',
          borderRadius: '10px',
          border: '1px solid var(--color-border)',
        }}
      >
        {filterTabs.map(({ key, label, count, color }) => {
          const isActive = activeFilter === key
          return (
            <button
              key={key}
              type="button"
              id={`filter-btn-${key.toLowerCase()}`}
              onClick={() => onFilterChange(key)}
              style={{
                padding: '6px 4px',
                borderRadius: '6px',
                background: isActive ? 'var(--color-bg-card-hover)' : 'transparent',
                border: isActive ? '1px solid var(--color-border-hover)' : '1px solid transparent',
                color: isActive ? 'var(--color-text-primary)' : 'var(--color-text-secondary)',
                fontWeight: isActive ? 700 : 500,
                fontSize: '11px',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '4px',
              }}
            >
              <span>{label}</span>
              <span
                style={{
                  fontSize: '10px',
                  fontWeight: 700,
                  padding: '1px 5px',
                  borderRadius: '10px',
                  background: color
                    ? `${color}20`
                    : 'rgba(108, 142, 245, 0.15)',
                  color: color || 'var(--color-accent-light)',
                }}
              >
                {count}
              </span>
            </button>
          )
        })}
      </div>

      {/* Clause Cards Scrollable List */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
          paddingRight: '4px',
        }}
      >
        {filteredClauses.length === 0 ? (
          <div
            style={{
              padding: '32px 16px',
              textAlign: 'center',
              borderRadius: '12px',
              background: 'var(--color-bg-card)',
              border: '1px dashed var(--color-border)',
              color: 'var(--color-text-muted)',
            }}
          >
            <p style={{ fontSize: '24px', marginBottom: '8px' }}>🔎</p>
            <p style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-text-secondary)' }}>
              No clauses matched
            </p>
            <p style={{ fontSize: '11px', marginTop: '4px' }}>
              {searchQuery
                ? 'Try adjusting your search terms or clearing filters.'
                : 'No clauses found for this risk level.'}
            </p>
            {(searchQuery || activeFilter !== 'ALL') && (
              <button
                type="button"
                onClick={() => {
                  onSearchChange('')
                  onFilterChange('ALL')
                }}
                className="btn-secondary"
                style={{
                  marginTop: '12px',
                  padding: '6px 12px',
                  fontSize: '11px',
                }}
              >
                Reset filters
              </button>
            )}
          </div>
        ) : (
          filteredClauses.map((clause) => (
            <ClauseCard
              key={clause.id}
              clause={clause}
              isSelected={clause.id === selectedClauseId}
              onClick={() => onSelectClause(clause)}
            />
          ))
        )}
      </div>
    </div>
  )
}
