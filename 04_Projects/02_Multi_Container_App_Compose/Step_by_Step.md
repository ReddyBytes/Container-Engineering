# Step-by-Step: Multi-Container App with Docker Compose

---

## Step 1 — Set Up Project Structure

Create the directory layout:

```bash
mkdir -p app
touch app/main.py Dockerfile requirements.txt docker-compose.yaml .env
```

Copy `.env.example` to `.env` and fill in values (see Step 4).

---

## Step 2 — Write the FastAPI App

Create `app/main.py` with endpoints that use both Postgres and Redis. See Code_Example.md for the full file.

The key behaviors:
- `POST /items` — writes a new item to Postgres
- `GET /items` — checks Redis first; on cache miss, queries Postgres, then writes result to Redis with a 60s TTL
- `GET /health` — verifies both DB and Redis connections are live

Install dependencies (for local development only — Docker handles this in CI):

```bash
# Optional: run locally
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

---

## Step 3 — Write docker-compose.yaml

Create `docker-compose.yaml` (see Code_Example.md for the full annotated file).

Three services:
- `db` — PostgreSQL with a named volume and a pg_isready healthcheck
- `cache` — Redis with a redis-cli ping healthcheck
- `api` — your FastAPI app, waits for both db and cache to be healthy before starting

---

## Step 4 — Configure the .env File

Create `.env` from the example template:

```bash
cp .env.example .env
```

Edit `.env` with your values:

```
POSTGRES_USER=appuser
POSTGRES_PASSWORD=supersecret
POSTGRES_DB=appdb
POSTGRES_HOST=db
POSTGRES_PORT=5432
REDIS_HOST=cache
REDIS_PORT=6379
```

The service names `db` and `cache` are the DNS names Compose assigns on the shared network. The API container resolves them by name.

**Never commit `.env` to git.** Add it to `.gitignore`:

```bash
echo ".env" >> .gitignore
```

---

## Step 5 — Start Everything

```bash
docker compose up -d
```

**Expected output:**
```
[+] Running 4/4
 ✔ Network 02_app-network           Created
 ✔ Container 02-db-1                Started
 ✔ Container 02-cache-1             Started
 ✔ Container 02-api-1               Started
```

Compose starts `db` and `cache` first, waits for them to be healthy, then starts `api`. This is `depends_on` with `condition: service_healthy` at work.

---

## Step 6 — Check Status

```bash
docker compose ps
```

**Expected:**
```
NAME            IMAGE              COMMAND                  SERVICE   STATUS         PORTS
02-api-1        02-api             "uvicorn app.main:ap…"   api       Up (healthy)   0.0.0.0:8000->8000/tcp
02-cache-1      redis:7-alpine     "docker-entrypoint.s…"   cache     Up (healthy)   6379/tcp
02-db-1         postgres:16-alpine "docker-entrypoint.s…"   db        Up (healthy)   5432/tcp
```

All three containers should show `Up (healthy)`. If `api` shows `Up` but not `(healthy)`, wait 10 seconds and re-run — the startup health check takes a moment.

If any container is `Up (unhealthy)`, check logs:

```bash
docker compose logs db
docker compose logs cache
docker compose logs api
```

---

## Step 7 — Test the API

Create an item:

```bash
curl -X POST http://localhost:8000/items \
  -H "Content-Type: application/json" \
  -d '{"name": "keyboard", "price": 149.99}'
```

**Expected:**
```json
{"id": 1, "name": "keyboard", "price": 149.99}
```

Create another:

```bash
curl -X POST http://localhost:8000/items \
  -H "Content-Type: application/json" \
  -d '{"name": "monitor", "price": 399.00}'
```

Fetch all items (first request — cache miss, hits Postgres):

```bash
curl http://localhost:8000/items
```

**Expected:**
```json
{"items": [{"id": 1, "name": "keyboard", "price": 149.99}, {"id": 2, "name": "monitor", "price": 399.0}], "source": "database"}
```

Fetch again immediately (cache hit — response from Redis):

```bash
curl http://localhost:8000/items
```

**Expected:**
```json
{"items": [...], "source": "cache"}
```

The `source` field tells you where the data came from. After 60 seconds the Redis TTL expires and the next request hits Postgres again.

Check health:

```bash
curl http://localhost:8000/health
```

**Expected:**
```json
{"status": "ok", "postgres": "connected", "redis": "connected"}
```

---

## Step 8 — View Logs

Follow logs from all services simultaneously:

```bash
docker compose logs -f
```

Follow a single service:

```bash
docker compose logs -f api
```

**Expected output (api logs):**
```
02-api-1  | INFO:     Started server process [1]
02-api-1  | INFO:     Application startup complete.
02-api-1  | INFO:     172.20.0.1:52304 - "POST /items HTTP/1.1" 201 Created
02-api-1  | INFO:     172.20.0.1:52305 - "GET /items HTTP/1.1" 200 OK
```

Exit log streaming with `Ctrl+C`.

---

## Step 9 — Stop the Stack

```bash
docker compose down
```

**Expected:**
```
[+] Running 4/4
 ✔ Container 02-api-1     Removed
 ✔ Container 02-cache-1   Removed
 ✔ Container 02-db-1      Removed
 ✔ Network 02_app-network  Removed
```

Note: `docker compose down` does **not** delete named volumes. Your Postgres data is still there.

---

## Step 10 — Verify Postgres Data Survives Restart

Bring everything back up:

```bash
docker compose up -d
```

Wait for health checks to pass, then fetch items:

```bash
curl http://localhost:8000/items
```

**Expected:**
```json
{"items": [{"id": 1, "name": "keyboard", "price": 149.99}, {"id": 2, "name": "monitor", "price": 399.0}], "source": "database"}
```

Your items are still there. The Postgres data persisted in the `postgres-data` named volume across the restart.

To actually destroy the data (volume included):

```bash
docker compose down -v
```

The `-v` flag removes named volumes. Use this carefully — it's permanent.

Inspect the volume:

```bash
docker volume ls
docker volume inspect 02_postgres-data
```

---

## Step 11 — Dev Mode with docker-compose.override.yml

Create `docker-compose.override.yml` (see Code_Example.md). It adds two things to the `api` service:

1. A bind mount of `./app` into `/app/app` — code changes appear in the container instantly
2. Overrides the command to start uvicorn with `--reload`

When the override file exists, Compose merges it automatically:

```bash
docker compose up -d
```

Edit `app/main.py` — add a comment, change a response message. Watch the api container reload:

```bash
docker compose logs -f api
```

**Expected:**
```
02-api-1  | WARNING:  StatReload detected changes in 'app/main.py'. Reloading...
02-api-1  | INFO:     Application startup complete.
```

Your change is live without rebuilding the image.

In CI or production, never use the override file. It's for local development only.

---

## Cleanup

```bash
docker compose down -v
docker rmi 02-api
```

---

## 📂 Navigation

| | |
|---|---|
| Guide | [Project_Guide.md](./Project_Guide.md) |
| Code | [Code_Example.md](./Code_Example.md) |
| All Projects | [04_Projects/](../) |
