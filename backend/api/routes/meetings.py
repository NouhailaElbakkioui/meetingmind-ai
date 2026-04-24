"""Routes /api/meetings — upload audio, liste, détail."""

import aiofiles
import uuid
import asyncio
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from db.database import get_db, Meeting, MeetingAnalysis
from services.s3_service import upload_audio
from nlp.pipeline import run_pipeline
from rag.chroma_store import index_meeting
from services.mlflow_tracker import log_pipeline_run

router = APIRouter()

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".mp4"}
MAX_FILE_SIZE_MB = 100


# ---------------------------------------------------------------------------
# Schémas de réponse
# ---------------------------------------------------------------------------

class MeetingResponse(BaseModel):
    id: str
    title: str
    date: str
    status: str
    duration_seconds: int | None
    language: str

    class Config:
        from_attributes = True


class MeetingDetailResponse(MeetingResponse):
    analysis: dict | None = None


# ---------------------------------------------------------------------------
# POST /api/meetings/upload
# ---------------------------------------------------------------------------

@router.post("/upload", response_model=MeetingResponse, status_code=201)
async def upload_meeting(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    language: str = Form("fr"),
    db: AsyncSession = Depends(get_db),
):
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Format non supporté. Formats acceptés : {ALLOWED_EXTENSIONS}")

    meeting_id = uuid.uuid4()
    tmp_path = f"C:/tmp/audio/{meeting_id}{ext}"
    Path("C:/tmp/audio").mkdir(parents=True, exist_ok=True)

    # Sauvegarde locale
    async with aiofiles.open(tmp_path, "wb") as f:
        content = await file.read()
        if len(content) > MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(413, "Fichier trop volumineux (max 100 MB)")
        await f.write(content)

    # Création en base
    meeting = Meeting(
        id=meeting_id,
        title=title,
        language=language,
        status="uploaded",
        date=datetime.utcnow(),
    )
    db.add(meeting)
    await db.commit()
    await db.refresh(meeting)

    # Traitement en background
    background_tasks.add_task(
        process_meeting_async, str(meeting_id), tmp_path, file.filename, language
    )

    return MeetingResponse(
        id=str(meeting.id),
        title=meeting.title,
        date=meeting.date.isoformat(),
        status=meeting.status,
        duration_seconds=meeting.duration_seconds,
        language=meeting.language,
    )


async def process_meeting_async(meeting_id: str, tmp_path: str, filename: str, language: str):
    """Traitement asynchrone : pipeline NLP + S3 + ChromaDB + MLflow."""
    from db.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        meeting = await db.get(Meeting, uuid.UUID(meeting_id))
        if not meeting:
            return

        meeting.status = "processing"
        await db.commit()

        try:
            # Upload S3 (optionnel — skip si pas de clés AWS)
            try:
                s3_key = upload_audio(tmp_path, meeting_id, filename)
                meeting.audio_s3_key = s3_key
            except Exception:
                meeting.audio_s3_key = tmp_path  # stockage local en dev

            # Pipeline NLP (CPU-bound — run dans executor)
            loop = asyncio.get_event_loop()
            nlp_result = await loop.run_in_executor(
                None, run_pipeline, tmp_path, language
            )

            # Sauvegarde analyse
            analysis = MeetingAnalysis(
                meeting_id=uuid.UUID(meeting_id),
                summary=nlp_result.summary,
                decisions=[{"text": d.text, "speaker": d.speaker} for d in nlp_result.decisions],
                action_items=[{"task": a.task, "owner": a.owner, "deadline": a.deadline} for a in nlp_result.action_items],
                topics=nlp_result.topics,
                sentiment_by_speaker=nlp_result.sentiment_by_speaker,
                speakers=nlp_result.speakers,
                minutes_report=nlp_result.minutes_report,
                processing_time_s=nlp_result.processing_time_s,
            )
            db.add(analysis)

            meeting.transcript = nlp_result.transcript
            meeting.status = "done"
            await db.commit()

            # Indexation RAG
            await loop.run_in_executor(
                None,
                index_meeting,
                meeting_id,
                nlp_result.transcript,
                nlp_result.summary,
                [{"text": d.text, "speaker": d.speaker} for d in nlp_result.decisions],
                [{"task": a.task, "owner": a.owner} for a in nlp_result.action_items],
                meeting.date,
                meeting.title,
            )

            # MLflow
            await loop.run_in_executor(None, log_pipeline_run, nlp_result, meeting_id, meeting.title)

        except Exception as e:
            meeting.status = "error"
            await db.commit()
            raise


# ---------------------------------------------------------------------------
# GET /api/meetings
# ---------------------------------------------------------------------------

@router.get("/", response_model=list[MeetingResponse])
async def list_meetings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Meeting).order_by(Meeting.date.desc()).limit(50))
    meetings = result.scalars().all()
    return [
        MeetingResponse(
            id=str(m.id),
            title=m.title,
            date=m.date.isoformat(),
            status=m.status,
            duration_seconds=m.duration_seconds,
            language=m.language,
        )
        for m in meetings
    ]


# ---------------------------------------------------------------------------
# GET /api/meetings/{id}
# ---------------------------------------------------------------------------

@router.get("/{meeting_id}", response_model=MeetingDetailResponse)
async def get_meeting(meeting_id: str, db: AsyncSession = Depends(get_db)):
    meeting = await db.get(Meeting, uuid.UUID(meeting_id))
    if not meeting:
        raise HTTPException(404, "Réunion introuvable")

    result = await db.execute(
        select(MeetingAnalysis).where(MeetingAnalysis.meeting_id == uuid.UUID(meeting_id))
    )
    analysis = result.scalar_one_or_none()

    return MeetingDetailResponse(
        id=str(meeting.id),
        title=meeting.title,
        date=meeting.date.isoformat(),
        status=meeting.status,
        duration_seconds=meeting.duration_seconds,
        language=meeting.language,
        analysis={
            "summary": analysis.summary,
            "decisions": analysis.decisions,
            "action_items": analysis.action_items,
            "topics": analysis.topics,
            "sentiment_by_speaker": analysis.sentiment_by_speaker,
            "speakers": analysis.speakers,
            "minutes_report": analysis.minutes_report,
            "processing_time_s": analysis.processing_time_s,
        } if analysis else None,
    )
