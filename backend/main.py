from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from api.routes import meetings, analysis, rag, health
from core.config import settings
from db.database import engine, Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
    await engine.dispose()


app = FastAPI(
    title="MeetingMind AI",
    description="Intelligent Meeting Analytics Platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(meetings.router, prefix="/api/meetings", tags=["meetings"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
app.include_router(rag.router, prefix="/api/rag", tags=["rag"])
