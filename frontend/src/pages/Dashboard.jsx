import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import axios from 'axios'

const card = {
  background: 'var(--bg2)', border: '1px solid var(--border)',
  borderRadius: 'var(--radius)', padding: 20,
}

const STATUS_COLORS = {
  done: 'var(--success)', processing: 'var(--warning)',
  uploaded: 'var(--accent)', error: 'var(--danger)',
}

const STATUS_LABELS = {
  done: 'Analysé', processing: 'En cours...', uploaded: 'En attente', error: 'Erreur',
}

export default function Dashboard() {
  const [meetings, setMeetings] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const nav = useNavigate()

  useEffect(() => {
    Promise.all([
      axios.get('/api/meetings/'),
      axios.get('/api/analysis/stats'),
    ]).then(([m, s]) => {
      setMeetings(m.data)
      setStats(s.data)
    }).finally(() => setLoading(false))

    // Polling pour les réunions en cours
    const interval = setInterval(() => {
      axios.get('/api/meetings/').then(r => setMeetings(r.data))
    }, 5000)
    return () => clearInterval(interval)
  }, [])

  if (loading) return <div style={{ color: 'var(--muted)' }}>Chargement...</div>

  const chartData = meetings.slice(0, 10).reverse().map(m => ({
    name: m.title.substring(0, 12) + '…',
    status: m.status,
  }))

  return (
    <div>
      <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 8 }}>Dashboard</h1>
      <p style={{ color: 'var(--muted)', marginBottom: 28 }}>
        Vue globale de vos réunions analysées
      </p>

      {/* Stats cards */}
      {stats && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 28 }}>
          {[
            { label: 'Réunions totales', value: stats.total_meetings, color: 'var(--accent)' },
            { label: 'Analysées', value: stats.processed, color: 'var(--success)' },
            { label: 'En attente', value: stats.pending, color: 'var(--warning)' },
          ].map(({ label, value, color }) => (
            <div key={label} style={card}>
              <div style={{ fontSize: 32, fontWeight: 700, color }}>{value}</div>
              <div style={{ color: 'var(--muted)', fontSize: 13, marginTop: 4 }}>{label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Liste réunions */}
      <div style={card}>
        <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>Dernières réunions</h2>
        {meetings.length === 0 ? (
          <p style={{ color: 'var(--muted)', textAlign: 'center', padding: 32 }}>
            Aucune réunion — <a href="/upload" style={{ color: 'var(--accent)' }}>upload ton premier fichier</a>
          </p>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                {['Titre', 'Date', 'Langue', 'Statut'].map(h => (
                  <th key={h} style={{ textAlign: 'left', padding: '8px 12px', color: 'var(--muted)', fontWeight: 500 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {meetings.map(m => (
                <tr
                  key={m.id}
                  onClick={() => m.status === 'done' && nav(`/meeting/${m.id}`)}
                  style={{
                    borderBottom: '1px solid var(--border)',
                    cursor: m.status === 'done' ? 'pointer' : 'default',
                    transition: 'background .1s',
                  }}
                  onMouseEnter={e => m.status === 'done' && (e.currentTarget.style.background = 'var(--bg3)')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                >
                  <td style={{ padding: '12px 12px', fontWeight: 500 }}>{m.title}</td>
                  <td style={{ padding: '12px 12px', color: 'var(--muted)' }}>
                    {new Date(m.date).toLocaleDateString('fr-FR')}
                  </td>
                  <td style={{ padding: '12px 12px', color: 'var(--muted)' }}>{m.language.toUpperCase()}</td>
                  <td style={{ padding: '12px 12px' }}>
                    <span style={{
                      background: STATUS_COLORS[m.status] + '22',
                      color: STATUS_COLORS[m.status],
                      padding: '3px 10px', borderRadius: 20, fontSize: 12, fontWeight: 500,
                    }}>
                      {STATUS_LABELS[m.status] || m.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
