import { useState } from 'react'
import axios from 'axios'
import { Search, Zap } from 'lucide-react'

const card = {
  background: 'var(--bg2)', border: '1px solid var(--border)',
  borderRadius: 'var(--radius)', padding: 20,
}

const EXAMPLES = [
  "Quelles décisions ont été prises ce mois-ci ?",
  "Qui est responsable de la migration AWS ?",
  "Résume les actions en attente sur le projet produit",
  "Quels sujets reviennent le plus dans nos réunions ?",
]

export default function RAGSearch() {
  const [question, setQuestion] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  const ask = async (q) => {
    const query = q || question
    if (!query.trim()) return
    setLoading(true)
    setResult(null)
    try {
      const res = await axios.post('/api/rag/query', { question: query })
      setResult(res.data)
    } catch (e) {
      setResult({ answer: 'Erreur : ' + (e.response?.data?.detail || e.message), sources: [], latency_s: 0 })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 720 }}>
      <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 8 }}>Recherche IA</h1>
      <p style={{ color: 'var(--muted)', marginBottom: 28 }}>
        Posez n'importe quelle question sur vos réunions passées
      </p>

      {/* Input */}
      <div style={{ ...card, marginBottom: 16, display: 'flex', gap: 10 }}>
        <input
          value={question}
          onChange={e => setQuestion(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && ask()}
          placeholder="Ex : Quelles décisions ont été prises sur le projet Alpha ?"
          style={{
            flex: 1, background: 'var(--bg3)', border: '1px solid var(--border)',
            borderRadius: 8, padding: '12px 16px', color: 'var(--text)', fontSize: 14, outline: 'none',
          }}
        />
        <button
          onClick={() => ask()}
          disabled={loading}
          style={{
            background: 'var(--accent)', color: 'white', border: 'none',
            borderRadius: 8, padding: '12px 20px', fontWeight: 600,
            display: 'flex', alignItems: 'center', gap: 6,
          }}
        >
          <Search size={16} /> {loading ? '...' : 'Chercher'}
        </button>
      </div>

      {/* Exemples */}
      {!result && !loading && (
        <div style={{ marginBottom: 24 }}>
          <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 10 }}>EXEMPLES DE QUESTIONS</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {EXAMPLES.map(ex => (
              <button
                key={ex}
                onClick={() => { setQuestion(ex); ask(ex) }}
                style={{
                  background: 'var(--bg2)', border: '1px solid var(--border)',
                  borderRadius: 20, padding: '6px 14px', fontSize: 13,
                  color: 'var(--muted)', cursor: 'pointer',
                  transition: 'all .15s',
                }}
                onMouseEnter={e => { e.target.style.color = 'var(--text)'; e.target.style.borderColor = 'var(--accent)' }}
                onMouseLeave={e => { e.target.style.color = 'var(--muted)'; e.target.style.borderColor = 'var(--border)' }}
              >
                {ex}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Réponse */}
      {loading && (
        <div style={{ ...card, display: 'flex', alignItems: 'center', gap: 10, color: 'var(--muted)' }}>
          <Zap size={16} color="var(--accent)" /> Analyse de l'historique en cours...
        </div>
      )}

      {result && (
        <div>
          <div style={{ ...card, marginBottom: 12 }}>
            <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 10, display: 'flex', justifyContent: 'space-between' }}>
              <span>RÉPONSE IA</span>
              <span>{result.latency_s}s</span>
            </div>
            <p style={{ lineHeight: 1.8, whiteSpace: 'pre-wrap' }}>{result.answer}</p>
          </div>

          {result.sources?.length > 0 && (
            <div style={card}>
              <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 10 }}>SOURCES</div>
              {result.sources.map((s, i) => (
                <div key={i} style={{
                  display: 'flex', justifyContent: 'space-between', padding: '8px 0',
                  borderBottom: i < result.sources.length - 1 ? '1px solid var(--border)' : 'none',
                  fontSize: 13,
                }}>
                  <span style={{ fontWeight: 500 }}>{s.title}</span>
                  <span style={{ color: 'var(--muted)' }}>
                    {s.date} · {s.chunk_type} · {Math.round(s.relevance * 100)}% pertinence
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
