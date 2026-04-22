from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown (cleanup if needed)


app = FastAPI(
    title="AI Diary API",
    description="Інтелектуальний застосунок для ведення особистого щоденника",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS for Vue.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
from app.api.auth import router as auth_router
from app.api.buffer import router as buffer_router
from app.api.entries import router as entries_router
from app.api.highlights import router as highlights_router
from app.api.webhook import router as webhook_router
from app.api.sse import router as sse_router

app.include_router(auth_router)
app.include_router(buffer_router)
app.include_router(entries_router)
app.include_router(highlights_router)
app.include_router(webhook_router)
app.include_router(sse_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
