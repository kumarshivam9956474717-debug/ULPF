from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.api import api_router


from app.services.syslog.manager import syslog_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Enforce active air-gap egress controls if configured
    if settings.AIR_GAPPED_MODE:
        try:
            from app.core.airgap import install_airgap_guard
            install_airgap_guard()
        except Exception:
            pass

    # Application startup: ensure database tables exist, load active profiles, and bootstrap admin
    try:
        from app.core.database import init_db, SessionLocal
        init_db()
        from app.services.parsers.configurable import load_active_profiles_into_registry
        from app.services.auth_bootstrap import init_admin_bootstrap
        db = SessionLocal()
        try:
            load_active_profiles_into_registry(db)
            init_admin_bootstrap(db)
        finally:
            db.close()
    except Exception:
        pass

    # Start syslog listeners if enabled
    if settings.SYSLOG_ENABLED:
        await syslog_manager.start()
    yield
    # Application shutdown: stop syslog listeners gracefully
    if syslog_manager.is_running:
        await syslog_manager.stop()



app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Universal Log Pre-processing Framework (ULPF) - Vendor-agnostic, lossless perimeter log processing engine.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response

# Cross-Origin Resource Sharing (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app|http://localhost:.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include v1 API router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root_redirect():
    return {
        "framework": "Universal Log Pre-processing Framework (ULPF)",
        "version": settings.VERSION,
        "health_endpoint": f"{settings.API_V1_PREFIX}/health",
        "air_gapped_mode": settings.AIR_GAPPED_MODE
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=settings.DEBUG
    )
