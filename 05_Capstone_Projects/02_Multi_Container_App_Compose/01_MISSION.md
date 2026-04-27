# 01 — Multi-Container App with Docker Compose

> Difficulty: 🟡 Partially Guided

---

## 🎯 The Mission

A single container works for a toy app. Real applications are never a single container. You need a web server, a database to persist data, a cache to keep the database from getting hammered on every request. Running these by hand — starting them in the right order, wiring up networking, passing secrets — gets painful fast.

**Docker Compose** solves this. It lets you describe your entire application stack in a single YAML file and bring everything up with one command: `docker compose up -d`.

In this project you will build a three-service stack: a FastAPI backend, a PostgreSQL database for persistence, and a Redis cache that makes repeated reads fast.

---

## 🏗️ What You'll Build

A three-service application stack:

- **api** — FastAPI app backed by Postgres with Redis caching GET responses for 60 seconds
- **db** — PostgreSQL 16, data persisted to a named Docker volume
- **cache** — Redis 7, caches the item list with a 60-second TTL

The whole stack starts with `docker compose up -d` and tears down with `docker compose down`.

---

## 🛠️ Skills Practiced

| Skill | Why it matters |
|---|---|
| Multi-service `docker-compose.yaml` | Defines an entire stack as code |
| `depends_on` with `condition: service_healthy` | Correct startup ordering |
| Health checks on all services | Orchestrator-visible readiness |
| Named volumes | Data persists across container restarts |
| `.env` files | Secrets out of source control |
| `docker-compose.override.yml` | Dev-only hot reload without polluting production config |
| Inter-container networking | Services talk by name, not IP |

---

## 📋 Prerequisites

| Tool | Version | Check command |
|---|---|---|
| Docker | 24+ | `docker --version` |
| Docker Compose v2 | bundled with Docker Desktop | `docker compose version` |

Compose v2 is included with Docker Desktop. On Linux, install the `docker-compose-plugin` package.

---

## 🗺️ Step Summary

1. Set up the project structure
2. Write `app/main.py` — FastAPI app using Postgres and Redis
3. Write `docker-compose.yaml` — three services with health checks and volumes
4. Configure `.env` with real credentials
5. Start the stack and verify all services are healthy
6. Test the API — create items, observe Redis caching
7. View live logs across services
8. Stop and restart — verify Postgres data survived
9. Add `docker-compose.override.yml` for hot reload in development

---

⬅️ **Prev:** [01 — Dockerize a Python App](../01_Dockerize_a_Python_App/01_MISSION.md) &nbsp;&nbsp; ➡️ **Next:** [03 — Deploy App to Kubernetes](../03_Deploy_App_to_Kubernetes/01_MISSION.md)

**Section:** [05 Capstone Projects](../) &nbsp;&nbsp; **Repo:** [Container-Engineering](../../README.md)
