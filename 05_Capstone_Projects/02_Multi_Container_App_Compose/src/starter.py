# starter.py
# Project 02: Multi-Container App with Docker Compose — scaffolded app
#
# This is the FastAPI application that will run inside the `api` container.
# It connects to Postgres (service name: db) and Redis (service name: cache).
#
# Fill in each TODO. When all endpoints work, move this to app/main.py
# and build with: docker compose up -d

import os
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from contextlib import asynccontextmanager

# ---------------------------------------------------------------------------
# Config — populated from .env via Compose env_file directive
# ---------------------------------------------------------------------------
POSTGRES_USER = os.getenv("POSTGRES_USER", "appuser")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "secret")
POSTGRES_DB = os.getenv("POSTGRES_DB", "appdb")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "db")        # ← Compose service name
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
REDIS_HOST = os.getenv("REDIS_HOST", "cache")           # ← Compose service name
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

CACHE_TTL = 60  # seconds

# ---------------------------------------------------------------------------
# Connection pool globals — set during lifespan startup
# ---------------------------------------------------------------------------
db_pool = None   # TODO: type hint as Optional[asyncpg.Pool]
redis_client = None  # TODO: type hint as Optional[aioredis.Redis]


# TODO: Implement the lifespan context manager.
# On startup:
#   1. Create an asyncpg connection pool
#   2. Create the "items" table (id SERIAL PRIMARY KEY, name TEXT, price NUMERIC)
#   3. Create a Redis client
# On shutdown (after yield):
#   4. Close the db_pool
#   5. Close the redis_client
@asynccontextmanager
async def lifespan(app):
    global db_pool, redis_client
    # TODO: implement startup and shutdown
    yield


app = FastAPI(title="Compose Demo API", version="1.0.0", lifespan=lifespan)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class ItemCreate(BaseModel):
    # TODO: add name: str and price: float fields
    pass


class ItemResponse(BaseModel):
    # TODO: add id: int, name: str, price: float fields
    pass


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    # TODO:
    # 1. Try: async with db_pool.acquire() as conn: await conn.fetchval("SELECT 1")
    # 2. Try: await redis_client.ping()
    # 3. Return {"status": "ok"/"degraded", "postgres": "connected"/"error: ...", "redis": ...}
    pass


@app.post("/items", response_model=ItemResponse, status_code=201)
async def create_item(item: ItemCreate):
    # TODO:
    # 1. INSERT into items (name, price) RETURNING id, name, price
    # 2. Delete the Redis cache key "items:all" (so next GET is fresh)
    # 3. Return the inserted row as a dict
    pass


@app.get("/items")
async def list_items():
    # TODO:
    # 1. GET "items:all" from Redis
    # 2. If hit: return {"items": json.loads(cached), "source": "cache"}
    # 3. If miss: SELECT id, name, price FROM items ORDER BY id
    # 4. SETEX "items:all" with CACHE_TTL and json.dumps(items)
    # 5. Return {"items": items, "source": "database"}
    pass


@app.get("/items/{item_id}", response_model=ItemResponse)
async def get_item(item_id: int):
    # TODO:
    # 1. SELECT id, name, price FROM items WHERE id = $1
    # 2. Return dict(row) if found
    # 3. Raise HTTPException(404) if not found
    pass
