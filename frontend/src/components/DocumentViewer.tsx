import { useEffect, useRef, useState, useMemo } from 'react'
import type { DocumentPage } from '../types/document'
import type { Clause } from '../types/clause'

interface DocumentViewerProps {
  filename: string
  fileType: string
  pages: DocumentPage[]
  clauses: Clause[]
  selectedClause: Clause | null
  onSelectClause: (clause: Clause) => void
}

export function DocumentViewer({
  filename,
  fileType,
  pages,
  clauses,
  selectedClause,
  onSelectClause,
}: DocumentViewerProps) {
  const [currentPageNum, setCurrentPageNum] = useState<number>(1)
  const [zoomLevel, setZoomLevel] = useState<number>(100)
  const activeHighlightRef = useRef<HTMLSpanElement | null>(null)
  const scrollContainerRef = useRef<HTMLDivElement | null>(null)

  const totalPages = pages.length > 0 ? Math.max(...pages.map((p) => p.page_number)) : 1

  // Automatically switch page and scroll when selected clause changes
  useEffect(() => {
    if (selectedClause && selectedClause.page_number) {
      setCurrentPageNum(selectedClause.page_number)
    }
  }, [selectedClause])

  // Smooth scroll into view when active highlight renders
  useEffect(() => {
    if (activeHighlightRef.current) {
      activeHighlightRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
      })
    }
  }, [selectedClause, currentPageNum])

  const currentPage = useMemo(() => {
    return pages.find((p) => p.page_number === currentPageNum) || pages[0]
  }, [pages, currentPageNum])

  // Clauses that reside on the current page
  const pageClauses = useMemo(() => {
    return clauses.filter((c) => (c.page_number || 1) === currentPageNum)
  }, [clauses, currentPageNum])

  // Render text with interactive clause highlights
  const renderedContent = useMemo(() => {
    if (!currentPage || !currentPage.text) {
      return (
        <div style={{ color: 'var(--color-text-muted)', fontStyle: 'italic', padding: '24px' }}>
          No text content extracted for Page {currentPageNum}.
        </div>
      )
    }

    const text = currentPage.text

    // If there are no clauses on this page, render plain text with optional viewer search
    if (pageClauses.length === 0) {
      return (
        <div
          style={{
            whiteSpace: 'pre-wrap',
            lineHeight: 1.8,
            fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
            fontSize: `${13 * (zoomLevel / 100)}px`,
            color: 'var(--color-text-primary)',
          }}
        >
          {text}
        </div>
      )
    }

    // Identify clause positions within current page text
    interface TextSegment {
      text: string
      clause?: Clause
      isActive?: boolean
      isMatch?: boolean
    }

    // Find occurrences of clause_text or character ranges in page text
    const segments: { start: number; end: number; clause: Clause }[] = []

    for (const clause of pageClauses) {
      if (!clause.clause_text) continue
      const needle = clause.clause_text.trim()
      if (needle.length < 5) continue

      let idx = text.indexOf(needle)
      if (idx !== -1) {
        segments.push({
          start: idx,
          end: idx + needle.length,
          clause,
        })
      } else {
        // Try matching first 60 chars
        const shortNeedle = needle.slice(0, 60)
        idx = text.indexOf(shortNeedle)
        if (idx !== -1) {
          segments.push({
            start: idx,
            end: Math.min(idx + needle.length, text.length),
            clause,
          })
        }
      }
    }

    // Sort segments by start position
    segments.sort((a, b) => a.start - b.start)

    // Merge non-overlapping slices
    const nonOverlapping: TextSegment[] = []
    let cursor = 0

    for (const seg of segments) {
      if (seg.start > cursor) {
        nonOverlapping.push({
          text: text.substring(cursor, seg.start),
        })
      }

      if (seg.start >= cursor) {
        const isSelected = selectedClause?.id === seg.clause.id
        nonOverlapping.push({
          text: text.substring(seg.start, seg.end),
          clause: seg.clause,
          isActive: isSelected,
        })
        cursor = seg.end
      }
    }

    if (cursor < text.length) {
      nonOverlapping.push({
        text: text.substring(cursor),
      })
    }

    return (
      <div
        style={{
          whiteSpace: 'pre-wrap',
          lineHeight: 1.8,
          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
          fontSize: `${13 * (zoomLevel / 100)}px`,
          color: 'var(--color-text-primary)',
        }}
      >
        {nonOverlapping.map((seg, i) => {
          if (!seg.clause) {
            return <span key={i}>{seg.text}</span>
          }

          const risk = seg.clause.risk_level.toUpperCase()
          const isHigh = risk === 'HIGH'
          const isMed = risk === 'MEDIUM'
          const isLow = risk === 'LOW'

          let highlightClass = 'clause-highlight '
          if (seg.isActive) {
            highlightClass += 'clause-highlight-active'
          } else if (isHigh) {
            highlightClass += 'clause-highlight-high'
          } else if (isMed) {
            highlightClass += 'clause-highlight-medium'
          } else if (isLow) {
            highlightClass += 'clause-highlight-low'
          }

          return (
            <span
              key={i}
              ref={seg.isActive ? activeHighlightRef : null}
              className={highlightClass}
              onClick={() => onSelectClause(seg.clause!)}
              title={`Click to view ${seg.clause.risk_level} risk explanation`}
              style={{
                display: 'inline',
                borderRadius: '3px',
                padding: '2px 3px',
              }}
            >
              {seg.text}
            </span>
          )
        })}
      </div>
    )
  }, [currentPage, pageClauses, selectedClause, zoomLevel, currentPageNum, onSelectClause])

  return (
    <div
      className="glass-card"
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        overflow: 'hidden',
        background: 'var(--color-bg-secondary)',
      }}
    >
      {/* Viewer Toolbar */}
      <div
        style={{
          padding: '12px 16px',
          borderBottom: '1px solid var(--color-border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px',
          background: 'var(--color-bg-card)',
        }}
      >
        {/* Document Name & Type */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '18px' }}>
            {fileType.toLowerCase() === 'pdf' ? '📑' : '📄'}
          </span>
          <div>
            <p
              style={{
                fontSize: '13px',
                fontWeight: 700,
                color: 'var(--color-text-primary)',
                margin: 0,
                maxWidth: '220px',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
              title={filename}
            >
              {filename}
            </p>
            <span
              style={{
                fontSize: '11px',
                color: 'var(--color-text-muted)',
                textTransform: 'uppercase',
                fontWeight: 600,
              }}
            >
              {fileType.toUpperCase()} Document
            </span>
          </div>
        </div>

        {/* Page Navigation */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            background: 'var(--color-bg-secondary)',
            padding: '4px 10px',
            borderRadius: '8px',
            border: '1px solid var(--color-border)',
          }}
        >
          <button
            type="button"
            disabled={currentPageNum <= 1}
            onClick={() => setCurrentPageNum((p) => Math.max(1, p - 1))}
            style={{
              background: 'transparent',
              border: 'none',
              color: currentPageNum <= 1 ? 'var(--color-text-muted)' : 'var(--color-text-primary)',
              cursor: currentPageNum <= 1 ? 'not-allowed' : 'pointer',
              fontWeight: 700,
              fontSize: '14px',
              padding: '0 4px',
            }}
            title="Previous page"
          >
            ‹
          </button>
          <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-primary)' }}>
            Page {currentPageNum} of {totalPages}
          </span>
          <button
            type="button"
            disabled={currentPageNum >= totalPages}
            onClick={() => setCurrentPageNum((p) => Math.min(totalPages, p + 1))}
            style={{
              background: 'transparent',
              border: 'none',
              color:
                currentPageNum >= totalPages
                  ? 'var(--color-text-muted)'
                  : 'var(--color-text-primary)',
              cursor: currentPageNum >= totalPages ? 'not-allowed' : 'pointer',
              fontWeight: 700,
              fontSize: '14px',
              padding: '0 4px',
            }}
            title="Next page"
          >
            ›
          </button>
        </div>

        {/* Zoom Controls */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            background: 'var(--color-bg-secondary)',
            padding: '4px 8px',
            borderRadius: '8px',
            border: '1px solid var(--color-border)',
          }}
        >
          <button
            type="button"
            onClick={() => setZoomLevel((z) => Math.max(70, z - 10))}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--color-text-primary)',
              cursor: 'pointer',
              fontWeight: 700,
              fontSize: '14px',
              padding: '0 4px',
            }}
            title="Zoom out"
          >
            -
          </button>
          <span
            style={{
              fontSize: '11px',
              fontWeight: 600,
              color: 'var(--color-text-secondary)',
              minWidth: '38px',
              textAlign: 'center',
            }}
          >
            {zoomLevel}%
          </span>
          <button
            type="button"
            onClick={() => setZoomLevel((z) => Math.min(150, z + 10))}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--color-text-primary)',
              cursor: 'pointer',
              fontWeight: 700,
              fontSize: '14px',
              padding: '0 4px',
            }}
            title="Zoom in"
          >
            +
          </button>
        </div>
      </div>

      {/* Document Text Paper Content */}
      <div
        ref={scrollContainerRef}
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '28px',
          background: 'var(--color-bg-primary)',
        }}
      >
        <div
          style={{
            maxWidth: '800px',
            margin: '0 auto',
            background: 'var(--color-bg-secondary)',
            padding: '36px',
            borderRadius: '12px',
            border: '1px solid var(--color-border)',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
            minHeight: '100%',
          }}
        >
          {renderedContent}
        </div>
      </div>
    </div>
  )
}
