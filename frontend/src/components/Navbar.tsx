import { Link, useLocation } from 'react-router-dom'

export function Navbar() {
  const location = useLocation()

  return (
    <header
      style={{
        background: 'rgba(10, 13, 20, 0.85)',
        backdropFilter: 'blur(20px)',
        borderBottom: '1px solid var(--color-border)',
        position: 'sticky',
        top: 0,
        zIndex: 100,
      }}
    >
      <nav
        style={{
          maxWidth: '1280px',
          margin: '0 auto',
          padding: '0 24px',
          height: '64px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        {/* Logo */}
        <Link
          to="/"
          style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '10px' }}
        >
          <div
            style={{
              width: '36px',
              height: '36px',
              background: 'linear-gradient(135deg, #6c8ef5, #a78bfa)',
              borderRadius: '10px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '18px',
              boxShadow: '0 4px 16px rgba(108,142,245,0.35)',
            }}
          >
            ⚖️
          </div>
          <span
            style={{
              fontSize: '16px',
              fontWeight: 700,
              color: 'var(--color-text-primary)',
              letterSpacing: '-0.01em',
            }}
          >
            LexAI
            <span style={{ color: 'var(--color-accent)', marginLeft: '2px' }}>Simplifier</span>
          </span>
        </Link>

        {/* Nav links */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <NavLink to="/" active={location.pathname === '/'} label="Upload" icon="⬆️" />
          <NavLink
            to="/dashboard"
            active={location.pathname === '/dashboard'}
            label="Dashboard"
            icon="📊"
          />
        </div>

        {/* Right pill */}
        <div
          style={{
            padding: '6px 14px',
            borderRadius: '20px',
            background: 'rgba(108,142,245,0.1)',
            border: '1px solid rgba(108,142,245,0.25)',
            fontSize: '12px',
            color: 'var(--color-accent-light)',
            fontWeight: 600,
          }}
        >
          Phase 3 — AI Contract Simplifier
        </div>
      </nav>
    </header>
  )
}

function NavLink({
  to,
  active,
  label,
  icon,
}: {
  to: string
  active: boolean
  label: string
  icon: string
}) {
  return (
    <Link
      to={to}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
        padding: '8px 14px',
        borderRadius: '8px',
        textDecoration: 'none',
        fontSize: '13px',
        fontWeight: 600,
        color: active ? 'var(--color-accent-light)' : 'var(--color-text-secondary)',
        background: active ? 'var(--color-accent-glow)' : 'transparent',
        border: `1px solid ${active ? 'rgba(108,142,245,0.3)' : 'transparent'}`,
        transition: 'all 0.15s ease',
      }}
    >
      <span style={{ fontSize: '14px' }}>{icon}</span>
      {label}
    </Link>
  )
}
