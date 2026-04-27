# 02 — Architecture: Multi-Container App with Docker Compose

---

## 🗺️ System Overview

Think of Docker Compose like a stage manager for a play. The actors (containers) each have their roles, their props (volumes), and their cues (depends_on health checks). The stage manager calls "places" in the right order — Postgres first, then Redis, then the API — and holds the curtain until each actor is ready.

Without Compose, you would have to manually start each container, wire them to a shared network, pass connection strings, and remember the right startup order every single time.

---

## 🖥️ Runtime Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                   Docker Compose Network                     │
│                    (app-network, bridge)                     │
│                                                              │
│   ┌──────────────┐     ┌──────────────┐  ┌──────────────┐  │
│   │   api        │────▶│   db         │  │   cache      │  │
│   │ FastAPI:8000 │     │ Postgres:5432│  │  Redis:6379  │  │
│   │              │────▶│              │  │              │  │
│   └──────┬───────┘     └──────┬───────┘  └──────────────┘  │
│          │                    │                              │
│          │            named volume:                          │
│          │            postgres-data                          │
└──────────┼─────────────────────────────────────────────────┘
           │ port 8000
      localhost:8000
           │
      curl / browser
```

Services communicate by service name (`db`, `cache`). Compose creates DNS entries on the shared network automatically. The API container reaches Postgres at hostname `db` — no IP addresses to manage.

---

## 🔄 Request Flow

```
GET /items (first request — cold cache)
    │
    ▼
FastAPI (api container)
    │
    ├──▶ Redis GET "items:all"  →  (nil) — cache miss
    │
    ├──▶ Postgres SELECT * FROM items
    │         │
    │         └──▶ Returns rows
    │
    ├──▶ Redis SETEX "items:all" 60 <json>  ←  write to cache
    │
    └──▶ Response: {"items": [...], "source": "database"}


GET /items (second request — warm cache, within 60s)
    │
    ▼
FastAPI
    │
    ├──▶ Redis GET "items:all"  →  <cached json>  — cache hit
    │
    └──▶ Response: {"items": [...], "source": "cache"}
```

---

## 🚀 Startup Ordering

```
docker compose up -d
        │
        ├──▶ Start db (Postgres)
        │         │
        │         └──▶ Wait for healthcheck: pg_isready passes
        │
        ├──▶ Start cache (Redis)
        │         │
        │         └──▶ Wait for healthcheck: redis-cli ping returns PONG
        │
        └──▶ Start api (only after db AND cache are healthy)
                  │
                  └──▶ FastAPI connects to Postgres and Redis on startup
```

The `depends_on` with `condition: service_healthy` enforces this order. Without it, the API would start and immediately crash trying to connect to a Postgres that has not finished initializing.

---

## 🗂️ Folder Structure

```
02_Multi_Container_App_Compose/
├── app/
│   └── main.py                     # FastAPI app (Postgres + Redis)
├── docker-compose.yaml             # Production-style Compose file
├── docker-compose.override.yml     # Dev overrides (hot reload)
├── Dockerfile                      # Multi-stage build for the API
├── requirements.txt                # Python dependencies
├── .env.example                    # Template — copy to .env
└── src/
    ├── starter.py                  # Scaffolded app — fill in TODOs
    └── solution.py                 # Complete working solution
```

---

## 🧱 Tech Stack

| Component | Technology | Purpose |
|---|---|---|
| Web framework | FastAPI | Request routing, async handlers |
| ASGI server | Uvicorn | Runs FastAPI |
| Database | PostgreSQL 16 | Persistent relational storage |
| Database driver | asyncpg | Async Postgres client |
| Cache | Redis 7 | In-memory TTL cache |
| Cache client | redis[asyncio] | Async Redis client |
| Data validation | Pydantic v2 | Request/response schemas |
| Orchestration | Docker Compose v2 | Multi-container lifecycle |

---

## 🔒 Volume Anatomy

```
Named volume: postgres-data
    │
    └── Managed by Docker at /var/lib/docker/volumes/myapp_postgres-data/
        │
        └── Survives: docker compose down
            Deleted by: docker compose down -v

Named volume: redis-data
    └── Persists Redis AOF log across restarts
```

---

⬅️ **Prev:** [01 — Dockerize a Python App](../01_Dockerize_a_Python_App/01_MISSION.md) &nbsp;&nbsp; ➡️ **Next:** [03 — Deploy App to Kubernetes](../03_Deploy_App_to_Kubernetes/01_MISSION.md)

**Section:** [05 Capstone Projects](../) &nbsp;&nbsp; **Repo:** [Container-Engineering](../../README.md)
