from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.api.v1.api import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown."""
    # Initialize DB tables on startup (in dev; use Alembic in prod)
    from app.db.base import Base
    from app.db.session import engine
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="CashFlow API",
    description=(
        "Complete Cash Flow Management System — "
        "Safe-to-Spend, Forecasting, Commitments, Receivables, "
        "Credit Cards, Purchase Orders, Decision Engine, Alerts, "
        "Plaid / QuickBooks / Shopify / Amazon integrations."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow localhost in dev and any Vercel preview URL in prod
_cors_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
]
if settings.FRONTEND_URL:
    _cors_origins.append(settings.FRONTEND_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok", "app": "CashFlow", "version": "1.0.0"}
