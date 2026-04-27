# solution.py
# Project 02: Multi-Container App with Docker Compose — complete solution
#
# In the real project, this file lives at app/main.py.
# Copy it there and run: docker compose up -d

import os
import json
import asyncpg
import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from contextlib import asynccontextmanager

# ---------------------------------------------------------------------------
# Config — values injected by Compose from .env via env_file directive
# ---------------------------------------------------------------------------
POSTGRES_USER = os.getenv("POSTGRES_USER", "appuser")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "secret")
POSTGRES_DB = os.getenv("POSTGRES_DB", "appdb")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "db")        # ← Compose service DNS name
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
REDIS_HOST = os.getenv("REDIS_HOST", "cache")           # ← Compose service DNS name
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

CACHE_TTL = 60  # seconds — how long Redis holds the items list

# ---------------------------------------------------------------------------
# App lifecycle — create connection pools on startup, close on shutdown
# ---------------------------------------------------------------------------
db_pool: Optional[asyncpg.Pool] = None
redis_client: Optional[aioredis.Redis] = None


@asynccontextmanager
async def lifespan(app: "FastAPI"):
    global db_pool, redis_client

    # Connect to Postgres using a connection pool (reuse connections across requests)
    db_pool = await asyncpg.create_pool(
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        database=POSTGRES_DB,
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
    )

    # Create the items table if it does not already exist (idempotent migration)
    async with db_pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id    SERIAL PRIMARY KEY,
                name  TEXT NOT NULL,
                price NUMERIC(10, 2) NOT NULL
            )
        """)

    # Connect to Redis — decode_responses=True so we get strings back, not bytes
    redis_client = aioredis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        decode_responses=True,  # ← returns str instead of bytes
    )

    yield  # App is running — request handlers execute here

    # Shutdown — close connections cleanly before the container stops
    await db_pool.close()
    await redis_client.close()


app = FastAPI(title="Compose Demo API", version="1.0.0", lifespan=lifespan)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class ItemCreate(BaseModel):
    name: str
    price: float


class ItemResponse(BaseModel):
    id: int
    name: str
    price: float


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    """Check that both Postgres and Redis are reachable."""
    pg_status = "connected"
    redis_status = "connected"

    try:
        async with db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")  # ← minimal roundtrip to verify DB is alive
    except Exception as e:
        pg_status = f"error: {e}"

    try:
        await redis_client.ping()  # ← sends PING, expects PONG
    except Exception as e:
        redis_status = f"error: {e}"

    overall = "ok" if pg_status == "connected" and redis_status == "connected" else "degraded"
    return {"status": overall, "postgres": pg_status, "redis": redis_status}


@app.post("/items", response_model=ItemResponse, status_code=201)
async def create_item(item: ItemCreate):
    """Insert an item into Postgres. Invalidate the Redis cache."""
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO items (name, price) VALUES ($1, $2) RETURNING id, name, price",
            item.name,
            item.price,  # asyncpg uses $1, $2 positional placeholders (not %s)
        )
    # Invalidate cache — the list has changed, so the next GET must hit Postgres
    await redis_client.delete("items:all")
    return dict(row)


@app.get("/items")
async def list_items():
    """
    Return all items.
    Redis cache is checked first. On a miss, Postgres is queried and the result
    is written to Redis with a TTL so subsequent requests are fast.
    """
    cached = await redis_client.get("items:all")
    if cached:
        return {"items": json.loads(cached), "source": "cache"}  # ← fast path

    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT id, name, price FROM items ORDER BY id")

    items = [dict(row) for row in rows]  # ← asyncpg returns Record objects, convert to dicts
    await redis_client.setex("items:all", CACHE_TTL, json.dumps(items))  # ← set with expiry
    return {"items": items, "source": "database"}


@app.get("/items/{item_id}", response_model=ItemResponse)
async def get_item(item_id: int):
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, name, price FROM items WHERE id = $1", item_id
        )
    if not row:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    return dict(row)
