import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.api.chat import router as chat_router
from app.api.orders import router as orders_router
from app.api.policy import router as policy_router
from app.api.escalations import router as escalations_router

app = FastAPI(
    title=settings.APP_NAME,
    description="Agentic Customer Support Assistant for Trendly — Fashion Retailer",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(chat_router)
app.include_router(orders_router)
app.include_router(policy_router)
app.include_router(escalations_router)

# Mount frontend static directory if exists
STATIC_DIR = Path(__file__).resolve().parent / "static"
if not STATIC_DIR.exists():
    STATIC_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
async def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {
        "status": "online",
        "service": settings.APP_NAME,
        "llm_provider": settings.LLM_PROVIDER,
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "llm_provider": settings.LLM_PROVIDER,
        "reference_date": settings.REFERENCE_DATE
    }
