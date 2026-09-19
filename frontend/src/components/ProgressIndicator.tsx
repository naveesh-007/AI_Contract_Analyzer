interface ProgressIndicatorProps {
  stage: 'uploading' | 'extracting' | 'completed' | 'failed'
  progress: number // 0–100
  filename?: string
}

const STAGE_CONFIG = {
  uploading: {
    label: 'Uploading document…',
    sublabel: 'Sending your file to the server',
    color: 'var(--color-accent)',
    icon: '⬆️',
  },
  extracting: {
    label: 'Extracting text…',
    sublabel: 'Parsing pages and indexing content',
    color: '#a78bfa',
    icon: '🔍',
  },
  completed: {
    label: 'Processing complete!',
    sublabel: 'Your document is ready',
    color: 'var(--color-success)',
    icon: '✅',
  },
  failed: {
    label: 'Processing failed',
    sublabel: 'Something went wrong',
    color: 'var(--color-error)',
    icon: '❌',
  },
}

export function ProgressIndicator({ stage, progress, filename }: ProgressIndicatorProps) {
  const config = STAGE_CONFIG[stage]
  const clampedProgress = Math.max(0, Math.min(100, progress))

  return (
    <div
      className="glass-card"
      style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}
    >
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <span style={{ fontSize: '24px' }}>{config.icon}</span>
        <div>
          <p
            style={{
              fontSize: '15px',
              fontWeight: 600,
              color: config.color,
              marginBottom: '2px',
            }}
          >
            {config.label}
          </p>
          {filename && (
            <p style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>
              {filename}
            </p>
          )}
          <p style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>
            {config.sublabel}
          </p>
        </div>
        <span
          style={{
            marginLeft: 'auto',
            fontSize: '14px',
            fontWeight: 700,
            color: config.color,
          }}
        >
          {stage === 'completed' ? '100%' : stage === 'failed' ? '—' : `${clampedProgress}%`}
        </span>
      </div>

      {/* Progress bar */}
      <div
        style={{
          height: '6px',
          borderRadius: '3px',
          background: 'var(--color-border)',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            height: '100%',
            width: `${stage === 'completed' ? 100 : clampedProgress}%`,
            borderRadius: '3px',
            background:
              stage === 'completed'
                ? 'var(--color-success)'
                : stage === 'failed'
                ? 'var(--color-error)'
                : `linear-gradient(90deg, ${config.color}, var(--color-accent-light))`,
            transition: 'width 0.4s ease',
          }}
        />
      </div>
    </div>
  )
}
