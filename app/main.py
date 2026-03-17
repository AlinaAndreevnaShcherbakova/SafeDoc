from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.db.mongo import connect_mongo, disconnect_mongo
from app.db.postgres import SessionLocal, engine
from app.db.init_db import create_schema, seed_defaults


@asynccontextmanager
async def lifespan(_: FastAPI):
    await create_schema(engine)
    async with SessionLocal() as session:
        await seed_defaults(session)

    try:
        await connect_mongo()
    except Exception:
        # MongoDB в MVP опциональна: без нее работает local fallback для файлов.
        pass

    yield

    await disconnect_mongo()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)
