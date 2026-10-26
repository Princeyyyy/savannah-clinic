import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.core.config import settings
from app.core.exceptions import DomainException
from app.api.v1.api import api_router
from app.db.init_db import init_db
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database schema is created and initial doctors are seeded on application startup
    try:
        init_db()
    except Exception as e:
        print(f"Warning: Database initialization error on startup: {e}")
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="""
    # Savannah Informatics — Clinic Booking System API
    
    A RESTful backend for managing doctor appointments in a small clinic environment.
    
    ### Key Features:
    * **Doctor Availability:** Dynamic 30-minute slot calculation based on weekly schedules.
    * **Strict Concurrency Protection:** Partial unique index prevents double-booking race conditions.
    * **Appointment Lifecycle:** Atomic booking, cancellation with reason, and rescheduling.
    * **Advance Scheduling & Patient History:** 1-hour advance notice booking protection & chronological patient upcoming appointments.
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handler for Domain Exceptions
@app.exception_handler(DomainException)
async def domain_exception_handler(request: Request, exc: DomainException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


# Mount API Router
app.include_router(api_router, prefix=settings.API_V1_STR)


# Health check endpoint
@app.get("/health", tags=["Health"], summary="Health check & database connectivity probe")
def health_check():
    """Verify service status and database connectivity."""
    engine_dialect = engine.dialect.name
    db_environment = "Local (SQLite)" if engine_dialect == "sqlite" else "Render Cloud (PostgreSQL)"
    db_status = "connected"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
        return JSONResponse(
            status_code=503,
            content={
                "status": "degraded",
                "database": {
                    "status": db_status,
                    "engine": engine_dialect,
                    "environment": db_environment
                }
            }
        )

    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "database": {
            "status": db_status,
            "engine": engine_dialect,
            "environment": db_environment
        }
    }


# Static dashboard serving
static_dir = Path(__file__).resolve().parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def serve_dashboard():
        html_file = static_dir / "index.html"
        return html_file.read_text(encoding="utf-8")
