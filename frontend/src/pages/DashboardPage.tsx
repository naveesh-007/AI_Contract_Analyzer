import { useEffect, useState, useCallback } from 'react'
import { useSearchParams, Link, useNavigate } from 'react-router-dom'
import {
  listDocuments,
  getDocument,
  getDocumentText,
  getDocumentSummary,
  getDocumentClauses,
  downloadDocumentReport,
} from '../services/api'
import { DocumentVisualizer } from '../components/DocumentVisualizer'
import { LoadingState } from '../components/LoadingState'
import { ErrorMessage } from '../components/ErrorMessage'
import type { Document, DocumentPage } from '../types/document'
import type { AnalysisSummary, Clause, RiskFilter } from '../types/clause'

export function DashboardPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const queryDocId = searchParams.get('doc')

  // Document list
  const [documents, setDocuments] = useState<Document[]>([])
  const [selectedDocId, setSelectedDocId] = useState<string | null>(queryDocId)

  // Selected document data
  const [doc, setDoc] = useState<Document | null>(null)
  const [pages, setPages] = useState<DocumentPage[]>([])
  const [summary, setSummary] = useState<AnalysisSummary | null>(null)
  const [clauses, setClauses] = useState<Clause[]>([])
  const [selectedClause, setSelectedClause] = useState<Clause | null>(null)

  // UI & Loading state
  const [activeFilter, setActiveFilter] = useState<RiskFilter>('ALL')
  const [loadingList, setLoadingList] = useState(true)
  const [loadingDoc, setLoadingDoc] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // ── 1. Fetch List of Uploaded Documents ─────────────────────────────────────
  useEffect(() => {
    async function fetchDocs() {
      setLoadingList(true)
      try {
        const docs = await listDocuments(50)
        setDocuments(docs)
        if (docs.length > 0) {
          const initialId = queryDocId && docs.some((d) => d.id === queryDocId) ? queryDocId : docs[0].id
          setSelectedDocId(initialId)
        }
      } catch (e: any) {
        console.error('Failed to load documents list:', e)
        setError(e?.response?.data?.detail || 'Failed to fetch document catalog.')
      } finally {
        setLoadingList(false)
      }
    }
    fetchDocs()
  }, [queryDocId])

  // ── 2. Load Selected Document Data & Visualizations ─────────────────────────
  const loadDocDetails = useCallback(async (id: string) => {
    setLoadingDoc(true)
    setError(null)
    try {
      const [docData, textData, summaryData, clausesData] = await Promise.all([
        getDocument(id),
        getDocumentText(id).catch(() => ({ document_id: id, total_pages: 1, pages: [] })),
        getDocumentSummary(id).catch(() => null),
        getDocumentClauses(id, { page_size: 100 }).catch(() => ({ items: [], total: 0, page: 1, page_size: 100, total_pages: 1 })),
      ])

      setDoc(docData)
      setPages(textData.pages || [])
      setSummary(summaryData)
      setClauses(clausesData.items || [])
      if (clausesData.items.length > 0) {
        const highRisk = clausesData.items.find((c) => c.risk_level === 'HIGH')
        setSelectedClause(highRisk || clausesData.items[0])
      } else {
        setSelectedClause(null)
      }
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to load details for the selected document.')
    } finally {
      setLoadingDoc(false)
    }
  }, [])

  useEffect(() => {
    if (selectedDocId) {
      loadDocDetails(selectedDocId)
    }
  }, [selectedDocId, loadDocDetails])

  const handleSelectDocument = (id: string) => {
    setSelectedDocId(id)
    setSearchParams({ doc: id })
  }

  // ── 3. Empty State: No Documents in System ──────────────────────────────────
  if (!loadingList && documents.length === 0) {
    return (
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: 'calc(100vh - 64px)',
          gap: '24px',
          padding: '48px 24px',
          textAlign: 'center',
          maxWidth: '600px',
          margin: '0 auto',
        }}
      >
        <div
          style={{
            width: '80px',
            height: '80px',
            borderRadius: '24px',
            background: 'linear-gradient(135deg, rgba(108,142,245,0.15), rgba(167,139,250,0.15))',
            border: '1px solid rgba(108,142,245,0.3)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '40px',
            boxShadow: '0 8px 32px rgba(108,142,245,0.2)',
          }}
        >
          📊
        </div>
        <div>
          <h1
            style={{
              fontSize: '26px',
              fontWeight: 800,
              color: 'var(--color-text-primary)',
              marginBottom: '10px',
            }}
          >
            No Documents In Dashboard
          </h1>
          <p
            style={{
              fontSize: '14px',
              color: 'var(--color-text-secondary)',
              lineHeight: 1.6,
            }}
          >
            Upload your first contract or legal document. Once uploaded, the dashboard will automatically generate interactive risk charts, health gauges, and page-by-page clause analytics.
          </p>
        </div>

        <Link to="/" className="btn-primary" id="upload-first-btn" style={{ padding: '14px 28px', fontSize: '15px' }}>
          ⬆️ Upload a Document Now
        </Link>
      </div>
    )
  }

  // ── 4. Main Dashboard UI ───────────────────────────────────────────────────
  return (
    <div
      style={{
        padding: '28px 32px',
        maxWidth: '1360px',
        margin: '0 auto',
        display: 'flex',
        flexDirection: 'column',
        gap: '24px',
      }}
    >
      {/* Dashboard Top Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '16px',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
            <h1
              style={{
                fontSize: '24px',
                fontWeight: 800,
                color: 'var(--color-text-primary)',
                letterSpacing: '-0.02em',
                margin: 0,
              }}
            >
              Document Intelligence Dashboard
            </h1>
            <span
              style={{
                fontSize: '11px',
                fontWeight: 700,
                padding: '3px 10px',
                borderRadius: '12px',
                background: 'rgba(108, 142, 245, 0.15)',
                color: 'var(--color-accent-light)',
                border: '1px solid rgba(108, 142, 245, 0.3)',
              }}
            >
              {documents.length} Contract{documents.length !== 1 ? 's' : ''} Analyzed
            </span>
          </div>
          <p style={{ fontSize: '13px', color: 'var(--color-text-muted)' }}>
            Real-time AI contract risk visualization, domain breakdown, and page distribution analytics.
          </p>
        </div>

        {/* Global Action Buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {selectedDocId && (
            <button
              type="button"
              onClick={() => downloadDocumentReport(selectedDocId, doc?.filename || 'Report.pdf')}
              className="btn-secondary"
              style={{ padding: '10px 16px', fontSize: '13px' }}
              title="Download PDF Executive Report"
            >
              📥 Download Report
            </button>
          )}

          {selectedDocId && (
            <button
              type="button"
              onClick={() => navigate(`/documents/${selectedDocId}`)}
              className="btn-primary"
              style={{ padding: '10px 18px', fontSize: '13px' }}
            >
              🔍 Open Interactive Inspector
            </button>
          )}

          <Link to="/" className="btn-secondary" style={{ padding: '10px 16px', fontSize: '13px' }}>
            ⬆️ Upload New
          </Link>
        </div>
      </div>

      {/* Error display if any */}
      {error && <ErrorMessage message={error} onDismiss={() => setError(null)} />}

      {/* ── Document Selector Carousel / Strip ───────────────────────────────── */}
      {documents.length > 0 && (
        <div
          className="glass-card"
          style={{
            padding: '16px 20px',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span
              style={{
                fontSize: '11.5px',
                fontWeight: 700,
                color: 'var(--color-text-secondary)',
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
              }}
            >
              📂 Select Contract To Visualize
            </span>
            <span style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>
              Click any document to load its full visual telemetry
            </span>
          </div>

          <div
            style={{
              display: 'flex',
              gap: '12px',
              overflowX: 'auto',
              paddingBottom: '6px',
            }}
          >
            {documents.map((d) => {
              const isSelected = d.id === selectedDocId
              return (
                <button
                  key={d.id}
                  type="button"
                  onClick={() => handleSelectDocument(d.id)}
                  style={{
                    flexShrink: 0,
                    minWidth: '220px',
                    maxWidth: '300px',
                    padding: '12px 14px',
                    borderRadius: '12px',
                    textAlign: 'left',
                    background: isSelected
                      ? 'linear-gradient(135deg, rgba(108,142,245,0.18) 0%, rgba(167,139,250,0.12) 100%)'
                      : 'rgba(15, 19, 32, 0.6)',
                    border: isSelected
                      ? '1px solid var(--color-accent)'
                      : '1px solid var(--color-border)',
                    boxShadow: isSelected ? '0 0 16px rgba(108,142,245,0.25)' : 'none',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                    <span
                      style={{
                        fontSize: '10px',
                        fontWeight: 700,
                        padding: '2px 6px',
                        borderRadius: '6px',
                        background: 'rgba(255,255,255,0.06)',
                        color: 'var(--color-text-secondary)',
                        textTransform: 'uppercase',
                      }}
                    >
                      {d.document_type || 'Contract'}
                    </span>
                    <span className={`badge badge-${d.status.toLowerCase()}`} style={{ fontSize: '9px', padding: '1px 5px' }}>
                      {d.status}
                    </span>
                  </div>
                  <p
                    style={{
                      fontSize: '13px',
                      fontWeight: 700,
                      color: isSelected ? 'var(--color-accent-light)' : 'var(--color-text-primary)',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      marginBottom: '4px',
                    }}
                  >
                    {d.filename}
                  </p>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '11px', color: 'var(--color-text-muted)' }}>
                    <span>{(d.file_size / 1024).toFixed(1)} KB</span>
                    <span>{new Date(d.created_at).toLocaleDateString()}</span>
                  </div>
                </button>
              )
            })}
          </div>
        </div>
      )}

      {/* ── Document Visualization Component ─────────────────────────────────── */}
      {loadingDoc ? (
        <div style={{ padding: '64px', display: 'flex', justifyContent: 'center' }}>
          <LoadingState message="Generating document visual analytics..." />
        </div>
      ) : (
        <DocumentVisualizer
          document={doc}
          summary={summary}
          clauses={clauses}
          pages={pages}
          selectedClauseId={selectedClause?.id || null}
          onSelectClause={(c) => {
            setSelectedClause(c)
            if (selectedDocId) {
              navigate(`/documents/${selectedDocId}`)
            }
          }}
          activeFilter={activeFilter}
          onFilterChange={setActiveFilter}
        />
      )}
    </div>
  )
}
