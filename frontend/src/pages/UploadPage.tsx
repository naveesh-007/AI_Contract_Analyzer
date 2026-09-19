import { useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { UploadBox } from '../components/UploadBox'
import { ProgressIndicator } from '../components/ProgressIndicator'
import { ErrorMessage } from '../components/ErrorMessage'
import { useUpload } from '../hooks/useUpload'
import type { DocumentType } from '../types/document'

/**
 * Upload Page — route: /
 *
 * Contains:
 * - App title & description
 * - Supported format info
 * - Drag-and-drop upload box
 * - Document type selector
 * - Real-time progress indicator
 * - Navigates to /dashboard on completion
 */
export function UploadPage() {
  const { state, upload, reset } = useUpload()
  const navigate = useNavigate()

  const isProcessing = state.stage === 'uploading' || state.stage === 'extracting'

  const handleSubmit = useCallback(
    async (file: File, documentType: DocumentType) => {
      const docId = await upload(file, documentType)
      if (docId) {
        // Brief pause so user sees the "completed" state, then navigate
        setTimeout(() => navigate(`/documents/${docId}`), 1000)
      }
    },
    [upload, navigate]
  )

  return (
    <div
      style={{
        minHeight: 'calc(100vh - 64px)',
        padding: '48px 32px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
      }}
    >
      {/* Hero */}
      <div
        style={{
          textAlign: 'center',
          maxWidth: '640px',
          marginBottom: '48px',
          animation: 'slideUp 0.5s ease',
        }}
      >
        {/* Badge */}
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '6px 16px',
            borderRadius: '20px',
            background: 'rgba(108,142,245,0.1)',
            border: '1px solid rgba(108,142,245,0.25)',
            fontSize: '12px',
            fontWeight: 700,
            color: 'var(--color-accent)',
            letterSpacing: '0.05em',
            marginBottom: '24px',
          }}
        >
          <span>⚖️</span> AI Legal Document Simplifier
        </div>

        <h1
          style={{
            fontSize: '40px',
            fontWeight: 800,
            lineHeight: 1.15,
            letterSpacing: '-0.02em',
            marginBottom: '16px',
          }}
        >
          Understand Every{' '}
          <span className="gradient-text">Legal Clause</span>
          {' '}Instantly
        </h1>

        <p
          style={{
            fontSize: '16px',
            color: 'var(--color-text-secondary)',
            lineHeight: 1.7,
            maxWidth: '520px',
            margin: '0 auto',
          }}
        >
          Upload your rental agreement, freelance contract, or terms of service.
          Our AI will extract, analyse, and explain every clause in plain English —
          no legal background required.
        </p>
      </div>

      {/* Main card */}
      <div
        className="glass-card glow-accent"
        style={{
          width: '100%',
          maxWidth: '600px',
          padding: '36px',
          animation: 'slideUp 0.55s ease',
        }}
      >
        {/* Card header */}
        <div style={{ marginBottom: '28px' }}>
          <h2
            style={{
              fontSize: '18px',
              fontWeight: 700,
              color: 'var(--color-text-primary)',
              marginBottom: '6px',
            }}
          >
            Upload Your Document
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>
            Supported formats: <strong style={{ color: 'var(--color-accent)' }}>PDF</strong> and{' '}
            <strong style={{ color: 'var(--color-accent)' }}>TXT</strong> — up to 25 MB
          </p>
        </div>

        {/* Progress indicator (shown while processing or on completion) */}
        {state.stage !== 'idle' && state.stage !== 'failed' && (
          <div style={{ marginBottom: '20px' }}>
            <ProgressIndicator
              stage={state.stage}
              progress={state.progress}
              filename={state.filename}
            />
          </div>
        )}

        {/* Error message */}
        {state.stage === 'failed' && state.error && (
          <div style={{ marginBottom: '20px' }}>
            <ErrorMessage message={state.error} onDismiss={reset} />
          </div>
        )}

        {/* Upload box — hidden while actively processing */}
        {(state.stage === 'idle' || state.stage === 'failed') && (
          <UploadBox onSubmit={handleSubmit} disabled={isProcessing} />
        )}

        {/* Reset after failure */}
        {state.stage === 'failed' && (
          <button
            id="try-again-btn"
            className="btn-secondary"
            onClick={reset}
            style={{ width: '100%', marginTop: '12px' }}
          >
            ↩ Try another file
          </button>
        )}
      </div>

      {/* Feature chips */}
      <div
        style={{
          marginTop: '48px',
          display: 'flex',
          flexWrap: 'wrap',
          gap: '12px',
          justifyContent: 'center',
          maxWidth: '700px',
          animation: 'fadeIn 0.8s ease',
        }}
      >
        {[
          { icon: '🔒', text: 'Secure upload' },
          { icon: '📄', text: 'Page-level extraction' },
          { icon: '🤖', text: 'AI analysis (Phase 2)' },
          { icon: '💬', text: 'RAG chat (Phase 4)' },
        ].map(({ icon, text }) => (
          <div
            key={text}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 16px',
              borderRadius: '12px',
              background: 'var(--color-bg-card)',
              border: '1px solid var(--color-border)',
              fontSize: '13px',
              color: 'var(--color-text-secondary)',
              fontWeight: 500,
            }}
          >
            <span>{icon}</span>
            {text}
          </div>
        ))}
      </div>
    </div>
  )
}
