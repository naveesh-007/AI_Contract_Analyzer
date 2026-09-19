export function LegalDisclaimer() {
  return (
    <div
      style={{
        padding: '10px 16px',
        borderRadius: '8px',
        background: 'rgba(30, 38, 64, 0.4)',
        border: '1px solid var(--color-border)',
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        fontSize: '12px',
        color: 'var(--color-text-secondary)',
        lineHeight: 1.4,
      }}
    >
      <span style={{ fontSize: '14px', flexShrink: 0 }}>ℹ️</span>
      <p style={{ margin: 0 }}>
        <strong>Legal Disclaimer:</strong> This tool provides general information to help you understand the document. It does not provide legal advice.
      </p>
    </div>
  )
}
