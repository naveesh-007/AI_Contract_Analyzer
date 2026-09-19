import { Navbar } from '../components/Navbar'
import { Sidebar } from '../components/Sidebar'
import { Outlet } from 'react-router-dom'

/**
 * Root application layout: sticky Navbar + Sidebar + main content outlet.
 */
export function AppLayout() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <Navbar />
      <div style={{ display: 'flex', flex: 1 }}>
        <Sidebar />
        <main
          style={{
            flex: 1,
            overflowY: 'auto',
            background: 'var(--color-bg-primary)',
          }}
        >
          <Outlet />
        </main>
      </div>
    </div>
  )
}
