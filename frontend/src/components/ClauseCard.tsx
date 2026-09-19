import type { Clause } from '../types/clause'

interface ClauseCardProps {
  clause: Clause
  isSelected: boolean
  onClick: () => void
}

export function ClauseCard({ clause, isSelected, onClick }: ClauseCardProps) {
  const getBadgeClass = (risk: string) => {
    switch (risk.toUpperCase()) {
      case 'HIGH':
        return 'badge-risk-high'
      case 'MEDIUM':
        return 'badge-risk-medium'
      case 'LOW':
        return 'badge-risk-low'
      default:
        return 'badge-uploaded'
    }
  }

  const getBorderColor = (risk: string) => {
    switch (risk.toUpperCase()) {
      case 'HIGH':
        return '#f87171'
      case 'MEDIUM':
        return '#fbbf24'
      case 'LOW':
        return '#34d399'
      default:
        return 'var(--color-accent)'
    }
  }

  const sectionDisplay = clause.section_number
    ? `${clause.section_number} ${clause.section_title ? '· ' + clause.section_title : ''}`
    : clause.section_title || 'General Clause'

  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        width: '100%',
        textAlign: 'left',
        padding: '14px 16px',
        borderRadius: '12px',
        background: isSelected
          ? 'rgba(108, 142, 245, 0.12)'
          : 'var(--color-bg-card)',
        border: `1px solid ${
          isSelected ? 'var(--color-accent)' : 'var(--color-border)'
        }`,
        borderLeft: `4px solid ${getBorderColor(clause.risk_level)}`,
        cursor: 'pointer',
        transition: 'all 0.2s ease',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
        boxShadow: isSelected ? '0 0 16px rgba(108, 142, 245, 0.2)' : 'none',
      }}
      className="clause-card-item"
    >
      {/* Header: Section/Title and Risk Badge */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '8px',
          width: '100%',
        }}
      >
        <span
          style={{
            fontSize: '13px',
            fontWeight: 700,
            color: isSelected ? 'var(--color-accent-light)' : 'var(--color-text-primary)',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
          title={sectionDisplay}
        >
          {sectionDisplay}
        </span>

        <span className={`badge ${getBadgeClass(clause.risk_level)}`} style={{ flexShrink: 0 }}>
          {clause.risk_level}
        </span>
      </div>

      {/* Short explanation preview */}
      <p
        style={{
          fontSize: '12px',
          color: 'var(--color-text-secondary)',
          lineHeight: 1.5,
          margin: 0,
          display: '-webkit-box',
          WebkitLineClamp: 2,
          WebkitBoxOrient: 'vertical',
          overflow: 'hidden',
        }}
      >
        {clause.explanation}
      </p>

      {/* Page location tag */}
      {clause.page_number && (
        <div
          style={{
            fontSize: '11px',
            color: 'var(--color-text-muted)',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
          }}
        >
          <span>📄</span> Page {clause.page_number}
        </div>
      )}
    </button>
  )
}
