"""Routes /api/rag — requêtes sémantiques sur l'historique."""

import time
from fastapi import APIRouter
from pydantic import BaseModel

from rag.chroma_store import query
from services.mlflow_tracker import log_rag_query

router = APIRouter()


class RAGRequest(BaseModel):
    question: str
    meeting_id: str | None = None  # optionnel : filtrer une réunion


class RAGResponse(BaseModel):
    answer: str
    sources: list[dict]
    latency_s: float


@router.post("/query", response_model=RAGResponse)
async def rag_query(req: RAGRequest):
    start = time.time()
    result = query(req.question, filter_meeting_id=req.meeting_id)
    latency = round(time.time() - start, 3)

    # MLflow logging
    avg_rel = (
        sum(s["relevance"] for s in result["sources"]) / len(result["sources"])
        if result["sources"] else 0.0
    )
    log_rag_query(req.question, len(result["sources"]), avg_rel, latency)

    return RAGResponse(
        answer=result["answer"],
        sources=result["sources"],
        latency_s=latency,
    )
