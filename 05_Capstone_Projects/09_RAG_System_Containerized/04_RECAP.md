# Project 09: Recap

## What You Built

You took a single-machine RAG script and turned it into a **portable, multi-container system** that any developer can run with one command. Along the way you touched every major Docker Compose feature: named volumes, health checks, service dependencies, worker patterns, and multi-stage builds.

The shape of this project — a database container, a stateless API container, and a short-lived worker — appears over and over in real infrastructure. Swap ChromaDB for Postgres, swap the ingestor for a migration runner, and you have a standard web application stack. The patterns transfer directly.

---

## Key Concepts

**Multi-container networking**

Docker Compose creates a private bridge network for your stack. Each service name becomes a DNS hostname. `fastapi` can reach `chromadb` at `http://chromadb:8000` without any hardcoded IP addresses. This is **service discovery** at the container level.

**ChromaDB HTTP mode vs embedded mode**

Embedded mode opens a local SQLite file. Only one process can safely write to it, and you can't share it across containers over a mount. **HTTP mode** runs ChromaDB as a server — any number of clients connect over the network, and ChromaDB handles concurrency internally. This is the correct architecture for any multi-container setup.

**Named volumes for persistence**

```
  chroma_data volume:

  Container start   Container stop   Container restart
       │                  │                │
       ▼                  ▼                ▼
  writes to          data stays       reads back
  /chroma/chroma     on host disk     same data
```

The volume outlives any individual container. The `docker compose down` command stops containers but does not delete volumes unless you pass `-v`. This is intentional — data persistence must be an explicit opt-in to destroy.

**Worker pattern**

A worker container does a finite job and exits with code 0. It is fundamentally different from a server container, which runs until you stop it. In Docker Compose, `restart: no` and `profiles:` work together to make workers explicit: they don't start automatically, they don't restart on failure (so you can inspect the logs), and they're not part of the default `up` command.

**Health checks and depends_on**

`condition: service_healthy` is a hard guarantee: Compose will not start a dependent service until the dependency's health check has passed. Without it, a race condition exists — FastAPI might try to connect to ChromaDB before ChromaDB's HTTP server is listening, causing a crash-restart loop.

---

## Architecture Diagram

```
  docker compose up

  1. chromadb starts → health check polls every 5s → passes after ~10s
  2. fastapi starts  → connects to chromadb:8000 on lifespan startup
  3. ingestor runs   → (only with --profile ingest) → exits 0 after loading docs

  Runtime state:

  [Client] ──GET /health──► [fastapi:8000]
  [Client] ──POST /query──► [fastapi:8000] ──query──► [chromadb:8000]
                                                             │
                                                     [chroma_data volume]
                                                     (HNSW index on disk)
```

---

## Extend It

**Add nginx as a reverse proxy**

Put an nginx container in front of FastAPI. nginx handles TLS termination, rate limiting, and serving static assets. FastAPI handles only business logic. This is the standard three-tier web architecture applied to containers.

```yaml
  nginx:
    image: nginx:alpine
    ports: ["443:443"]
    depends_on: [fastapi]
```

**Deploy to Kubernetes with a PVC**

In K8s, named volumes become **PersistentVolumeClaims**. The ChromaDB deployment gets a PVC that survives pod restarts. The ingestion worker becomes a K8s **Job** — a one-shot workload that runs to completion and is tracked by the cluster.

**Add Prometheus metrics**

Instrument FastAPI with `prometheus-client`. Expose `/metrics`. Track:
- `rag_query_duration_seconds` — latency histogram per endpoint
- `rag_chromadb_documents_total` — gauge for indexed document count
- `rag_query_requests_total` — counter by status code

This makes the system **observable** — you can alert when query latency spikes or when the document count drops unexpectedly.

---

## Lessons Learned

| Problem | Root cause | Fix |
|---|---|---|
| FastAPI crashes on startup with `ConnectionRefused` | No health check on chromadb, depends_on uses `service_started` | Add healthcheck + `condition: service_healthy` |
| Re-running ingestor creates duplicate chunks | IDs are random (e.g. `uuid4()`) instead of deterministic | Use `hashlib.md5(filename + chunk_index)` as ID, call `upsert` not `add` |
| ChromaDB data lost on restart | Volume not declared in docker-compose.yml or path is wrong | Check `/chroma/chroma` is the exact mount path for the official image |
| Worker keeps restarting | Default restart policy is `unless-stopped` | Set `restart: "no"` on worker services |

---

## 📂 Navigation

⬅️ **Prev:** [08 — E-Commerce API on K8s](../08_Ecommerce_API_K8s/01_MISSION.md) &nbsp;&nbsp; ➡️ **Next:** [10 — AI Agent K8s Microservice](../10_AI_Agent_K8s_Microservice/01_MISSION.md)

**Section:** [05 Capstone Projects](../) &nbsp;&nbsp; **Repo:** [Container-Engineering](../../README.md)
