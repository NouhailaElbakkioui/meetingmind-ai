import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import toast from 'react-hot-toast'
import { Upload as UploadIcon, Mic } from 'lucide-react'

const card = {
  background: 'var(--bg2)', border: '1px solid var(--border)',
  borderRadius: 'var(--radius)', padding: 32,
}

export default function Upload() {
  const [file, setFile] = useState(null)
  const [title, setTitle] = useState('')
  const [language, setLanguage] = useState('fr')
  const [uploading, setUploading] = useState(false)
  const nav = useNavigate()

  const onDrop = useCallback(accepted => {
    if (accepted[0]) {
      setFile(accepted[0])
      if (!title) setTitle(accepted[0].name.replace(/\.[^.]+$/, ''))
    }
  }, [title])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'audio/*': ['.mp3', '.wav', '.m4a', '.ogg', '.flac'], 'video/mp4': ['.mp4'] },
    maxFiles: 1,
  })

  const handleSubmit = async () => {
    if (!file || !title.trim()) return toast.error('Titre et fichier requis')
    setUploading(true)
    const formData = new FormData()
    formData.append('file', file)
    formData.append('title', title)
    formData.append('language', language)

    try {
      const res = await axios.post('/api/meetings/upload', formData)
      toast.success('Upload réussi — analyse en cours...')
      nav('/')
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Erreur upload')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div style={{ maxWidth: 640 }}>
      <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 8 }}>Upload une réunion</h1>
      <p style={{ color: 'var(--muted)', marginBottom: 28 }}>
        MP3, WAV, M4A, OGG, FLAC ou MP4 — max 100 MB
      </p>

      <div style={{ ...card, marginBottom: 20 }}>
        <div
          {...getRootProps()}
          style={{
            border: `2px dashed ${isDragActive ? 'var(--accent)' : 'var(--border)'}`,
            borderRadius: 10, padding: '48px 24px', textAlign: 'center',
            cursor: 'pointer', transition: 'all .2s',
            background: isDragActive ? 'var(--accent)11' : 'transparent',
          }}
        >
          <input {...getInputProps()} />
          {file ? (
            <div>
              <Mic size={32} color="var(--success)" style={{ marginBottom: 12 }} />
              <div style={{ fontWeight: 600 }}>{file.name}</div>
              <div style={{ color: 'var(--muted)', fontSize: 13 }}>
                {(file.size / 1024 / 1024).toFixed(1)} MB
              </div>
            </div>
          ) : (
            <div>
              <UploadIcon size={32} color="var(--muted)" style={{ marginBottom: 12 }} />
              <div style={{ fontWeight: 500 }}>
                {isDragActive ? 'Dépose ici' : 'Glisse un fichier audio ici'}
              </div>
              <div style={{ color: 'var(--muted)', fontSize: 13, marginTop: 6 }}>ou clique pour parcourir</div>
            </div>
          )}
        </div>
      </div>

      <div style={{ ...card, display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div>
          <label style={{ fontSize: 13, color: 'var(--muted)', display: 'block', marginBottom: 6 }}>
            Titre de la réunion
          </label>
          <input
            value={title}
            onChange={e => setTitle(e.target.value)}
            placeholder="Ex: Réunion hebdo produit — 23 avril"
            style={{
              width: '100%', background: 'var(--bg3)', border: '1px solid var(--border)',
              borderRadius: 8, padding: '10px 14px', color: 'var(--text)', fontSize: 14,
              outline: 'none',
            }}
          />
        </div>

        <div>
          <label style={{ fontSize: 13, color: 'var(--muted)', display: 'block', marginBottom: 6 }}>
            Langue
          </label>
          <select
            value={language}
            onChange={e => setLanguage(e.target.value)}
            style={{
              background: 'var(--bg3)', border: '1px solid var(--border)',
              borderRadius: 8, padding: '10px 14px', color: 'var(--text)', fontSize: 14,
            }}
          >
            <option value="fr">Français</option>
            <option value="en">English</option>
          </select>
        </div>

        <button
          onClick={handleSubmit}
          disabled={uploading || !file}
          style={{
            background: uploading ? 'var(--bg3)' : 'var(--accent)',
            color: 'white', border: 'none', borderRadius: 8,
            padding: '12px 24px', fontSize: 15, fontWeight: 600,
            opacity: !file ? 0.5 : 1, transition: 'opacity .2s',
          }}
        >
          {uploading ? 'Upload en cours...' : 'Lancer l\'analyse'}
        </button>
      </div>
    </div>
  )
}
