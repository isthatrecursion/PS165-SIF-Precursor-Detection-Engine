"""
SIH165 — SIF Precursor Detection Engine
FastAPI Application Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import reports, ingest, decisions, dashboard, audit, active_learning, score
from app.db.database import init_db
from app.core.config import settings

app = FastAPI(
    title="SIH165 — SIF Precursor Detection Engine",
    description=(
        "AI/NLP engine to detect Serious Injury & Fatality (SIF) precursors "
        "in industrial safety reports. Supports unsafe act, unsafe condition, "
        "and near-miss report triage for HSE officers and leadership."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS (allow frontend dev server) ──────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Startup: initialise database ──────────────────────────────────────────────
@app.on_event("startup")
async def on_startup():
    await init_db()

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(ingest.router,          prefix="/api/v1", tags=["Ingestion"])
app.include_router(reports.router,         prefix="/api/v1", tags=["Reports"])
app.include_router(decisions.router,       prefix="/api/v1", tags=["Officer Decisions"])
app.include_router(dashboard.router,       prefix="/api/v1", tags=["Leadership Dashboard"])
app.include_router(audit.router,           prefix="/api/v1", tags=["Audit Log"])
app.include_router(active_learning.router, prefix="/api/v1", tags=["Active Learning"])
app.include_router(score.router,           prefix="/api/v1", tags=["Stage 2 Scoring"])

# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "service": "SIH165 SIF Precursor Engine", "version": "0.1.0"}
