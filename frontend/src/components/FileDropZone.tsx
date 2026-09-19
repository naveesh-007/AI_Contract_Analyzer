import { useCallback, useState } from 'react'
import { validateFile } from '../utils/fileUtils'
import type { ValidationResult } from '../utils/fileUtils'

interface FileDropZoneProps {
  onFileSelected: (file: File) => void
  disabled?: boolean
  accept?: string
}

/**
 * Raw drag-and-drop target. Validates on drop and calls onFileSelected.
 */
export function FileDropZone({ onFileSelected, disabled = false, accept }: FileDropZoneProps) {
  const [isDragging, setIsDragging] = useState(false)
  const [dropError, setDropError] = useState<string | null>(null)

  const handleFile = useCallback(
    (file: File) => {
      setDropError(null)
      const result: ValidationResult = validateFile(file)
      if (!result.valid) {
        setDropError(result.error ?? 'Invalid file.')
        return
      }
      onFileSelected(file)
    },
    [onFileSelected]
  )

  const onDragOver = useCallback((e: React.DragEvent<HTMLElement>) => {
    e.preventDefault()
    if (!disabled) setIsDragging(true)
  }, [disabled])

  const onDragLeave = useCallback(() => setIsDragging(false), [])

  const onDrop = useCallback(
    (e: React.DragEvent<HTMLElement>) => {
      e.preventDefault()
      setIsDragging(false)
      if (disabled) return
      const file = e.dataTransfer.files?.[0]
      if (file) handleFile(file)
    },
    [disabled, handleFile]
  )

  const onInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0]
      if (file) handleFile(file)
      // Reset so same file can be re-selected
      e.target.value = ''
    },
    [handleFile]
  )

  return (
    <div>
      <label
        id="file-drop-zone"
        htmlFor="file-input"
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        style={{
          display: 'block',
          border: `2px dashed ${
            isDragging
              ? 'var(--color-accent)'
              : dropError
              ? 'var(--color-error)'
              : 'var(--color-border-hover)'
          }`,
          borderRadius: '16px',
          padding: '56px 32px',
          textAlign: 'center',
          cursor: disabled ? 'not-allowed' : 'pointer',
          background: isDragging
            ? 'var(--color-accent-glow)'
            : 'rgba(15, 19, 32, 0.5)',
          transition: 'all 0.2s ease',
          transform: isDragging ? 'scale(1.01)' : 'scale(1)',
          opacity: disabled ? 0.5 : 1,
        }}
      >
        <input
          id="file-input"
          type="file"
          accept={accept ?? '.pdf,.txt'}
          onChange={onInputChange}
          disabled={disabled}
          style={{ display: 'none' }}
        />

        {/* Icon */}
        <div
          style={{
            width: '72px',
            height: '72px',
            margin: '0 auto 20px',
            borderRadius: '20px',
            background: isDragging
              ? 'linear-gradient(135deg, #6c8ef5, #a78bfa)'
              : 'var(--color-bg-card)',
            border: `1px solid ${isDragging ? 'transparent' : 'var(--color-border)'}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '32px',
            transition: 'all 0.25s ease',
            boxShadow: isDragging ? '0 8px 32px rgba(108,142,245,0.4)' : 'none',
          }}
        >
          {isDragging ? '📂' : '📄'}
        </div>

        <p
          style={{
            fontSize: '16px',
            fontWeight: 600,
            color: isDragging ? 'var(--color-accent-light)' : 'var(--color-text-primary)',
            marginBottom: '8px',
          }}
        >
          {isDragging ? 'Drop your document here' : 'Drag & drop your document'}
        </p>
        <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginBottom: '20px' }}>
          or click to browse from your computer
        </p>

        {/* Format chips */}
        <div style={{ display: 'flex', justifyContent: 'center', gap: '8px', flexWrap: 'wrap' }}>
          {['PDF', 'TXT'].map((fmt) => (
            <span
              key={fmt}
              style={{
                padding: '4px 12px',
                borderRadius: '20px',
                fontSize: '11px',
                fontWeight: 700,
                letterSpacing: '0.06em',
                background: 'rgba(108,142,245,0.1)',
                color: 'var(--color-accent)',
                border: '1px solid rgba(108,142,245,0.25)',
              }}
            >
              {fmt}
            </span>
          ))}
          <span
            style={{
              padding: '4px 12px',
              borderRadius: '20px',
              fontSize: '11px',
              fontWeight: 600,
              color: 'var(--color-text-muted)',
              border: '1px solid var(--color-border)',
            }}
          >
            max 25 MB
          </span>
        </div>
      </label>

      {dropError && (
        <p
          style={{
            marginTop: '10px',
            fontSize: '13px',
            color: 'var(--color-error)',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}
        >
          ⚠️ {dropError}
        </p>
      )}
    </div>
  )
}
