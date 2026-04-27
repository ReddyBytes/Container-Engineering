# Project 09: Containerize a RAG System

## 🟠 Minimal Hints · 6 hours

---

## The Problem

You've built a **Retrieval-Augmented Generation (RAG)** pipeline that runs beautifully as a local Python script. You point it at a folder of PDFs, it embeds them into a vector store, and you can ask questions against the documents. It works great on your machine.

Then someone else needs to use it. You zip up the folder and send it. They're missing `sentence-transformers`. You send a `requirements.txt`. Now the ChromaDB data path is wrong on their OS. Three hours later nothing runs.

This is the "works on my machine" problem, and containers solve it completely.

---

## Your Mission

Take a working RAG pipeline and package it as **three containers** that anyone can spin up with a single `docker compose up`:

- **API container** — a FastAPI service that accepts natural language queries and returns answers
- **ChromaDB container** — a vector database running in HTTP server mode, persisting its index to a named volume
- **Ingestion worker** — a one-shot container that reads documents from a shared volume, embeds them, and loads them into ChromaDB

When you're done, a teammate can clone your repo, drop PDFs into a `documents/` folder, run `docker compose up`, and start querying immediately — no Python environment setup, no path issues, no "which version of torch do I need?"

---

## Skills You'll Practice

- **Multi-container networking** — FastAPI talks to ChromaDB over Docker's internal DNS, not localhost
- **Named volumes for persistence** — the vector index survives container restarts
- **Worker pattern** — a short-lived container that does a job and exits, separate from long-lived services
- **Health checks and depends_on** — ChromaDB must be ready before FastAPI tries to connect
- **ChromaDB HTTP mode** — running Chroma as a server (not embedded) so multiple containers can share it

---

## What You're Building

```
                  ┌──────────────────────────────────────────┐
                  │          docker-compose network           │
                  │                                           │
  HTTP query      │  ┌─────────────┐      ┌───────────────┐  │
  ──────────────► │  │  fastapi    │─────►│   chromadb    │  │
  port 8000       │  │  :8000      │      │   :8001       │  │
                  │  └─────────────┘      └───────┬───────┘  │
                  │                               │           │
                  │  ┌─────────────┐      volume: chroma_data │
                  │  │  ingestor   │──────────────┘           │
                  │  │  (worker)   │                          │
                  │  └──────┬──────┘                          │
                  │         │                                  │
                  │  volume: documents                        │
                  └──────────────────────────────────────────┘
```

---

## Prerequisites

| Skill | Where to review |
|---|---|
| Docker Compose | [02_Multi_Container_App_Compose](../../05_Capstone_Projects/02_Multi_Container_App_Compose/03_GUIDE.md) |
| Multi-stage Dockerfiles | [11_Multi_Stage_Builds](../../01_Docker/11_Multi_Stage_Builds/Theory.md) |
| RAG concepts | Basic understanding of embeddings and vector search |
| FastAPI | Familiarity with route handlers and Pydantic models |

---

## Acceptance Criteria

Your solution passes when:

1. `docker compose up chromadb` starts cleanly and the health check passes
2. `docker compose run ingestor` loads all PDFs from the `documents/` volume into ChromaDB
3. `docker compose up fastapi` starts and `/health` returns `{"status": "ok"}`
4. `curl -X POST localhost:8000/query -d '{"question":"..."}'` returns a real answer drawn from the ingested documents
5. Stopping and restarting all containers does not lose any ingested data (volume persistence)
6. The FastAPI container does not start until ChromaDB passes its health check

---

## Difficulty: 🟠 Minimal Hints

The guide gives you one `💡` hint per step — a nudge in the right direction, not the answer. The full working solution lives in `src/solution.py` if you get stuck, but try each step yourself first.

Time estimate: **6 hours** for someone comfortable with Docker and Python.

---

## 📂 Navigation

⬅️ **Prev:** [08 — E-Commerce API on K8s](../08_Ecommerce_API_K8s/01_MISSION.md) &nbsp;&nbsp; ➡️ **Next:** [10 — AI Agent K8s Microservice](../10_AI_Agent_K8s_Microservice/01_MISSION.md)

**Section:** [05 Capstone Projects](../) &nbsp;&nbsp; **Repo:** [Container-Engineering](../../README.md)
