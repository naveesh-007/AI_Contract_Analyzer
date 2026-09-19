import { useState, useMemo } from 'react'
import type { AnalysisSummary, Clause, RiskFilter } from '../types/clause'
import type { Document, DocumentPage } from '../types/document'

interface DocumentVisualizerProps {
  document?: Document | null
  summary: AnalysisSummary | null
  clauses: Clause[]
  pages?: DocumentPage[]
  selectedClauseId?: string | null
  onSelectClause?: (clause: Clause) => void
  onFilterChange?: (filter: RiskFilter) => void
  activeFilter?: RiskFilter
  compact?: boolean
}

// Category keywords for intelligent domain categorization
const CATEGORY_DEFINITIONS: Record<string, { label: string; icon: string; keywords: string[] }> = {
  liability: {
    label: 'Liability & Indemnity',
    icon: '🛡️',
    keywords: ['liab', 'indemn', 'damage', 'loss', 'consequential', 'remedy', 'remedies', 'hold harmless'],
  },
  termination: {
    label: 'Termination & Exit',
    icon: '🚪',
    keywords: ['terminat', 'expir', 'cancel', 'default', 'breach', 'notice period', 'survival'],
  },
  financial: {
    label: 'Payment & Financials',
    icon: '💳',
    keywords: ['pay', 'fee', 'price', 'invoic', 'cost', 'charge', 'tax', 'interest', 'refund', 'gst'],
  },
  ip_confidentiality: {
    label: 'IP & Confidentiality',
    icon: '🔒',
    keywords: ['confident', 'intellectual property', 'patent', 'copyright', 'trade secret', 'non-disclosure', 'nda', 'proprietary'],
  },
  disputes: {
    label: 'Disputes & Governing Law',
    icon: '⚖️',
    keywords: ['jurisdiction', 'governing law', 'arbitrat', 'court', 'dispute', 'venue', 'settlement'],
  },
  warranties: {
    label: 'Warranties & Compliance',
    icon: '📜',
    keywords: ['warrant', 'represent', 'complian', 'covenant', 'law', 'standard', 'guarantee'],
  },
  general: {
    label: 'General & Boilerplate',
    icon: '📑',
    keywords: ['severability', 'entire agreement', 'amendment', 'assignment', 'force majeure', 'miscellaneous', 'notice'],
  },
}

function classifyClause(clause: Clause): string {
  const text = `${clause.section_title || ''} ${clause.explanation || ''} ${clause.clause_text || ''}`.toLowerCase()

  for (const [key, def] of Object.entries(CATEGORY_DEFINITIONS)) {
    if (key === 'general') continue
    if (def.keywords.some((kw) => text.includes(kw))) {
      return key
    }
  }
  return 'general'
}

