import type { AnalysisSummary, RiskFilter } from '../types/clause'

interface RiskSummaryProps {
  summary: AnalysisSummary
  activeFilter?: RiskFilter
  onFilterChange?: (filter: RiskFilter) => void
}

export function RiskSummary({ summary, activeFilter = 'ALL', onFilterChange }: RiskSummaryProps) {
  const total = summary.total_clauses || (summary.high + summary.medium + summary.low) || 1
  const highPercent = Math.round((summary.high / total) * 100)
  const medPercent = Math.round((summary.medium / total) * 100)
  const lowPercent = Math.round((summary.low / total) * 100)

  return (
    <div
      className="glass-card"
      style={{
        padding: '20px',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
      }}
    >
      {/* Header & Overall Summary */}
      <div>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: '8px',
          }}
        >
          <h2
            style={{
              fontSize: '13px',
              fontWeight: 700,
              color: 'var(--color-text-secondary)',
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
            }}
          >
            Risk Assessment Summary
          </h2>
          <span
            style={{
              fontSize: '11px',
              fontWeight: 700,
              padding: '2px 8px',
              borderRadius: '12px',
              background: 'rgba(108, 142, 245, 0.15)',
              color: 'var(--color-accent-light)',
            }}
          >
            {summary.total_clauses} Total Clauses
          </span>
        </div>

        {summary.overall_summary && (
          <p
            style={{
              fontSize: '13px',
              color: 'var(--color-text-primary)',
              lineHeight: 1.6,
              background: 'rgba(15, 19, 32, 0.6)',
              padding: '12px 14px',
              borderRadius: '10px',
              border: '1px solid var(--color-border)',
            }}
          >
            {summary.overall_summary}
          </p>
        )}
      </div>

      {/* Visual Multi-Segment Risk Bar */}
      <div>
        <div
          style={{
            display: 'flex',
            height: '8px',
            borderRadius: '4px',
            overflow: 'hidden',
            background: 'var(--color-bg-secondary)',
            marginBottom: '12px',
          }}
        >
          {summary.high > 0 && (
            <div
              style={{
                width: `${highPercent}%`,
                background: '#f87171',
                transition: 'width 0.4s ease',
              }}
              title={`High Risk: ${summary.high} clauses (${highPercent}%)`}
            />
          )}
          {summary.medium > 0 && (
            <div
              style={{
                width: `${medPercent}%`,
                background: '#fbbf24',
                transition: 'width 0.4s ease',
              }}
              title={`Medium Risk: ${summary.medium} clauses (${medPercent}%)`}
            />
          )}
          {summary.low > 0 && (
            <div
              style={{
                width: `${lowPercent}%`,
                background: '#34d399',
                transition: 'width 0.4s ease',
              }}
              title={`Low Risk: ${summary.low} clauses (${lowPercent}%)`}
            />
          )}
        </div>

        {/* Clickable Metric Badges */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: '8px',
          }}
        >
          {/* High */}
          <button
            type="button"
            onClick={() => onFilterChange?.(activeFilter === 'HIGH' ? 'ALL' : 'HIGH')}
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              padding: '10px 8px',
              borderRadius: '10px',
              background:
                activeFilter === 'HIGH'
                  ? 'rgba(248, 113, 113, 0.22)'
                  : 'rgba(248, 113, 113, 0.08)',
              border: `1px solid ${
                activeFilter === 'HIGH' ? '#f87171' : 'rgba(248, 113, 113, 0.25)'
              }`,
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
          >
            <span style={{ fontSize: '18px', fontWeight: 800, color: '#f87171' }}>
              {summary.high}
            </span>
            <span
              style={{
                fontSize: '11px',
                fontWeight: 700,
                color: '#fca5a5',
                textTransform: 'uppercase',
                letterSpacing: '0.04em',
                marginTop: '2px',
              }}
            >
              High Risk
            </span>
          </button>

          {/* Medium */}
          <button
            type="button"
            onClick={() => onFilterChange?.(activeFilter === 'MEDIUM' ? 'ALL' : 'MEDIUM')}
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              padding: '10px 8px',
              borderRadius: '10px',
              background:
                activeFilter === 'MEDIUM'
                  ? 'rgba(251, 191, 36, 0.22)'
                  : 'rgba(251, 191, 36, 0.08)',
              border: `1px solid ${
                activeFilter === 'MEDIUM' ? '#fbbf24' : 'rgba(251, 191, 36, 0.25)'
              }`,
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
          >
            <span style={{ fontSize: '18px', fontWeight: 800, color: '#fbbf24' }}>
              {summary.medium}
            </span>
            <span
              style={{
                fontSize: '11px',
                fontWeight: 700,
                color: '#fde68a',
                textTransform: 'uppercase',
                letterSpacing: '0.04em',
                marginTop: '2px',
              }}
            >
              Medium Risk
            </span>
          </button>

          {/* Low */}
          <button
            type="button"
            onClick={() => onFilterChange?.(activeFilter === 'LOW' ? 'ALL' : 'LOW')}
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              padding: '10px 8px',
              borderRadius: '10px',
              background:
                activeFilter === 'LOW'
                  ? 'rgba(52, 211, 153, 0.22)'
                  : 'rgba(52, 211, 153, 0.08)',
              border: `1px solid ${
                activeFilter === 'LOW' ? '#34d399' : 'rgba(52, 211, 153, 0.25)'
              }`,
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
          >
            <span style={{ fontSize: '18px', fontWeight: 800, color: '#34d399' }}>
              {summary.low}
            </span>
            <span
              style={{
                fontSize: '11px',
                fontWeight: 700,
                color: '#a7f3d0',
                textTransform: 'uppercase',
                letterSpacing: '0.04em',
                marginTop: '2px',
              }}
            >
              Low Risk
            </span>
          </button>
        </div>
      </div>
    </div>
  )
}
