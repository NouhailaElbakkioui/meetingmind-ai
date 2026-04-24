"""
RAG — Retrieval-Augmented Generation sur l'historique des réunions.

Permet des requêtes comme :
  "Quelles décisions ont été prises sur le projet Alpha depuis janvier ?"
  "Qui a été assigné à la migration AWS ?"
  "Résume les dernières réunions de l'équipe produit"
"""

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
import anthropic
from datetime import datetime

from core.config import settings


# ---------------------------------------------------------------------------
# Client ChromaDB
# ---------------------------------------------------------------------------

def get_chroma_client() -> chromadb.HttpClient:
    return chromadb.HttpClient(
        host=settings.chroma_host,
        port=settings.chroma_port,
        settings=ChromaSettings(anonymized_telemetry=False),
    )


def get_collection(client: chromadb.HttpClient):
    return client.get_or_create_collection(
        name=settings.chroma_collection,
        metadata={"hnsw:space": "cosine"},
    )


# ---------------------------------------------------------------------------
# Modèle d'embedding
# ---------------------------------------------------------------------------

_embedding_model = None


def get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    return _embedding_model


def embed(texts: list[str]) -> list[list[float]]:
    model = get_embedding_model()
    return model.encode(texts, normalize_embeddings=True).tolist()


# ---------------------------------------------------------------------------
# Indexation d'une réunion
# ---------------------------------------------------------------------------

def index_meeting(
    meeting_id: str,
    transcript: str,
    summary: str,
    decisions: list[dict],
    action_items: list[dict],
    date: datetime,
    title: str,
) -> int:
    """
    Découpe la réunion en chunks sémantiques et les indexe dans ChromaDB.
    Retourne le nombre de chunks indexés.
    """
    client = get_chroma_client()
    collection = get_collection(client)

    chunks = []
    metadatas = []
    ids = []

    base_meta = {
        "meeting_id": str(meeting_id),
        "title": title,
        "date": date.isoformat(),
    }

    # Chunk 1 : résumé
    chunks.append(f"Résumé de la réunion '{title}' ({date.date()}) : {summary}")
    metadatas.append({**base_meta, "chunk_type": "summary"})
    ids.append(f"{meeting_id}_summary")

    # Chunks décisions
    for i, dec in enumerate(decisions):
        text = f"Décision prise lors de '{title}' ({date.date()}) : {dec.get('text', '')} — par {dec.get('speaker', '?')}"
        chunks.append(text)
        metadatas.append({**base_meta, "chunk_type": "decision"})
        ids.append(f"{meeting_id}_decision_{i}")

    # Chunks action items
    for i, act in enumerate(action_items):
        text = f"Action assignée lors de '{title}' ({date.date()}) : {act.get('task', '')} → responsable : {act.get('owner', '?')} — deadline : {act.get('deadline', '?')}"
        chunks.append(text)
        metadatas.append({**base_meta, "chunk_type": "action_item"})
        ids.append(f"{meeting_id}_action_{i}")

    # Chunks transcript (fenêtres de 500 caractères avec chevauchement)
    window, overlap = 500, 100
    for i in range(0, len(transcript), window - overlap):
        chunk_text = transcript[i: i + window].strip()
        if len(chunk_text) < 50:
            continue
        chunks.append(chunk_text)
        metadatas.append({**base_meta, "chunk_type": "transcript"})
        ids.append(f"{meeting_id}_transcript_{i}")

    if not chunks:
        return 0

    embeddings = embed(chunks)
    collection.upsert(documents=chunks, embeddings=embeddings, metadatas=metadatas, ids=ids)
    return len(chunks)


# ---------------------------------------------------------------------------
# Requête RAG
# ---------------------------------------------------------------------------

_RAG_SYSTEM = """Tu es un assistant expert en analyse de réunions professionnelles.
Tu réponds aux questions en te basant UNIQUEMENT sur les extraits de réunions fournis.
Si l'information n'est pas dans les extraits, dis-le clairement.
Cite les réunions sources (titre + date) dans ta réponse.
Réponds en français sauf si la question est posée en anglais."""

_RAG_USER = """Question : {question}

Extraits de réunions pertinents :
{context}

Réponds de façon concise et précise."""


def query(question: str, n_results: int = 8, filter_meeting_id: str | None = None) -> dict:
    """
    Requête sémantique sur l'historique des réunions.
    Retourne la réponse générée + les sources.
    """
    client_chroma = get_chroma_client()
    collection = get_collection(client_chroma)

    query_embedding = embed([question])[0]

    where = {"meeting_id": filter_meeting_id} if filter_meeting_id else None

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    docs = results["documents"][0]
    metas = results["metadatas"][0]
    distances = results["distances"][0]

    if not docs:
        return {"answer": "Aucune réunion indexée ne correspond à cette question.", "sources": []}

    # Filtrer les résultats trop éloignés (distance cosine > 0.7)
    filtered = [(d, m, dist) for d, m, dist in zip(docs, metas, distances) if dist < 0.7]
    if not filtered:
        filtered = list(zip(docs[:3], metas[:3], distances[:3]))

    context = "\n\n".join(
        f"[{m.get('title', '?')} — {m.get('date', '?')[:10]}] {d}"
        for d, m, _ in filtered
    )

    sources = [
        {
            "meeting_id": m.get("meeting_id"),
            "title": m.get("title"),
            "date": m.get("date", "")[:10],
            "chunk_type": m.get("chunk_type"),
            "relevance": round(1 - dist, 3),
        }
        for _, m, dist in filtered
    ]

    # Dédupliquer les sources par meeting
    seen = set()
    unique_sources = []
    for s in sources:
        if s["meeting_id"] not in seen:
            seen.add(s["meeting_id"])
            unique_sources.append(s)

    # Générer la réponse avec Claude
    anthropic_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    message = anthropic_client.messages.create(
        model=settings.anthropic_model,
        max_tokens=1024,
        system=_RAG_SYSTEM,
        messages=[{
            "role": "user",
            "content": _RAG_USER.format(question=question, context=context),
        }],
    )

    return {
        "answer": message.content[0].text,
        "sources": unique_sources,
    }
