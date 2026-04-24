import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer, PieChart, Pie, Cell, Tooltip } from 'recharts'
import axios from 'axios'
import { CheckSquare, Lightbulb, Users, Tag, FileText } from 'lucide-react'

const card = {
  background: 'var(--bg2)', border: '1px solid var(--border)',
  borderRadius: 'var(--radius)', padding: 20, marginBottom: 16,
}

const SENTIMENT_COLORS = { positive: '#4ade80', neutral: '#7b82a0', negative: '#f87171' }

export default function MeetingDetail() {
  const { id } = useParams()
  const [meeting, setMeeting] = useState(null)
  const [tab, setTab] = useState('summary')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    axios.get(`/api/meetings/${id}`).then(r => setMeeting(r.data)).finally(() => setLoading(false))
  }, [id])

  if (loading) return <div style={{ color: 'var(--muted)' }}>Chargement...</div>
  if (!meeting) return <div>Réunion introuvable</div>

  const a = meeting.analysis

  const tabs = [
    { key: 'summary', label: 'Résumé', icon: FileText },
    { key: 'decisions', label: `Décisions (${a?.decisions?.length || 0})`, icon: Lightbulb },
    { key: 'actions', label: `Actions (${a?.action_items?.length || 0})`, icon: CheckSquare },
    { key: 'speakers', label: 'Participants', icon: Users },
    { key: 'minutes', label: 'Compte-rendu', icon: FileText },
  ]

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700 }}>{meeting.title}</h1>
        <div style={{ color: 'var(--muted)', fontSize: 13, marginTop: 4 }}>
          {new Date(meeting.date).toLocaleDateString('fr-FR', { dateStyle: 'long' })} · {meeting.language.toUpperCase()}
          {a?.processing_time_s && ` · Traité en ${a.processing_time_s}s`}
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 20, borderBottom: '1px solid var(--border)', paddingBottom: 0 }}>
        {tabs.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            style={{
              background: 'none', border: 'none', padding: '10px 14px',
              color: tab === key ? 'var(--text)' : 'var(--muted)',
              borderBottom: tab === key ? '2px solid var(--accent)' : '2px solid transparent',
              fontSize: 14, fontWeight: tab === key ? 600 : 400,
              display: 'flex', alignItems: 'center', gap: 6,
              cursor: 'pointer', transition: 'color .15s',
            }}
          >
            <Icon size={14} /> {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === 'summary' && a && (
        <div>
          <div style={card}>
            <h3 style={{ fontSize: 14, color: 'var(--muted)', marginBottom: 10 }}>RÉSUMÉ</h3>
            <p style={{ lineHeight: 1.7 }}>{a.summary}</p>
          </div>
          {a.topics?.length > 0 && (
            <div style={card}>
              <h3 style={{ fontSize: 14, color: 'var(--muted)', marginBottom: 12 }}>SUJETS ABORDÉS</h3>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {a.topics.map((t, i) => (
                  <span key={i} style={{
                    background: 'var(--accent)22', color: 'var(--accent)',
                    padding: '4px 12px', borderRadius: 20, fontSize: 13,
                  }}>
                    {t.topic}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {tab === 'decisions' && a && (
        <div style={card}>
          {a.decisions?.length === 0 ? (
            <p style={{ color: 'var(--muted)' }}>Aucune décision formelle détectée</p>
          ) : (
            a.decisions.map((d, i) => (
              <div key={i} style={{
                padding: '12px 0', borderBottom: i < a.decisions.length - 1 ? '1px solid var(--border)' : 'none',
                display: 'flex', gap: 12, alignItems: 'flex-start',
              }}>
                <div style={{ background: 'var(--accent)', borderRadius: '50%', width: 24, height: 24, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 700, flexShrink: 0 }}>{i + 1}</div>
                <div>
                  <div style={{ fontWeight: 500 }}>{d.text}</div>
                  <div style={{ color: 'var(--muted)', fontSize: 12, marginTop: 3 }}>— {d.speaker}</div>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {tab === 'actions' && a && (
        <div style={card}>
          {a.action_items?.length === 0 ? (
            <p style={{ color: 'var(--muted)' }}>Aucune action assignée</p>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)' }}>
                  {['Tâche', 'Responsable', 'Deadline'].map(h => (
                    <th key={h} style={{ textAlign: 'left', padding: '8px 12px', color: 'var(--muted)', fontWeight: 500 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {a.action_items.map((act, i) => (
                  <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td style={{ padding: '12px', fontWeight: 500 }}>{act.task}</td>
                    <td style={{ padding: '12px', color: 'var(--accent2)' }}>{act.owner}</td>
                    <td style={{ padding: '12px', color: 'var(--muted)' }}>{act.deadline}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {tab === 'speakers' && a && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          {Object.entries(a.sentiment_by_speaker || {}).map(([speaker, data]) => (
            <div key={speaker} style={card}>
              <div style={{ fontWeight: 600, marginBottom: 8 }}>{speaker}</div>
              <div style={{ display: 'flex', gap: 16, fontSize: 13 }}>
                <div>
                  <span style={{ color: 'var(--muted)' }}>Sentiment : </span>
                  <span style={{ color: SENTIMENT_COLORS[data.label] || 'var(--text)', fontWeight: 600 }}>
                    {data.label}
                  </span>
                </div>
                <div>
                  <span style={{ color: 'var(--muted)' }}>Temps parole : </span>
                  <span style={{ fontWeight: 600 }}>{Math.round((data.talk_ratio || 0) * 100)}%</span>
                </div>
              </div>
              {/* Bar temps de parole */}
              <div style={{ background: 'var(--bg3)', borderRadius: 4, height: 6, marginTop: 12, overflow: 'hidden' }}>
                <div style={{ background: 'var(--accent)', width: `${(data.talk_ratio || 0) * 100}%`, height: '100%', borderRadius: 4 }} />
              </div>
            </div>
          ))}
        </div>
      )}

      {tab === 'minutes' && a && (
        <div style={{ ...card, fontFamily: 'monospace', fontSize: 13, whiteSpace: 'pre-wrap', lineHeight: 1.8 }}>
          {a.minutes_report || 'Compte-rendu non disponible'}
        </div>
      )}
    </div>
  )
}
