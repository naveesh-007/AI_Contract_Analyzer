import { useEffect, useState, useCallback } from 'react'
import { useParams, useSearchParams, Link } from 'react-router-dom'
import {
  getDocument,
  getDocumentText,
  getDocumentSummary,
  getDocumentClauses,
  analyzeDocument,
  downloadDocumentReport,
} from '../services/api'

import { RiskSummary } from '../components/RiskSummary'
import { ClauseList } from '../components/ClauseList'
import { ClauseDetail } from '../components/ClauseDetail'
import { DocumentViewer } from '../components/DocumentViewer'
import { ContractChatPanel } from '../components/ContractChatPanel'
import { LegalDisclaimer } from '../components/LegalDisclaimer'
import { LoadingState } from '../components/LoadingState'
import { ErrorMessage } from '../components/ErrorMessage'
import type { Document, DocumentPage } from '../types/document'
import type { AnalysisSummary, Clause, RiskFilter } from '../types/clause'

export function DocumentAnalysisPage() {
  const { documentId: paramDocId } = useParams<{ documentId: string }>()
  const [searchParams] = useSearchParams()

  const docId = paramDocId || searchParams.get('doc')

  // Document metadata and text pages
  const [doc, setDoc] = useState<Document | null>(null)
  const [pages, setPages] = useState<DocumentPage[]>([])

  // AI Analysis & Clauses
  const [summary, setSummary] = useState<AnalysisSummary | null>(null)
  const [clauses, setClauses] = useState<Clause[]>([])
  const [selectedClause, setSelectedClause] = useState<Clause | null>(null)

  // Filtering and Search
  const [activeFilter, setActiveFilter] = useState<RiskFilter>('ALL')
  const [searchQuery, setSearchQuery] = useState<string>('')

  // Column 3 tab switcher: 'chat' | 'detail'
  const [rightTab, setRightTab] = useState<'chat' | 'detail'>('chat')

  // Mobile active tab: 'clauses' | 'viewer' | 'detail' | 'chat'
  const [mobileTab, setMobileTab] = useState<'clauses' | 'viewer' | 'detail' | 'chat'>('clauses')

  // Processing & Loading States
  const [loading, setLoading] = useState<boolean>(true)
  const [analyzing, setAnalyzing] = useState<boolean>(false)
  const [analysisStep, setAnalysisStep] = useState<string>('Loading document data...')
  const [error, setError] = useState<string | null>(null)
  const [notFound, setNotFound] = useState<boolean>(false)

  // ─── Fetch Document & Analysis ──────────────────────────────────────────────

  const loadDocumentData = useCallback(async (id: string) => {
    setLoading(true)
    setError(null)
    setNotFound(false)

    try {
      // 1. Fetch document metadata & extracted text
      setAnalysisStep('Loading document pages...')
      const [docData, textData] = await Promise.all([
        getDocument(id),
        getDocumentText(id),
      ])

      setDoc(docData)
      setPages(textData.pages || [])

      // 2. Fetch or trigger AI Analysis
      try {
        setAnalysisStep('Loading risk assessment...')
        const [summaryData, clausesData] = await Promise.all([
          getDocumentSummary(id),
          getDocumentClauses(id, { page_size: 100 }),
        ])

        setSummary(summaryData)
        setClauses(clausesData.items || [])
        if (clausesData.items.length > 0) {
          const highRisk = clausesData.items.find((c) => c.risk_level === 'HIGH')
          setSelectedClause(highRisk || clausesData.items[0])
        }
      } catch (analysisErr: any) {
        if (analysisErr?.response?.status === 404 || docData.status !== 'ANALYZED') {
          await triggerAnalysis(id)
        } else {
          console.warn('Analysis summary not ready:', analysisErr)
        }
      }
    } catch (err: any) {
      if (err?.response?.status === 404) {
        setNotFound(true)
      } else {
        const msg = err?.response?.data?.detail || 'Failed to load document.'
        setError(msg)
      }
    } finally {
      setLoading(false)
    }
  }, [])

  // ─── Trigger AI Analysis ───────────────────────────────────────────────────

  const triggerAnalysis = async (id: string) => {
    setAnalyzing(true)
    setError(null)

    try {
      setAnalysisStep('Extracting contractual provisions...')
      await new Promise((r) => setTimeout(r, 600))

      setAnalysisStep('AI analyzing risk levels and simplifying clauses...')
      const analysisResult = await analyzeDocument(id)

      setSummary(analysisResult.summary)
      setClauses(analysisResult.clauses)
      if (analysisResult.clauses.length > 0) {
        const highRisk = analysisResult.clauses.find((c) => c.risk_level === 'HIGH')
        setSelectedClause(highRisk || analysisResult.clauses[0])
      }
    } catch (err: any) {
      const msg = err?.response?.data?.detail || 'AI Analysis failed. Please try again.'
      setError(msg)
    } finally {
      setAnalyzing(false)
    }
  }

  useEffect(() => {
    if (docId) {
      loadDocumentData(docId)
    } else {
      setLoading(false)
    }
  }, [docId, loadDocumentData])

  // Clause selection handler
  const handleSelectClause = (clause: Clause) => {
    setSelectedClause(clause)
    if (window.innerWidth < 1024) {
      setMobileTab('viewer')
    }
  }

  // ─── Empty state (No Document ID) ──────────────────────────────────────────

  if (!docId) {
    return (
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: 'calc(100vh - 64px)',
          gap: '20px',
          padding: '48px',
          textAlign: 'center',
        }}
      >
        <div style={{ fontSize: '56px' }}>⚖️</div>
        <h1 style={{ fontSize: '24px', fontWeight: 700, color: 'var(--color-text-primary)' }}>
          No Document Selected
        </h1>
        <p style={{ fontSize: '14px', color: 'var(--color-text-secondary)', maxWidth: '440px' }}>
          Please upload a contract or legal document to view its AI risk assessment and simplified clause breakdown.
        </p>
        <Link to="/" className="btn-primary" id="upload-first-btn">
          ⬆️ Upload a Document
        </Link>
      </div>
    )
  }

  // ─── 404 Not Found State ───────────────────────────────────────────────────

  if (notFound) {
    return (
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: 'calc(100vh - 64px)',
          gap: '16px',
          padding: '48px',
          textAlign: 'center',
        }}
      >
        <div style={{ fontSize: '56px' }}>🔍</div>
        <h1 style={{ fontSize: '24px', fontWeight: 800, color: 'var(--color-text-primary)' }}>
          Document Not Found
        </h1>
        <p style={{ fontSize: '14px', color: 'var(--color-text-secondary)', maxWidth: '440px' }}>
          The requested document (ID: <code style={{ color: 'var(--color-accent)' }}>{docId}</code>) could not be located in the database.
        </p>
        <div style={{ display: 'flex', gap: '12px', marginTop: '12px' }}>
          <button
            type="button"
            onClick={() => loadDocumentData(docId)}
            className="btn-secondary"
          >
            🔄 Retry
          </button>
          <Link to="/" className="btn-primary">
            ⬆️ Upload New
          </Link>
        </div>
      </div>
    )
  }

  // ─── Loading / Analyzing State ─────────────────────────────────────────────

  if (loading || analyzing) {
    return (
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: 'calc(100vh - 64px)',
          gap: '24px',
          padding: '48px',
        }}
      >
        <LoadingState message={analysisStep} />
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            fontSize: '12px',
            color: 'var(--color-text-muted)',
          }}
        >
          <span className="badge badge-processing">Real-time Processing</span>
          <span>Do not refresh the page</span>
        </div>
      </div>
    )
  }

  // ─── Main Professional Dashboard ───────────────────────────────────────────

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: 'calc(100vh - 64px)',
        overflow: 'hidden',
        background: 'var(--color-bg-primary)',
      }}
    >
      {/* Top Header Bar */}
      <header
        style={{
          padding: '12px 24px',
          borderBottom: '1px solid var(--color-border)',
          background: 'var(--color-bg-secondary)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px',
          flexShrink: 0,
        }}
      >
        {/* Document Title & Type */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Link
            to="/"
            style={{
              color: 'var(--color-text-secondary)',
              textDecoration: 'none',
              fontSize: '13px',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            ← Back
          </Link>
          <div style={{ width: '1px', height: '20px', background: 'var(--color-border)' }} />
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h1
                style={{
                  fontSize: '16px',
                  fontWeight: 800,
                  color: 'var(--color-text-primary)',
                  margin: 0,
                }}
              >
                {doc?.filename || 'Document Analysis'}
              </h1>
              <span className="badge badge-uploaded">
                {doc?.document_type || 'Contract'}
              </span>
              <span className="badge badge-analyzed">
                {doc?.status || 'ANALYZED'}
              </span>
            </div>
          </div>
        </div>

        {/* Actions, Report Download & Re-Analyze */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            type="button"
            id="download-report-btn"
            onClick={() => downloadDocumentReport(docId, doc?.filename || 'Report.pdf')}
            className="btn-secondary"
            style={{ padding: '8px 14px', fontSize: '12px', background: 'rgba(59, 130, 246, 0.12)', border: '1px solid rgba(59, 130, 246, 0.3)', color: 'var(--color-accent-light)' }}
            title="Download Executive PDF Risk Report"
          >
            📥 Download Report
          </button>

          <button
            type="button"
            onClick={() => triggerAnalysis(docId)}
            className="btn-secondary"
            style={{ padding: '8px 14px', fontSize: '12px' }}
            title="Re-run AI clause extraction and risk analysis"
          >
            🤖 Re-Analyze Document
          </button>

          <Link
            to="/"
            className="btn-primary"
            style={{ padding: '8px 16px', fontSize: '12px' }}
          >
            ⬆️ Upload Another
          </Link>
        </div>

      </header>

      {/* Global Error Banner if any */}
      {error && (
        <div style={{ padding: '8px 24px', background: 'rgba(248, 113, 113, 0.1)' }}>
          <ErrorMessage message={error} onDismiss={() => setError(null)} />
        </div>
      )}

      {/* Mobile Tab Switcher (<1024px) */}
      <div
        className="mobile-tab-bar"
        style={{
          display: 'none',
          background: 'var(--color-bg-secondary)',
          borderBottom: '1px solid var(--color-border)',
          padding: '6px 12px',
          gap: '8px',
        }}
      >
        <button
          type="button"
          onClick={() => setMobileTab('clauses')}
          className={`btn-secondary ${mobileTab === 'clauses' ? 'active' : ''}`}
          style={{ flex: 1, padding: '8px', fontSize: '11px' }}
        >
          📋 Clauses ({clauses.length})
        </button>
        <button
          type="button"
          onClick={() => setMobileTab('viewer')}
          className={`btn-secondary ${mobileTab === 'viewer' ? 'active' : ''}`}
          style={{ flex: 1, padding: '8px', fontSize: '11px' }}
        >
          📑 Document Viewer
        </button>
        <button
          type="button"
          onClick={() => {
            setMobileTab('chat')
            setRightTab('chat')
          }}
          className={`btn-secondary ${mobileTab === 'chat' ? 'active' : ''}`}
          style={{ flex: 1, padding: '8px', fontSize: '11px' }}
        >
          💬 Ask AI
        </button>
        <button
          type="button"
          onClick={() => {
            setMobileTab('detail')
            setRightTab('detail')
          }}
          className={`btn-secondary ${mobileTab === 'detail' ? 'active' : ''}`}
          style={{ flex: 1, padding: '8px', fontSize: '11px' }}
        >
          💡 Detail
        </button>
      </div>

      {/* Main 3-Column Responsive Work Area */}
      <main
        style={{
          flex: 1,
          display: 'grid',
          gridTemplateColumns: '320px 1fr 380px',
          gap: '16px',
          padding: '16px 20px',
          overflow: 'hidden',
          minHeight: 0,
        }}
        className="analysis-grid-container"
      >
        {/* ─── COLUMN 1 (LEFT): Risk Summary + Filterable Clause List ────── */}
        <section
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
            height: '100%',
            overflow: 'hidden',
          }}
          className={`column-clauses ${mobileTab !== 'clauses' ? 'mobile-hidden' : ''}`}
        >
          {summary && (
            <RiskSummary
              summary={summary}
              activeFilter={activeFilter}
              onFilterChange={setActiveFilter}
            />
          )}

          <div
            className="glass-card"
            style={{
              flex: 1,
              padding: '16px',
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
            }}
          >
            <ClauseList
              clauses={clauses}
              selectedClauseId={selectedClause?.id || null}
              onSelectClause={handleSelectClause}
              activeFilter={activeFilter}
              onFilterChange={setActiveFilter}
              searchQuery={searchQuery}
              onSearchChange={setSearchQuery}
            />
          </div>
        </section>

        {/* ─── COLUMN 2 (CENTER): Original Document Viewer with Highlights ─ */}
        <section
          style={{
            height: '100%',
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
          }}
          className={`column-viewer ${mobileTab !== 'viewer' ? 'mobile-hidden' : ''}`}
        >
          <DocumentViewer
            filename={doc?.filename || 'Document'}
            fileType={doc?.file_type || 'txt'}
            pages={pages}
            clauses={clauses}
            selectedClause={selectedClause}
            onSelectClause={handleSelectClause}
          />
        </section>

        {/* ─── COLUMN 3 (RIGHT): Tabbed Ask AI Chat + Clause Breakdown ────── */}
        <section
          style={{
            height: '100%',
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
          }}
          className={`column-detail ${mobileTab !== 'detail' && mobileTab !== 'chat' ? 'mobile-hidden' : ''}`}
        >
          {/* Header Mode Switcher Tabs */}
          <div
            style={{
              display: 'flex',
              background: 'var(--color-bg-secondary)',
              padding: '4px',
              borderRadius: '10px',
              border: '1px solid var(--color-border)',
              flexShrink: 0,
            }}
          >
            <button
              type="button"
              id="tab-ask-contract-btn"
              onClick={() => setRightTab('chat')}
              style={{
                flex: 1,
                padding: '8px 12px',
                borderRadius: '8px',
                border: 'none',
                background: rightTab === 'chat' ? 'var(--color-accent)' : 'transparent',
                color: rightTab === 'chat' ? '#ffffff' : 'var(--color-text-secondary)',
                fontWeight: 700,
                fontSize: '12px',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              💬 Ask this Contract
            </button>
            <button
              type="button"
              id="tab-clause-detail-btn"
              onClick={() => setRightTab('detail')}
              style={{
                flex: 1,
                padding: '8px 12px',
                borderRadius: '8px',
                border: 'none',
                background: rightTab === 'detail' ? 'var(--color-accent)' : 'transparent',
                color: rightTab === 'detail' ? '#ffffff' : 'var(--color-text-secondary)',
                fontWeight: 700,
                fontSize: '12px',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              💡 Clause Analysis
            </button>
          </div>

          <div style={{ flex: 1, overflow: 'hidden' }}>
            {rightTab === 'chat' ? (
              <ContractChatPanel
                documentId={docId}
                clauses={clauses}
                onSelectClause={handleSelectClause}
              />
            ) : (
              <div
                style={{
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px',
                  overflow: 'hidden',
                }}
              >
                <div style={{ flex: 1, overflow: 'hidden' }}>
                  <ClauseDetail
                    clause={selectedClause}
                    onNavigateToClause={(c) => {
                      setSelectedClause(c)
                      if (window.innerWidth < 1024) setMobileTab('viewer')
                    }}
                  />
                </div>
                <LegalDisclaimer />
              </div>
            )}
          </div>
        </section>
      </main>
    </div>
  )
}
