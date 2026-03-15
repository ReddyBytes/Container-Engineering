# Project 02: Multi-Container App with Docker Compose

Running one container is easy. Real applications are never one container. You have a web server, a database, a cache, maybe a message queue. Managing these by hand — starting them in the right order, wiring up networking, passing secrets — gets painful fast. Docker Compose solves this by letting you describe your entire application stack in a single YAML file and bring it up with one command.

In this project you'll build a FastAPI backend connected to PostgreSQL for persistence and Redis for caching, all orchestrated with Compose.

---

## What You'll Build

A three-service application stack:

- **api** — FastAPI app with endpoints for creating and retrieving items, backed by Postgres and with Redis caching the GET responses
- **db** — PostgreSQL 16, data persisted to a named Docker volume
- **cache** — Redis 7, used to cache item list responses for 60 seconds

The whole stack starts with `docker compose up -d` and tears down with `docker compose down`.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Docker Compose Network                     │
│                    (app-network, bridge)                     │
│                                                              │
│   ┌──────────────┐     ┌──────────────┐  ┌──────────────┐  │
│   │   api        │────▶│   db         │  │   cache      │  │
│   │ FastAPI:8000 │     │ Postgres:5432│  │  Redis:6379  │  │
│   │              │────▶│              │  │              │  │
│   └──────┬───────┘     └──────────────┘  └──────────────┘  │
│          │                    │                              │
│          │            named volume:                          │
│          │            postgres-data                          │
└──────────┼─────────────────────────────────────────────────┘
           │ port 8000
      localhost:8000
           │
      curl / browser
```

Services communicate by service name (`db`, `cache`). Compose creates a shared network automatically.

---

## Skills Practiced

- Writing multi-service `docker-compose.yaml`
- Service dependencies with `depends_on` and `condition: service_healthy`
- Health checks for every service
- Named volumes for data persistence
- Environment variables and `.env` files
- Using `docker-compose.override.yml` for development (hot reload)
- Reading logs across multiple services
- Inter-container networking by service name

---

## Prerequisites

| Tool            | Version | Check command              |
|-----------------|---------|----------------------------|
| Docker          | 24+     | `docker --version`         |
| Docker Compose  | v2      | `docker compose version`   |

Compose v2 is bundled with Docker Desktop. On Linux, install the `docker-compose-plugin` package.

---

## Folder Structure

```
02_Multi_Container_App_Compose/
├── app/
│   └── main.py                     # FastAPI app (Postgres + Redis)
├── docker-compose.yaml             # Production-style Compose file
├── docker-compose.override.yml     # Dev overrides (hot reload)
├── Dockerfile                      # Multi-stage build for the API
├── requirements.txt                # Python dependencies
├── .env.example                    # Template for secrets
├── Project_Guide.md                # This file
├── Step_by_Step.md                 # Numbered walkthrough
└── Code_Example.md                 # Full working code
```

---

## What You'll Build — Step Summary

1. Set up the project structure and write the FastAPI app
2. Write `docker-compose.yaml` with all three services, healthchecks, and volumes
3. Configure `.env` with real credentials
4. Start the stack and verify all services are healthy
5. Test the API — create items, read them, watch Redis caching in action
6. View live logs across all services
7. Restart and verify Postgres data survives (named volume)
8. Use `docker-compose.override.yml` to add hot reload during development

---

## 📂 Navigation

| | |
|---|---|
| Next | [Step_by_Step.md](./Step_by_Step.md) |
| Code | [Code_Example.md](./Code_Example.md) |
| All Projects | [04_Projects/](../) |
