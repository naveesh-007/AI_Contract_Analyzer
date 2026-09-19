import { useEffect, useState } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { getDocument, getDocumentText } from '../services/api'
import { LoadingState } from '../components/LoadingState'
import { ErrorMessage } from '../components/ErrorMessage'
import type { Document, DocumentTextResponse } from '../types/document'

/**
 * Dashboard Page — route: /dashboard
 *
 * Phase 1: Shows the processed document metadata and extracted text.
 * Phase 2 will add AI analysis, risk scoring, and clause extraction.
 */
export function DashboardPage() {
  const [searchParams] = useSearchParams()
  const docId = searchParams.get('doc')

  const [doc, setDoc] = useState<Document | null>(null)
  const [textData, setTextData] = useState<DocumentTextResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!docId) return

    async function load() {
      setLoading(true)
      setError(null)
      try {
        const [docResult, textResult] = await Promise.all([
          getDocument(docId!),
          getDocumentText(docId!),
        ])
        setDoc(docResult)
        setTextData(textResult)
      } catch (e: unknown) {
        const axiosMsg = (e as { response?: { data?: { detail?: string } } })
          ?.response?.data?.detail
        setError(axiosMsg ?? 'Failed to load document.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [docId])

  // No document selected
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
        }}
      >
        <div style={{ fontSize: '64px' }}>📂</div>
        <h1
          style={{
            fontSize: '24px',
            fontWeight: 700,
            color: 'var(--color-text-primary)',
          }}
        >
          No document selected
        </h1>
        <p style={{ fontSize: '14px', color: 'var(--color-text-secondary)', textAlign: 'center' }}>
          Upload a document first to view its extracted content here.
        </p>
        <Link to="/" className="btn-primary" id="go-upload-btn">
          ⬆️ Upload a Document
        </Link>
      </div>
    )
  }

  return (
    <div style={{ padding: '36px 32px', maxWidth: '900px', margin: '0 auto' }}>
      <h1
        style={{
          fontSize: '26px',
          fontWeight: 800,
          color: 'var(--color-text-primary)',
          marginBottom: '4px',
        }}
      >
        Document Dashboard
      </h1>
      <p style={{ fontSize: '13px', color: 'var(--color-text-muted)', marginBottom: '32px' }}>
        Phase 1 — Extraction &amp; Storage
      </p>

      {loading && <LoadingState message="Loading document data…" />}
      {error && <ErrorMessage message={error} />}

      {doc && (
        <>
          {/* Metadata card */}
          <div className="glass-card" style={{ padding: '24px', marginBottom: '24px' }}>
            <h2
              style={{
                fontSize: '14px',
                fontWeight: 700,
                color: 'var(--color-text-secondary)',
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
                marginBottom: '16px',
              }}
            >
              Document Metadata
            </h2>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                gap: '16px',
              }}
            >
              {[
                { label: 'Filename', value: doc.filename },
                { label: 'Document Type', value: doc.document_type },
                { label: 'File Type', value: doc.file_type.toUpperCase() },
                {
                  label: 'File Size',
                  value: `${(doc.file_size / 1024).toFixed(1)} KB`,
                },
                {
                  label: 'Status',
                  value: doc.status,
                  badge: true,
                },
                {
                  label: 'Uploaded',
                  value: new Date(doc.created_at).toLocaleString(),
                },
              ].map(({ label, value, badge }) => (
                <div key={label}>
                  <p
                    style={{
                      fontSize: '11px',
                      fontWeight: 700,
                      color: 'var(--color-text-muted)',
                      letterSpacing: '0.06em',
                      textTransform: 'uppercase',
                      marginBottom: '4px',
                    }}
                  >
                    {label}
                  </p>
                  {badge ? (
                    <span className={`badge badge-${value.toLowerCase()}`}>{value}</span>
                  ) : (
                    <p
                      style={{
                        fontSize: '13px',
                        fontWeight: 600,
                        color: 'var(--color-text-primary)',
                        wordBreak: 'break-all',
                      }}
                    >
                      {value}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Extracted text */}
          {textData && (
            <div className="glass-card" style={{ padding: '24px' }}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  marginBottom: '20px',
                }}
              >
                <h2
                  style={{
                    fontSize: '14px',
                    fontWeight: 700,
                    color: 'var(--color-text-secondary)',
                    letterSpacing: '0.08em',
                    textTransform: 'uppercase',
                  }}
                >
                  Extracted Text
                </h2>
                <span
                  style={{
                    fontSize: '12px',
                    color: 'var(--color-text-muted)',
                    fontWeight: 600,
                  }}
                >
                  {textData.total_pages} page{textData.total_pages !== 1 ? 's' : ''}
                </span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {textData.pages.map((page) => (
                  <div
                    key={page.id}
                    style={{
                      borderLeft: '3px solid var(--color-accent)',
                      paddingLeft: '16px',
                    }}
                  >
                    <p
                      style={{
                        fontSize: '11px',
                        fontWeight: 700,
                        color: 'var(--color-accent)',
                        letterSpacing: '0.08em',
                        textTransform: 'uppercase',
                        marginBottom: '8px',
                      }}
                    >
                      Page {page.page_number}
                    </p>
                    <p
                      style={{
                        fontSize: '13px',
                        color: 'var(--color-text-secondary)',
                        lineHeight: 1.8,
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                        maxHeight: '200px',
                        overflowY: 'auto',
                      }}
                    >
                      {page.text || '(no text on this page)'}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Phase 2 placeholder */}
          <div
            style={{
              marginTop: '24px',
              padding: '24px',
              borderRadius: '16px',
              background:
                'linear-gradient(135deg, rgba(108,142,245,0.06) 0%, rgba(167,139,250,0.06) 100%)',
              border: '1px dashed rgba(108,142,245,0.3)',
              textAlign: 'center',
            }}
          >
            <p style={{ fontSize: '20px', marginBottom: '8px' }}>🤖</p>
            <p style={{ fontSize: '14px', fontWeight: 600, color: 'var(--color-accent)', marginBottom: '4px' }}>
              AI Analysis — Phase 2
            </p>
            <p style={{ fontSize: '13px', color: 'var(--color-text-muted)' }}>
              Risk scoring, clause extraction, and plain-English summaries will appear here once Phase 2 is implemented.
            </p>
          </div>
        </>
      )}
    </div>
  )
}
