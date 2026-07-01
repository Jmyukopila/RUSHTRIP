import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from backend.routes.airports import router as airports_router
from backend.routes.flights  import router as flights_router
from backend.routes.hotels   import router as hotels_router
from backend.routes.cars     import router as cars_router
from backend.routes.plan     import router as plan_router
from backend.routes.weather  import router as weather_router
from backend.routes.activities import router as activities_router
from core.config import settings
from core.errors import AppError, ExternalAPIError
from core.logging import setup_logging

@asynccontextmanager
async def lifespan(app: FastAPI):
    from core.http import http_client
    from core.database_cache import init_db as init_cache_db
    from core.rate_limiter import init_db as init_rate_limiter_db

    init_cache_db()
    init_rate_limiter_db()
    from loguru import logger
    logger.info("Cache persistente y rate limiter inicializados (SQLite WAL)")

    yield
    await http_client.aclose()

app = FastAPI(
    lifespan=lifespan,
    title="RushTrip API",
    description="""
    API para planificar viajes ajustados a tu presupuesto.

    Características:
    - Búsqueda de vuelos con fallback inteligente (Aviasales/Travelpayouts)
    - Búsqueda de hoteles reales (Hotels.nl) con fotos y links de reserva
    - Alquiler de coches (RapidAPI) con fallback a Localrent/EconomyBookings
    - Búsqueda de aeropuertos y ciudades
    - Plan de viaje optimizado por presupuesto
    """,
    version="1.1.0",
    contact={
        "name":  "RushTrip Support",
        "url":   "https://myrushtrip.com/contact",
        "email": "support@myrushtrip.com",
    },
    license_info={
        "name": "MIT License",
        "url":  "https://opensource.org/licenses/MIT",
    },
    openapi_tags=[
        {
            "name":        "Plan de viaje",
            "description": "Genera el plan de viaje mas ajustado a tu presupuesto"
        },
        {
            "name":        "Vuelos",
            "description": "Busqueda de vuelos con fallback inteligente por mes"
        },
        {
            "name":        "Hoteles",
            "description": "Busqueda de hoteles reales (Hotels.nl) con fotos y links de reserva"
        },
        {
            "name":        "Coches",
            "description": "Busqueda de alquiler de coches (RapidAPI / Localrent)"
        },
        {
            "name":        "Aeropuertos",
            "description": "Autocomplete de aeropuertos y ciudades"
        },
        {
            "name":        "Clima",
            "description": "Pronóstico y clima típico del destino (Open-Meteo)"
        },
        {
            "name":        "Actividades",
            "description": "Mejores actividades y atracciones del destino (OpenTripMap)"
        },
    ]
)

# ── Stripear prefijo /api para compatibilidad frontend ───────────────────
@app.middleware("http")
async def strip_api_prefix(request: Request, call_next):
    path = request.url.path
    if path.startswith("/api/"):
        request.scope["path"] = path[4:]
    elif path == "/api":
        request.scope["path"] = ""
    return await call_next(request)

# ── CORS ─────────────────────────────────────────────────────────────────
origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ── Security headers (CSP) ──────────────────────────────────────────────
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' https://tpwidg.com https://*.tpwidg.com 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https: http:; "
        "connect-src 'self' https://*.travelpayouts.com https://*.rapidapi.com"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response

# ── Rate limiting persistente (por IP, sobrevive reinicios) ────────────
from core.rate_limiter import check_rate_limit, get_remaining

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    path = request.url.path
    if path in ("/health", "/", "/docs", "/openapi.json"):
        return await call_next(request)

    # En desarrollo (DEBUG=true) no se aplica rate limiting: en local todo llega
    # desde 127.0.0.1 y unas decenas de pruebas agotan el cupo diario, devolviendo
    # 429 y rompiendo la app. Producción DEBE correr con DEBUG=false para mantener
    # la protección diaria por IP.
    if settings.debug:
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"

    allowed, remaining = check_rate_limit(client_ip, path)
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={
                "error": True,
                "code": "rate_limit",
                "detail": "Has alcanzado el límite diario de consultas. Vuelve mañana o intenta con rutas menos específicas.",
            },
        )

    response = await call_next(request)
    remaining, limit = get_remaining(client_ip, path)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Limit"] = str(limit)
    return response

# ── Inicializar logging ─────────────────────────────────────────────────
setup_logging()

# ── Exception handlers globales ─────────────────────────────────────────
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=502 if exc.code == "external_api_error" else 422,
        content={
            "error": True,
            "code": exc.code,
            "detail": exc.message,
        },
    )

@app.exception_handler(ExternalAPIError)
async def external_api_error_handler(request: Request, exc: ExternalAPIError):
    return JSONResponse(
        status_code=502,
        content={
            "error": True,
            "code": "external_api_error",
            "detail": "No pudimos consultar disponibilidad en este momento. Por favor, intenta de nuevo.",
            "provider": exc.provider,
        },
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    from loguru import logger
    logger.exception(f"Error no manejado: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "code": "internal_error",
            "detail": "Ocurrio un error inesperado. El equipo ha sido notificado.",
        },
    )

# ── Rutas API ────────────────────────────────────────────────────────────
app.include_router(plan_router)
app.include_router(airports_router)
app.include_router(flights_router)
app.include_router(hotels_router)
app.include_router(cars_router)
app.include_router(weather_router)
app.include_router(activities_router)

# ── Health check ─────────────────────────────────────────────────────────
@app.get("/health", tags=["Root"])
async def health():
    return {"status": "ok", "app": "RushTrip API", "version": "1.1.0"}

@app.get("/", tags=["Root"])
async def root():
    return {"status": "ok", "app": "RushTrip API", "version": "1.1.0", "docs": "/docs"}

# ── Frontend estatico (solo en desarrollo local) ───────────────────────
STATIC_DIR = Path(__file__).resolve().parent / "frontend" / "dist"
if STATIC_DIR.is_dir() and os.environ.get("VERCEL") is None:
    from fastapi.staticfiles import StaticFiles
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file_path = STATIC_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        index_path = STATIC_DIR / "index.html"
        if index_path.is_file():
            return FileResponse(index_path, media_type="text/html")
        return JSONResponse({"detail": "Not Found"}, status_code=404)