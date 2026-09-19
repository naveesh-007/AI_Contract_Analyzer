interface ErrorMessageProps {
  message: string
  onDismiss?: () => void
}

export function ErrorMessage({ message, onDismiss }: ErrorMessageProps) {
  return (
    <div
      role="alert"
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: '12px',
        padding: '16px 20px',
        borderRadius: '12px',
        background: 'rgba(248, 113, 113, 0.08)',
        border: '1px solid rgba(248, 113, 113, 0.25)',
        animation: 'slideUp 0.3s ease',
      }}
    >
      <span style={{ fontSize: '18px', flexShrink: 0, marginTop: '1px' }}>⚠️</span>
      <div style={{ flex: 1 }}>
        <p style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-error)', marginBottom: '2px' }}>
          Upload Error
        </p>
        <p style={{ fontSize: '13px', color: '#fca5a5', lineHeight: 1.5 }}>{message}</p>
      </div>
      {onDismiss && (
        <button
          onClick={onDismiss}
          aria-label="Dismiss error"
          style={{
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            color: 'var(--color-text-muted)',
            fontSize: '18px',
            lineHeight: 1,
            flexShrink: 0,
            padding: '0',
            transition: 'color 0.15s',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--color-error)')}
          onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--color-text-muted)')}
        >
          ✕
        </button>
      )}
    </div>
  )
}
