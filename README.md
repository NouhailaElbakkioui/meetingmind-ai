# MeetingMind AI 🎙️

**Intelligent Meeting Analytics Platform**

## Screenshots

### 🔍 AI Search — Semantic queries on meeting history
![Recherche IA](https://raw.githubusercontent.com/NouhailaElbakkioui/meetingmind-ai/main/docs/search.png)

### 📤 Upload — Analyze a meeting audio file
![Upload](https://raw.githubusercontent.com/NouhailaElbakkioui/meetingmind-ai/main/docs/upload.png)

Pipeline NLP end-to-end : upload un audio de réunion → transcription automatique, extraction de décisions et actions, analyse de sentiment par participant, RAG sémantique sur l'historique, génération de compte-rendu professionnel par Claude.

---

## Stack

| Composant | Technologie |
|---|---|
| Transcription | OpenAI Whisper |
| Diarisation | pyannote.audio 3.1 |
| Résumé | facebook/bart-large-cnn |
| Extraction décisions/actions | Anthropic Claude (claude-sonnet-4) |
| Sentiment | cardiffnlp/twitter-roberta-base-sentiment |
| Topics | BERTopic |
| RAG | ChromaDB + sentence-transformers |
| LLM orchestration | LangChain + Anthropic |
| MLOps | MLflow |
| Backend | FastAPI + PostgreSQL (async) |
| Frontend | React + Recharts + Vite |
| Infra | Docker Compose |
| Cloud | AWS S3 |

---

## Démarrage rapide

### Prérequis
- Docker + Docker Compose
- Python 3.11+ (pour dev local sans Docker)
- Une clé API Anthropic (https://console.anthropic.com)

### Installation

```bash
git clone https://github.com/ton-repo/meetingmind-ai
cd meetingmind-ai

# Config environnement
cp .env.example .env
# → Ouvre .env et ajoute ta clé ANTHROPIC_API_KEY

# Lancement
docker-compose up --build
```

### Accès

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| API Backend | http://localhost:8000 |
| Swagger docs | http://localhost:8000/docs |
| MLflow | http://localhost:5000 |
| ChromaDB | http://localhost:8001 |

---

## Utilisation

### 1. Upload une réunion
Accède à http://localhost:3000/upload, glisse un fichier audio (MP3/WAV/M4A), donne un titre et lance l'analyse.

### 2. Voir l'analyse
Une fois le traitement terminé (1-5 min selon la durée), clique sur la réunion dans le Dashboard pour voir :
- Résumé automatique
- Décisions prises
- Plan d'action avec responsables
- Analyse de sentiment par participant
- Compte-rendu professionnel généré par Claude

### 3. Requête RAG
Accède à "Recherche IA" et pose des questions sur l'historique :
```
"Quelles décisions ont été prises sur le projet X ?"
"Qui est responsable de la migration AWS ?"
"Résume les actions en attente de l'équipe produit"
```

### 4. Monitoring MLflow
Ouvre http://localhost:5000 pour consulter :
- Temps de traitement par réunion
- Nombre de décisions/actions extraites
- Qualité des requêtes RAG (relevance score)
- Artifacts : transcripts et comptes-rendus générés

---

## Architecture

```
Audio/Texte réunion
      ↓
Transcription + Diarisation (Whisper + pyannote)
      ↓
NLP Pipeline (résumé, décisions, actions, sentiment, topics)
      ↓
RAG : ChromaDB + embeddings → requêtes sémantiques
      ↓
LLM : Claude génère le compte-rendu professionnel
      ↓
Dashboard React + API FastAPI + MLflow monitoring
```

---

## Structure du projet

```
meetingmind/
├── backend/
│   ├── api/routes/        # FastAPI routes
│   ├── core/              # Config, settings
│   ├── db/                # SQLAlchemy models
│   ├── nlp/               # Pipeline NLP complet
│   ├── rag/               # ChromaDB store
│   ├── services/          # S3, MLflow
│   └── main.py
├── frontend/
│   └── src/
│       ├── pages/         # Dashboard, Upload, Detail, Search
│       └── components/    # Layout
├── docker-compose.yml
└── .env.example
```

---

## Dev local sans Docker

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Lancer PostgreSQL et ChromaDB séparément ou via Docker :
docker-compose up postgres chromadb mlflow -d

uvicorn main:app --reload
```

```bash
cd frontend
npm install
npm run dev
```

---

## Notes diarisation

La diarisation pyannote.audio requiert d'accepter les conditions d'utilisation sur HuggingFace :
1. https://hf.co/pyannote/speaker-diarization-3.1
2. https://hf.co/pyannote/segmentation-3.0

Puis ajoute ton token dans `.env` : `HF_TOKEN=hf_...`

Sans token, le système utilise un fallback mono-speaker.

---

## Licence

MIT
