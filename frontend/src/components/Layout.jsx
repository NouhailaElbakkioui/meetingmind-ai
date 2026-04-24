import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Upload, Search, Mic } from 'lucide-react'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/upload', icon: Upload, label: 'Upload' },
  { to: '/search', icon: Search, label: 'Recherche IA' },
]

const s = {
  root: { display: 'flex', minHeight: '100vh' },
  sidebar: {
    width: 220, background: 'var(--bg2)', borderRight: '1px solid var(--border)',
    display: 'flex', flexDirection: 'column', padding: '24px 0', position: 'fixed',
    top: 0, left: 0, height: '100vh',
  },
  logo: {
    display: 'flex', alignItems: 'center', gap: 10, padding: '0 20px 32px',
    fontSize: 18, fontWeight: 700, color: 'var(--accent)',
  },
  nav: { display: 'flex', flexDirection: 'column', gap: 4, padding: '0 12px' },
  link: {
    display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px',
    borderRadius: 8, color: 'var(--muted)', fontSize: 14, fontWeight: 500,
    transition: 'all .15s',
  },
  main: { marginLeft: 220, flex: 1, padding: 32, maxWidth: 1200 },
}

export default function Layout({ children }) {
  return (
    <div style={s.root}>
      <aside style={s.sidebar}>
        <div style={s.logo}>
          <Mic size={22} /> MeetingMind
        </div>
        <nav style={s.nav}>
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              style={({ isActive }) => ({
                ...s.link,
                background: isActive ? 'var(--bg3)' : 'transparent',
                color: isActive ? 'var(--text)' : 'var(--muted)',
              })}
            >
              <Icon size={16} /> {label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main style={s.main}>{children}</main>
    </div>
  )
}
