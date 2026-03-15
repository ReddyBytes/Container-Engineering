# Code Examples: Multi-Container App with Docker Compose

---

## app/main.py

```python
# app/main.py
# FastAPI app with PostgreSQL persistence and Redis caching.
# Connects to services by their Compose service names (db, cache).

import os
import json
import asyncpg
import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from contextlib import asynccontextmanager

# ---------------------------------------------------------------------------
# Config — values come from .env file via Compose's env_file directive
# ---------------------------------------------------------------------------
POSTGRES_USER = os.getenv("POSTGRES_USER", "appuser")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "secret")
POSTGRES_DB = os.getenv("POSTGRES_DB", "appdb")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "db")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
REDIS_HOST = os.getenv("REDIS_HOST", "cache")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

CACHE_TTL = 60  # seconds

# ---------------------------------------------------------------------------
# App lifecycle — set up DB table and connections on startup
# ---------------------------------------------------------------------------
db_pool: Optional[asyncpg.Pool] = None
redis_client: Optional[aioredis.Redis] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool, redis_client

    # Connect to Postgres
    db_pool = await asyncpg.create_pool(
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        database=POSTGRES_DB,
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
    )

    # Create table if it doesn't exist (idempotent)
    async with db_pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                price NUMERIC(10, 2) NOT NULL
            )
        """)

    # Connect to Redis
    redis_client = aioredis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

    yield  # App is running

    # Shutdown — close connections cleanly
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
            await conn.fetchval("SELECT 1")
    except Exception as e:
        pg_status = f"error: {e}"

    try:
        await redis_client.ping()
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
            item.price,
        )
    # Invalidate cache so the next GET fetches fresh data
    await redis_client.delete("items:all")
    return dict(row)


@app.get("/items")
async def list_items():
    """
    Return all items.
    Checks Redis first (cache hit returns immediately).
    On cache miss, queries Postgres and writes result to Redis with TTL.
    """
    cached = await redis_client.get("items:all")
    if cached:
        return {"items": json.loads(cached), "source": "cache"}

    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT id, name, price FROM items ORDER BY id")

    items = [dict(row) for row in rows]
    # Cache the result for CACHE_TTL seconds
    await redis_client.setex("items:all", CACHE_TTL, json.dumps(items))
    return {"items": items, "source": "database"}


@app.get("/items/{item_id}", response_model=ItemResponse)
async def get_item(item_id: int):
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT id, name, price FROM items WHERE id = $1", item_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    return dict(row)
```

---

## requirements.txt

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
asyncpg==0.29.0
redis==5.0.4
pydantic==2.7.1
```

---

## Dockerfile

```dockerfile
# Same multi-stage pattern as Project 01.
# The builder stage installs deps; the runtime stage is clean and lean.

FROM python:3.12-slim AS builder
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip --no-cache-dir && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --no-create-home appuser

WORKDIR /app
COPY --from=builder /install /usr/local
COPY app/ ./app/
RUN chown -R appuser:appgroup /app

USER appuser
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## docker-compose.yaml

```yaml
# docker-compose.yaml
# Three-service stack: FastAPI API + PostgreSQL + Redis
# Run: docker compose up -d
# Stop: docker compose down
# Stop + delete volumes: docker compose down -v

name: myapp  # Prefix for container names. Default is the directory name.

services:

  # ---------------------------------------------------------------------------
  # PostgreSQL — persistent relational database
  # ---------------------------------------------------------------------------
  db:
    image: postgres:16-alpine
    # alpine variant is smaller and sufficient for development + production.

    environment:
      # These are picked up from the .env file (see env_file below).
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}

    env_file:
      - .env

    volumes:
      # Named volume — data persists across `docker compose down` and restarts.
      # Only `docker compose down -v` removes it.
      - postgres-data:/var/lib/postgresql/data

    # Health check using Postgres's own pg_isready utility.
    # The API service depends on this being healthy before it starts.
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s

    # Only expose Postgres on the internal network, not to the host.
    # If you need to connect with a GUI (TablePlus, DBeaver), uncomment:
    # ports:
    #   - "5432:5432"

    restart: unless-stopped
    networks:
      - app-network

  # ---------------------------------------------------------------------------
  # Redis — in-memory cache
  # ---------------------------------------------------------------------------
  cache:
    image: redis:7-alpine

    # Persist Redis data across restarts using AOF (Append Only File).
    # Remove this command if you want Redis to be purely ephemeral.
    command: redis-server --appendonly yes

    volumes:
      - redis-data:/data

    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

    restart: unless-stopped
    networks:
      - app-network

  # ---------------------------------------------------------------------------
  # API — FastAPI application
  # ---------------------------------------------------------------------------
  api:
    # Build from the local Dockerfile.
    # In CI you'd replace this with image: yourregistry/myapp:${TAG}
    build:
      context: .
      dockerfile: Dockerfile

    env_file:
      - .env

    ports:
      - "8000:8000"

    # Don't start the API until db AND cache are both healthy.
    # Without this, the API starts, tries to connect to Postgres,
    # fails because Postgres is still initializing, and crashes.
    depends_on:
      db:
        condition: service_healthy
      cache:
        condition: service_healthy

    restart: unless-stopped
    networks:
      - app-network

# ---------------------------------------------------------------------------
# Named volumes — managed by Docker, persisted across container restarts
# ---------------------------------------------------------------------------
volumes:
  postgres-data:
    # No extra config needed. Docker creates and manages this directory.
  redis-data:

# ---------------------------------------------------------------------------
# Network — all services share this bridge network
# Services can reach each other by service name (e.g., host=db, host=cache)
# ---------------------------------------------------------------------------
networks:
  app-network:
    driver: bridge
```

---

## docker-compose.override.yml

```yaml
# docker-compose.override.yml
# Development overrides — auto-merged by Compose when present.
# Do NOT use in production or CI.
# This file adds hot reload for the API service.

services:
  api:
    # Bind mount local source code into the container.
    # Changes to ./app/*.py are immediately visible inside the container.
    volumes:
      - ./app:/app/app

    # Override the CMD from Dockerfile to enable --reload.
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

    # In dev you might want more descriptive logging
    environment:
      LOG_LEVEL: debug
```

---

## .env.example

```bash
# .env.example
# Copy this to .env and fill in real values.
# Never commit .env to version control.

# PostgreSQL
POSTGRES_USER=appuser
POSTGRES_PASSWORD=changeme_use_a_real_secret
POSTGRES_DB=appdb
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Redis
REDIS_HOST=cache
REDIS_PORT=6379
```

---

## 📂 Navigation

| | |
|---|---|
| Guide | [Project_Guide.md](./Project_Guide.md) |
| Steps | [Step_by_Step.md](./Step_by_Step.md) |
| All Projects | [04_Projects/](../) |
