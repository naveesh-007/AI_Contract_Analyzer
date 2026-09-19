import { Link, useLocation } from 'react-router-dom'

interface SidebarLink {
  to: string
  label: string
  icon: string
  badge?: string
}

const links: SidebarLink[] = [
  { to: '/', label: 'Upload Document', icon: '⬆️' },
  { to: '/dashboard', label: 'Dashboard', icon: '📊', badge: 'Soon' },
]

export function Sidebar() {
  const location = useLocation()

  return (
    <aside
      style={{
        width: '220px',
        flexShrink: 0,
        background: 'var(--color-bg-secondary)',
        borderRight: '1px solid var(--color-border)',
        padding: '24px 12px',
        display: 'flex',
        flexDirection: 'column',
        gap: '4px',
        minHeight: 'calc(100vh - 64px)',
      }}
    >
      <p
        style={{
          fontSize: '10px',
          fontWeight: 700,
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
          color: 'var(--color-text-muted)',
          padding: '0 12px',
          marginBottom: '8px',
        }}
      >
        Navigation
      </p>

      {links.map((link) => {
        const active = location.pathname === link.to
        return (
          <Link
            key={link.to}
            to={link.to}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '10px',
              padding: '10px 12px',
              borderRadius: '8px',
              textDecoration: 'none',
              fontSize: '13px',
              fontWeight: active ? 600 : 500,
              color: active ? 'var(--color-accent-light)' : 'var(--color-text-secondary)',
              background: active ? 'var(--color-accent-glow)' : 'transparent',
              border: `1px solid ${active ? 'rgba(108,142,245,0.25)' : 'transparent'}`,
              transition: 'all 0.15s ease',
            }}
          >
            <span style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ fontSize: '15px' }}>{link.icon}</span>
              {link.label}
            </span>
            {link.badge && (
              <span
                style={{
                  fontSize: '9px',
                  fontWeight: 700,
                  letterSpacing: '0.05em',
                  padding: '2px 6px',
                  borderRadius: '10px',
                  background: 'rgba(251,191,36,0.15)',
                  color: 'var(--color-warning)',
                  border: '1px solid rgba(251,191,36,0.3)',
                }}
              >
                {link.badge}
              </span>
            )}
          </Link>
        )
      })}

      {/* Coming soon section */}
      <div style={{ marginTop: 'auto', padding: '16px 12px' }}>
        <div
          style={{
            padding: '12px',
            borderRadius: '10px',
            background: 'rgba(108,142,245,0.06)',
            border: '1px solid rgba(108,142,245,0.15)',
          }}
        >
          <p style={{ fontSize: '11px', fontWeight: 600, color: 'var(--color-accent)', marginBottom: '4px' }}>
            Phase 2 coming
          </p>
          <p style={{ fontSize: '11px', color: 'var(--color-text-muted)', lineHeight: 1.5 }}>
            AI risk analysis, clause extraction &amp; RAG chat will be added next.
          </p>
        </div>
      </div>
    </aside>
  )
}
