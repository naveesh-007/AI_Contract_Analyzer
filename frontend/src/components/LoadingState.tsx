interface LoadingStateProps {
  message?: string
  size?: 'sm' | 'md' | 'lg'
}

const SIZE_MAP = {
  sm: { spinner: 20, font: 12 },
  md: { spinner: 32, font: 14 },
  lg: { spinner: 48, font: 16 },
}

export function LoadingState({ message = 'Loading…', size = 'md' }: LoadingStateProps) {
  const { spinner, font } = SIZE_MAP[size]

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '16px',
        padding: '48px 24px',
      }}
    >
      {/* Spinner */}
      <div
        style={{
          width: spinner,
          height: spinner,
          borderRadius: '50%',
          border: `3px solid var(--color-border)`,
          borderTopColor: 'var(--color-accent)',
          animation: 'spin 0.8s linear infinite',
        }}
      />
      <p
        style={{
          fontSize: font,
          color: 'var(--color-text-secondary)',
          fontWeight: 500,
          animation: 'pulse 2s ease-in-out infinite',
        }}
      >
        {message}
      </p>

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}
