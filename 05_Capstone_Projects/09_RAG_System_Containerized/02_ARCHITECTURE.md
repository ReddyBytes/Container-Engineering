# Project 09: Architecture

---

## System Overview

Think of this system like a library with three staff members:

- The **librarian** (FastAPI) sits at the front desk answering questions. She doesn't store any books herself — she consults the card catalog.
- The **card catalog** (ChromaDB) is the vector index. It holds embeddings and knows which document chunks are relevant to a given query.
- The **acquisitions clerk** (ingestion worker) is a part-time role. She processes new books, generates index cards for each passage, and files them in the catalog. Once she's done, she goes home.

What makes this containerized version interesting is that all three talk over a private network, and the catalog data outlives any individual container restart.

---

## Architecture Diagram

```
  ┌────────────────────────────────────────────────────────────────┐
  │                    docker-compose network: rag-net             │
  │                                                                │
  │   External traffic                                             │
  │   port 8000 ──────► ┌───────────────────────────────────┐     │
  │                      │      fastapi container            │     │
  │                      │      image: rag-api               │     │
  │                      │      POST /query                  │     │
  │                      │      GET  /health                 │     │
  │                      └──────────────┬────────────────────┘     │
  │                                     │ HTTP to chromadb:8001     │
  │                                     ▼                           │
  │                      ┌───────────────────────────────────┐     │
  │                      │      chromadb container           │     │
  │                      │      image: chromadb/chroma       │     │
  │                      │      port 8001                    │     │
  │                      │      health: GET /api/v1/heartbeat│     │
  │                      └──────────────┬────────────────────┘     │
  │                                     │                           │
  │                              volume: chroma_data                │
  │                              (vector index persisted here)      │
  │                                                                 │
  │   ┌───────────────────────────────────────┐                    │
  │   │      ingestor container (worker)       │                    │
  │   │      image: rag-ingestor               │                    │
  │   │      runs once, then exits with code 0 │                    │
  │   │      reads /documents/*.pdf            │                    │
  │   │      embeds + upserts to chromadb:8001 │                    │
  │   └─────────────────────┬─────────────────┘                    │
  │                          │                                      │
  │                   volume: documents                             │
  │                   (PDFs dropped here by user)                   │
  └────────────────────────────────────────────────────────────────┘
```

---

## Volume Strategy

**Two named volumes** solve two distinct problems:

| Volume | Purpose | Shared By |
|---|---|---|
| `chroma_data` | Persist the vector index across restarts | chromadb (write), fastapi (read via HTTP) |
| `documents` | Stage PDFs for ingestion | ingestor (read) |

The key insight: FastAPI never mounts `chroma_data` directly. It talks to ChromaDB over HTTP. This means you can scale FastAPI to multiple replicas without any file-locking issues on the vector index.

```
  chroma_data volume lifecycle:

  First run:   chromadb writes fresh index to /chroma/chroma (inside container)
  Restart:     chromadb mounts same volume → index is already there → no re-ingestion needed
  Scale-out:   only ONE chromadb container writes; fastapi replicas all query over HTTP
```

---

## Service Dependency Order

Startup order matters. ChromaDB takes a few seconds to initialize its HTTP server. If FastAPI connects before ChromaDB is ready, the client throws a `ConnectionRefused` on startup.

```
  docker compose up order:

  1. chromadb starts
        │
        └── health check: GET /api/v1/heartbeat → 200 OK
                │
                └── (passes after ~3-5 seconds)
                        │
  2. fastapi starts ◄───┘  (depends_on: chromadb condition: service_healthy)
        │
        └── connects to chromadb:8001 on startup

  3. ingestor (run separately or as a one-shot profile)
        │
        └── can start any time after chromadb is healthy
        └── exits 0 when ingestion is complete
```

The `depends_on` with `condition: service_healthy` is the Docker Compose feature that enforces this. Without it, FastAPI might start, fail to connect, and crash — causing confusing restart loops.

---

## Tech Stack

| Component | Technology | Why |
|---|---|---|
| API | FastAPI + uvicorn | Async, fast, OpenAPI docs for free |
| Vector DB | `chromadb/chroma` (official image) | Supports HTTP server mode natively |
| Embeddings | `sentence-transformers` (all-MiniLM-L6-v2) | Runs locally, no API key needed |
| PDF loading | `langchain-community` PyPDFLoader | Handles multi-page PDFs, splits by page |
| Base image | `python:3.12-slim` | Small footprint, security updates |
| Compose | Docker Compose v2 | `docker compose` (not `docker-compose`) |

---

## ChromaDB HTTP Mode vs Embedded Mode

This is the most important architectural choice in the project.

**Embedded mode** (what most tutorials show):

```python
import chromadb
client = chromadb.Client()  # ← opens a local SQLite file
```

This works fine when one process owns the database. In a containerized world, two containers cannot safely share a SQLite file over a bind mount.

**HTTP mode** (what this project uses):

```python
import chromadb
client = chromadb.HttpClient(host="chromadb", port=8001)  # ← connects over network
```

ChromaDB runs as a dedicated server container. Any number of clients (FastAPI replicas, ingestion workers, notebooks) connect to it over the network. The server handles all concurrency internally.

---

## Network Naming

Docker Compose creates an internal DNS namespace. Each service name becomes a resolvable hostname:

```
  Service name "chromadb" in docker-compose.yml
  ↓
  Any container on the same network can connect to:
      http://chromadb:8001
  ↓
  Docker's internal DNS resolves "chromadb" to the container's IP
```

You never need to hardcode IP addresses. If you rename the service, update the hostname string everywhere it's referenced.

---

## 📂 Navigation

⬅️ **Prev:** [01_MISSION.md](./01_MISSION.md) &nbsp;&nbsp; ➡️ **Next:** [03_GUIDE.md](./03_GUIDE.md)

**Section:** [05 Capstone Projects](../) &nbsp;&nbsp; **Repo:** [Container-Engineering](../../README.md)
