from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, String, Text, DateTime, Float, JSON, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from core.config import settings

engine = create_async_engine(settings.database_url, echo=settings.debug)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    date = Column(DateTime, default=datetime.utcnow)
    duration_seconds = Column(Integer, nullable=True)
    audio_s3_key = Column(String(512), nullable=True)
    transcript = Column(Text, nullable=True)
    language = Column(String(10), default="fr")
    status = Column(String(50), default="uploaded")  # uploaded | processing | done | error
    created_at = Column(DateTime, default=datetime.utcnow)


class MeetingAnalysis(Base):
    __tablename__ = "meeting_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey("meetings.id"), nullable=False)
    summary = Column(Text, nullable=True)
    decisions = Column(JSON, default=list)       # [{"text": str, "speaker": str}]
    action_items = Column(JSON, default=list)    # [{"task": str, "owner": str, "deadline": str}]
    topics = Column(JSON, default=list)          # [{"topic": str, "weight": float}]
    sentiment_by_speaker = Column(JSON, default=dict)  # {"Speaker_0": {"positive": 0.7, ...}}
    speakers = Column(JSON, default=list)        # [{"id": str, "talk_time_pct": float}]
    minutes_report = Column(Text, nullable=True)  # compte-rendu généré par Claude
    processing_time_s = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
