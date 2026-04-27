# Project 09: Build Guide

## 🟠 Minimal Hints Format

Each step has a goal, context, and exactly one `💡` hint. The hint points you at the right concept or flag — it does not give you the answer. Write the code yourself, then check against `src/solution.py` if you get stuck.

---

## Step 1 — Write the ChromaDB service in docker-compose.yml

**Goal:** Define a `chromadb` service that:
- Uses the official `chromadb/chroma` image
- Exposes port 8001
- Mounts the `chroma_data` named volume to `/chroma/chroma` inside the container
- Has a health check that polls the ChromaDB heartbeat endpoint

**Context:** ChromaDB's HTTP server listens on port 8000 inside the container by default. You'll map it to 8001 on the host to avoid collisions with FastAPI on 8000. The volume path `/chroma/chroma` is where the official image writes its persistence files.

**💡 Hint:** Look up the `healthcheck` key in docker-compose.yml — it takes `test`, `interval`, `timeout`, and `retries`. The test command is `curl -f http://localhost:8000/api/v1/heartbeat`.

---

## Step 2 — Write the FastAPI app with /query and /health

**Goal:** In `src/starter.py`, implement the two endpoints:
- `GET /health` — returns `{"status": "ok", "chromadb": "connected"}` if ChromaDB is reachable, otherwise `503`
- `POST /query` — accepts `{"question": "..."}`, queries the ChromaDB collection, returns top-3 results with a generated answer

**Context:** The ChromaDB Python client in HTTP mode connects to the server container using the service name as hostname. The collection name should be configurable via an environment variable so the worker and API use the same name.

**💡 Hint:** `chromadb.HttpClient(host=os.environ["CHROMA_HOST"], port=int(os.environ["CHROMA_PORT"]))` — put this in a startup function, not at module level, so the app doesn't crash if ChromaDB isn't up yet when the module loads.

---

## Step 3 — Write the ingestion worker script

**Goal:** Write `src/ingest.py` (or extend `starter.py`) to:
- Walk `/documents` looking for `.pdf` and `.txt` files
- Load each file, split into chunks (≤500 chars, 50-char overlap)
- Embed each chunk using `sentence-transformers` (model: `all-MiniLM-L6-v2`)
- Upsert chunks into a ChromaDB collection with document ID and source metadata
- Print progress and exit with code 0 on success, code 1 on error

**Context:** The worker is a batch script, not a server. It runs, does its job, and exits. Docker Compose's `restart: no` (the default) means it won't loop forever. Use deterministic IDs for upsert so re-running the worker doesn't create duplicate embeddings.

**💡 Hint:** `collection.upsert(ids=[...], embeddings=[...], documents=[...], metadatas=[...])` — the `ids` list must be unique strings. A good ID pattern is `f"{filename}_{chunk_index}"`.

---

## Step 4 — Write the Dockerfile for the FastAPI service

**Goal:** Write `Dockerfile.api` with a **multi-stage build**:
- Stage 1 (`builder`): install all Python deps from `requirements.txt` into a venv
- Stage 2 (`runtime`): copy only the venv and the app code, run as a non-root user

**Context:** `sentence-transformers` pulls in torch, which is large. A multi-stage build ensures you don't ship build tools in the final image. The runtime stage should be as lean as possible.

**💡 Hint:** In the builder stage, use `pip install --no-cache-dir -r requirements.txt --target /install` — then in the runtime stage, `COPY --from=builder /install /usr/local/lib/python3.12/site-packages`.

---

## Step 5 — Write the Dockerfile for the ingestion worker

**Goal:** Write `Dockerfile.ingestor`. It shares most dependencies with the API, so it should reuse the same builder stage.

**Context:** Both services need `sentence-transformers` and `chromadb`. The difference is the entrypoint: the API runs uvicorn; the worker runs the ingestion script. You can use a single multi-stage `Dockerfile` with a build argument to select the entrypoint, or two Dockerfiles that share a common base image.

**💡 Hint:** Use `ARG ENTRYPOINT_CMD` and `CMD ["sh", "-c", "${ENTRYPOINT_CMD}"]` — set the arg differently for each service in docker-compose.yml with the `build.args` key.

---

## Step 6 — Wire up docker-compose.yml with all three services

**Goal:** Complete `docker-compose.yml` with:
- `chromadb` service (from Step 1)
- `fastapi` service: depends_on chromadb with `condition: service_healthy`, passes `CHROMA_HOST=chromadb`, `CHROMA_PORT=8000`, `COLLECTION_NAME` env vars
- `ingestor` service: mounts `documents` volume, depends_on chromadb healthy, `restart: no` (or a `profiles:` key so it doesn't start automatically)
- Named volumes section at the bottom: `chroma_data` and `documents`
- All services on a custom bridge network

**Context:** The `profiles` key is a cleaner pattern for worker containers. With `profiles: ["ingest"]`, the worker only starts when you explicitly run `docker compose --profile ingest up`. This prevents it from running every time you do `docker compose up`.

**💡 Hint:** `condition: service_healthy` in `depends_on` requires the dependency to have a `healthcheck` defined. If the healthcheck is missing, Docker Compose silently falls back to `service_started` and you lose the ordering guarantee.

---

## Step 7 — Test the full pipeline

**Goal:** Prove the system works end to end:

1. Drop a PDF into `./documents/` on your host (it bind-mounts to the `documents` volume)
2. Ingest it: `docker compose --profile ingest up ingestor`
3. Start the stack: `docker compose up chromadb fastapi -d`
4. Health check: `curl http://localhost:8000/health`
5. Query: `curl -X POST http://localhost:8000/query -H "Content-Type: application/json" -d '{"question": "What is this document about?"}'`
6. Restart everything and confirm the data is still there: `docker compose down && docker compose up -d && curl http://localhost:8000/health`

**Context:** Step 6 is the persistence test. If you see empty results after restarting, the volume isn't mounted correctly.

**💡 Hint:** `docker volume inspect <volume_name>` shows you the actual path on disk where the data lives. If it's `/var/lib/docker/volumes/.../_data` and that directory has files after ingestion, your volume is working correctly.

---

## Full Solution

If you're stuck on implementation details, the complete working solution is at:

```
src/solution.py
```

It includes the FastAPI app, ingestion worker, ChromaDB client setup, and working example `docker-compose.yml` embedded as a string at the bottom of the file.

---

## 📂 Navigation

⬅️ **Prev:** [02_ARCHITECTURE.md](./02_ARCHITECTURE.md) &nbsp;&nbsp; ➡️ **Next:** [04_RECAP.md](./04_RECAP.md)

**Section:** [05 Capstone Projects](../) &nbsp;&nbsp; **Repo:** [Container-Engineering](../../README.md)
