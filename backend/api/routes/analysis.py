"""Routes /api/analysis — agrégats et stats globales."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from db.database import get_db, Meeting, MeetingAnalysis

router = APIRouter()

@router.get("/stats")
async def global_stats(db: AsyncSession = Depends(get_db)):
    total = await db.scalar(select(func.count()).select_from(Meeting))
    done = await db.scalar(
        select(func.count()).select_from(Meeting).where(Meeting.status == "done")
    )
    return {
        "total_meetings": total or 0,
        "processed": done or 0,
        "pending": (total or 0) - (done or 0),
    }
