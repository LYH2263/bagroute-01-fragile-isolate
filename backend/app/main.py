from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.router import api_router
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.services.seed import seed_if_empty

# 既有库增量列（create_all 不会改已有表）；ADD COLUMN IF NOT EXISTS 幂等
_EXTRA_COLUMNS = [
    "ALTER TABLE subscriber_stops ADD COLUMN IF NOT EXISTS is_fragile BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE pack_bags ADD COLUMN IF NOT EXISTS kind VARCHAR(20) NOT NULL DEFAULT 'normal'",
    "ALTER TABLE pack_bags ADD COLUMN IF NOT EXISTS split_reason VARCHAR(20)",
    "ALTER TABLE bag_items ADD COLUMN IF NOT EXISTS is_fragile BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE reject_records ADD COLUMN IF NOT EXISTS reason_code VARCHAR(30) NOT NULL DEFAULT 'over_limit'",
]


def ensure_schema() -> None:
    with engine.begin() as conn:
        for ddl in _EXTRA_COLUMNS:
            conn.execute(text(ddl))


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_schema()
    if settings.seed_on_empty:
        db = SessionLocal()
        try:
            seed_if_empty(db)
        finally:
            db.close()
    yield


app = FastAPI(title="BagRoute", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix="/api")
