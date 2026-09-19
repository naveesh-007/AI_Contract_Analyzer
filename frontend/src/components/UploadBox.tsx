import { useState, useCallback } from 'react'
import { FileDropZone } from './FileDropZone'
import { validateFile, formatFileSize } from '../utils/fileUtils'
import { DOCUMENT_TYPES } from '../types/document'
import type { DocumentType } from '../types/document'

interface UploadBoxProps {
  onSubmit: (file: File, documentType: DocumentType) => void
  disabled?: boolean
}

/**
 * Full upload card: drop zone + file preview + doc type selector + submit button.
 */
export function UploadBox({ onSubmit, disabled = false }: UploadBoxProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [documentType, setDocumentType] = useState<DocumentType>('Other')

  const handleFileSelected = useCallback((file: File) => {
    setSelectedFile(file)
  }, [])

  const handleRemoveFile = useCallback(() => {
    setSelectedFile(null)
  }, [])

  const handleSubmit = useCallback(() => {
    if (!selectedFile || disabled) return
    const result = validateFile(selectedFile)
    if (!result.valid) return
    onSubmit(selectedFile, documentType)
  }, [selectedFile, documentType, disabled, onSubmit])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Drop zone (hidden when file is selected) */}
      {!selectedFile && (
        <FileDropZone
          onFileSelected={handleFileSelected}
          disabled={disabled}
        />
      )}

      {/* File preview */}
      {selectedFile && (
        <div
          className="glass-card"
          style={{
            padding: '16px 20px',
            display: 'flex',
            alignItems: 'center',
            gap: '14px',
          }}
        >
          <div
            style={{
              width: '44px',
              height: '44px',
              borderRadius: '10px',
              background: 'linear-gradient(135deg, rgba(108,142,245,0.2), rgba(167,139,250,0.2))',
              border: '1px solid rgba(108,142,245,0.3)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '20px',
              flexShrink: 0,
            }}
          >
            {selectedFile.name.endsWith('.pdf') ? '📑' : '📝'}
          </div>

          <div style={{ flex: 1, minWidth: 0 }}>
            <p
              style={{
                fontSize: '13px',
                fontWeight: 600,
                color: 'var(--color-text-primary)',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
              }}
            >
              {selectedFile.name}
            </p>
            <p style={{ fontSize: '12px', color: 'var(--color-text-muted)', marginTop: '2px' }}>
              {formatFileSize(selectedFile.size)} •{' '}
              {selectedFile.name.split('.').pop()?.toUpperCase()}
            </p>
          </div>

          {!disabled && (
            <button
              onClick={handleRemoveFile}
              aria-label="Remove selected file"
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                fontSize: '16px',
                color: 'var(--color-text-muted)',
                padding: '4px',
                borderRadius: '6px',
                transition: 'color 0.15s',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--color-error)')}
              onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--color-text-muted)')}
            >
              ✕
            </button>
          )}
        </div>
      )}

      {/* Document type selector */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <label
          htmlFor="document-type"
          style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-text-secondary)' }}
        >
          Document Type
        </label>
        <select
          id="document-type"
          value={documentType}
          onChange={(e) => setDocumentType(e.target.value as DocumentType)}
          disabled={disabled}
          className="input-field"
          style={{ cursor: disabled ? 'not-allowed' : 'pointer' }}
        >
          {DOCUMENT_TYPES.map((type) => (
            <option key={type} value={type}>
              {type}
            </option>
          ))}
        </select>
      </div>

      {/* Submit */}
      <button
        id="upload-submit-btn"
        className="btn-primary"
        onClick={handleSubmit}
        disabled={!selectedFile || disabled}
        style={{
          width: '100%',
          padding: '14px',
          fontSize: '15px',
          opacity: !selectedFile || disabled ? 0.5 : 1,
          cursor: !selectedFile || disabled ? 'not-allowed' : 'pointer',
          transform: 'none',
        }}
      >
        {disabled ? '⏳ Processing…' : '⬆️ Upload & Extract'}
      </button>
    </div>
  )
}