export function DocumentVisualizer({
  document,
  summary,
  clauses,
  pages = [],
  selectedClauseId,
  onSelectClause,
  onFilterChange,
  activeFilter = 'ALL',
  compact = false,
}: DocumentVisualizerProps) {
  const [activeCategory, setActiveCategory] = useState<string | null>(null)
  const [hoveredDonut, setHoveredDonut] = useState<string | null>(null)

  // ── 1. Calculate Metrics ────────────────────────────────────────────────────
  const total = summary?.total_clauses || clauses.length || 1
  const highCount = summary?.high ?? clauses.filter((c) => c.risk_level === 'HIGH').length
  const medCount = summary?.medium ?? clauses.filter((c) => c.risk_level === 'MEDIUM').length
  const lowCount = summary?.low ?? clauses.filter((c) => c.risk_level === 'LOW').length

  const highPct = Math.round((highCount / total) * 100)
  const medPct = Math.round((medCount / total) * 100)
  const lowPct = Math.round((lowCount / total) * 100)

  // Overall Contract Health Score (0–100 scale: higher is healthier / safer)
  // Deduct 25 pts for high risk clauses, 10 for medium risk clauses proportionally
  const healthScore = useMemo(() => {
    if (total === 0) return 100
    const rawPenalty = (highCount * 30 + medCount * 12) / total
    return Math.max(15, Math.min(100, Math.round(100 - rawPenalty)))
  }, [total, highCount, medCount])

  const healthGrade = useMemo(() => {
    if (healthScore >= 80) return { label: 'Low Risk • High Safety', color: '#34d399', bg: 'rgba(52, 211, 153, 0.12)' }
    if (healthScore >= 55) return { label: 'Moderate Risk • Review Advised', color: '#fbbf24', bg: 'rgba(251, 191, 36, 0.12)' }
    return { label: 'High Risk • Critical Scrutiny Needed', color: '#f87171', bg: 'rgba(248, 113, 113, 0.12)' }
  }, [healthScore])

  // ── 2. Categorize Clauses for Domain Distribution ─────────────────────────
  const categoryStats = useMemo(() => {
    const stats: Record<string, { total: number; high: number; med: number; low: number; clauses: Clause[] }> = {}

    for (const key of Object.keys(CATEGORY_DEFINITIONS)) {
      stats[key] = { total: 0, high: 0, med: 0, low: 0, clauses: [] }
    }

    clauses.forEach((c) => {
      const cat = classifyClause(c)
      if (!stats[cat]) {
        stats[cat] = { total: 0, high: 0, med: 0, low: 0, clauses: [] }
      }
      stats[cat].total += 1
      stats[cat].clauses.push(c)
      if (c.risk_level === 'HIGH') stats[cat].high += 1
      else if (c.risk_level === 'MEDIUM') stats[cat].med += 1
      else stats[cat].low += 1
    })

    return stats
  }, [clauses])

  // ── 3. Page Distribution & Heatmap ─────────────────────────────────────────
  const pageStats = useMemo(() => {
    const totalPages = Math.max(pages.length, 1)
    const map: Record<number, { pageNum: number; clauses: Clause[]; high: number; med: number; low: number }> = {}

    for (let p = 1; p <= totalPages; p++) {
      map[p] = { pageNum: p, clauses: [], high: 0, med: 0, low: 0 }
    }

    clauses.forEach((c) => {
      const p = c.page_number && c.page_number > 0 ? c.page_number : 1
      if (!map[p]) {
        map[p] = { pageNum: p, clauses: [], high: 0, med: 0, low: 0 }
      }
      map[p].clauses.push(c)
      if (c.risk_level === 'HIGH') map[p].high += 1
      else if (c.risk_level === 'MEDIUM') map[p].med += 1
      else map[p].low += 1
    })

    return Object.values(map)
  }, [pages, clauses])

  // ── Donut Chart Parameters ────────────────────────────────────────────────
  const radius = 42
  const circumference = 2 * Math.PI * radius
  const highStroke = (highPct / 100) * circumference
  const medStroke = (medPct / 100) * circumference
  const lowStroke = (lowPct / 100) * circumference

  const highOffset = 0
  const medOffset = -highStroke
  const lowOffset = -(highStroke + medStroke)

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: compact ? '16px' : '24px',
        width: '100%',
      }}
    >
      {/* ── Top Key Metric Badges & Scorecard ─────────────────────────────── */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: compact ? 'repeat(2, 1fr)' : 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '14px',
        }}
      >
        {/* Health Score Dial */}
        <div
          className="glass-card"
          style={{
            padding: '18px',
            display: 'flex',
            alignItems: 'center',
            gap: '16px',
            position: 'relative',
            overflow: 'hidden',
          }}
        >
          <div style={{ position: 'relative', width: '68px', height: '68px', flexShrink: 0 }}>
            <svg viewBox="0 0 100 100" style={{ width: '100%', height: '100%', transform: 'rotate(-90deg)' }}>
              <circle
                cx="50"
                cy="50"
                r="40"
                fill="transparent"
                stroke="rgba(255,255,255,0.06)"
                strokeWidth="10"
              />
              <circle
                cx="50"
                cy="50"
                r="40"
                fill="transparent"
                stroke={healthGrade.color}
                strokeWidth="10"
                strokeDasharray={`${(healthScore / 100) * 251.2} 251.2`}
                strokeLinecap="round"
                style={{ transition: 'stroke-dasharray 0.8s ease' }}
              />
            </svg>
            <div
              style={{
                position: 'absolute',
                inset: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexDirection: 'column',
              }}
            >
              <span style={{ fontSize: '18px', fontWeight: 800, color: healthGrade.color }}>
                {healthScore}
              </span>
              <span style={{ fontSize: '9px', fontWeight: 700, color: 'var(--color-text-muted)', marginTop: '-2px' }}>
                /100
              </span>
            </div>
          </div>
          <div>
            <span
              style={{
                fontSize: '11px',
                fontWeight: 700,
                color: 'var(--color-text-muted)',
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
              }}
            >
              Contract Health
            </span>
            <p
              style={{
                fontSize: '13px',
                fontWeight: 700,
                color: healthGrade.color,
                marginTop: '3px',
                lineHeight: 1.3,
              }}
            >
              {healthGrade.label}
            </p>
          </div>
        </div>

        {/* High Risk Flags */}
        <div
          className="glass-card"
          onClick={() => onFilterChange?.(activeFilter === 'HIGH' ? 'ALL' : 'HIGH')}
          style={{
            padding: '18px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            cursor: onFilterChange ? 'pointer' : 'default',
            border: activeFilter === 'HIGH' ? '1px solid #f87171' : '1px solid var(--color-border)',
            background: activeFilter === 'HIGH' ? 'rgba(248, 113, 113, 0.12)' : 'var(--color-bg-card)',
            transition: 'all 0.2s ease',
          }}
        >
          <div>
            <span
              style={{
                fontSize: '11px',
                fontWeight: 700,
                color: '#f87171',
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
              }}
            >
              High Risk Flags
            </span>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px', marginTop: '4px' }}>
              <span style={{ fontSize: '24px', fontWeight: 800, color: '#f87171' }}>{highCount}</span>
              <span style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>({highPct}%)</span>
            </div>
          </div>
          <div
            style={{
              width: '38px',
              height: '38px',
              borderRadius: '10px',
              background: 'rgba(248, 113, 113, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '18px',
            }}
          >
            ⚠️
          </div>
        </div>

        {/* Medium Warnings */}
        <div
          className="glass-card"
          onClick={() => onFilterChange?.(activeFilter === 'MEDIUM' ? 'ALL' : 'MEDIUM')}
          style={{
            padding: '18px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            cursor: onFilterChange ? 'pointer' : 'default',
            border: activeFilter === 'MEDIUM' ? '1px solid #fbbf24' : '1px solid var(--color-border)',
            background: activeFilter === 'MEDIUM' ? 'rgba(251, 191, 36, 0.12)' : 'var(--color-bg-card)',
            transition: 'all 0.2s ease',
          }}
        >
          <div>
            <span
              style={{
                fontSize: '11px',
                fontWeight: 700,
                color: '#fbbf24',
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
              }}
            >
              Moderate Risks
            </span>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px', marginTop: '4px' }}>
              <span style={{ fontSize: '24px', fontWeight: 800, color: '#fbbf24' }}>{medCount}</span>
              <span style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>({medPct}%)</span>
            </div>
          </div>
          <div
            style={{
              width: '38px',
              height: '38px',
              borderRadius: '10px',
              background: 'rgba(251, 191, 36, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '18px',
            }}
          >
            ⚡
          </div>
        </div>

        {/* Total Analyzed Clauses */}
        <div
          className="glass-card"
          onClick={() => onFilterChange?.('ALL')}
          style={{
            padding: '18px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            cursor: onFilterChange ? 'pointer' : 'default',
            border: activeFilter === 'ALL' ? '1px solid var(--color-accent)' : '1px solid var(--color-border)',
            background: activeFilter === 'ALL' ? 'rgba(108, 142, 245, 0.1)' : 'var(--color-bg-card)',
            transition: 'all 0.2s ease',
          }}
        >
          <div>
            <span
              style={{
                fontSize: '11px',
                fontWeight: 700,
                color: 'var(--color-accent-light)',
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
              }}
            >
              Total Provisions
            </span>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px', marginTop: '4px' }}>
              <span style={{ fontSize: '24px', fontWeight: 800, color: 'var(--color-text-primary)' }}>
                {total}
              </span>
              <span style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>clauses</span>
            </div>
          </div>
          <div
            style={{
              width: '38px',
              height: '38px',
              borderRadius: '10px',
              background: 'rgba(108, 142, 245, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '18px',
            }}
          >
            📋
          </div>
        </div>
      </div>

      {/* ── Main Visualization Grid ───────────────────────────────────────── */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: compact ? '1fr' : '1fr 1.3fr',
          gap: '20px',
        }}
      >
        {/* Left Column: Risk Severity Donut & Overview */}
        <div
          className="glass-card"
          style={{
            padding: '22px',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            gap: '18px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <h3
              style={{
                fontSize: '13px',
                fontWeight: 700,
                color: 'var(--color-text-secondary)',
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
              }}
            >
              📊 Risk Severity Distribution
            </h3>
            {document && (
              <span
                style={{
                  fontSize: '11px',
                  fontWeight: 600,
                  color: 'var(--color-text-muted)',
                }}
              >
                {document.filename}
              </span>
            )}
          </div>

          {/* SVG Donut Chart */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '28px',
              padding: '12px 0',
              flexWrap: 'wrap',
            }}
          >
            <div style={{ position: 'relative', width: '130px', height: '130px' }}>
              <svg viewBox="0 0 100 100" style={{ width: '100%', height: '100%', transform: 'rotate(-90deg)' }}>
                {/* Background base */}
                <circle
                  cx="50"
                  cy="50"
                  r={radius}
                  fill="transparent"
                  stroke="rgba(255,255,255,0.05)"
                  strokeWidth="12"
                />

                {/* High Risk Segment */}
                {highCount > 0 && (
                  <circle
                    cx="50"
                    cy="50"
                    r={radius}
                    fill="transparent"
                    stroke="#f87171"
                    strokeWidth="12"
                    strokeDasharray={`${highStroke} ${circumference}`}
                    strokeDashoffset={highOffset}
                    style={{
                      transition: 'all 0.3s ease',
                      cursor: 'pointer',
                      opacity: hoveredDonut && hoveredDonut !== 'HIGH' ? 0.4 : 1,
                    }}
                    onMouseEnter={() => setHoveredDonut('HIGH')}
                    onMouseLeave={() => setHoveredDonut(null)}
                    onClick={() => onFilterChange?.(activeFilter === 'HIGH' ? 'ALL' : 'HIGH')}
                  />
                )}

                {/* Med Risk Segment */}
                {medCount > 0 && (
                  <circle
                    cx="50"
                    cy="50"
                    r={radius}
                    fill="transparent"
                    stroke="#fbbf24"
                    strokeWidth="12"
                    strokeDasharray={`${medStroke} ${circumference}`}
                    strokeDashoffset={medOffset}
                    style={{
                      transition: 'all 0.3s ease',
                      cursor: 'pointer',
                      opacity: hoveredDonut && hoveredDonut !== 'MEDIUM' ? 0.4 : 1,
                    }}
                    onMouseEnter={() => setHoveredDonut('MEDIUM')}
                    onMouseLeave={() => setHoveredDonut(null)}
                    onClick={() => onFilterChange?.(activeFilter === 'MEDIUM' ? 'ALL' : 'MEDIUM')}
                  />
                )}

                {/* Low Risk Segment */}
                {lowCount > 0 && (
                  <circle
                    cx="50"
                    cy="50"
                    r={radius}
                    fill="transparent"
                    stroke="#34d399"
                    strokeWidth="12"
                    strokeDasharray={`${lowStroke} ${circumference}`}
                    strokeDashoffset={lowOffset}
                    style={{
                      transition: 'all 0.3s ease',
                      cursor: 'pointer',
                      opacity: hoveredDonut && hoveredDonut !== 'LOW' ? 0.4 : 1,
                    }}
                    onMouseEnter={() => setHoveredDonut('LOW')}
                    onMouseLeave={() => setHoveredDonut(null)}
                    onClick={() => onFilterChange?.(activeFilter === 'LOW' ? 'ALL' : 'LOW')}
                  />
                )}
              </svg>

              {/* Center Stat */}
              <div
                style={{
                  position: 'absolute',
                  inset: 0,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexDirection: 'column',
                  pointerEvents: 'none',
                }}
              >
                <span style={{ fontSize: '20px', fontWeight: 800, color: 'var(--color-text-primary)' }}>
                  {hoveredDonut === 'HIGH'
                    ? `${highPct}%`
                    : hoveredDonut === 'MEDIUM'
                    ? `${medPct}%`
                    : hoveredDonut === 'LOW'
                    ? `${lowPct}%`
                    : total}
                </span>
                <span
                  style={{
                    fontSize: '9px',
                    fontWeight: 700,
                    color: 'var(--color-text-muted)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.04em',
                  }}
                >
                  {hoveredDonut ? `${hoveredDonut.toLowerCase()} risk` : 'Total'}
                </span>
              </div>
            </div>

            {/* Legend & Details */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', minWidth: '130px' }}>
              <div
                onClick={() => onFilterChange?.(activeFilter === 'HIGH' ? 'ALL' : 'HIGH')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '6px 8px',
                  borderRadius: '6px',
                  background: activeFilter === 'HIGH' ? 'rgba(248, 113, 113, 0.15)' : 'transparent',
                  cursor: 'pointer',
                }}
              >
                <span style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: '#f87171' }}>
                  <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#f87171' }} />
                  High Risk
                </span>
                <span style={{ fontSize: '12px', fontWeight: 700, color: '#f87171' }}>
                  {highCount} ({highPct}%)
                </span>
              </div>

              <div
                onClick={() => onFilterChange?.(activeFilter === 'MEDIUM' ? 'ALL' : 'MEDIUM')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '6px 8px',
                  borderRadius: '6px',
                  background: activeFilter === 'MEDIUM' ? 'rgba(251, 191, 36, 0.15)' : 'transparent',
                  cursor: 'pointer',
                }}
              >
                <span style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: '#fbbf24' }}>
                  <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#fbbf24' }} />
                  Medium Risk
                </span>
                <span style={{ fontSize: '12px', fontWeight: 700, color: '#fbbf24' }}>
                  {medCount} ({medPct}%)
                </span>
              </div>

              <div
                onClick={() => onFilterChange?.(activeFilter === 'LOW' ? 'ALL' : 'LOW')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '6px 8px',
                  borderRadius: '6px',
                  background: activeFilter === 'LOW' ? 'rgba(52, 211, 153, 0.15)' : 'transparent',
                  cursor: 'pointer',
                }}
              >
                <span style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: '#34d399' }}>
                  <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#34d399' }} />
                  Low Risk
                </span>
                <span style={{ fontSize: '12px', fontWeight: 700, color: '#34d399' }}>
                  {lowCount} ({lowPct}%)
                </span>
              </div>
            </div>
          </div>

          {/* AI Executive Verdict */}
          {summary?.overall_summary && (
            <div
              style={{
                background: 'rgba(15, 19, 32, 0.7)',
                border: '1px solid var(--color-border)',
                borderRadius: '10px',
                padding: '12px 14px',
                fontSize: '12px',
                color: 'var(--color-text-secondary)',
                lineHeight: 1.6,
              }}
            >
              <span style={{ fontWeight: 700, color: 'var(--color-text-primary)' }}>💡 AI Summary: </span>
              {summary.overall_summary}
            </div>
          )}
        </div>

        {/* Right Column: Clause Categories & Risk Breakdown */}
        <div
          className="glass-card"
          style={{
            padding: '22px',
            display: 'flex',
            flexDirection: 'column',
            gap: '14px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <h3
              style={{
                fontSize: '13px',
                fontWeight: 700,
                color: 'var(--color-text-secondary)',
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
              }}
            >
              📑 Domain &amp; Clause Category Breakdown
            </h3>
            <span style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>
              Interactive Category Map
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', overflowY: 'auto', maxHeight: '310px', paddingRight: '4px' }}>
            {Object.entries(CATEGORY_DEFINITIONS).map(([key, def]) => {
              const stats = categoryStats[key] || { total: 0, high: 0, med: 0, low: 0, clauses: [] }
              if (stats.total === 0) return null

              const isCatActive = activeCategory === key
              const catHighPct = (stats.high / stats.total) * 100
              const catMedPct = (stats.med / stats.total) * 100
              const catLowPct = (stats.low / stats.total) * 100

              return (
                <div
                  key={key}
                  onClick={() => setActiveCategory(isCatActive ? null : key)}
                  style={{
                    background: isCatActive ? 'rgba(108, 142, 245, 0.08)' : 'rgba(15, 19, 32, 0.5)',
                    border: `1px solid ${isCatActive ? 'var(--color-accent)' : 'var(--color-border)'}`,
                    borderRadius: '10px',
                    padding: '10px 12px',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                    <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span>{def.icon}</span>
                      <span>{def.label}</span>
                    </span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      {stats.high > 0 && (
                        <span style={{ fontSize: '10px', fontWeight: 700, color: '#f87171', background: 'rgba(248, 113, 113, 0.15)', padding: '2px 6px', borderRadius: '4px' }}>
                          {stats.high} High
                        </span>
                      )}
                      {stats.med > 0 && (
                        <span style={{ fontSize: '10px', fontWeight: 700, color: '#fbbf24', background: 'rgba(251, 191, 36, 0.15)', padding: '2px 6px', borderRadius: '4px' }}>
                          {stats.med} Med
                        </span>
                      )}
                      <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--color-text-muted)' }}>
                        {stats.total} total
                      </span>
                    </div>
                  </div>

                  {/* Multi-segment Bar for Category */}
                  <div
                    style={{
                      height: '6px',
                      borderRadius: '3px',
                      background: 'rgba(255,255,255,0.05)',
                      display: 'flex',
                      overflow: 'hidden',
                    }}
                  >
                    {stats.high > 0 && (
                      <div style={{ width: `${catHighPct}%`, background: '#f87171', height: '100%' }} />
                    )}
                    {stats.med > 0 && (
                      <div style={{ width: `${catMedPct}%`, background: '#fbbf24', height: '100%' }} />
                    )}
                    {stats.low > 0 && (
                      <div style={{ width: `${catLowPct}%`, background: '#34d399', height: '100%' }} />
                    )}
                  </div>

                  {/* Expand list of clauses in this category */}
                  {isCatActive && stats.clauses.length > 0 && (
                    <div style={{ marginTop: '10px', display: 'flex', flexDirection: 'column', gap: '6px', borderTop: '1px solid var(--color-border)', paddingTop: '8px' }}>
                      {stats.clauses.map((c) => (
                        <div
                          key={c.id}
                          onClick={(e) => {
                            e.stopPropagation()
                            onSelectClause?.(c)
                          }}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            padding: '6px 8px',
                            borderRadius: '6px',
                            background: selectedClauseId === c.id ? 'rgba(108, 142, 245, 0.2)' : 'rgba(255,255,255,0.03)',
                            border: `1px solid ${selectedClauseId === c.id ? 'var(--color-accent)' : 'transparent'}`,
                            fontSize: '11.5px',
                            cursor: 'pointer',
                          }}
                        >
                          <span style={{ color: 'var(--color-text-primary)', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '240px' }}>
                            {c.section_title || c.clause_text.slice(0, 45) + '...'}
                          </span>
                          <span
                            className={`badge badge-risk-${c.risk_level.toLowerCase()}`}
                            style={{ fontSize: '9px', padding: '1px 5px' }}
                          >
                            {c.risk_level}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* ── Page-by-Page Risk Heatmap & Density ────────────────────────────── */}
      <div
        className="glass-card"
        style={{
          padding: '20px',
          display: 'flex',
          flexDirection: 'column',
          gap: '14px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
          <div>
            <h3
              style={{
                fontSize: '13px',
                fontWeight: 700,
                color: 'var(--color-text-secondary)',
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
              }}
            >
              🗺️ Document Page Risk Heatmap &amp; Clause Distribution
            </h3>
            <p style={{ fontSize: '11.5px', color: 'var(--color-text-muted)', marginTop: '2px' }}>
              Visual risk distribution along document flow. Click any clause pin to inspect.
            </p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '11px' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#f87171' }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#f87171' }} /> High Risk
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#fbbf24' }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#fbbf24' }} /> Medium
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#34d399' }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#34d399' }} /> Low
            </span>
          </div>
        </div>

        {/* Heatmap Page Blocks */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: `repeat(auto-fit, minmax(${pageStats.length > 4 ? '160px' : '220px'}, 1fr))`,
            gap: '12px',
          }}
        >
          {pageStats.map((page) => {
            const hasHigh = page.high > 0
            const hasMed = page.med > 0
            const borderColor = hasHigh
              ? 'rgba(248, 113, 113, 0.4)'
              : hasMed
              ? 'rgba(251, 191, 36, 0.4)'
              : 'rgba(52, 211, 153, 0.3)'

            return (
              <div
                key={page.pageNum}
                style={{
                  background: 'rgba(15, 19, 32, 0.6)',
                  border: `1px solid ${borderColor}`,
                  borderRadius: '10px',
                  padding: '12px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--color-accent-light)' }}>
                    📄 Page {page.pageNum}
                  </span>
                  <span style={{ fontSize: '10px', color: 'var(--color-text-muted)', fontWeight: 600 }}>
                    {page.clauses.length} clause{page.clauses.length !== 1 ? 's' : ''}
                  </span>
                </div>

                {/* Clauses Pills inside Page */}
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px' }}>
                  {page.clauses.length > 0 ? (
                    page.clauses.map((c) => (
                      <button
                        key={c.id}
                        type="button"
                        onClick={() => onSelectClause?.(c)}
                        title={`${c.section_title || 'Clause'}: ${c.risk_level} risk\n${c.explanation.slice(0, 100)}...`}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px',
                          padding: '3px 7px',
                          borderRadius: '6px',
                          fontSize: '10.5px',
                          fontWeight: 600,
                          cursor: 'pointer',
                          border: selectedClauseId === c.id ? '1px solid #ffffff' : 'none',
                          background:
                            c.risk_level === 'HIGH'
                              ? 'rgba(248, 113, 113, 0.25)'
                              : c.risk_level === 'MEDIUM'
                              ? 'rgba(251, 191, 36, 0.25)'
                              : 'rgba(52, 211, 153, 0.2)',
                          color:
                            c.risk_level === 'HIGH'
                              ? '#fca5a5'
                              : c.risk_level === 'MEDIUM'
                              ? '#fde68a'
                              : '#a7f3d0',
                          transition: 'transform 0.15s ease',
                        }}
                      >
                        <span
                          style={{
                            width: '6px',
                            height: '6px',
                            borderRadius: '50%',
                            background:
                              c.risk_level === 'HIGH'
                                ? '#f87171'
                                : c.risk_level === 'MEDIUM'
                                ? '#fbbf24'
                                : '#34d399',
                          }}
                        />
                        <span>{c.section_title ? c.section_title.slice(0, 14) : `§ ${c.id.slice(0, 4)}`}</span>
                      </button>
                    ))
                  ) : (
                    <span style={{ fontSize: '11px', color: 'var(--color-text-muted)', fontStyle: 'italic' }}>
                      Introductory / General Text
                    </span>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
