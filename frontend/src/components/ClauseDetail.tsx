import { useState } from 'react'
import type { Clause } from '../types/clause'

interface ClauseDetailProps {
  clause: Clause | null
  onNavigateToClause?: (clause: Clause) => void
}

export function ClauseDetail({ clause, onNavigateToClause }: ClauseDetailProps) {
  const [sideBySide, setSideBySide] = useState<boolean>(false)

  if (!clause) {
    return (
      <div
        className="glass-card"
        style={{
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '32px 24px',
          textAlign: 'center',
          gap: '12px',
          color: 'var(--color-text-muted)',
        }}
      >
        <div
          style={{
            width: '48px',
            height: '48px',
            borderRadius: '50%',
            background: 'var(--color-bg-secondary)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '22px',
          }}
        >
          👆
        </div>
        <h3 style={{ fontSize: '15px', fontWeight: 700, color: 'var(--color-text-primary)' }}>
          No Clause Selected
        </h3>
        <p style={{ fontSize: '13px', lineHeight: 1.6, maxWidth: '280px' }}>
          Select a clause from the sidebar or click any highlighted section in the document to view its simplified explanation.
        </p>
      </div>
    )
  }

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

  const getRiskIcon = (risk: string) => {
    switch (risk.toUpperCase()) {
      case 'HIGH':
        return '⚠️'
      case 'MEDIUM':
        return '⚡'
      case 'LOW':
        return '✅'
      default:
        return '📄'
    }
  }

  return (
    <div
      className="glass-card"
      style={{
        padding: '20px',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
        overflowY: 'auto',
        height: '100%',
      }}
    >
      {/* Header: Title, Section, Risk Badge & Side-by-Side Toggle */}
      <div style={{ borderBottom: '1px solid var(--color-border)', paddingBottom: '14px' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            gap: '12px',
            marginBottom: '8px',
          }}
        >
          <div>
            <span
              style={{
                fontSize: '11px',
                fontWeight: 700,
                color: 'var(--color-accent)',
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
              }}
            >
              {clause.section_number ? `Section ${clause.section_number}` : 'Clause'}
            </span>
            <h2
              style={{
                fontSize: '16px',
                fontWeight: 800,
                color: 'var(--color-text-primary)',
                marginTop: '2px',
                margin: 0,
              }}
            >
              {clause.section_title || 'Contract Provision'}
            </h2>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className={`badge ${getBadgeClass(clause.risk_level)}`} style={{ flexShrink: 0 }}>
              {getRiskIcon(clause.risk_level)} {clause.risk_level} RISK
            </span>
            <button
              type="button"
              id="toggle-side-by-side-btn"
              onClick={() => setSideBySide(!sideBySide)}
              className="btn-secondary"
              style={{ padding: '4px 8px', fontSize: '11px' }}
              title="Toggle Side-by-Side Original vs Explanation view"
            >
              {sideBySide ? '📄 Standard' : '↔️ Side-by-Side'}
            </button>
          </div>
        </div>

        {clause.page_number && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              fontSize: '12px',
              color: 'var(--color-text-secondary)',
            }}
          >
            <span>Document Location: Page {clause.page_number}</span>
            {onNavigateToClause && (
              <button
                type="button"
                onClick={() => onNavigateToClause(clause)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--color-accent-light)',
                  cursor: 'pointer',
                  fontSize: '12px',
                  fontWeight: 600,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                }}
              >
                Jump to text ↗
              </button>
            )}
          </div>
        )}
      </div>

      {/* Side-by-Side View vs Standard View */}
      {sideBySide ? (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: '12px',
            flex: 1,
            minHeight: 0,
          }}
        >
          {/* Left Column: Original Text */}
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              background: 'var(--color-bg-secondary)',
              border: '1px solid var(--color-border)',
              borderRadius: '10px',
              padding: '12px',
              overflowY: 'auto',
            }}
          >
            <div
              style={{
                fontSize: '10.5px',
                fontWeight: 700,
                color: 'var(--color-text-muted)',
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
                marginBottom: '8px',
              }}
            >
              Original Contract Text
            </div>
            <div
              style={{
                fontSize: '12px',
                fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
                color: 'var(--color-text-secondary)',
                lineHeight: 1.6,
                whiteSpace: 'pre-wrap',
              }}
            >
              {clause.clause_text}
            </div>
          </div>

          {/* Right Column: Plain Language Explanation */}
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '10px',
              overflowY: 'auto',
            }}
          >
            <div
              style={{
                background: 'rgba(108, 142, 245, 0.08)',
                border: '1px solid rgba(108, 142, 245, 0.25)',
                borderRadius: '10px',
                padding: '12px',
              }}
            >
              <div
                style={{
                  fontSize: '11px',
                  fontWeight: 700,
                  color: 'var(--color-accent-light)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em',
                  marginBottom: '6px',
                }}
              >
                💡 What this means
              </div>
              <p style={{ fontSize: '12.5px', color: 'var(--color-text-primary)', lineHeight: 1.6, margin: 0 }}>
                {clause.explanation}
              </p>
            </div>

            <div
              style={{
                background:
                  clause.risk_level === 'HIGH'
                    ? 'rgba(248, 113, 113, 0.08)'
                    : clause.risk_level === 'MEDIUM'
                    ? 'rgba(251, 191, 36, 0.08)'
                    : 'rgba(52, 211, 153, 0.08)',
                border: `1px solid ${
                  clause.risk_level === 'HIGH'
                    ? 'rgba(248, 113, 113, 0.25)'
                    : clause.risk_level === 'MEDIUM'
                    ? 'rgba(251, 191, 36, 0.25)'
                    : 'rgba(52, 211, 153, 0.25)'
                }`,
                borderRadius: '10px',
                padding: '12px',
              }}
            >
              <div
                style={{
                  fontSize: '11px',
                  fontWeight: 700,
                  color:
                    clause.risk_level === 'HIGH'
                      ? '#fca5a5'
                      : clause.risk_level === 'MEDIUM'
                      ? '#fde68a'
                      : '#a7f3d0',
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em',
                  marginBottom: '6px',
                }}
              >
                🚩 Why Flagged
              </div>
              <p style={{ fontSize: '12px', color: 'var(--color-text-secondary)', lineHeight: 1.5, margin: 0 }}>
                {clause.reason}
              </p>
            </div>
          </div>
        </div>
      ) : (
        <>
          {/* Section 1: "What this means" (Plain-Language Explanation) */}
          <div
            style={{
              background: 'rgba(108, 142, 245, 0.08)',
              border: '1px solid rgba(108, 142, 245, 0.25)',
              borderRadius: '12px',
              padding: '16px',
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '12px',
                fontWeight: 700,
                color: 'var(--color-accent-light)',
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
                marginBottom: '8px',
              }}
            >
              <span>💡</span> What this means
            </div>
            <p
              style={{
                fontSize: '13.5px',
                color: 'var(--color-text-primary)',
                lineHeight: 1.65,
                margin: 0,
              }}
            >
              {clause.explanation}
            </p>
          </div>

          {/* Section 2: "Why this was flagged" (Risk Rationale) */}
          <div
            style={{
              background:
                clause.risk_level === 'HIGH'
                  ? 'rgba(248, 113, 113, 0.08)'
                  : clause.risk_level === 'MEDIUM'
                  ? 'rgba(251, 191, 36, 0.08)'
                  : 'rgba(52, 211, 153, 0.08)',
              border: `1px solid ${
                clause.risk_level === 'HIGH'
                  ? 'rgba(248, 113, 113, 0.25)'
                  : clause.risk_level === 'MEDIUM'
                  ? 'rgba(251, 191, 36, 0.25)'
                  : 'rgba(52, 211, 153, 0.25)'
              }`,
              borderRadius: '12px',
              padding: '16px',
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '12px',
                fontWeight: 700,
                color:
                  clause.risk_level === 'HIGH'
                    ? '#fca5a5'
                    : clause.risk_level === 'MEDIUM'
                    ? '#fde68a'
                    : '#a7f3d0',
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
                marginBottom: '8px',
              }}
            >
              <span>🚩</span> Why this was flagged
            </div>
            <p
              style={{
                fontSize: '13px',
                color: 'var(--color-text-secondary)',
                lineHeight: 1.6,
                margin: 0,
              }}
            >
              {clause.reason}
            </p>
          </div>

          {/* Section 3: Original Contractual Text (Verbatim Excerpt) */}
          <div>
            <div
              style={{
                fontSize: '11px',
                fontWeight: 700,
                color: 'var(--color-text-muted)',
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
                marginBottom: '8px',
              }}
            >
              Original Contract Text (Verbatim)
            </div>
            <div
              style={{
                background: 'var(--color-bg-secondary)',
                border: '1px solid var(--color-border)',
                borderRadius: '10px',
                padding: '14px',
                fontSize: '12.5px',
                fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
                color: 'var(--color-text-secondary)',
                lineHeight: 1.7,
                whiteSpace: 'pre-wrap',
                maxHeight: '180px',
                overflowY: 'auto',
              }}
            >
              {clause.clause_text}
            </div>
          </div>
        </>
      )}
    </div>
  )
}

